"""Initial-bias engine — closing session direction + strength.

The label for trading day T is computed ONLY from day T-1's 5-minute candles
(purely pre-open information).

Hierarchy:
  1. Extreme zone (new_high/new_low/highs_extreme/lows_extreme) → overview overrides
  2. Closing session direction + strong sustain → closing session decides
  3. Overview lean as tiebreaker (non-extreme zones)
  4. UNBIASED — sab chup

Multi-day flow (3-6 day):
  Daily pivots tagged HH/HL/LH/LL across recent sessions
  HH+HL = bullish flow → bias stays bullish
  LH+LL = bearish flow → bias stays bearish
  Mix → no flow signal
"""

from __future__ import annotations

import pandas as pd

from .swing import find_pivots
from .overview import compute_overview, overview_for_next

# --- tunable thresholds -----------------------------------------------------
CLOSING_START = "12:00"
CLOSING_END = "15:30"
CLOSING_MIN_FRAC = 0.15        # |net move| >= 15% of day range to count as direction
SUSTAIN_FRAC = 0.30            # close in top/bottom 30% of session range = strong
PIVOT_N_CLOSING = 4            # pivot half-length for closing session (~20 min each side)
MIN_CANDLES = 20               # below this a session is treated as insufficient input


def _closing_session_window(day: pd.DataFrame) -> pd.DataFrame:
    """Filter day's candles to the closing session (12:00-15:30)."""
    t = day["timestamp"].dt.strftime("%H:%M")
    return day[(t >= CLOSING_START) & (t < CLOSING_END)].copy()


def _closing_session_direction(day: pd.DataFrame, day_rng: float) -> dict:
    """Direction: 12:00-15:30 net move / day range."""
    win = _closing_session_window(day)
    if win.empty or day_rng <= 0:
        return {"signal": None, "net_pts": None, "frac": None}
    net = float(win["close"].iloc[-1]) - float(win["open"].iloc[0])
    frac = net / day_rng
    if frac >= CLOSING_MIN_FRAC:
        sig = "bullish"
    elif frac <= -CLOSING_MIN_FRAC:
        sig = "bearish"
    else:
        sig = None
    return {"signal": sig, "net_pts": round(net, 2), "frac": round(frac, 4)}


def _tag_sequence(swings: list[dict], kind: str) -> list[dict]:
    """Tag each swing vs the previous one of its kind: HH/LH for highs, HL/LL for lows."""
    tagged = []
    for i, p in enumerate(swings):
        if i == 0:
            tag = None
        else:
            rising = p["price"] > swings[i - 1]["price"]
            tag = ("HH" if rising else "LH") if kind == "high" else ("HL" if rising else "LL")
        tagged.append(
            {
                "index": int(p["index"]),
                "ts": int(p["ts"]),
                "price": float(p["price"]),
                "time": p["date"],
                "kind": kind,
                "tag": tag,
            }
        )
    return tagged


def _full_day_strength(day: pd.DataFrame) -> dict:
    """Strength: full-day pivots + close sustain within full day range.

    - Pivots from full day (9:15-15:30), n=PIVOT_N_CLOSING
    - Tag HH/HL/LH/LL
    - Structure: HH+HL = bullish, LH+LL = bearish, mix = unclear
    - Sustain: close position within FULL DAY range
      top/bottom 30% = strong, middle 40% = weak
    """
    out: dict = {
        "structure": "unclear",
        "sustain": "weak",
        "summary": "",
        "swings": [],
        "breaks": [],
    }

    n = PIVOT_N_CLOSING
    if len(day) < 2 * n + 2 or day["timestamp"].dt.strftime("%H:%M").nunique() < 4:
        return out

    d = day.reset_index(drop=True)
    pivots = find_pivots(d, n)
    highs = [p for p in pivots if p["kind"] == "high"]
    lows = [p for p in pivots if p["kind"] == "low"]

    hs = _tag_sequence(highs, "high")
    ls = _tag_sequence(lows, "low")
    out["swings"] = sorted(hs + ls, key=lambda s: s["index"])

    # structure verdict
    hh = sum(1 for x in hs if x["tag"] == "HH")
    lh = sum(1 for x in hs if x["tag"] == "LH")
    hl = sum(1 for x in ls if x["tag"] == "HL")
    ll = sum(1 for x in ls if x["tag"] == "LL")

    highs_up = hh > lh if (hh + lh) > 0 else None
    lows_up = hl > ll if (hl + ll) > 0 else None

    if highs_up is True and lows_up is True:
        out["structure"] = "bullish"
    elif highs_up is False and lows_up is False:
        out["structure"] = "bearish"
    elif highs_up is not None or lows_up is not None:
        out["structure"] = "mixed"

    # sustain: close position within FULL DAY range
    day_hi = float(day["high"].max())
    day_lo = float(day["low"].min())
    day_rng = day_hi - day_lo
    if day_rng > 0:
        close_pos = (float(day["close"].iloc[-1]) - day_lo) / day_rng
        if close_pos >= (1 - SUSTAIN_FRAC):
            out["sustain"] = "strong"  # near day high
        elif close_pos <= SUSTAIN_FRAC:
            out["sustain"] = "strong"  # near day low
        else:
            out["sustain"] = "weak"
        out["close_pos_pct"] = round(close_pos * 100, 1)
    else:
        out["close_pos_pct"] = None

    # break-with-close on last swing high/low within full day
    breaks: list[dict] = []
    if highs:
        after = d.iloc[highs[-1]["index"] + 1 :]
        hit = after[after["close"] > highs[-1]["price"]]
        if not hit.empty:
            breaks.append({"kind": "above", "level": round(float(highs[-1]["price"]), 2),
                           "closed_beyond": True, "at": str(hit["timestamp"].iloc[0])})
    if lows:
        after = d.iloc[lows[-1]["index"] + 1 :]
        hit = after[after["close"] < lows[-1]["price"]]
        if not hit.empty:
            breaks.append({"kind": "below", "level": round(float(lows[-1]["price"]), 2),
                           "closed_beyond": True, "at": str(hit["timestamp"].iloc[0])})
    out["breaks"] = breaks

    # summary
    parts = [f"HHx{hh}/LHx{lh}", f"HLx{hl}/LLx{ll}"]
    brk_txt = []
    for b in breaks:
        side = "prior high" if b["kind"] == "above" else "prior low"
        brk_txt.append(f"{side} closed beyond")
    out["summary"] = "; ".join(parts) + (f" | {' & '.join(brk_txt)}" if brk_txt else "")
    return out


