"""Overview layer (pre-open) — daily confirmed-swing ranges -> zone/path lean.

Port of `docs/1 - overview + bias creation (initial bias pre open).md` (§2, §3, §5, §6).

Lookahead safety (the core design constraint):
    Swings are Williams-fractal pivots on DAILY candles (same algorithm as the
    chart), but a pivot at bar j only becomes USABLE once bars j+1..j+n have
    CLOSED (confirmation lag, n = PIVOT_N_DAILY). We enforce this by recomputing
    pivots on the series truncated at T-1 for every label day T — identical to
    what a trader could actually know live. Backtest and front therefore share
    the same blind spots by construction.

Zone logic (course-aligned):
    Extreme zones (>85% / <15%) = strong lean (at highs/strength, at lows/weakness)
    High/Low zones (70-85% / 15-30%) = behavioral rule only ("don't short" / "don't buy")
        -> lean = None (neutral) — closing session decides
    Mid zones (30-70%) = depends on direction from SH/SL
        -> check if falling from high or rising from low
        -> only lean if clear signal, otherwise neutral

Key course rules:
    - One-line law: higher level test = strength, lower level = weakness
    - Steps rule: falling FROM high -> falls come in steps, bounce expected
    - Mirror: rising FROM low -> rises take resistance first
    - At ATH: don't short (but not necessarily "buy") — behavioral expectation
    - At lows: don't buy (but not necessarily "sell") — behavioral expectation
"""

from __future__ import annotations

import pandas as pd

from .swing import find_pivots

PIVOT_N_DAILY = 10        # same as chart default (docs/pinescript-swing-sr.md)
EXTREME_HIGH = 0.85       # pos >= -> strength extreme -> bullish lean
EXTREME_LOW = 0.15        # pos <= -> weakness extreme -> bearish lean
BEHAVIORAL_HIGH = 0.70    # pos >= -> "don't short" but no lean
BEHAVIORAL_LOW = 0.30     # pos <= -> "don't buy" but no lean
FALL_LEAN_START = 0.55    # falling-from-highs keeps buying lean while pos >= this
RISE_LEAN_END = 0.45      # rising-from-lows keeps selling lean while pos <= this


def _last_confirmed(day_slice: pd.DataFrame):
    """Latest confirmed swing high & low usable strictly before 'today'."""
    swings = find_pivots(day_slice, PIVOT_N_DAILY)
    highs = [s for s in swings if s["kind"] == "high"]
    lows = [s for s in swings if s["kind"] == "low"]
    return (highs[-1] if highs else None), (lows[-1] if lows else None)


def _prep_daily(daily_df: pd.DataFrame) -> pd.DataFrame:
    df = daily_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    return df.reset_index(drop=True)


def _zone_for(hist: pd.DataFrame, today: str) -> dict:
    """Zone/lean decision for *today* using only bars strictly before it.

    *hist* must already be sorted and contain every daily bar known before
    *today* opens (i.e. today itself excluded).
    """
    prev_close = float(hist["close"].iloc[-1])

    sh, sl = _last_confirmed(hist)
    if sh is None or sl is None:
        return {
            "zone": "none",
            "lean": None,
            "reason": "not enough confirmed daily swings yet",
        }

    rng = float(sh["price"]) - float(sl["price"])
    if rng <= 0:
        return {
            "zone": "none",
            "lean": None,
            "reason": "degenerate range (confirmed SH <= SL)",
        }

    pos = (prev_close - float(sl["price"])) / rng
    last_kind = "high" if sh["index"] >= sl["index"] else "low"

    base = {
        "sh_price": round(float(sh["price"]), 2),
        "sh_date": sh["date_only"],
        "sl_price": round(float(sl["price"]), 2),
        "sl_date": sl["date_only"],
        "pos_pct": round(pos * 100, 1),
    }

    # --- Extreme zones: strong lean (course: at highs = strength, at lows = weakness)
    if pos >= 1.0:
        zone = "new_high"
        lean = "bullish"
        reason = f"new high above SH {base['sh_price']} ({base['pos_pct']}% of range) - strength side"
    elif pos <= 0.0:
        zone = "new_low"
        lean = "bearish"
        reason = f"new low below SL {base['sl_price']} ({base['pos_pct']}% of range) - weakness side"
    elif pos >= EXTREME_HIGH:
        zone = "highs_extreme"
        lean = "bullish"
        reason = f"testing major highs ({base['pos_pct']}% of range) - strength extreme"
    elif pos <= EXTREME_LOW:
        zone = "lows_extreme"
        lean = "bearish"
        reason = f"testing major lows ({base['pos_pct']}% of range) - weakness extreme"

    # --- Behavioral zones: "don't short" / "don't buy" but NO lean
    elif pos >= BEHAVIORAL_HIGH:
        zone = "highs"
        lean = None
        reason = f"at major highs ({base['pos_pct']}% of range) - behavioral: no short, closing session decides"
    elif pos <= BEHAVIORAL_LOW:
        zone = "lows"
        lean = None
        reason = f"at major lows ({base['pos_pct']}% of range) - behavioral: no buy, closing session decides"

    # --- Mid zones: direction from SH/SL matters
    elif last_kind == "high":
        if pos >= FALL_LEAN_START:
            zone = "falling_from_highs"
            lean = "bullish"
            reason = (
                f"falling from SH {base['sh_price']} "
                f"({base['pos_pct']}% of range) - falls come in steps, bounce expected"
            )
        else:
            zone = "mid_fall_unclear"
            lean = None
            reason = (
                f"deep into fall from SH ({base['pos_pct']}% of range) - overview unclear"
            )
    else:  # last_kind == "low"
        if pos <= RISE_LEAN_END:
            zone = "rising_from_lows"
            lean = "bearish"
            reason = (
                f"rising from SL {base['sl_price']} "
                f"({base['pos_pct']}% of range) - rises take resistance first"
            )
        else:
            zone = "mid_rise_unclear"
            lean = None
            reason = f"extended rise from SL ({base['pos_pct']}% of range) - overview unclear"

    return {"zone": zone, "lean": lean, "reason": reason, **base}


def compute_overview(daily_df: pd.DataFrame) -> dict[str, dict]:
    """For every trading day T: overview computed ONLY from bars up to T-1.

    Returns {date: {zone, lean, reason, sh_price, sh_date, sl_price, sl_date,
    pos_pct}} where lean is 'bullish' | 'bearish' | None.
    """
    df = _prep_daily(daily_df)

    out: dict[str, dict] = {}
    dates = df["timestamp"].dt.strftime("%Y-%m-%d")

    for t in range(1, len(df)):
        out[dates.iloc[t]] = _zone_for(df.iloc[:t], dates.iloc[t])

    return out


def overview_for_next(daily_df: pd.DataFrame, next_date: str) -> dict | None:
    """Overview for a synthetic date (the next trading day after the data).

    Every row in *daily_df* is treated as closed history — correct for a
    pre-open planning label computed after the last session ended.
    """
    df = _prep_daily(daily_df)
    if len(df) == 0:
        return None
    return _zone_for(df, next_date)
