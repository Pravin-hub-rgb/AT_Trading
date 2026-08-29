"""Intraday backtest engine — port of `docs/2 - intraday-trading-system.md`.

Runs over historical 5-minute candles using ONLY pre-open information for
direction: the bias label for day T (computed from day T-1 by bias.py).

Course rules implemented here:
    - No entries before 9:45 (hard rule), cutoff ~11:12, nothing past 12 (S5)
    - First-candle neglect: opening candle fully consumed -> swing recounts
      from the reversal point (S4)
    - Pace-of-momentum break = S/R location; three types (S5):
        1. candle-wise   : structure break (lower high then micro-low gives way)
        2. domination    : aggressive candle consumes prior body (>=60%, S6)
        3. candle-size   : range far above session average
    - Confirmation: domination candle CLOSES + first-time continuation follows;
      one big candle alone is NOT confirmed (S5)
    - Bias overrides pattern: only bias-aligned setups are traded (S6);
      UNBIASED days are skipped in v1
    - Risk: SL = average candle size near the extreme (never at the extreme),
      target 1:3, max 2 entries/day, cost-to-cost exit after >2R travelled
      unlocks the second entry, NO trailing (S5/S6)
    - Square-off 15:15 (user setting); ambiguous candle (SL & target both
      touched) resolves conservatively as SL-first
"""

from __future__ import annotations

import pandas as pd
from collections import Counter

# --- tunable thresholds -------------------------------------------------------
ENTRY_START = "09:45"        # hard rule: no entries before this (S1/S4/S5)
OPENING_SETTLE = "09:45"     # first swing = the 9:15 -> settle initial move itself (S5/S6)
ENTRY_END = "11:12"          # cutoff for NEW entries (~S5:203)
EOD_EXIT = "15:15"           # square-off time (user setting)
MIN_CANDLES = 20             # skip thin sessions (same guard as bias.py)

BIG_CANDLE_MULT = 1.5        # pace-break type 3: range >= mult x avg session range
CONSUME_PCT = 0.60           # domination: body overlaps >= 60% of prior body (S6:17)
AVG_LOOKBACK_DAYS = 10       # avg candle size = mean range of previous <=10 sessions
FALLBACK_AVG_RANGE = 21.5    # zero-history fallback (dataset-wide qualifying mean, researched)
MICRO_PIVOT_N = 2            # half-length for intraday micro pivots (structure break)
LEVEL_TOL_MULT = 0.25        # "near level" tolerance in multiples of avg range
LEVEL_INVALID_MULT = 1.0     # close beyond level by > this x avg disarms setup
SWING_TIMEOUT_CANDLES = 12   # give up an armed confirmation hunt after this many candles
RETRO_TIMEOUT_CANDLES = 24   # retracement legs need room to complete before reversing
RETRO_LEG_MIN_BARS = 3       # counter-leg must run at least this long before reversal hunting
VOID_CONSECUTIVE = 4         # swing voided after 3-4 consecutive opposing candles (S6)
RR_TARGET = 3.0              # 1:3 general realistic expectation (S6:67)
MAX_ENTRIES = 2              # per day (S6:134 two-entry provision)
COST_TO_COST_R = 2.0         # >2R travelled then reversal -> breakeven exit (S6)
DOM_CLOSE_Q = 0.50           # domination candle must close in its direction half ("closes near the extreme", S6:36)
SWING_MIN_AVG_MULT = 1.5     # swing must span >= this x avg range before its break counts ("unusually big retracements", S5:193)
MOMENTUM_BARS = 4            # bars after entry for the immediate-momentum check (S5:36)
MOMENTUM_MIN_R = 0.0         # DISABLED: backtest showed the filter cuts winners
                             # (targets/EOD) more than it saves SLs; S5:36's '5 points'
                             # refers to option premium, not index spot. Revisit after
                             # visual chart review.
SL_AVG_MULT = 1.0            # SL distance beyond reference low/high = mult x average candle size
                             # (1.0 = course default; user experiment: decreasing fractions)

# --- experiment switches (best-combo search, BTC-backtester style) ------------
# Defaults preserve the current engine behaviour exactly.
DEFAULT_CFG = {
    "sl_mode": "avg",        # avg | avg075 | avg05 | fixed8
    "execution": "5min",     # 5min (conservative, SL-first) | 1min (color-aware precise)
    "trailing": "off",       # off (course: fixed 3R target) | ladder (R-chunk trail; disables 3R target)
    "trail_distance_r": 1.0, # ladder step size in R
    "gap_pct": 0.0027,       # |open - prev_close| beyond this fraction = gap-up/down
                             # 0.27% researched from labeled examples (Oct-Dec'25,
                             # Mar-Apr'26): separates GOOD vs noise gaps 8/9
    "first_swing_v2": False,  # use new FirstSwingEngine (port of frontend logic)
}

SL_MODE_MULT = {"avg": 1.0, "avg075": 0.75, "avg05": 0.5}
SL_MODE_FIXED = {"fixed8": 8.0}


def resolve_cfg(cfg: dict | None) -> dict:
    out = dict(DEFAULT_CFG)
    if cfg:
        for k, v in cfg.items():
            if k in out and v is not None:
                out[k] = v
    return out


EXTREME_ZONES_HIGH = {"new_high", "highs_extreme"}
EXTREME_ZONES_LOW = {"new_low", "lows_extreme"}


def gap_type_of(open_price: float, prev_close: float | None, gap_pct: float) -> str:
    """gap-up | gap-down | flat — vs previous session's close."""
    if prev_close is None or prev_close <= 0:
        return "flat"
    frac = abs(open_price - prev_close) / prev_close
    if frac <= gap_pct:
        return "flat"
    return "gap-up" if open_price > prev_close else "gap-down"