PIVOT_N_DAILY_FLOW = 6    # daily pivot half-length for flow detection (~6 sessions each side)
FLOW_LOOKBACK = 8         # look at last 8 daily bars for flow


def _multi_day_flow(daily_df: pd.DataFrame, today_idx: int) -> dict:
    """Multi-day flow: last 3-6 daily pivots tagged HH/HL/LH/LL.

    Returns {flow: 'bullish'|'bearish'|None, summary: str}.
    """
    out = {"flow": None, "summary": ""}
    n = PIVOT_N_DAILY_FLOW
    if today_idx < 2 * n + 2:
        return out

    hist = daily_df.iloc[:today_idx]
    pivots = find_pivots(hist.reset_index(drop=True), n)
    if len(pivots) < 4:
        return out

    highs = sorted([p for p in pivots if p["kind"] == "high"], key=lambda p: p["index"])
    lows = sorted([p for p in pivots if p["kind"] == "low"], key=lambda p: p["index"])

    # tag last 3-4 swings of each kind
    hh = lh = hl = ll = 0
    for i in range(1, len(highs)):
        if highs[i]["price"] > highs[i - 1]["price"]:
            hh += 1
        else:
            lh += 1
    for i in range(1, len(lows)):
        if lows[i]["price"] > lows[i - 1]["price"]:
            hl += 1
        else:
            ll += 1

    bullish_score = hh + hl
    bearish_score = lh + ll
    total = bullish_score + bearish_score

    if total >= 3:
        if bullish_score > bearish_score and bullish_score >= 3:
            out["flow"] = "bullish"
        elif bearish_score > bullish_score and bearish_score >= 3:
            out["flow"] = "bearish"
    out["summary"] = f"HHx{hh}/LHx{lh} HLx{hl}/LLx{ll}"
    return out


