"""1-minute precision execution for the intraday engine.

Extracted from intraday.py to keep the main engine readable. Owns:
- `manage_1m_chunk(trade, m1_day, upto_ts, cfg)` — color-aware exit fills
- `resolve_pending_direct(pending, m1_day)` — convert a pending 5-min direct entry
  into a 1-min bar close for precision timing

Design rule: when cfg['execution'] == '1min' AND a 1-min candle is available,
the entry fires at the 1-min bar close. The 5-min bar is used only for swing
context (SL calculation, level reference). Positions still display on both
charts via `entry_ts` / `entry_time`.
"""

from __future__ import annotations

import pandas as pd

# All 1min management constants live here so the main engine can stay slim.
EOD_EXIT = "15:15"


def _exit_outcome(t_dir: int, entry: float, cur_sl: float, init_sl: float) -> str:
    """Classify the exit reason for a fill at cur_sl (float-safe vs rounded stored sl)."""
    if t_dir == 1:
        if cur_sl >= entry - 1e-9:
            return "cost-to-cost"
        return "trail" if cur_sl > init_sl + 1e-9 else "sl"
    if cur_sl <= entry + 1e-9:
        return "cost-to-cost"
    return "trail" if cur_sl < init_sl - 1e-9 else "sl"


def manage_1m_chunk(
    trade: dict,
    m1_day: pd.DataFrame,
    upto_ts: int,
    cfg: dict,
    on_exit: callable,
) -> bool:
    """Color-aware 1-minute execution over bars since last processed ts.

    Ported from the BTC Strategy-3 engine: a candle's colour tells the
    intra-bar path — green means low printed early (adverse-first for longs),
    red means high printed early. Exits fill AT the level.
    Returns True when the trade closed.

    `on_exit(price, outcome, exit_time, exit_ts)` is called by the engine to
    actually close the trade (see `_close_trade` in intraday.py).
    """
    t_dir = 1 if trade["dir"] == "long" else -1
    entry = float(trade["entry_price"])
    init_risk = abs(entry - float(trade["sl"])) or 1e-9
    cur_sl = float(trade["_cur_sl"])
    max_profit = float(trade["_max_profit"])
    init_sl = float(trade["_init_sl"])
    trail_dist = float(cfg["trail_distance_r"]) * init_risk
    ladder_on = cfg["trailing"] == "ladder"

    rows = m1_day[(m1_day["ts"] > trade["_last_m1_ts"]) & (m1_day["ts"] <= upto_ts)]
    if rows.empty:
        return False

    for row in rows.sort_values("ts").itertuples():
        trade["_last_m1_ts"] = int(row.ts)
        hhmm = str(row.timestamp)[11:16]
        if hhmm >= EOD_EXIT:
            # square-off at this bar's open
            on_exit(float(row.open), "eod", hhmm + ":00", int(row.ts))
            return True

        green = float(row.close) > float(row.open)
        hi, lo, cl = float(row.high), float(row.low), float(row.close)
        exited = False

        if t_dir == 1:
            if green:
                # adverse first (low early)
                if lo <= cur_sl:
                    on_exit(cur_sl, _exit_outcome(t_dir, entry, cur_sl, init_sl),
                            str(row.timestamp)[11:16] + ":00", int(row.ts))
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
                        on_exit(cur_sl, _exit_outcome(t_dir, entry, cur_sl, init_sl),
                                str(row.timestamp)[11:16] + ":00", int(row.ts))
                        exited = True
                    elif not ladder_on and hi >= float(trade["target"]):
                        on_exit(float(trade["target"]), "target",
                                str(row.timestamp)[11:16] + ":00", int(row.ts))
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
                    on_exit(float(trade["target"]), "target",
                            str(row.timestamp)[11:16] + ":00", int(row.ts))
                    exited = True
                elif lo <= cur_sl or cl <= cur_sl:
                    px = cur_sl if lo <= cur_sl else cur_sl
                    on_exit(px, _exit_outcome(t_dir, entry, cur_sl, init_sl),
                            str(row.timestamp)[11:16] + ":00", int(row.ts))
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
                    on_exit(float(trade["target"]), "target",
                            str(row.timestamp)[11:16] + ":00", int(row.ts))
                    exited = True
                elif hi >= cur_sl or cl >= cur_sl:
                    on_exit(cur_sl, _exit_outcome(t_dir, entry, cur_sl, init_sl),
                            str(row.timestamp)[11:16] + ":00", int(row.ts))
                    exited = True
            else:
                # SHORT + green candle: adverse first (high early)
                if hi >= cur_sl:
                    on_exit(cur_sl, _exit_outcome(t_dir, entry, cur_sl, init_sl),
                            str(row.timestamp)[11:16] + ":00", int(row.ts))
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
                        on_exit(cur_sl, _exit_outcome(t_dir, entry, cur_sl, init_sl),
                                str(row.timestamp)[11:16] + ":00", int(row.ts))
                        exited = True
                    elif not ladder_on and lo <= float(trade["target"]):
                        on_exit(float(trade["target"]), "target",
                                str(row.timestamp)[11:16] + ":00", int(row.ts))
                        exited = True

        if exited:
            return True

    trade["_cur_sl"] = cur_sl
    trade["_max_profit"] = max_profit
    return False


def resolve_pending_direct(
    pending: dict,
    m1_day: pd.DataFrame,
    upto_ts: int,
) -> dict | None:
    """Resolve a pending 5-min direct entry into the FIRST 1-min bar that broke the pivot.

    When execution=1min, we want the entry to fire at the exact 1-min candle that
    actually broke the pivot level, not the last bar of the 5-min window.

    - For shorts (trade_dir=-1): find the FIRST bar whose low < level (pivot broken down)
    - For longs (trade_dir=1): find the FIRST bar whose high > level (pivot broken up)

    Returns the first breaking 1-min bar, or None if no break found in the window.
    Caller should re-check next bar if None.
    """
    if m1_day is None or len(m1_day) == 0:
        return None
    armed_ts = int(pending["armed_ts"])
    level = float(pending["level"])
    trade_dir = int(pending["trade_dir"])

    rows = m1_day[(m1_day["ts"] > armed_ts) & (m1_day["ts"] <= upto_ts)].sort_values("ts")
    if rows.empty:
        return None

    # Find the FIRST 1-min bar that actually broke the pivot level.
    # For shorts: low < level (price broke below pivot)
    # For longs: high > level (price broke above pivot)
    for _, bar in rows.iterrows():
        low = float(bar["low"])
        high = float(bar["high"])
        if trade_dir == -1 and low < level:
            return {
                "ts": int(bar["ts"]),
                "timestamp": bar["timestamp"],
                "open": float(bar["open"]),
                "high": float(bar["high"]),
                "low": low,
                "close": float(bar["close"]),
            }
        elif trade_dir == 1 and high > level:
            return {
                "ts": int(bar["ts"]),
                "timestamp": bar["timestamp"],
                "open": float(bar["open"]),
                "high": high,
                "low": float(bar["low"]),
                "close": float(bar["close"]),
            }

    return None