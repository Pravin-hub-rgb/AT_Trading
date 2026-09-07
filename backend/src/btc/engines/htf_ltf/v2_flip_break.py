"""HTF-LTF v2 — Flip high/low break triggers LTF. When 1h Flip high/low breaks, then LTF trades in that direction.

For 1h Flip at 06:30, entry low/high break triggers LTF: if high breaks, long LTF; if low breaks, short LTF. This is more precise than just HTF window.
"""
from __future__ import annotations
import bisect
from typing import Optional

def simulate_htf_ltf_flip_break(
    candles_htf: list[dict],
    swings_htf: list[dict],
    candles_ltf: list[dict],
    swings_ltf: list[dict],
    fine_ltf: Optional[list[dict]] = None,
    *,
    htf_entry_break: str = "flip",
    ltf_entry_break: str = "decisive",
    sl_mode: str = "swing",
    rr_target: float = 3.0,
    ltf_trailing: str = "swing",
    htf_cap_days: int = 16,
) -> dict:
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    import bisect

    # HTF trades
    from src.btc.btc_routes import _load_fine_1m
    # HTF fine not needed for this, but we need HTF trades
    # Use HTF candles and swings to get HTF trades
    # We need to get HTF fine for HTF trades
    htf_fine = None
    # Find HTF fine via global? For now, assume fine_ltf covers HTF window as well (1m)
    # Use htf candles' fine as ltf fine's range (both cover same period)
    htf_trades = simulate_btc_trades_v7(
        candles_htf, swings_htf,
        entry_break=htf_entry_break, sl_mode=sl_mode, rr_target=rr_target, trailing="off", breakeven_r=0,
        fine=fine_ltf, entry_selection="stream", cap_days=htf_cap_days,
    )
    # For each HTF trade, determine flip high/low break levels
    # For HTF flip long, high break level = HTF flip candle high, low break level = HTF flip candle low
    # LTF trades: only those where LTF entry is after HTF flip candle high/low break in that direction
    # We need to find HTF flip candle for each HTF trade
    # The HTF trade's entry_idx corresponds to HTF flip candle's break confirmation? Actually entry_idx is break bar close, not flip candle high/low.
    # For this experiment, we define flip high/low as the HTF flip candle's high/low (the candle that formed the flip)
    # Use HTF trade's entry's swing? Simpler: Use HTF trade's entry candle high/low as trigger
    # LTF trade must have entry_ts > HTF flip candle's high/low break time
    htf_trades_filtered = []
    for ht in htf_trades:
        if ht["outcome"] == "open":
            continue
        # HTF flip candle high/low
        htf_entry_idx = ht["entry_idx"]
        # For HTF 1h, the flip candle is at entry_idx - maybe previous? Actually entry is break bar close, so flip candle is at entry_idx
        # Use that candle's high/low as levels
        htf_high = float(candles_htf[htf_entry_idx]["high"])
        htf_low = float(candles_htf[htf_entry_idx]["low"])
        htf_dir = 1 if ht["dir"]=="long" else -1
        # Find LTF trades that occur after HTF entry and before HTF exit, and where LTF entry breaks HTF flip high/low in same direction
        # For long HTF, LTF long must have broken HTF high at some point before LTF entry
        # For short HTF, LTF short must have broken HTF low
        # We need to collect all LTF trades and filter
        htf_trades_filtered.append((ht, htf_high, htf_low, htf_dir))

    # Now get all LTF trades (standalone) and filter
    from src.btc.btc_engine import simulate_btc_trades
    # Need LTF swings with appropriate minBars
    ltf_trades_all = simulate_btc_trades(
        candles_ltf, swings_ltf,
        entry_break=ltf_entry_break, sl_mode=sl_mode, rr_target=rr_target, trailing=ltf_trailing, breakeven_r=0,
        fine=fine_ltf, entry_selection="stream"
    )
    # Filter LTF trades by HTF flip high/low break
    filtered_ltf = []
    for lt in ltf_trades_all:
        lt_ts = int(lt["entry_ts"])
        lt_dir = 1 if lt["dir"]=="long" else -1
        # Find HTF interval containing lt_ts
        found = False
        for ht, htf_high, htf_low, htf_dir in htf_trades_filtered:
            htf_entry_ts = int(ht["entry_ts"])
            htf_exit_ts = int(ht["exit_ts"])
            if not (htf_entry_ts < lt_ts <= htf_exit_ts):
                continue
            if lt_dir != htf_dir:
                continue
            # Check if HTF flip high/low was broken before LTF entry
            # For long, need HTF high broken by LTF price action before LTF entry
            # Find if any LTF candle high between HTF entry and LTF entry broke HTF high
            # Find LTF indices between HTF entry and LTF entry
            # Find HTF flip candle idx to LTF entry idx range
            # For simplicity, check if LTF entry price itself broke HTF high/low
            # For long, LTF entry should be above HTF high; for short, below HTF low
            # Use LTF entry price vs HTF high/low
            if lt_dir == 1 and float(lt["entry_price"]) > htf_high:
                found = True
                break
            if lt_dir == -1 and float(lt["entry_price"]) < htf_low:
                found = True
                break
            # Alternative: check if any LTF high/low between HTF entry and LTF entry broke
            # Find LTF idx range
            # For now, require entry price break
        if found:
            filtered_ltf.append(lt)

    # Also need to handle busy for LTF filtered trades (they already have busy from standalone, but after filtering, need to re-apply busy? The LTF trades_all already have busy, so filtered will maintain non-overlap)
    # For HTF trades, keep as is
    # Return
    return {"htf_trades": htf_trades, "ltf_trades": filtered_ltf, "intervals": [(int(t["entry_ts"]), int(t["exit_ts"]), 1 if t["dir"]=="long" else -1) for t in htf_trades if t["outcome"]!="open"]}