def _compute_single_bias(
    day: pd.DataFrame,
    prev: str,
    today: str,
    overview: dict,
    flow_map: dict[str, dict],
    groups: dict[str, pd.DataFrame],
    ordered_dates: list[str],
) -> dict:
    """Compute a single bias label for *today* using *prev* day's 5-min data."""
    hi = float(day["high"].max())
    lo = float(day["low"].min())
    rng = hi - lo

    cs = _closing_session_direction(day, rng)
    st = _full_day_strength(day)

    cs_sig = cs["signal"]
    strength = st["sustain"]
    structure = st["structure"]

    def _dir_txt(sig: str | None) -> str:
        if sig == "bullish":
            return f"buying held into 12-3:30 ({cs['net_pts']:+.0f} pts, {cs['frac']*100:.0f}% of day range)"
        if sig == "bearish":
            return f"selling held into 12-3:30 ({cs['net_pts']:+.0f} pts, {cs['frac']*100:.0f}% of day range)"
        return "12-3:30 flat/ambiguous"

    st_txt = f"closing structure {structure} ({st['summary']})" if st["summary"] else ""
    sustain_pct = st.get("close_pos_pct")
    sustain_txt = f"sustain: {strength}" + (f" (close at {sustain_pct}% of session range)" if sustain_pct is not None else "")

    details = {
        "prev_date": prev,
        "prev_close": float(day["close"].iloc[-1]),
        "closing_signal": cs_sig,
        "closing_net_pts": cs["net_pts"],
        "closing_frac": cs["frac"],
        "closing_sustain": strength,
        "closing_structure": structure,
    }

    # ---- Layer 1: daily-swing overview -----
    ov = overview.get(today)
    ov_zone = ov.get("zone") if ov else None
    ov_lean = ov.get("lean") if ov else None
    is_extreme = ov_zone in ("new_high", "new_low", "highs_extreme", "lows_extreme")

    # ---- Multi-day flow (3-6 day trend) -----
    fl = flow_map.get(today, {})
    fl_dir = fl.get("flow")
    fl_txt = f"flow: {fl_dir} ({fl.get('summary', '')})" if fl_dir else ""

    if ov_lean and is_extreme:
        lean = ov_lean
        if cs_sig == lean:
            bias = lean
            agree = "both layers agree"
        elif cs_sig is None:
            bias = lean
            agree = ""
        elif cs_sig and cs_sig != lean:
            prev_dates_before = [d for d in ordered_dates if d < prev]
            lower_high = False
            higher_low = False
            if prev_dates_before:
                prev_prev = prev_dates_before[-1]
                prev_prev_day = groups.get(prev_prev)
                if prev_prev_day is not None and len(prev_prev_day) > 0:
                    prev_hi = float(day["high"].max())
                    prev_prev_hi = float(prev_prev_day["high"].max())
                    lower_high = prev_hi < prev_prev_hi

                    prev_lo = float(day["low"].min())
                    prev_prev_lo = float(prev_prev_day["low"].min())
                    higher_low = prev_lo > prev_prev_lo

            # Bullish extreme: check lower_high + selling close
            # Bearish extreme: check higher_low + buying close
            if lean == "bullish":
                structural_failure = lower_high
                close_opposes = cs_sig == "bearish"
            else:
                structural_failure = higher_low
                close_opposes = cs_sig == "bullish"

            close_near_support = (strength == "strong" and close_opposes)

            if structural_failure and close_near_support:
                bias = "unbiased"
                if lean == "bullish":
                    agree = "indecision - extreme level + lower high + strong selling close"
                else:
                    agree = "indecision - extreme level + higher low + strong buying close"
            else:
                why = (
                    "extreme highs - retracement, no shorting"
                    if lean == "bullish"
                    else "extreme lows - retracement, no buying"
                )
                bias = lean
                agree = f"overview overrides ({why})"
        reason = f"[{ov_zone}] {ov['reason']}; prev day {prev}: {_dir_txt(cs_sig)}"
        if fl_txt:
            reason += f"; {fl_txt}"
        if st_txt:
            reason += f"; {st_txt}"
        reason += f"; {sustain_txt}"
        if agree:
            reason += f" - {agree}"
    elif cs_sig and strength == "strong":
        bias = cs_sig
        if ov_lean == cs_sig:
            reason = f"Prev day {prev}: {_dir_txt(cs_sig)}; {st_txt}; {sustain_txt} - closing session confirms overview"
        elif fl_dir == cs_sig:
            reason = f"Prev day {prev}: {_dir_txt(cs_sig)}; {st_txt}; {sustain_txt}; {fl_txt} - closing session + flow agree"
        else:
            reason = f"Prev day {prev}: {_dir_txt(cs_sig)}; {st_txt}; {sustain_txt} - strong closing session decides"
    elif ov_lean and ov_lean == fl_dir:
        bias = ov_lean
        reason = f"[{ov_zone}] {ov['reason']}; prev day {prev}: {_dir_txt(cs_sig)}; {st_txt}; {sustain_txt}; {fl_txt} - overview + flow agree"
    elif ov_lean:
        bias = ov_lean
        reason = f"[{ov_zone}] {ov['reason']}; prev day {prev}: {_dir_txt(cs_sig)}; {st_txt}; {sustain_txt}"
        if fl_txt:
            reason += f"; {fl_txt}"
    elif fl_dir:
        bias = fl_dir
        reason = f"Prev day {prev}: {_dir_txt(cs_sig)}; {st_txt}; {sustain_txt}; {fl_txt} - flow decides"
    else:
        bias, reason = "unbiased", f"Prev day {prev}: {_dir_txt(cs_sig)}"

    return {
        "date": today,
        "bias": bias,
        "reason": reason,
        "details": details,
        "overview": ov,
        "prev_day": {
            "structure": structure,
            "sustain": strength,
            "summary": st["summary"],
            "close_pos_pct": st.get("close_pos_pct"),
            "breaks": st["breaks"],
            "swings": st["swings"],
        },
    }