def classify_case(eff_bias: str, gap: str, extreme: str | None, swing_dir: str | None) -> str | None:
    """Map (bias, gap, extreme-zone, first-swing) -> case id from the master list."""
    if eff_bias == "bullish":
        if extreme == "highs":
            return "B7" if swing_dir == "buying" else "B8"
        if swing_dir == "buying":
            return {"gap-up": "B1", "gap-down": "B3", "flat": "B5"}.get(gap)
        return {"gap-up": "B2", "gap-down": "B4", "flat": "B6"}.get(gap)
    if eff_bias == "bearish":
        if extreme == "lows":
            return "Bc7" if swing_dir == "selling" else "Bc8"
        if swing_dir == "selling":
            return {"gap-down": "Bc1", "gap-up": "Bc3", "flat": "Bc5"}.get(gap)
        return {"gap-down": "Bc2", "gap-up": "Bc4", "flat": "Bc6"}.get(gap)
    # unbiased: first swing decides (U1/U2)
    if swing_dir == "buying":
        return "U1"
    if swing_dir == "selling":
        return "U2"
    return None


# --- helpers -------------------------------------------------------------------

def _prep_day(day: pd.DataFrame) -> list[dict]:
    """Day slice -> list of candle dicts with derived fields."""
    out = []
    for i, row in enumerate(day.reset_index(drop=True).itertuples()):
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        body_hi, body_lo = max(o, c), min(o, c)
        out.append(
            {
                "index": i,
                "time": row.timestamp.strftime("%H:%M"),
                "ts": int(row.ts),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "range": h - l,
                "body": abs(c - o),
                "color": 1 if c > o else (-1 if c < o else 0),
                "body_hi": body_hi,
                "body_lo": body_lo,
            }
        )
    return out


def _consumes(cur: dict, prev: dict) -> bool:
    """True when cur's body overlaps >= CONSUME_PCT of prev's body (S6)."""
    if prev["body"] <= 0 or cur["color"] == 0:
        return False
    overlap = min(cur["body_hi"], prev["body_hi"]) - max(cur["body_lo"], prev["body_lo"])
    return overlap / prev["body"] >= CONSUME_PCT


def _micro_pivots(candles: list[dict], upto: int, kind: str) -> list[float]:
    """Williams-fractal micro pivots (n=MICRO_PIVOT_N) fully confirmed before bar `upto`."""
    n = MICRO_PIVOT_N
    prices: list[float] = []
    for i in range(n, upto - n):
        if kind == "high":
            win_l = [c["high"] for c in candles[i - n : i]]
            win_r = [c["high"] for c in candles[i + 1 : i + n + 1]]
            if candles[i]["high"] > max(win_l) and candles[i]["high"] > max(win_r):
                prices.append(candles[i]["high"])
        else:
            win_l = [c["low"] for c in candles[i - n : i]]
            win_r = [c["low"] for c in candles[i + 1 : i + n + 1]]
            if candles[i]["low"] < min(win_l) and candles[i]["low"] < min(win_r):
                prices.append(candles[i]["low"])
    return prices


def _classify_first_swing(candles: list[dict]) -> tuple[str | None, int, list[dict]]:
    """First swing = the opening move ITSELF, from the open until 9:45.

    The market's initial run (9:15 -> settle) IS the first swing; entries
    only come later, on its break/retracement (S5: 'never inside the first
    swing', S6: 'forms around 9:45-10').

    Direction: whichever extreme printed LATE inside the window tells where
    the leg was heading at completion — low early + high late = buying;
    high early + low late = selling. Ties fall back to the window's net
    move, then to the opening candle colour.

    Returns (direction ('buying'|'selling'|None), extreme_bar_index, events).
    """
    events: list[dict] = []
    if not candles:
        return None, -1, events

    win = [c for c in candles if c["time"] < OPENING_SETTLE]
    if not win:
        win = candles[:1]

    hi_i = max(range(len(win)), key=lambda k: win[k]["high"])
    lo_i = min(range(len(win)), key=lambda k: win[k]["low"])

    if hi_i > lo_i:
        direction, seed = "buying", lo_i   # low printed first, rose into settle
    elif hi_i < lo_i:
        direction, seed = "selling", hi_i  # high printed first, fell into settle
    else:
        net = win[-1]["close"] - win[0]["open"]
        if net > 0:
            direction, seed = "buying", lo_i
        elif net < 0:
            direction, seed = "selling", hi_i
        else:
            direction = "buying" if win[0]["color"] >= 0 else "selling"
            seed = lo_i

    events.append(
        {
            "type": "swing_classified",
            "bar": seed,
            "time": candles[min(seed, len(candles) - 1)]["time"],
            "direction": direction,
        }
    )
    return direction, seed, events


    return direction, seed, events


def _classify_first_swing_v2(candles: list[dict], day_date: str) -> tuple[str | None, int, list[dict]]:
    """First-swing classification using the new FirstSwingEngine.

    Uses advanced price-action detection (continuation/reversal + chop/sustain
    confirmation). Falls back to legacy _classify_first_swing if not declared.
    """
    from datetime import datetime, timezone
    from .swing_engine import FirstSwingEngine
    from .walker import FlowCandle

    events: list[dict] = []
    if not candles:
        return None, -1, events

    flow_candles: list[FlowCandle] = []
    for c in candles:
        ts = c.get("ts", 0)
        if ts:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            dt = f"{day_date}T{c.get('time', '00:00')}:00"
        flow_candles.append(FlowCandle(
            date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"],
        ))

    eng = FirstSwingEngine()
    for g_idx, fc in enumerate(flow_candles):
        eng.process_bar(fc, g_idx)

    if not eng.declared:
        return _classify_first_swing(candles)

    direction = "buying" if eng.dir == "up" else "selling"
    seed = eng.start_idx
    events.append({
        "type": "swing_classified_v2",
        "bar": seed,
        "time": eng.start_time,
        "direction": direction,
        "engine": "FirstSwingEngine",
        "source": eng.confirm_source,
    })
    events.append({
        "type": "fs_breaks",
        "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px}
                   for b in eng.break_marks],
    })
    events.append({
        "type": "fs_segment",
        "dir": eng.dir,
        "start_idx": eng.start_idx,
        "start_px": eng.start_px,
        "end_idx": eng.end_idx,
        "end_px": eng.end_px,
        "confirmed_at_idx": eng.confirmed_at_idx,
        "confirmed_at_time": eng.confirmed_at_time,
    })
    return direction, seed, events


