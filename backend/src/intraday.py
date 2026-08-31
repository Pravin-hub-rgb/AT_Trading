
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
    - SL modes: avg (default), prev_pivot (uses WalkerEngine pivot + buffer)
"""

from __future__ import annotations

import pandas as pd
from collections import Counter
from .walker import WalkerEngine, FlowCandle
from .intraday_1m import manage_1m_chunk, resolve_pending_direct

# --- tunable thresholds -------------------------------------------------------
ENTRY_START = "09:45"        # hard rule: no entries before this (S1/S4/S5)
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

# --- prev-pivot SL constants -------------------------------------------------
SL_PIVOT_BUFFER = 1.0        # points beyond the opposing pivot for SL (prev_pivot mode)

# --- experiment switches (best-combo search, BTC-backtester style) ------------
# Defaults preserve the current engine behaviour exactly.
DEFAULT_CFG = {
    "sl_mode": "avg",        # avg | avg075 | avg05 | fixed8 | prev_pivot
    "execution": "5min",     # 5min (conservative, SL-first) | 1min (color-aware precise)
    "trailing": "off",       # off (course: fixed 3R target) | ladder (R-chunk trail; disables 3R target)
    "trail_distance_r": 1.0, # ladder step size in R
    "gap_pct": 0.0027,       # |open - prev_close| beyond this fraction = gap-up/down
                             # 0.27% researched from labeled examples (Oct-Dec'25,
                             # Mar-Apr'26): separates GOOD vs noise gaps 8/9
    "sl_pivot_buffer": 1.0,  # buffer in absolute points for prev_pivot SL mode
    "ft_fail_enabled": True,  # early exit when close goes beyond dom_level within 2 bars (S5:98)
    "entry_method": "pace_break",   # pace_break | pivot_break
    "swing_mode": "opposite_swing_needed",  # none | opposite_swing_needed (1min only)
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


def _classify_first_swing_v2(candles: list[dict], day_date: str) -> tuple[str | None, int, list[dict], int, int, float, str]:
    """First-swing classification using the new FirstSwingEngine.

    Uses advanced price-action detection (continuation/reversal + chop/sustain
    confirmation). Falls back to legacy _classify_first_swing if not declared.

    Returns: (direction, start_idx, events, confirmed_at_idx, end_idx, end_px, end_time)
      direction: 'buying' or 'selling' or None
      start_idx: bar index where the first swing seeds
      events: list of event dicts for chart annotation
      confirmed_at_idx: bar index where FsV2 confirmed the swing (-1 if not confirmed)
      end_idx: bar index of the swing's confirmed extreme (high for buying, low for selling)
      end_px: price of the swing's confirmed extreme
      end_time: HH:MM time of the confirmed extreme
    """
    from datetime import datetime, timezone, timedelta
    from .firstswing import FirstSwingEngine
    from .walker import FlowCandle

    events: list[dict] = []
    if not candles:
        return None, -1, events, -1, -1, float("nan"), ""

    # Candle `ts` values are IST epoch seconds (see upstox_fetcher). The engine
    # parses HH:MM out of the date string and gates on session times (timeCap
    # 09:29 etc.), so we MUST render in IST — formatting in UTC shifted every
    # session 5h30m early ("09:15" -> "03:45") and nothing ever declared.
    IST = timezone(timedelta(hours=5, minutes=30))
    flow_candles: list[FlowCandle] = []
    for c in candles:
        ts = c.get("ts", 0)
        if ts:
            dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            dt = f"{day_date}T{c.get('time', '00:00')}:00"
        flow_candles.append(FlowCandle(
            date=dt, open=c["open"], high=c["high"], low=c["low"], close=c["close"],
        ))

    eng = FirstSwingEngine()
    for g_idx, fc in enumerate(flow_candles):
        eng.process_bar(fc, g_idx)

    if not eng.declared:
        # No swing declared - return None (no swing direction for this day)
        return None, -1, [{"type": "no_swing_declared"}], -1, -1, float("nan"), ""

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
    return (
        direction, seed, events, eng.confirmed_at_idx,
        eng.end_idx, eng.end_px, eng.end_time,
    )


# --- second swing detection (1min only) -----------------------------------------

def detect_second_swing(
    candles: list[dict],
    day_date: str,
    fs1_dir: str,
    fs1_end_idx: int,
    fs1_end_px: float,
    fs1_end_time: str,
    m1_candles: list[dict] | None = None,
) -> tuple[str | None, int, list[dict], int]:
    """Run FsV2 from the first-swing extreme onwards to detect the second swing.

    Args:
        candles: full day candle list (5min reference for index mapping)
        day_date: date string for timestamp formatting
        fs1_dir: first swing direction ('buying' | 'selling')
        fs1_end_idx: bar index of the first swing's confirmed extreme (in `candles` units)
        fs1_end_px: price of the first swing's confirmed extreme
        fs1_end_time: HH:MM time of the first swing's confirmed extreme
        m1_candles: optional 1-min candles for finer-grain detection (1min execution)

    Returns: (direction, start_idx, events, confirmed_at_idx)
        direction: second swing direction or None if not declared
        start_idx, confirmed_at_idx: indices expressed in `candles` units (5min) so the
        entry-gate `i > entry_swing_confirmed_idx` check works against the main loop.
        If m1_candles is supplied, indices are mapped back from 1min to 5min by finding
        the 5min bar whose timestamp <= the 1min bar's timestamp.
    """
    from datetime import datetime, timezone, timedelta
    from .firstswing import FirstSwingEngine
    from .walker import FlowCandle

    events: list[dict] = []

    # Decide which candle list to use for detection
    if m1_candles:
        # 1min execution: detect second swing on 1min bars for precision.
        # SECOND SWING SPEC: start from first swing's END (cyan line), not its
        # confirmation. The first swing's end is the new "09:15" for the second
        # swing — we run the EXACT same FirstSwingEngine logic (B1/B2/FLIP +
        # chop/sustain) on bars AFTER that end.
        # e.g. 28 Aug: first swing end = 09:27 high 24158.25, FS at 09:30.
        # Second swing feeds 09:28 onward, B1 at 09:30, B2 at 09:36, FS at 09:42.
        fs1_end_ts = candles[fs1_end_idx].get("ts", 0) if fs1_end_idx >= 0 else 0
        fs1_end_m1_idx = -1
        for k, mc in enumerate(m1_candles):
            if mc.get("ts", 0) <= fs1_end_ts:
                fs1_end_m1_idx = k
            else:
                break

        if fs1_end_m1_idx < 0:
            return None, -1, [{"type": "no_second_swing", "reason": "m1_timestamp_not_found"}], -1

        # User fix: give ALL OHLC from 09:28 to the first-swing engine.
        # 09:28 is the new 09:15 — feed from 09:28 inclusive, so 09:28 nothing,
        # 09:29 nothing, 09:30 B1 breaking 09:29 low, 09:36 B2 breaking 09:31 low.
        # This is exactly "from 9:28 give all the ohlc value to first swing engine".
        seed_m1_idx = fs1_end_m1_idx + 1
        if seed_m1_idx >= len(m1_candles):
            return None, -1, [{"type": "no_second_swing", "reason": "no_m1_seed_after_first_swing"}], -1
        # Feed from 09:28 inclusive — fresh engine, no reset, just processBar from seed.
        IST = timezone(timedelta(hours=5, minutes=30))
        flow_candles: list[tuple[int, FlowCandle]] = []
        for idx in range(seed_m1_idx, len(m1_candles)):
            mc = m1_candles[idx]
            mts = mc.get("ts", 0)
            dt = datetime.fromtimestamp(int(mts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if mts else f"{day_date}T{mc.get('time','00:00')}:00"
            flow_candles.append((idx, FlowCandle(date=dt, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))))
        eng = FirstSwingEngine()
        for g_idx, fc in flow_candles:
            eng.process_bar(fc, g_idx)

        if not eng.declared:
            return None, -1, [{"type": "no_second_swing_declared"}], -1

        # Map 1min indices back to 5min for the entry gate:
        # For each 1min index, find the 5min bar whose open_ts <= 1min_ts
        def m1_idx_to_5(idx: int) -> int:
            mts = m1_candles[idx].get("ts", 0)
            result = 0
            for j, c5 in enumerate(candles):
                if c5.get("ts", 0) <= mts:
                    result = j
                else:
                    break
            return result

        start_idx_5 = m1_idx_to_5(eng.start_idx)
        confirmed_at_idx_5 = m1_idx_to_5(eng.confirmed_at_idx)
        end_idx_5 = m1_idx_to_5(eng.end_idx)
        start_px = eng.start_px
        end_px = eng.end_px
        start_time = eng.start_time
        confirmed_at_time = eng.confirmed_at_time
    else:
        # 5min fallback: give ALL OHLC from seed (09:28) to first-swing engine
        seed_5_idx = fs1_end_idx + 1
        if seed_5_idx >= len(candles):
            return None, -1, [{"type": "no_second_swing", "reason": "no_5min_seed_after_first_swing"}], -1
        IST = timezone(timedelta(hours=5, minutes=30))
        flow_candles_5: list[tuple[int, FlowCandle]] = []
        for idx in range(seed_5_idx, len(candles)):
            c = candles[idx]
            ts = c.get("ts", 0)
            dt = datetime.fromtimestamp(int(ts), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if ts else f"{day_date}T{c.get('time','00:00')}:00"
            flow_candles_5.append((idx, FlowCandle(date=dt, open=float(c["open"]), high=float(c["high"]), low=float(c["low"]), close=float(c["close"]))))
        eng = FirstSwingEngine()
        for g_idx, fc in flow_candles_5:
            eng.process_bar(fc, g_idx)

        if not eng.declared:
            return None, -1, [{"type": "no_second_swing_declared"}], -1

        start_idx_5 = eng.start_idx
        confirmed_at_idx_5 = eng.confirmed_at_idx
        end_idx_5 = eng.end_idx
        start_px = eng.start_px
        end_px = eng.end_px
        start_time = eng.start_time
        confirmed_at_time = eng.confirmed_at_time

    direction = "buying" if eng.dir == "up" else "selling"
    events.append({
        "type": "swing2_classified",
        "dir": direction,
        "bar": start_idx_5,
        "time": start_time,
        "first_swing": fs1_dir,
    })
    events.append({
        "type": "fs2_segment",
        "dir": eng.dir,
        "start_idx": start_idx_5,
        "start_px": start_px,
        "end_idx": end_idx_5,
        "end_px": end_px,
        "confirmed_at_idx": confirmed_at_idx_5,
        "confirmed_at_time": confirmed_at_time,
    })

    return direction, start_idx_5, events, confirmed_at_idx_5


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


def detect_pivot_break(
    candles: list[dict],
    i: int,
    trade_dir: int,           # 1 = long, -1 = short
    normal_highs: list,
    normal_lows: list,
) -> dict | None:
    """Bar i breaks the most recent sealed pivot in the trade direction.

    For a LONG (trade_dir=1): close above most recent sealed HIGH pivot.
    For a SHORT (trade_dir=-1): close below most recent sealed LOW pivot.

    Returns {type: 'pivot_break', level, bar} or None.

    Used by the 'pivot_break' entry method (1min execution).
    """
    if i < 2:
        return None
    cur = candles[i]
    if trade_dir == 1:
        if normal_highs and cur["close"] > normal_highs[-1].px:
            return {"type": "pivot_break", "level": normal_highs[-1].px, "bar": i}
    else:
        if normal_lows and cur["close"] < normal_lows[-1].px:
            return {"type": "pivot_break", "level": normal_lows[-1].px, "bar": i}
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

    # WalkerEngine: track pivots for prev_pivot SL mode (5-min reference)
    walker = WalkerEngine()
    normal_highs: list = []   # sealed H pivots
    normal_lows: list = []    # sealed L pivots

    (swing_dir, swing_start, ev, fs_confirmed_idx,
     fs1_end_idx, fs1_end_px, fs1_end_time) = _classify_first_swing_v2(candles[: len(candles)], result["date"])
    result["swing_direction"] = swing_dir
    result["first_swing_confirmed_idx"] = fs_confirmed_idx
    result["first_swing_end_time"] = fs1_end_time
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
    if cur_swing is not None and swing_start >= 0:
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
    else:
        # No swing declared — seed from first candle
        swing_extreme = candles[0]["high"]
        swing_base = candles[0]["low"]

    def _swing_size() -> float:
        return abs(swing_extreme - swing_base)

    day_setup: dict | None = None  # THE day level: first bias-aligned pace break (S5:63 ~10 o'clock S/R)
    armed: dict | None = None      # active confirmation hunt at the day level
    retro: dict | None = None      # retracement candidate: counter-break level serving the bias
    pending_direct: dict | None = None  # 1-min precision entry: deferred until next 1-min bar close
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

    def _open_trade(
        bar_idx: int, dirn: int, ref_level: float, dbar: dict, btype: str,
        m1_bar: dict | None = None,
    ) -> bool:
        """Open a new trade at the given 5-min bar index.

        When m1_bar is provided (1min execution mode), the entry price, timestamp,
        and OHLC come from the 1-min candle instead of the 5-min bar. The SL is still
        calculated against the 5-min reference (consistent with the engine's swing context).
        bar_idx is used only for logging / the 5-min bar record.
        """
        nonlocal open_trade, entries_done
        # Entry data: prefer 1-min bar if available, else 5-min bar
        if m1_bar is not None:
            entry = float(m1_bar["close"])
            entry_ts = int(m1_bar["ts"])
            entry_time = str(m1_bar["timestamp"])[11:16] + ":00"
            entry_candle_low = float(m1_bar["low"])
            entry_candle_high = float(m1_bar["high"])
            dom_low = entry_candle_low
            dom_high = entry_candle_high
            dom_time = entry_time
        else:
            entry = candles[bar_idx]["close"]
            entry_ts = int(candles[bar_idx]["ts"])
            entry_time = candles[bar_idx]["time"]
            entry_candle_low = candles[bar_idx]["low"]
            entry_candle_high = candles[bar_idx]["high"]
            dom_low = dbar["low"]
            dom_high = dbar["high"]
            dom_time = dbar["time"]

        sl_mode = cfg["sl_mode"]
        sl_used_mode = sl_mode
        pivot_ref = None

        if sl_mode == "prev_pivot":
            # SL = swing in the OPPOSITE direction + buffer.
            # For a LONG: SL goes below entry -> use the most recent LOW pivot
            # (recent support). For a SHORT: SL goes above entry -> use the
            # most recent HIGH pivot (recent resistance).
            # HOWEVER: if that pivot has already been breached by the entry
            # candle's low/high, fall back to Entry Candle Low/High - buffer.
            buf = float(cfg.get("sl_pivot_buffer", SL_PIVOT_BUFFER))
            opposing_pool = normal_lows if dirn == 1 else normal_highs
            if opposing_pool:
                pivot_ref = opposing_pool[-1]  # most recent sealed opposing pivot
                pivot_px = pivot_ref.px
                # Check if pivot was already breached by the entry candle.
                # A LOW pivot is "breached" if the entry candle went below it
                # (price action already went through that support).
                # A HIGH pivot is "breached" if the entry candle went above it.
                if dirn == 1:
                    breached = pivot_px >= entry_candle_low  # L pivot above ECL → breached
                else:
                    breached = pivot_px <= entry_candle_high  # H pivot below ECH → breached

                if breached:
                    # Pivot already breached — use Entry Candle Low/High instead
                    if dirn == 1:
                        sl = entry_candle_low - buf
                    else:
                        sl = entry_candle_high + buf
                    pivot_ref = None  # mark as ECL fallback
                else:
                    # Pivot still intact — use it
                    if dirn == 1:
                        sl = pivot_px - buf
                    else:
                        sl = pivot_px + buf
            else:
                # No opposing pivot yet — fallback to avg
                sl_used_mode = "avg"

        if sl_used_mode != "prev_pivot":
            if sl_mode in SL_MODE_FIXED:
                ref_dist = float(SL_MODE_FIXED[sl_mode])
            else:
                ref_dist = base_avg * SL_MODE_MULT.get(sl_mode, 1.0)
            if dirn == 1:
                sl = min(ref_level, candles[bar_idx]["low"]) - ref_dist
            else:
                sl = max(ref_level, candles[bar_idx]["high"]) + ref_dist

        if dirn == 1:
            risk = entry - sl
            target = entry + RR_TARGET * risk
            direction = "long"
        else:
            risk = sl - entry
            target = entry - RR_TARGET * risk
            direction = "short"
        if risk <= 0:
            return False
        open_trade = {
            "dir": direction,
            "case": result.get("case"),
            "entry_time": entry_time,
            "entry_ts": entry_ts,
            "entry_price": round(entry, 2),
            "sl": round(sl, 2),
            "target": round(target, 2),
            "level": round(ref_level, 2),
            "pace_break_type": btype,
            "domination_time": dom_time,
            "mfe_r": 0.0,
            "entry_bar": bar_idx,
            "validate_until": bar_idx + 2,
            "dom_low": dom_low,
            "dom_high": dom_high,
            "validated": False,
            "sl_mode_used": sl_used_mode,
            "pivot_ref": {"px": pivot_ref.px, "time": pivot_ref.time, "kind": pivot_ref.kind, "idx": pivot_ref.idx} if pivot_ref is not None else None,
            # live execution state (1-min mode)
            "_cur_sl": sl,
            "_init_sl": sl,
            "_max_profit": 0.0,
            "_last_m1_ts": entry_ts,
        }
        entries_done += 1
        result["events"].append(
            {
                "type": "entry",
                "bar": bar_idx,
                "time": entry_time,
                "dir": direction,
                "price": round(entry, 2),
                "sl": round(sl, 2),
                "target": round(target, 2),
            }
        )
        return True

    use_1m = cfg["execution"] == "1min" and m1_day is not None and len(m1_day) > 0

    # Separate WalkerEngine for 1-min candles (used for pivot_break detection
    # when execution=1min + entry_method=pivot_break). The 1-min walker sees
    # finer-grained pivot structure (e.g. the 10:23 low on the 1-min chart)
    # so breaks are detected on the correct timeframe, not the 5-min one.
    walker_1m: WalkerEngine | None = None
    normal_highs_1m: list = []
    normal_lows_1m: list = []
    m1_candles: list[dict] = []
    if use_1m and cfg.get("entry_method") == "pivot_break":
        walker_1m = WalkerEngine()
        m1_candles = _prep_day(m1_day) if m1_day is not None else []
        for idx, mc in enumerate(m1_candles):
            mc_dt = f"{result['date']}T{mc['time']}:00"
            fc = FlowCandle(date=mc_dt, open=mc["open"], high=mc["high"], low=mc["low"], close=mc["close"])
            new_p = walker_1m.process_bar(fc, idx)
            for p in new_p:
                if p.kind == "H":
                    normal_highs_1m.append(p)
                else:
                    normal_lows_1m.append(p)

    # ── second-swing detection (1min only, when swing_mode = opposite_swing_needed) ──
    # For 1min mode: second swing is on 1-min chart, starting from the candle
    # AFTER the 1-min cyan end (09:28). This mirrors exactly how the 1-min
    # first swing was found (09:27 low→high), per user: "it goes form 9:27 low
    # to high okay ... we should start from 9:28 candle".
    # We compute the 1-min first swing separately (its end is 09:27), then seed
    # the second swing with 09:28 OHLC and feed 09:29 onward.
    swing_mode = cfg.get("swing_mode", "none")
    fs2_dir: str | None = None
    fs2_confirmed_idx: int = -1
    # 1-min first swing info (used for 2nd swing direction detection)
    fs1_1min_dir: str | None = None
    fs1_1min_confirmed_idx: int = -1
    fs1_1min_end_idx: int = -1
    fs1_1min_end_px: float = float("nan")
    fs1_1min_end_time: str = ""
    m1_day_candles: list[dict] = []
    # Keep 5min first swing for bias/entry logic, but for second swing on 1min we
    # use the 1-min first swing's end (09:27) as the anchor, matching the chart.
    # Always compute 1-min first swing if 1-min data is available, so the gate
    # can use the EARLIER of (1-min FS confirmed, 5-min FS confirmed) regardless
    # of swing_mode. The 1-min FS confirms earlier (09:30 vs 10:25 for 28-Aug)
    # and is the correct one after the revert.
    m1_day_candles = _prep_day(m1_day) if m1_day is not None else []
    fs1_1min_dir: str | None = None
    fs1_1min_confirmed_idx: int = -1
    fs1_1min_end_idx: int = -1
    fs1_1min_end_px: float = 0.0
    fs1_1min_end_time: str = ""
    if m1_day_candles:
        fs1_1min_dir, _, _, fs1_1min_confirmed_idx, fs1_1min_end_idx, fs1_1min_end_px, fs1_1min_end_time = _classify_first_swing_v2(m1_day_candles, result["date"])
    # Map 1-min FS confirmed idx to 5-min bar idx for the entry loop gate
    fs1_1min_confirmed_idx_5 = -1
    if m1_day_candles and fs1_1min_confirmed_idx >= 0:
        mts = m1_day_candles[fs1_1min_confirmed_idx].get("ts", 0)
        for k5, c5 in enumerate(candles):
            if c5.get("ts", 0) <= mts:
                fs1_1min_confirmed_idx_5 = k5
            else:
                break
    result["fs1_1min_confirmed_idx_5min"] = fs1_1min_confirmed_idx_5
    result["fs1_1min_confirmed_time"] = fs1_1min_end_time

    if use_1m and swing_mode == "opposite_swing_needed" and swing_dir is not None and fs1_end_idx >= 0:
        # Use 1-min first swing if available, else fall back to 5-min
        use_fs1_for_2nd_dir = fs1_1min_dir if fs1_1min_dir is not None else swing_dir
        use_fs1_end_idx = fs1_1min_end_idx if fs1_1min_end_idx >= 0 else fs1_end_idx
        use_fs1_end_px = fs1_1min_end_px if fs1_1min_end_idx >= 0 else fs1_end_px
        use_fs1_end_time = fs1_1min_end_time if fs1_1min_end_idx >= 0 else fs1_end_time
        # For second swing we want the *next* candle after the cyan end as the new 09:15
        # (09:28). When we have the 1-min cyan end, we can seed directly with 09:28
        # and feed 09:29 onward — no 5-min mapping needed for the seed.
        if use_fs1_for_2nd_dir is not None and use_fs1_end_idx >= 0:
            # If we have a valid 1-min cyan end, do direct 1-min second swing
            if fs1_1min_end_idx >= 0 and m1_day_candles:
                from datetime import datetime, timezone, timedelta
                from src.firstswing import FirstSwingEngine
                from src.walker import FlowCandle as _FC
                IST = timezone(timedelta(hours=5, minutes=30))
                seed_idx = fs1_1min_end_idx + 1  # 09:28
                if seed_idx < len(m1_day_candles):
                    seed_c = m1_day_candles[seed_idx]
                    seed_dt = datetime.fromtimestamp(int(seed_c.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if seed_c.get("ts") else f"{result['date']}T{seed_c.get('time','00:00')}:00"
                    seed_fc = _FC(date=seed_dt, open=float(seed_c["open"]), high=float(seed_c["high"]), low=float(seed_c["low"]), close=float(seed_c["close"]))
                    eng2 = FirstSwingEngine()
                    eng2.reset_with_candle(seed_fc, seed_idx)
                    # Build flow for 09:29 onward
                    for j in range(seed_idx+1, len(m1_day_candles)):
                        mc = m1_day_candles[j]
                        dt = datetime.fromtimestamp(int(mc.get("ts", 0)), tz=IST).strftime("%Y-%m-%dT%H:%M:%S") if mc.get("ts") else f"{result['date']}T{mc.get('time','00:00')}:00"
                        fc = _FC(date=dt, open=float(mc["open"]), high=float(mc["high"]), low=float(mc["low"]), close=float(mc["close"]))
                        eng2.process_bar(fc, j)
                    if eng2.declared:
                        fs2_dir = "buying" if eng2.dir == "up" else "selling"
                        # Map 1-min confirmed idx back to 5-min for gate (entry loop is 5-min)
                        def m1_to_5(idx: int) -> int:
                            mts = m1_day_candles[idx].get("ts", 0)
                            res = 0
                            for k5, c5 in enumerate(candles):
                                if c5.get("ts", 0) <= mts:
                                    res = k5
                                else:
                                    break
                            return res
                        fs2_confirmed_idx = m1_to_5(eng2.confirmed_at_idx)
                        fs2_events: list[dict] = [
                            {"type": "swing2_classified", "dir": fs2_dir, "bar": m1_to_5(eng2.start_idx), "time": eng2.start_time, "first_swing": use_fs1_for_2nd_dir},
                            {"type": "fs2_segment", "dir": eng2.dir, "start_idx": m1_to_5(eng2.start_idx), "start_px": eng2.start_px, "end_idx": m1_to_5(eng2.end_idx), "end_px": eng2.end_px, "confirmed_at_idx": fs2_confirmed_idx, "confirmed_at_time": eng2.confirmed_at_time},
                        ]
                        # also include break marks for chart if needed
                        fs2_events.append({"type": "fs_breaks_2", "breaks": [{"idx": b.idx, "time": b.time, "kind": b.kind, "dir": b.dir, "px": b.px} for b in eng2.break_marks]})
                    else:
                        fs2_dir = None
                        fs2_confirmed_idx = -1
                        fs2_events = [{"type": "no_second_swing_declared"}]
                else:
                    fs2_dir = None
                    fs2_confirmed_idx = -1
                    fs2_events = [{"type": "no_second_swing", "reason": "no_seed_after_cyan"}]
                result["events"].extend(fs2_events)
                result["swing2_direction"] = fs2_dir
                result["swing2_confirmed_idx"] = fs2_confirmed_idx
                swing_dir_for_gate = use_fs1_for_2nd_dir
            else:
                # Fallback to original 5-min→1-min mapping path
                fs2_dir, _fs2_start, _fs2_ev, fs2_confirmed_idx = detect_second_swing(
                    candles, result["date"], use_fs1_for_2nd_dir, use_fs1_end_idx, use_fs1_end_px, use_fs1_end_time,
                    m1_candles=m1_day_candles if m1_day_candles else None,
                )
                result["events"].extend(_fs2_ev)
                result["swing2_direction"] = fs2_dir
                result["swing2_confirmed_idx"] = fs2_confirmed_idx
                swing_dir_for_gate = use_fs1_for_2nd_dir
        else:
            result["swing2_direction"] = None
            result["swing2_confirmed_idx"] = -1
            swing_dir_for_gate = swing_dir
    else:
        result["swing2_direction"] = None
        result["swing2_confirmed_idx"] = -1
        swing_dir_for_gate = swing_dir

    # ── entry-swing gate ──
    # The ENTRY GATE is always the FIRST SWING (cyan line). The second swing
    # (yellow line) is used only for DIRECTION FILTERING, not the gate.
    gate_first_dir = locals().get("swing_dir_for_gate", swing_dir)
    if use_1m and swing_mode == "opposite_swing_needed":
        # Gate uses the first-swing confirmed index from the relevant timeframe.
        # After the revert, the 1-min FsV2 correctly finds FS at 09:30 (idx 15).
        # Use 1-min FS confirmed (mapped to 5-min idx) if available, else 5-min FS.
        # The earlier gate time is the correct one — FS or SUS confirms the first swing.
        if fs1_1min_confirmed_idx_5 >= 0:
            entry_swing_confirmed_idx = fs1_1min_confirmed_idx_5
        else:
            entry_swing_confirmed_idx = fs_confirmed_idx

        if fs2_dir is not None and fs2_dir != gate_first_dir:
            result["events"].append({
                "type": "second_swing_armed",
                "dir": fs2_dir,
                "confirmed_at_idx": fs2_confirmed_idx,
                "gate_uses_fs1": True,
            })
        else:
            # Same direction as first swing or not declared → skip day.
            entry_swing_confirmed_idx = 9999999
            result["events"].append({
                "type": "skipped_same_direction_swing2",
                "fs1_dir": gate_first_dir,
                "fs2_dir": fs2_dir,
            })
    else:
        # 5min OR swing_mode=none: use FsV2 gate (existing behavior).
        # If we have a valid 1-min first swing, prefer it (it's the correct one
        # after the revert — 1-min FS confirms earlier at 09:30 vs 5-min at 10:25).
        if use_1m and fs1_1min_confirmed_idx_5 >= 0:
            entry_swing_confirmed_idx = fs1_1min_confirmed_idx_5
        else:
            entry_swing_confirmed_idx = fs_confirmed_idx

    def _manage_1m_chunk(trade: dict, upto_ts: int) -> bool:
        """Delegate 1-min exit management to the intraday_1m module."""
        return manage_1m_chunk(
            trade, m1_day, upto_ts, cfg,
            on_exit=lambda price, outcome, exit_time, exit_ts:
                _close_trade(trade, i, price, outcome, exit_time=exit_time, exit_ts=exit_ts),
        )


    while i < len(candles):
        cur = candles[i]

        # ---- WalkerEngine: feed candles and collect pivots for prev_pivot SL + pivot_break entry ----
        dt_str = f"{result['date']}T{cur['time']}:00"
        fc = FlowCandle(date=dt_str, open=cur["open"], high=cur["high"], low=cur["low"], close=cur["close"])
        new_pivots = walker.process_bar(fc, i)
        for p in new_pivots:
            if p.kind == "H":
                normal_highs.append(p)
            else:
                normal_lows.append(p)

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
                        if cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:
                            _close_trade(t, i, cur["close"], "ft_fail")
                            exited = True
                    else:
                        if cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:
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
                    elif cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] < t["dom_low"]:
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
                    elif cfg["ft_fail_enabled"] and not t["validated"] and i <= t["validate_until"] and cur["close"] > t["dom_high"]:
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

        # ---- 1-min precision entry hunt ----
        # When a direct pace break was deferred in 1-min mode, resolve it now
        # using the most recent 1-min bar close that falls inside this 5-min bar.
        # MUST respect the swing gate + entry-window + max-entries, same as every
        # other entry path. pending_direct was set when can_enter was True (gate open
        # at that moment), but the 1-min bar close may arrive on a subsequent 5-min
        # bar iteration where the gate needs to be re-verified.
        if open_trade is None and pending_direct is not None and use_1m:
            # Recompute the gate check here — same formula as can_enter below.
            # This ensures the 1-min hunt fires only when the gate is still open.
            gate_ok = entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx
            # In 1-min mode, the ENTRY_START minimum is bypassed for pending_direct
            # since the entry window is already controlled by the fs_gate (first swing
            # confirmation). The pending_direct entry was armed AFTER the swing confirmed
            # and after entry_start, so it's safe to allow it without re-checking ENTRY_START.
            window_ok = ENTRY_START <= cur["time"] <= ENTRY_END
            if use_1m:
                window_ok = True  # Trust the fs_gate + entry_start already enforced at arm time
            entries_ok = entries_done < MAX_ENTRIES
            if not (gate_ok and window_ok and entries_ok):
                # Gate/window still closed: drop the deferred entry.
                # Rationale: pace breaks detected before the gate has no trade value
                # once the gate finally opens (the 1-min bar is stale). A 9:45 pace
                # break firing as a 10:25 entry violates "can't trade before swing
                # confirmed". Drop it and let the retest path re-arm if needed.
                result["events"].append({
                    "type": "setup_disarmed_pre_gate",
                    "bar": i,
                    "time": cur["time"],
                    "reason": "swing_gate_not_open_yet",
                    "armed_ts": int(pending_direct.get("armed_ts", 0)),
                })
                pending_direct = None
            else:
                m1_bar = resolve_pending_direct(pending_direct, m1_day, cur["ts"])
                if m1_bar is not None and m1_bar["ts"] <= cur["ts"]:
                    if _open_trade(
                        pending_direct["bar_idx"],
                        pending_direct["trade_dir"],
                        pending_direct["level"],
                        candles[pending_direct["bar_idx"]],
                        pending_direct["break_type"],
                        m1_bar=m1_bar,
                    ):
                        pending_direct = None

        # ---- square-off / window guards for NEW work ----
        # FsV2 gate: wait for first-swing confirmation before entering.
        # Every trade must happen AFTER the entry-relevant swing is confirmed.
        # For 1min with swing_mode=opposite_swing_needed → wait for second swing.
        # Otherwise → wait for first swing (FsV2 gate).
        fs_gate_ok = entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx
        # In 1-min mode, entry window starts from the first swing confirmation
        # (fs1_1min_end_time or fs1_end_time). This allows earlier entries (e.g. 09:36)
        # after a 1-min FS confirms at 09:30, instead of the hardcoded 09:45 minimum.
        # 5-min mode retains the default 09:45 start.
        entry_start = ENTRY_START
        if use_1m:
            # Use the 1-min FS end time if available, else 5-min FS end time
            fs_end_t = fs1_1min_end_time if fs1_1min_end_time else fs1_end_time
            if fs_end_t and fs_end_t < ENTRY_START:
                entry_start = fs_end_t
        can_enter = (
            open_trade is None
            and entries_done < MAX_ENTRIES
            and entry_start <= cur["time"] <= ENTRY_END
            and fs_gate_ok
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

        # ---- entry trigger: pace_break or pivot_break ----
        if i > 0 and cur_swing is not None and can_enter:
            trade_dir = -1 if cur_swing == "buying" else 1
            if cfg.get("entry_method") == "pivot_break":
                # In 1-min mode, pivot_break uses the 1-min Walker's sealed pivots
                # (finer-grained structure, e.g. the 10:23 low on the 1-min chart)
                # rather than 5-min pivots. Detection scans for the most recent
                # sealed pivot at or before the current 5-min bar's time, then checks
                # if the 5-min bar's LOW (short) or HIGH (long) broke through it.
                brk = None
                if use_1m and walker_1m is not None:
                    cur_5_ts = cur["ts"]
                    # find the last 1-min bar whose ts <= current 5-min bar's ts
                    m1_end_idx = -1
                    for k in range(len(m1_candles) - 1, -1, -1):
                        if m1_candles[k]["ts"] <= cur_5_ts:
                            m1_end_idx = k
                            break
                    if m1_end_idx >= 0:
                        if trade_dir == -1 and normal_lows_1m:
                            # SHORT pivot break: the 5-min bar's LOW breaks below the
                            # most recent sealed L-pivot.
                            for piv in reversed(normal_lows_1m):
                                if piv.idx <= m1_end_idx:
                                    if cur["low"] < piv.px:
                                        brk = {"type": "pivot_break", "level": piv.px, "bar": i}
                                    break
                        elif trade_dir == 1 and normal_highs_1m:
                            for piv in reversed(normal_highs_1m):
                                if piv.idx <= m1_end_idx:
                                    if cur["high"] > piv.px:
                                        brk = {"type": "pivot_break", "level": piv.px, "bar": i}
                                    break
                if brk is None:
                    brk = detect_pivot_break(candles, i, trade_dir, normal_highs, normal_lows)
            else:
                brk = detect_pace_break(candles, i, cur_swing, swing_extreme, _swing_size(), base_avg)
            if brk is not None:
                # break of a buying swing = selling pressure -> expect SUPPORT longs
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
                    if brk["type"] in ("domination", "candle-size", "pivot_break"):
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
                        if use_1m:
                            # 1-min precision: defer the entry to the next 1-min bar close.
                            # The 5-min close has already printed; the 1-min bar that
                            # closes inside this 5-min bar gives a tighter entry price.
                            # Resolved in the 1-min hunt loop below (after _manage_1m_chunk).
                            pending_direct = {
                                "bar_idx": i,
                                "trade_dir": trade_dir,
                                "level": brk["level"],
                                "break_type": brk["type"],
                                "armed_ts": int(cur["ts"]),
                            }
                            result["events"].append({
                                "type": "pending_direct_1m",
                                "bar": i, "time": cur["time"],
                                "ts": int(cur["ts"]),
                                "level": round(brk["level"], 2),
                                "break_type": brk["type"],
                            })
                            entered = False
                        else:
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
    # Preserve original ts (IST epoch) if present — recomputing from naive timestamp
    # treats 09:15 IST as 09:15 UTC (+5:30 error) and shifts swing times to 14:45.
    if "ts" in df.columns and not df["ts"].isna().all():
        df["ts"] = df["ts"].astype("int64")
    else:
        df["ts"] = (df["timestamp"].astype("int64") // 1_000_000_000).astype("int64")
    df = df.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
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