def compute_bias(df_5min: pd.DataFrame, daily_df: pd.DataFrame | None = None) -> list[dict]:
    """Return one bias label per trading day T, derived from day T-1.

    Hierarchy: extreme zone override > closing session > overview tiebreaker > unbiased.
    Multi-day flow (3-6 day HH/HL/LH/LL) adds confirmation weight.

    Also computes next-day bias for the last available date so users can
    plan tomorrow's trade tonight.

    CLOSE CORRECTION: daily-API close uses official index closing methodology
    and mismatches the 5-min last tick on ~244/261 rows (up to ±85 pts).
    Overview pos_pct needs yesterday's TRUE session close -> we rewrite the
    daily copy's `close` from 5-min data (O/H/L already match perfectly).
    """
    if daily_df is not None and len(daily_df) > 0 and df_5min is not None and len(df_5min) > 0:
        d5s = df_5min.copy()
        d5s["timestamp"] = pd.to_datetime(d5s["timestamp"])
        d5s = d5s.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
        d5_dates = d5s["timestamp"].dt.strftime("%Y-%m-%d")
        close_map = d5s.groupby(d5_dates)["close"].last()

        dd = daily_df.copy()
        dd["timestamp"] = pd.to_datetime(dd["timestamp"])
        dd_keys = dd["timestamp"].dt.strftime("%Y-%m-%d")
        dd["close"] = dd_keys.map(close_map).fillna(dd["close"])
        daily_df = dd

    overview = compute_overview(daily_df) if daily_df is not None else {}

    # Pre-compute multi-day flow for each day (from daily pivots)
    flow_map: dict[str, dict] = {}
    if daily_df is not None and len(daily_df) > 0:
        ddf = daily_df.copy()
        ddf["timestamp"] = pd.to_datetime(ddf["timestamp"])
        ddf = ddf.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
        ddf = ddf.reset_index(drop=True)
        d_dates = ddf["timestamp"].dt.strftime("%Y-%m-%d")
        for i in range(1, len(ddf)):
            flow_map[d_dates.iloc[i]] = _multi_day_flow(ddf, i)

    df = df_5min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")

    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d, g in df.groupby(dates, sort=True)}
    ordered_dates = sorted(groups)

    labels: list[dict] = []
    for today, prev in zip(ordered_dates[1:], ordered_dates[:-1]):
        day = groups[prev]
        if len(day) < MIN_CANDLES:
            labels.append(
                {
                    "date": today,
                    "bias": "unbiased",
                    "reason": f"Previous session {prev} has insufficient data ({len(day)} candles)",
                    "details": {"prev_date": prev},
                }
            )
            continue

        labels.append(
            _compute_single_bias(day, prev, today, overview, flow_map, groups, ordered_dates)
        )

    # --- Next-day bias: use last available date's data for the following trading day ---
    if ordered_dates:
        last_date = ordered_dates[-1]
        last_day = groups[last_date]
        if len(last_day) >= MIN_CANDLES:
            next_date = (pd.Timestamp(last_date) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")

            # Planning day: everything known so far is history, so overview
            # and flow must be computed for the synthetic next date too.
            if daily_df is not None and len(daily_df) > 0:
                ov_next = overview_for_next(daily_df, next_date)
                if ov_next is not None:
                    overview[next_date] = ov_next
                flow_map[next_date] = _multi_day_flow(ddf, len(ddf))

            labels.append(
                _compute_single_bias(last_day, last_date, next_date, overview, flow_map, groups, ordered_dates)
            )

    return labels


# ── Bias modes for master dropdown (clean separation) ───────────────────────

BIAS_MODES = ["daily_swing", "ema_daily_10", "ema_daily_5", "ema_5min_20_50", "opposite_first", "streak_3_1_1", "ema_daily_10_far_50", "ema_daily_5_far_50", "ema_5min_20_50_far_30", "ema_1min_5_far_20", "ema_1min_10_far_30", "ema_daily_10_inverse", "ema_daily_5_inverse", "ema_5min_20_50_inverse", "ema_1min_5_inverse", "ema_1min_10_inverse"]

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def compute_ema_bias(daily_df: pd.DataFrame, span: int = 10, use_hl2: bool = False) -> list[dict]:
    """EMA-based bias: close vs EMA(span). Pure daily trend, no overview/flow."""
    if daily_df is None or len(daily_df) == 0:
        return []
    df = daily_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df = df.reset_index(drop=True)
    price = (df["high"] + df["low"]) / 2 if use_hl2 else df["close"]
    ema = _ema(price, span)
    out = []
    for i in range(1, len(df)):
        today = df["timestamp"].dt.strftime("%Y-%m-%d").iloc[i]
        prev_close = float(df["close"].iloc[i-1]) if i-1 >=0 else 0
        # Use prior day's close vs EMA at prior day (no lookahead)
        prev_ema = float(ema.iloc[i-1])
        # Need prior day's close
        pc = float(df["close"].iloc[i-1])
        if pc > prev_ema:
            bias = "bullish"
            reason = f"EMA{span} daily trend: close {pc:.1f} > EMA {prev_ema:.1f} → bullish"
        elif pc < prev_ema:
            bias = "bearish"
            reason = f"EMA{span} daily trend: close {pc:.1f} < EMA {prev_ema:.1f} → bearish"
        else:
            bias = "unbiased"
            reason = f"EMA{span} daily: close {pc:.1f} == EMA"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"ema": prev_ema, "prev_close": pc}, "overview": None})
    # next-day
    if len(df) >= 1:
        last = df.iloc[-1]
        next_date = (pd.Timestamp(last["timestamp"]) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        pc = float(last["close"])
        ema_last = float(ema.iloc[-1])
        if pc > ema_last:
            bias = "bullish"
        elif pc < ema_last:
            bias = "bearish"
        else:
            bias = "unbiased"
        out.append({"date": next_date, "bias": bias, "reason": f"EMA{span} next-day: close {pc:.1f} vs EMA {ema_last:.1f}", "details": {"ema": ema_last, "prev_close": pc}, "overview": None})
    return out

def compute_ema_5min_bias(df_5min: pd.DataFrame, fast: int = 20, slow: int = 50) -> list[dict]:
    """5-min EMA cross bias: EMA20 > EMA50 → bullish, else bearish. Uses last 5-min bar per day."""
    if df_5min is None or len(df_5min) == 0:
        return []
    df = df_5min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df["ema_fast"] = _ema(df["close"], fast)
    df["ema_slow"] = _ema(df["close"], slow)
    # Group by date, take last bar per day as day's close_5m
    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    g = df.groupby(dates)
    ordered = sorted(g.groups.keys())
    out = []
    for i in range(1, len(ordered)):
        today = ordered[i]
        prev = ordered[i-1]
        # Use prev day's last bar EMA cross
        prev_grp = g.get_group(prev)
        last_row = prev_grp.iloc[-1]
        ef = float(last_row["ema_fast"])
        es = float(last_row["ema_slow"])
        if ef > es:
            bias = "bullish"
            reason = f"5min EMA{fast}>{slow}: {ef:.1f}>{es:.1f} → bullish"
        elif ef < es:
            bias = "bearish"
            reason = f"5min EMA{fast}<{slow}: {ef:.1f}<{es:.1f} → bearish"
        else:
            bias = "unbiased"
            reason = f"5min EMA{fast}=={slow}"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"ema_fast": ef, "ema_slow": es}, "overview": None})
    if ordered:
        last = ordered[-1]
        grp = g.get_group(last)
        last_row = grp.iloc[-1]
        ef = float(last_row["ema_fast"])
        es = float(last_row["ema_slow"])
        next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        if ef > es:
            bias = "bullish"
        elif ef < es:
            bias = "bearish"
        else:
            bias = "unbiased"
        out.append({"date": next_date, "bias": bias, "reason": f"5min EMA next: {ef:.1f} vs {es:.1f}", "details": {"ema_fast": ef, "ema_slow": es}, "overview": None})
    return out