# --- pace break -----------------------------------------------------------------

def detect_pace_break(
    candles: list[dict],
    i: int,
    swing_dir: str,
    swing_extreme: float,
    swing_size: float | None = None,
    base_avg: float | None = None,
) -> dict | None:
    """Check whether bar i (just closed) is a pace break of the current swing.

    Returns {type, level, bar} or None. Level = S/R candidate:
      structure break -> the broken micro-pivot price,
      domination/size -> break candle's extreme (S5: 'woh candle ka low = S/R').

    swing_size: magnitude of the current leg; below SWING_MIN_AVG_MULT x avg
    the leg is noise, not a swing worth breaking (S5:193).
    base_avg: stable 10-session average candle size (see AVG_LOOKBACK_DAYS).
    """
    cur = candles[i]
    prev = candles[i - 1] if i > 0 else None
    avg = base_avg
    if cur["range"] <= 0:
        return None
    if avg and swing_size is not None and swing_size < SWING_MIN_AVG_MULT * avg:
        return None

    if swing_dir == "buying":
        opp = -1  # selling pressure breaks a buying swing
    else:
        opp = 1

    # --- type 3: candle-size (S5:92 'far above session average')
    if avg and cur["range"] >= BIG_CANDLE_MULT * avg and cur["color"] == opp:
        lvl = cur["low"] if opp == -1 else cur["high"]
        return {"type": "candle-size", "level": lvl, "bar": i}

    # --- type 2: domination (S6:102 aggressive body consumption)
    if prev and prev["body"] > 0 and prev["color"] == -opp and _consumes(cur, prev):
        lvl = cur["low"] if opp == -1 else cur["high"]
        return {"type": "domination", "level": lvl, "bar": i}

    # --- type 1: candle-wise structure break (S6:102 lower high + lows breaking)
    if avg:
        if swing_dir == "buying":
            pivots = _micro_pivots(candles, i, "low")
            made_lower_high = cur["high"] < swing_extreme
            if pivots and made_lower_high and cur["close"] < pivots[-1]:
                return {"type": "structure", "level": pivots[-1], "bar": i}
        else:
            pivots = _micro_pivots(candles, i, "high")
            made_higher_low = cur["low"] > swing_extreme
            if pivots and made_higher_low and cur["close"] > pivots[-1]:
                return {"type": "structure", "level": pivots[-1], "bar": i}

    return None


# --- day simulation ---------------------------------------------------------------