def compute_opposite_first_bias(df_1min: pd.DataFrame) -> list[dict]:
    """Opposite of first swing: B→bearish (short), S→bullish (long). Ignores bias.py."""
    if df_1min is None or len(df_1min) == 0:
        return []
    df = df_1min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    # Need whole-day swings
    from .firstswing import compute_swing_results
    from .walker import FlowCandle
    # Build FlowCandles
    cands = []
    for _, row in df.iterrows():
        dt = row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")
        cands.append(FlowCandle(date=dt, open=float(row["open"]), high=float(row["high"]), low=float(row["low"]), close=float(row["close"])))
    swings = compute_swing_results(cands, {"timeCap": "09:29", "minBars": 14}, swing_count=1)  # first swing only
    # Map day -> first dir
    m = {s["day"]: s["seg"]["dir"] for s in swings}  # B or S
    # Need ordered dates from df
    dates = sorted(df["timestamp"].dt.strftime("%Y-%m-%d").unique().tolist())
    out = []
    for i in range(len(dates)):
        today = dates[i]
        dir_today = m.get(today)  # B/S for today’s first swing (intraday opposite)
        if dir_today == "B":
            bias = "bearish"  # B (buying) -> opposite short
            reason = f"Opposite of first swing: {today} first B (buying) → bearish (short) — fade first"
        elif dir_today == "S":
            bias = "bullish"
            reason = f"Opposite of first swing: {today} first S (selling) → bullish (long) — fade first"
        else:
            bias = "unbiased"
            reason = f"No first swing for {today}"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"first_dir": dir_today}, "overview": None})
    if dates:
        last = dates[-1]
        next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        # Next trading day's first swing unknown at planning time → unbiased
        out.append({"date": next_date, "bias": "unbiased", "reason": "Opposite first next-day: first swing unknown → unbiased", "details": {}, "overview": None})
    return out

def compute_streak_bias(daily_df: pd.DataFrame, streak_len: int = 3) -> list[dict]:
    """Daily color streak 3-1-1: 3 in streak → trade regime, 4th break still fade, 5th pause, then flip."""
    if daily_df is None or len(daily_df) == 0:
        return []
    df = daily_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df["date_str"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["color"] = df.apply(lambda r: "green" if float(r["close"]) > float(r["open"]) else "red" if float(r["close"]) < float(r["open"]) else "doji", axis=1)
    colors = list(df[["date_str","color"]].itertuples(index=False, name=None))
    regime_for_day = {}
    for i in range(len(colors)):
        date_str = colors[i][0]
        if i == 0:
            regime_for_day[date_str] = "unbiased"
            continue
        cur_reg = None
        streak = 0
        pause = False
        for j in range(i):
            col = colors[j][1]
            if pause:
                if col == "green":
                    cur_reg = "long"
                elif col == "red":
                    cur_reg = "short"
                else:
                    cur_reg = None
                streak = 1 if cur_reg else 0
                pause = False
                continue
            if cur_reg is None:
                if col == "green":
                    cur_reg = "long"
                    streak = 1
                elif col == "red":
                    cur_reg = "short"
                    streak = 1
                continue
            regime_color = "green" if cur_reg=="long" else "red"
            if col == regime_color:
                streak += 1
            else:
                # break
                pause = True
        if pause:
            regime_for_day[date_str] = "unbiased"
        else:
            if cur_reg == "long":
                regime_for_day[date_str] = "bullish"
            elif cur_reg == "short":
                regime_for_day[date_str] = "bearish"
            else:
                regime_for_day[date_str] = "unbiased"
    # Convert to labels list sorted by date
    dates = sorted(regime_for_day.keys())
    out = []
    for d in dates:
        bias = regime_for_day[d]
        out.append({"date": d, "bias": bias, "reason": f"Streak {streak_len}-1-1 regime: {bias}", "details": {}, "overview": None})
    # Next day is already included as last regime_for_day includes next? Actually colors includes all daily dates, regime_for_day includes each date's regime based on prior, so last date's regime is for last date itself (which is based on prior). Need next-day
    if dates:
        last = dates[-1]
        next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        # Compute regime for next date by simulating one more step with last color
        # For simplicity, reuse last regime_for_day logic for next
        # If last day was pause, next is based on last color; else same regime
        # We'll just use last computed regime for next (conservative)
        bias = regime_for_day[last]
        # Actually should compute for next, but approximate as unbiased if last was pause else same
        # For now, just use unbiased for next
        out.append({"date": next_date, "bias": "unbiased", "reason": "Streak next-day placeholder", "details": {}, "overview": None})
    return out

def compute_ema_far_bias(daily_df: pd.DataFrame, span: int = 10, thr_pts: float = 50, inverse: bool = True) -> list[dict]:
    """Far-from-EMA mean-reversion: if dist = close - EMA >= thr → fade (short if far above), else follow trend or pause."""
    if daily_df is None or len(daily_df) == 0:
        return []
    df = daily_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df = df.reset_index(drop=True)
    price = df["close"]
    ema = _ema(price, span)
    out = []
    for i in range(1, len(df)):
        today = df["timestamp"].dt.strftime("%Y-%m-%d").iloc[i]
        prev_close = float(df["close"].iloc[i-1])
        prev_ema = float(ema.iloc[i-1])
        dist = prev_close - prev_ema
        if abs(dist) >= thr_pts:
            if inverse:
                bias = "bearish" if dist > 0 else "bullish"  # far above → short, far below → long (mean reversion)
                reason = f"Far EMA{span}: close {prev_close:.1f} dist {dist:+.1f} vs EMA {prev_ema:.1f} thr {thr_pts} → {bias} (fade)"
            else:
                bias = "bullish" if dist > 0 else "bearish"
                reason = f"EMA{span} trend: close {prev_close:.1f} dist {dist:+.1f} → {bias}"
        else:
            bias = "unbiased"
            reason = f"Near EMA{span}: dist {dist:+.1f} < thr {thr_pts} → unbiased pause"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"ema": prev_ema, "dist": dist, "thr": thr_pts}, "overview": None})
    if len(df) >= 1:
        last = df.iloc[-1]
        next_date = (pd.Timestamp(last["timestamp"]) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        out.append({"date": next_date, "bias": "unbiased", "reason": "Far EMA next-day placeholder", "details": {}, "overview": None})
    return out

def compute_ema_5min_far_bias(df_5min: pd.DataFrame, fast: int = 20, slow: int = 50, thr_pts: float = 30) -> list[dict]:
    """5min far: distance of close_5m to EMA cross midpoint, fade if far."""
    if df_5min is None or len(df_5min) == 0:
        return []
    df = df_5min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df["ema_fast"] = _ema(df["close"], fast)
    df["ema_slow"] = _ema(df["close"], slow)
    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    g = df.groupby(dates)
    ordered = sorted(g.groups.keys())
    out = []
    for i in range(1, len(ordered)):
        today = ordered[i]
        prev = ordered[i-1]
        prev_grp = g.get_group(prev)
        last_row = prev_grp.iloc[-1]
        ef = float(last_row["ema_fast"])
        es = float(last_row["ema_slow"])
        close = float(last_row["close"])
        mid = (ef + es) / 2
        dist = close - mid
        if abs(dist) >= thr_pts:
            bias = "bearish" if dist > 0 else "bullish"  # far above → short
            reason = f"5min Far EMA{fast}>{slow}: close {close:.1f} dist {dist:+.1f} mid {mid:.1f} thr {thr_pts} → {bias} (fade)"
        else:
            bias = "unbiased"
            reason = f"5min Near: dist {dist:+.1f} < thr {thr_pts} → unbiased"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"ema_fast": ef, "ema_slow": es, "dist": dist, "thr": thr_pts}, "overview": None})
    if ordered:
        last = ordered[-1]
        next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        out.append({"date": next_date, "bias": "unbiased", "reason": "5min Far next placeholder", "details": {}, "overview": None})
    return out