def simulate_day(
    day: pd.DataFrame,
    bias: str,
    cfg: dict | None = None,
    m1_day: pd.DataFrame | None = None,
    ctx: dict | None = None,
) -> dict:
    """Simulate one session under a fixed pre-open bias. Returns day result.

    cfg switches (see DEFAULT_CFG): sl_mode, execution, trailing, gap_pct.
    m1_day: that date's 1-minute candles (required when execution='1min').
    ctx: classification context {gap: str, extreme, avg_range: float}.
         avg_range = STABLE baseline from previous <=10 sessions
         (AVG_LOOKBACK_DAYS); falls back to FALLBACK_AVG_RANGE.
    """
    cfg = resolve_cfg(cfg)
    ctx = ctx or {}
    base_avg = float(ctx.get("avg_range") or FALLBACK_AVG_RANGE)
    result = {
        "date": str(day["timestamp"].iloc[0].date()),
        "bias": bias,
        "effective_bias": None,
        "case": None,
        "swing_direction": None,
        "trades": [],
        "events": [],
    }

    candles = _prep_day(day)
    if len(candles) < MIN_CANDLES:
        result["events"].append({"type": "skipped_thin_session", "bars": len(candles)})
        return result

    if cfg.get("first_swing_v2"):
        swing_dir, swing_start, ev = _classify_first_swing_v2(candles[: len(candles)], result["date"])
    else:
        swing_dir, swing_start, ev = _classify_first_swing(candles[: len(candles)])
    result["swing_direction"] = swing_dir
    result["events"].extend(ev)

    if bias in ("bullish", "bearish"):
        want_dir = 1 if bias == "bullish" else -1
    elif bias == "unbiased":
        # U1/U2: no overview held — the first swing itself declares the day's
        # direction ('unbiased + first swing X = take X direction', S6). U3/U5
        # (choppy/indecision) fall out naturally when setups never confirm.
        if swing_dir == "buying":
            want_dir = 1
        elif swing_dir == "selling":
            want_dir = -1
        else:
            result["events"].append({"type": "skipped_unbiased"})
            return result
        result["effective_bias"] = "bullish" if want_dir == 1 else "bearish"
        result["events"].append(
            {
                "type": "effective_bias_from_first_swing",
                "bar": swing_start,
                "time": candles[swing_start]["time"],
                "direction": result["effective_bias"],
            }
        )
    else:
        result["events"].append({"type": "skipped_unbiased"})
        return result

    # case classification (master list in intraday-trading-explained.md)
    eff_bias_for_case = "bullish" if want_dir == 1 else "bearish"
    result["case"] = classify_case(eff_bias_for_case, ctx.get("gap", "flat"), ctx.get("extreme"), swing_dir)

    # running swing state (reclassified as breaks print)
    cur_swing = swing_dir
    swing_extreme = (
        max(c["high"] for c in candles[: swing_start + 1])
        if cur_swing == "buying"
        else min(c["low"] for c in candles[: swing_start + 1])
    )
    swing_base = (
        min(c["low"] for c in candles[: swing_start + 1])
        if cur_swing == "buying"
        else max(c["high"] for c in candles[: swing_start + 1])
    )

    def _swing_size() -> float:
        return abs(swing_extreme - swing_base)

    day_setup: dict | None = None  # THE day level: first bias-aligned pace break (S5:63 ~10 o'clock S/R)
    armed: dict | None = None      # active confirmation hunt at the day level
    retro: dict | None = None      # retracement candidate: counter-break level serving the bias
    consec_opp = 0                 # consecutive low/high-breaking candles (voiding)
    entries_done = 0
    open_trade: dict | None = None
    i = 0

    def _close_trade(
        trade: dict,
        bar_idx: int,
        price: float,
        outcome: str,
        exit_time: str | None = None,
        exit_ts: int | None = None,
    ):
        nonlocal open_trade
        risk = abs(trade["entry_price"] - trade["sl"])
        r = ((price - trade["entry_price"]) / risk) * (1 if trade["dir"] == "long" else -1)
        xt = exit_time or candles[bar_idx]["time"]
        xts = int(exit_ts if exit_ts is not None else candles[bar_idx]["ts"])
        trade.update(
            exit_time=xt,
            exit_ts=xts,
            exit_price=round(price, 2),
            outcome=outcome,
            r_multiple=round(r, 2),
        )
        result["trades"].append(trade)
        result["events"].append(
            {
                "type": "exit",
                "bar": bar_idx,
                "time": xt,
                "outcome": outcome,
                "price": round(price, 2),
                "r": round(r, 2),
            }
        )
        open_trade = None

    def _open_trade(bar_idx: int, dirn: int, ref_level: float, dbar: dict, btype: str) -> bool:
        nonlocal open_trade, entries_done
        if cfg["sl_mode"] in SL_MODE_FIXED:
            ref_dist = float(SL_MODE_FIXED[cfg["sl_mode"]])
        else:
            ref_dist = base_avg * SL_MODE_MULT.get(cfg["sl_mode"], 1.0)
        entry = candles[bar_idx]["close"]
        if dirn == 1:
            sl = min(ref_level, candles[bar_idx]["low"]) - ref_dist
            risk = entry - sl
            target = entry + RR_TARGET * risk
            direction = "long"
        else:
            sl = max(ref_level, candles[bar_idx]["high"]) + ref_dist
            risk = sl - entry
            target = entry - RR_TARGET * risk
            direction = "short"
        if risk <= 0:
            return False
        open_trade = {
            "dir": direction,
            "case": result.get("case"),
            "entry_time": candles[bar_idx]["time"],
            "entry_ts": int(candles[bar_idx]["ts"]),
            "entry_price": round(entry, 2),
            "sl": round(sl, 2),
            "target": round(target, 2),
            "level": round(ref_level, 2),
            "pace_break_type": btype,
            "domination_time": dbar["time"],
            "mfe_r": 0.0,
            "entry_bar": bar_idx,
            "validate_until": bar_idx + 2,
            "dom_low": dbar["low"],
            "dom_high": dbar["high"],
            "validated": False,
            # live execution state (1-min mode)
            "_cur_sl": sl,
            "_init_sl": sl,
            "_max_profit": 0.0,
            "_last_m1_ts": int(candles[bar_idx]["ts"]),
        }
        entries_done += 1
        result["events"].append(
            {
                "type": "entry",
                "bar": bar_idx,
                "time": candles[bar_idx]["time"],
                "dir": direction,
                "price": round(entry, 2),
                "sl": round(sl, 2),
                "target": round(target, 2),
            }
        )
        return True

    use_1m = cfg["execution"] == "1min" and m1_day is not None and len(m1_day) > 0

    def _manage_1m_chunk(trade: dict, upto_ts: int) -> bool:
        """Color-aware 1-minute execution over bars since the last processed ts.

        Ported from the BTC Strategy-3 engine: a candle's colour tells the
        intra-bar path — green means low printed early (adverse-first for
        longs), red means high printed early. Exits fill AT the level.
        Returns True when the trade closed.
        """
        nonlocal open_trade
        t_dir = 1 if trade["dir"] == "long" else -1
        entry = float(trade["entry_price"])
        init_risk = abs(entry - float(trade["sl"])) or 1e-9
        cur_sl = float(trade["_cur_sl"])
        max_profit = float(trade["_max_profit"])
        trail_dist = float(cfg["trail_distance_r"]) * init_risk
        ladder_on = cfg["trailing"] == "ladder"

        rows = m1_day[(m1_day["ts"] > trade["_last_m1_ts"]) & (m1_day["ts"] <= upto_ts)]
        if rows.empty:
            return False

        init_sl = float(trade["_init_sl"])

        def _oc() -> str:
            """Exit outcome for a fill at cur_sl (float-safe vs rounded stored sl)."""
            if t_dir == 1:
                if cur_sl >= entry - 1e-9:
                    return "cost-to-cost"
                return "trail" if cur_sl > init_sl + 1e-9 else "sl"
            if cur_sl <= entry + 1e-9:
                return "cost-to-cost"
            return "trail" if cur_sl < init_sl - 1e-9 else "sl"

        for row in rows.sort_values("ts").itertuples():
            trade["_last_m1_ts"] = int(row.ts)
            hhmm = str(row.timestamp)[11:16]
            if hhmm >= EOD_EXIT:
                # square-off at this bar's open
                _close_trade(trade, i, float(row.open), "eod", exit_time=hhmm + ":00", exit_ts=int(row.ts))
                return True

            green = float(row.close) > float(row.open)
            hi, lo, cl = float(row.high), float(row.low), float(row.close)
            exited = False

            if t_dir == 1:
                if green:
                    # adverse first (low early)
                    if lo <= cur_sl:
                        outcome = _oc()
                        _close_trade(trade, i, cur_sl, outcome, exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                        exited = True
                    else:
                        max_profit = max(max_profit, hi - entry)
                        if ladder_on and trail_dist > 0:
                            lvl = int(max_profit // trail_dist)
                            if lvl >= 1:
                                cand = entry + (lvl - 1) * trail_dist
                                if cand > cur_sl:
                                    cur_sl = cand
                        if not exited and cl <= cur_sl:
                            outcome = _oc()
                            _close_trade(trade, i, cur_sl, outcome, exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                            exited = True
                        elif not ladder_on and hi >= float(trade["target"]):
                            _close_trade(trade, i, float(trade["target"]), "target", exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                            exited = True
                else:
                    # favourable first (high early): target/trail before SL check
                    max_profit = max(max_profit, hi - entry)
                    if ladder_on and trail_dist > 0:
                        lvl = int(max_profit // trail_dist)
                        if lvl >= 1:
                            cand = entry + (lvl - 1) * trail_dist
                            if cand > cur_sl:
                                cur_sl = cand
                    if not ladder_on and hi >= float(trade["target"]):
                        _close_trade(trade, i, float(trade["target"]), "target", exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                        exited = True
                    elif lo <= cur_sl or cl <= cur_sl:
                        px = cur_sl if lo <= cur_sl else cur_sl
                        outcome = _oc()
                        _close_trade(trade, i, px, outcome, exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                        exited = True
            else:
                if not green:
                    # SHORT + red candle: favourable first (low early)
                    max_profit = max(max_profit, entry - lo)
                    if ladder_on and trail_dist > 0:
                        lvl = int(max_profit // trail_dist)
                        if lvl >= 1:
                            cand = entry - (lvl - 1) * trail_dist
                            if cand < cur_sl:
                                cur_sl = cand
                    if not ladder_on and lo <= float(trade["target"]):
                        _close_trade(trade, i, float(trade["target"]), "target", exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                        exited = True
                    elif hi >= cur_sl or cl >= cur_sl:
                        outcome = _oc()
                        _close_trade(trade, i, cur_sl, outcome, exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                        exited = True
                else:
                    # SHORT + green candle: adverse first (high early)
                    if hi >= cur_sl:
                        outcome = _oc()
                        _close_trade(trade, i, cur_sl, outcome, exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                        exited = True
                    else:
                        max_profit = max(max_profit, entry - lo)
                        if ladder_on and trail_dist > 0:
                            lvl = int(max_profit // trail_dist)
                            if lvl >= 1:
                                cand = entry - (lvl - 1) * trail_dist
                                if cand < cur_sl:
                                    cur_sl = cand
                        if not exited and cl >= cur_sl:
                            outcome = _oc()
                            _close_trade(trade, i, cur_sl, outcome, exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                            exited = True
                        elif not ladder_on and lo <= float(trade["target"]):
                            _close_trade(trade, i, float(trade["target"]), "target", exit_time=str(row.timestamp)[11:16] + ":00", exit_ts=int(row.ts))
                            exited = True

            if exited:
                return True

        trade["_cur_sl"] = cur_sl
        trade["_max_profit"] = max_profit
        return False

    while i < len(candles):
        cur = candles[i]

        # ---- manage open trade ----
        if open_trade is not None:
            t = open_trade
            exited = False

            if use_1m:
                # precise color-aware fills on real 1-minute bars
                exited = _manage_1m_chunk(t, cur["ts"])
                if not exited:
                    risk = abs(t["entry_price"] - t["sl"]) or 1e-9
                    if t["dir"] == "long":
                        if not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:
                            _close_trade(t, i, cur["close"], "ft_fail")
                            exited = True
                    else:
                        if not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:
                            _close_trade(t, i, cur["close"], "ft_fail")
                            exited = True
                    if not exited and not t["validated"] and i > t["validate_until"]:
                        t["validated"] = True
            else:
                risk = abs(t["entry_price"] - t["sl"]) or 1e-9
                if t["dir"] == "long":
                    if cur["low"] <= t["sl"]:
                        _close_trade(t, i, t["sl"], "sl")
                        exited = True
                    elif not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:
                        # follow-through never arrived -> bad entry, admit it fast (S5:98)
                        _close_trade(t, i, cur["close"], "ft_fail")
                        exited = True
                    elif cur["high"] >= t["target"]:
                        _close_trade(t, i, t["target"], "target")
                        exited = True
                else:
                    if cur["high"] >= t["sl"]:
                        _close_trade(t, i, t["sl"], "sl")
                        exited = True
                    elif not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:
                        _close_trade(t, i, cur["close"], "ft_fail")
                        exited = True
                    elif cur["low"] <= t["target"]:
                        _close_trade(t, i, t["target"], "target")
                        exited = True

                if not exited:
                    if not t["validated"] and i > t["validate_until"]:
                        t["validated"] = True
                    if not exited:
                        if t["dir"] == "long":
                            t["mfe_r"] = max(t.get("mfe_r", 0.0), (cur["high"] - t["entry_price"]) / risk)
                            if t.get("mfe_r", 0.0) >= COST_TO_COST_R and cur["low"] <= t["entry_price"]:
                                _close_trade(t, i, t["entry_price"], "cost-to-cost")
                                exited = True
                        else:
                            t["mfe_r"] = max(t.get("mfe_r", 0.0), (t["entry_price"] - cur["low"]) / risk)
                            if t.get("mfe_r", 0.0) >= COST_TO_COST_R and cur["high"] >= t["entry_price"]:
                                _close_trade(t, i, t["entry_price"], "cost-to-cost")
                                exited = True

                if cur["time"] >= EOD_EXIT and open_trade is not None:
                    _close_trade(open_trade, i, cur["close"], "eod")

        # ---- square-off / window guards for NEW work ----
        can_enter = (
            open_trade is None
            and entries_done < MAX_ENTRIES
            and ENTRY_START <= cur["time"] <= ENTRY_END
        )

        # ---- voiding: consecutive LOW/HIGH-breaking candles reclassify the leg (S6:102) ----
        prev_c = candles[i - 1] if i > 0 else None
        if prev_c is not None and cur_swing is not None:
            if cur_swing == "buying" and cur["low"] < prev_c["low"]:
                consec_opp += 1
            elif cur_swing == "selling" and cur["high"] > prev_c["high"]:
                consec_opp += 1
            else:
                consec_opp = 0
        if consec_opp >= VOID_CONSECUTIVE and cur_swing is not None:
            flipped = "selling" if cur_swing == "buying" else "buying"
            result["events"].append(
                {
                    "type": "swing_voided",
                    "bar": i,
                    "time": cur["time"],
                    "from": cur_swing,
                    "to": flipped,
                }
            )
            cur_swing = flipped
            swing_extreme = cur["high"] if flipped == "buying" else cur["low"]
            swing_base = cur["low"] if flipped == "buying" else cur["high"]
            consec_opp = 0
            if armed is not None or day_setup is not None:
                result["events"].append(
                    {"type": "setup_disarmed", "bar": i, "time": cur["time"], "reason": "swing_voided"}
                )
                armed = None
                day_setup = None

        # ---- update swing extreme ----
        if cur_swing == "buying":
            swing_extreme = max(swing_extreme, cur["high"])
            swing_base = min(swing_base, cur["low"])
        elif cur_swing == "selling":
            swing_extreme = min(swing_extreme, cur["low"])
            swing_base = max(swing_base, cur["high"])

        # ---- armed setup: invalidation check ----
        if armed is not None:
            avg_now = base_avg
            if avg_now:
                if armed["trade_dir"] == 1 and cur["close"] < armed["level"] - LEVEL_INVALID_MULT * avg_now:
                    result["events"].append(
                        {"type": "setup_disarmed", "bar": i, "time": cur["time"], "reason": "level_invalidated"}
                    )
                    armed = None
                    day_setup = None
                elif armed["trade_dir"] == -1 and cur["close"] > armed["level"] + LEVEL_INVALID_MULT * avg_now:
                    result["events"].append(
                        {"type": "setup_disarmed", "bar": i, "time": cur["time"], "reason": "level_invalidated"}
                    )
                    armed = None
                    day_setup = None
                if armed is not None:
                    armed["age"] = armed.get("age", 0) + 1
                    if armed["age"] > SWING_TIMEOUT_CANDLES:
                        result["events"].append(
                            {"type": "setup_disarmed", "bar": i, "time": cur["time"], "reason": "timeout"}
                        )
                        armed = None

        # ---- pace break detection on every closed bar ----
        if i > 0 and cur_swing is not None and can_enter:
            brk = detect_pace_break(candles, i, cur_swing, swing_extreme, _swing_size(), base_avg)
            if brk is not None:
                # break of a buying swing = selling pressure -> expect SUPPORT longs
                trade_dir = -1 if cur_swing == "buying" else 1
                aligned = trade_dir == want_dir
                result["events"].append(
                    {
                        "type": "pace_break",
                        "bar": i,
                        "time": cur["time"],
                        "break_type": brk["type"],
                        "level": round(brk["level"], 2),
                        "swing_before": cur_swing,
                        "swing_size": round(_swing_size(), 2),
                        "aligned_with_bias": aligned,
                    }
                )
                # swing flips: the break starts the opposing leg
                new_swing = "selling" if cur_swing == "buying" else "buying"
                cur_swing = new_swing
                swing_extreme = cur["low"] if new_swing == "selling" else cur["high"]
                swing_base = cur["high"] if new_swing == "selling" else cur["low"]
                consec_opp = 0
                if aligned and day_setup is None:
                    day_setup = {
                        "level": brk["level"],
                        "trade_dir": trade_dir,
                        "break_type": brk["type"],
                        "bar": i,
                    }
                    result["events"].append(
                        {
                            "type": "day_level_set",
                            "bar": i,
                            "time": cur["time"],
                            "ts": int(cur["ts"]),
                            "level": round(brk["level"], 2),
                            "break_type": brk["type"],
                        }
                    )
                    if brk["type"] in ("domination", "candle-size"):
                        # Direct flow-favor entry ON the aggressive break candle
                        # (S5:193 'sold live on the aggressive candle', S5:101
                        # 'direct buy on the pace break'). The candle must close
                        # near its extreme ("closes near the extreme", S6:36);
                        # follow-through becomes 2-bar post-entry validation.
                        brk_q = (
                            (cur["close"] - cur["low"]) / cur["range"]
                            if trade_dir == 1
                            else (cur["high"] - cur["close"]) / cur["range"]
                        ) if cur["range"] > 0 else 0.0
                        entered = brk_q >= DOM_CLOSE_Q and _open_trade(
                            i, trade_dir, brk["level"], cur, brk["type"]
                        )
                        if not entered:
                            armed = {
                                "level": brk["level"],
                                "trade_dir": trade_dir,
                                "break_type": brk["type"],
                                "armed_at": i,
                                "age": 0,
                            }
                    else:
                        # Structure breaks are weaker signals: hunt the retest +
                        # domination + follow-through confirmation instead.
                        armed = {
                            "level": brk["level"],
                            "trade_dir": trade_dir,
                            "break_type": brk["type"],
                            "armed_at": i,
                            "age": 0,
                        }
                elif aligned and day_setup is not None and retro is not None:
                    result["events"].append(
                        {"type": "retro_dropped", "bar": i, "time": cur["time"], "reason": "aligned_day_level_active"}
                    )
                    retro = None
                elif not aligned and day_setup is None:
                    # Counter-break on a biased day = retracement leg building
                    # against the overview. Its level becomes a bias-side S/R
                    # candidate ('bias overrides pattern': selling into buying
                    # overview = retracement -> trade AT the level it creates).
                    # Fresh counter-breaks UPDATE the candidate (deeper tests
                    # improve odds, S6:134).
                    retro = {
                        "level": brk["level"],
                        "dir": want_dir,
                        "break_type": brk["type"],
                        "age": 0,
                        "set_at": i,
                        "leg": cur["low"] if want_dir == 1 else cur["high"],
                    }
                    result["events"].append(
                        {
                            "type": "retro_level_set",
                            "bar": i,
                            "time": cur["time"],
                            "ts": int(cur["ts"]),
                            "level": round(brk["level"], 2),
                            "break_type": brk["type"],
                        }
                    )

        # ---- re-arm confirmation hunt when price revisits the day level ----
        if day_setup is not None and armed is None and open_trade is None and can_enter:
            avg_r0 = base_avg
            tol0 = avg_r0 * LEVEL_TOL_MULT
            touched = (
                cur["low"] <= day_setup["level"] + tol0
                if day_setup["trade_dir"] == 1
                else cur["high"] >= day_setup["level"] - tol0
            )
            if touched:
                armed = {
                    "level": day_setup["level"],
                    "trade_dir": day_setup["trade_dir"],
                    "break_type": day_setup["break_type"],
                    "armed_at": i,
                    "age": 0,
                }
                result["events"].append(
                    {"type": "rearm", "bar": i, "time": cur["time"], "level": round(day_setup["level"], 2)}
                )

        # ---- retracement candidate: age out only (leg continuation past the
        # break level is EXPECTED — 'maybe after breaking lows first', S5:63;
        # support is confirmed by the reversal itself, not by holding a line) ----
        if retro is not None:
            # track the running leg extreme (true support/resistance test zone)
            if retro["dir"] == 1:
                retro["leg"] = min(retro.get("leg", cur["low"]), cur["low"])
            else:
                retro["leg"] = max(retro.get("leg", cur["high"]), cur["high"])
            retro["age"] += 1
            if retro["age"] > RETRO_TIMEOUT_CANDLES:
                result["events"].append(
                    {"type": "retro_disarmed", "bar": i, "time": cur["time"], "reason": "timeout"}
                )
                retro = None

        # ---- retracement confirmation: leg exhausted + bias-domination AT the leg extreme ----
        if (
            retro is not None
            and open_trade is None
            and can_enter
            and i > retro.get("set_at", i)
            and i - retro["set_at"] >= RETRO_LEG_MIN_BARS
        ):
            avg_r2 = base_avg
            tol1 = avg_r2 * LEVEL_TOL_MULT
            prev_r = candles[i - 1] if i > 0 else None
            if "dom_bar" not in retro:
                testing_leg = (
                    cur["low"] <= retro["leg"] + tol1
                    if retro["dir"] == 1
                    else cur["high"] >= retro["leg"] - tol1
                )
                close_q = (
                    (cur["close"] - cur["low"]) / cur["range"]
                    if retro["dir"] == 1
                    else (cur["high"] - cur["close"]) / cur["range"]
                ) if cur["range"] > 0 else 0.0
                dom = (
                    testing_leg
                    and close_q >= DOM_CLOSE_Q
                    and cur["color"] == retro["dir"]
                    and prev_r is not None
                    and (
                        _consumes(cur, prev_r)
                        or (avg_r2 and cur["range"] >= BIG_CANDLE_MULT * avg_r2)
                    )
                )
                if dom:
                    retro["dom_bar"] = i
                    result["events"].append(
                        {
                            "type": "domination",
                            "bar": i,
                            "time": cur["time"],
                            "price": round(cur["close"], 2),
                            "via": "retracement",
                        }
                    )
            elif i <= retro["dom_bar"] + 2:
                dbar_r = candles[retro["dom_bar"]]
                ft = (
                    cur["color"] == 1 and cur["low"] >= dbar_r["low"] and cur["close"] > dbar_r["close"]
                    if retro["dir"] == 1
                    else cur["color"] == -1 and cur["high"] <= dbar_r["high"] and cur["close"] < dbar_r["close"]
                )
                if ft:
                    sl_ref = (
                        min(retro["leg"], dbar_r["low"])
                        if retro["dir"] == 1
                        else max(retro["leg"], dbar_r["high"])
                    )
                    if _open_trade(i, retro["dir"], sl_ref, dbar_r, f"{retro['break_type']}+retrace"):
                        retro = None

        # ---- confirmation: domination close + follow-through -> entry ----
        if armed is not None and can_enter and i > armed["armed_at"]:
            avg_now = base_avg

            if "dom_bar" not in armed:
                # retest path: wait for price to come back to the level, then dominate
                near_tol = (avg_now or 0.0) * LEVEL_TOL_MULT
                prev = candles[i - 1]
                at_level = (
                    cur["low"] <= armed["level"] + near_tol
                    if armed["trade_dir"] == 1
                    else cur["high"] >= armed["level"] - near_tol
                )
                close_q = (
                    (cur["close"] - cur["low"]) / cur["range"]
                    if armed["trade_dir"] == 1
                    else (cur["high"] - cur["close"]) / cur["range"]
                ) if cur["range"] > 0 else 0.0
                dom = (
                    at_level
                    and close_q >= DOM_CLOSE_Q
                    and cur["color"] == armed["trade_dir"]
                    and (
                        _consumes(cur, prev)
                        or (avg_now and cur["range"] >= BIG_CANDLE_MULT * avg_now)
                    )
                )

                if dom:
                    armed["dom_bar"] = i
                    result["events"].append(
                        {
                            "type": "domination",
                            "bar": i,
                            "time": cur["time"],
                            "price": round(cur["close"], 2),
                        }
                    )
            elif i <= armed["dom_bar"] + 2:
                # follow-through: same-direction candle holding the domination
                # extreme, within two candles of it (S5:98 'confirmation within
                # two candles', S6:137 'next candle sustaining')
                dbar = candles[armed["dom_bar"]]
                ft = (
                    cur["color"] == 1 and cur["low"] >= dbar["low"] and cur["close"] > dbar["close"]
                    if armed["trade_dir"] == 1
                    else cur["color"] == -1 and cur["high"] <= dbar["high"] and cur["close"] < dbar["close"]
                )
                if ft and avg_now:
                    if _open_trade(i, armed["trade_dir"], armed["level"], dbar, armed["break_type"]):
                        armed = None

        # ---- immediate-momentum sanity (S5:36 ~5 pts) recorded, not enforced ----
        i += 1

    # force-close anything left at EOD
    if open_trade is not None:
        last = candles[-1]
        _close_trade(open_trade, len(candles) - 1, last["close"], "eod")

    return result


# --- backtest -------------------------------------------------------------------

def run_backtest(
    df_5min: pd.DataFrame,
    bias_labels: list[dict],
    cfg: dict | None = None,
    df_1min: pd.DataFrame | None = None,
) -> dict:
    """Run the engine across every labelled day.

    bias_labels come from bias.compute_bias(); label[T] uses only T-1 data,
    matching live pre-open knowledge. The trailing next-day planning label is
    ignored (no session data exists for it).

    cfg: experiment switches (DEFAULT_CFG). df_1min enables precise execution
    when cfg['execution'] == '1min'.
    """
    cfg = resolve_cfg(cfg)

    df = df_5min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d, g in df.groupby(dates, sort=True)}

    m1_map: dict[str, pd.DataFrame] = {}
    if cfg["execution"] == "1min" and df_1min is not None and len(df_1min) > 0:
        d1 = df_1min.copy()
        d1["timestamp"] = pd.to_datetime(d1["timestamp"])
        d1["ts"] = d1["ts"].astype("int64")
        d1 = d1.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
        d1_dates = d1["timestamp"].dt.strftime("%Y-%m-%d")
        m1_map = {d: g for d, g in d1.groupby(d1_dates, sort=True)}

    bias_map: dict[str, str] = {}
    zone_map: dict[str, str | None] = {}
    for l in bias_labels:
        bias_map[l["date"]] = l["bias"]
        ov = l.get("overview") or {}
        zone_map[l["date"]] = ov.get("zone")
    traded_dates = set(groups) & set(bias_map)

    # previous-session close per date (gap detection) + extreme-zone context
    ordered = sorted(groups)
    prev_close_by_date: dict[str, float] = {}
    for i in range(1, len(ordered)):
        prev_g = groups[ordered[i - 1]]
        prev_close_by_date[ordered[i]] = float(prev_g["close"].iloc[-1])

    def _extreme_of(zone: str | None) -> str | None:
        if zone in EXTREME_ZONES_HIGH:
            return "highs"
        if zone in EXTREME_ZONES_LOW:
            return "lows"
        return None

    # avg candle size baseline (STABLE all day): mean range of the previous
    # <=10 sessions, excluding each session's first candle and >=15:15 churn.
    def _qualifying_ranges(g: pd.DataFrame) -> list[float]:
        rows = g.reset_index(drop=True)
        out: list[float] = []
        for k in range(1, len(rows)):  # skip session's first candle
            row = rows.iloc[k]
            if row["timestamp"].strftime("%H:%M") >= EOD_EXIT:
                continue
            out.append(float(row["high"]) - float(row["low"]))
        return out

    day_ranges = {d: _qualifying_ranges(groups[d]) for d in ordered}
    avg_by_date: dict[str, float | None] = {}
    for i, d in enumerate(ordered):
        flat = [
            x
            for j in range(max(0, i - AVG_LOOKBACK_DAYS), i)
            for x in day_ranges[ordered[j]]
        ]
        avg_by_date[d] = (sum(flat) / len(flat)) if flat else None

    days: list[dict] = []
    for d in sorted(traded_dates):
        g = groups[d]
        gap = gap_type_of(float(g["open"].iloc[0]), prev_close_by_date.get(d), cfg["gap_pct"])
        ctx = {
            "gap": gap,
            "extreme": _extreme_of(zone_map.get(d)),
            "avg_range": avg_by_date.get(d),
        }
        days.append(simulate_day(g, bias_map[d], cfg=cfg, m1_day=m1_map.get(d), ctx=ctx))

    # stats
    all_trades = [t for dy in days for t in dy["trades"]]
    wins = [t for t in all_trades if t["r_multiple"] > 0]
    outcomes = Counter(t["outcome"] for t in all_trades)
    stats = {
        "days_total": len(days),
        "days_traded": sum(1 for dy in days if dy["trades"]),
        "trades": len(all_trades),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(all_trades) * 100, 1) if all_trades else 0.0,
        "total_r": round(sum(t["r_multiple"] for t in all_trades), 2),
        "avg_r": round(sum(t["r_multiple"] for t in all_trades) / len(all_trades), 2) if all_trades else 0.0,
        "outcomes": dict(outcomes),
        "longs": sum(1 for t in all_trades if t["dir"] == "long"),
        "shorts": sum(1 for t in all_trades if t["dir"] == "short"),
    }

    # per-case breakdown (master list tracker)
    case_agg: dict[str, dict] = {}
    for dy in days:
        c = dy.get("case")
        if c:
            slot = case_agg.setdefault(c, {"trades": 0, "wins": 0, "total_r": 0.0})
            for t in dy["trades"]:
                slot["trades"] += 1
                slot["wins"] += 1 if t["r_multiple"] > 0 else 0
                slot["total_r"] += t["r_multiple"]
    for slot in case_agg.values():
        slot["total_r"] = round(slot["total_r"], 2)
    stats["cases"] = dict(sorted(case_agg.items()))

    return {"stats": stats, "days": days, "config": cfg}