def compute_ema_inverse_bias(daily_df: pd.DataFrame, span: int = 10) -> list[dict]:
    """Inverse EMA: close > EMA -> bearish (short), close < EMA -> bullish (long) — no band, always fade."""
    if daily_df is None or len(daily_df) == 0:
        return []
    df = daily_df.copy()
    df["timestamp"] = pd.to_datetime(daily_df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df = df.reset_index(drop=True)
    price = df["close"]
    ema = _ema(price, span)
    out = []
    for i in range(1, len(df)):
        today = df["timestamp"].dt.strftime("%Y-%m-%d").iloc[i]
        prev_close = float(df["close"].iloc[i-1])
        prev_ema = float(ema.iloc[i-1])
        if prev_close > prev_ema:
            bias = "bearish"  # inverse: above -> short
            reason = f"EMA{span} inverse: close {prev_close:.1f} > EMA {prev_ema:.1f} → bearish (short, fade)"
        elif prev_close < prev_ema:
            bias = "bullish"
            reason = f"EMA{span} inverse: close {prev_close:.1f} < EMA {prev_ema:.1f} → bullish (long, fade)"
        else:
            bias = "unbiased"
            reason = f"EMA{span} inverse: close {prev_close:.1f} == EMA"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"ema": prev_ema, "prev_close": prev_close}, "overview": None})
    if len(df) >= 1:
        last = df.iloc[-1]
        next_date = (pd.Timestamp(last["timestamp"]) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        pc = float(last["close"])
        ema_last = float(ema.iloc[-1])
        if pc > ema_last:
            bias = "bearish"
        elif pc < ema_last:
            bias = "bullish"
        else:
            bias = "unbiased"
        out.append({"date": next_date, "bias": bias, "reason": f"EMA{span} inverse next: close {pc:.1f} vs EMA {ema_last:.1f}", "details": {}, "overview": None})
    return out

def compute_ema_1min_far_bias(df_1min: pd.DataFrame, span: int = 5, thr_pts: float = 20) -> list[dict]:
    """1min far: distance of 1min close to EMA(span) on 1min, fade if far."""
    if df_1min is None or len(df_1min) == 0:
        return []
    df = df_1min.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    df["ema"] = _ema(df["close"], span)
    dates = df["timestamp"].dt.strftime("%Y-%m-%d")
    g = df.groupby(dates)
    ordered = sorted(g.groups.keys())
    out = []
    for i in range(1, len(ordered)):
        today = ordered[i]
        prev = ordered[i-1]
        prev_grp = g.get_group(prev)
        last_row = prev_grp.iloc[-1]
        close = float(last_row["close"])
        ema = float(last_row["ema"])
        dist = close - ema
        if abs(dist) >= thr_pts:
            bias = "bearish" if dist > 0 else "bullish"
            reason = f"1min Far EMA{span}: close {close:.1f} dist {dist:+.1f} EMA {ema:.1f} thr {thr_pts} → {bias} (fade)"
        else:
            bias = "unbiased"
            reason = f"1min Near EMA{span}: dist {dist:+.1f} < thr {thr_pts} → unbiased"
        out.append({"date": today, "bias": bias, "reason": reason, "details": {"ema": ema, "dist": dist, "thr": thr_pts}, "overview": None})
    if ordered:
        last = ordered[-1]
        next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
        out.append({"date": next_date, "bias": "unbiased", "reason": "1min Far next placeholder", "details": {}, "overview": None})
    return out

def compute_bias_with_mode(df_5min: pd.DataFrame, daily_df: pd.DataFrame | None, df_1min: pd.DataFrame | None = None, mode: str = "daily_swing") -> list[dict]:
    """Dispatcher for master dropdown."""
    mode = (mode or "daily_swing").lower()
    if mode in ("daily_swing", "daily", "original"):
        return compute_bias(df_5min, daily_df)
    elif mode in ("ema_daily_10", "ema10", "ema_daily"):
        return compute_ema_bias(daily_df, span=10, use_hl2=False)
    elif mode in ("ema_daily_5", "ema5"):
        return compute_ema_bias(daily_df, span=5, use_hl2=False)
    elif mode in ("ema_5min_20_50", "ema_5min", "ema_cross"):
        return compute_ema_5min_bias(df_5min, fast=20, slow=50)
    elif mode == "ema_daily_10_far_50":
        return compute_ema_far_bias(daily_df, span=10, thr_pts=50, inverse=True)
    elif mode == "ema_daily_5_far_50":
        return compute_ema_far_bias(daily_df, span=5, thr_pts=50, inverse=True)
    elif mode == "ema_5min_20_50_far_30":
        return compute_ema_5min_far_bias(df_5min, fast=20, slow=50, thr_pts=30)
    elif mode == "ema_1min_5_far_20":
        return compute_ema_1min_far_bias(df_1min, span=5, thr_pts=20)
    elif mode == "ema_1min_10_far_30":
        return compute_ema_1min_far_bias(df_1min, span=10, thr_pts=30)
    elif mode in ("ema_daily_10_inverse", "ema10_inverse"):
        return compute_ema_inverse_bias(daily_df, span=10)
    elif mode in ("ema_daily_5_inverse", "ema5_inverse"):
        return compute_ema_inverse_bias(daily_df, span=5)
    elif mode in ("ema_5min_20_50_inverse", "ema_5min_inverse"):
        # For 5min inverse, we can reuse 5min far with thr 0 (always inverse, no band)
        # Instead, compute 5min cross inverse: EMA20>50 -> bearish (inverse of trend)
        # For simplicity, use 5min cross inverse logic here
        if df_5min is not None and len(df_5min) > 0:
            df = df_5min.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
            df["ema_fast"] = _ema(df["close"], 20)
            df["ema_slow"] = _ema(df["close"], 50)
            dates = df["timestamp"].dt.strftime("%Y-%m-%d")
            g = df.groupby(dates)
            ordered = sorted(g.groups.keys())
            out = []
            for i in range(1, len(ordered)):
                today = ordered[i]
                prev = ordered[i-1]
                last_row = g.get_group(prev).iloc[-1]
                ef = float(last_row["ema_fast"])
                es = float(last_row["ema_slow"])
                if ef > es:
                    bias = "bearish"  # inverse: cross up -> short
                elif ef < es:
                    bias = "bullish"
                else:
                    bias = "unbiased"
                out.append({"date": today, "bias": bias, "reason": f"5min EMA20>50 inverse: {ef:.1f} vs {es:.1f} → {bias}", "details": {}, "overview": None})
            if ordered:
                last = ordered[-1]
                next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
                out.append({"date": next_date, "bias": "unbiased", "reason": "5min inverse next", "details": {}, "overview": None})
            return out
        return compute_ema_5min_bias(df_5min, fast=20, slow=50)
    elif mode in ("ema_1min_5_inverse", "ema_1min_10_inverse"):
        span = 5 if "5" in mode else 10
        if df_1min is not None and len(df_1min) > 0:
            df = df_1min.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
            df["ema"] = _ema(df["close"], span)
            dates = df["timestamp"].dt.strftime("%Y-%m-%d")
            g = df.groupby(dates)
            ordered = sorted(g.groups.keys())
            out = []
            for i in range(1, len(ordered)):
                today = ordered[i]
                prev = ordered[i-1]
                last_row = g.get_group(prev).iloc[-1]
                close = float(last_row["close"])
                ema = float(last_row["ema"])
                if close > ema:
                    bias = "bearish"
                elif close < ema:
                    bias = "bullish"
                else:
                    bias = "unbiased"
                out.append({"date": today, "bias": bias, "reason": f"1min EMA{span} inverse: close {close:.1f} vs EMA {ema:.1f} → {bias}", "details": {}, "overview": None})
            if ordered:
                last = ordered[-1]
                next_date = (pd.Timestamp(last) + pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")
                out.append({"date": next_date, "bias": "unbiased", "reason": "1min inverse next", "details": {}, "overview": None})
            return out
        return []
    elif mode in ("opposite_first", "opposite"):
        # Needs 1min
        if df_1min is not None:
            return compute_opposite_first_bias(df_1min)
        # Fallback to 5min if no 1min
        return compute_opposite_first_bias(df_5min)
    elif mode in ("streak_3_1_1", "streak", "streak_3"):
        return compute_streak_bias(daily_df, streak_len=3)
    else:
        return compute_bias(df_5min, daily_df)
