"""htf_ltf v6 - Extension Stop + N-bar structure-range SL (built on v1_15m).

SL placement: the highest high (short) / lowest low (long) of the last
sl_hhll_n 15m bars - a pure structure-range stop. The smooth-mode variant:
win rate jumps ~7 points, drawdown and loss streaks shrink hard, net R is
sacrificed slightly vs the pivot SL.

Research 2026-09-07 (v3-gated 15m legs, FULL window, 1m fills, 0.05%+2pt):
    v3 (pivot SL)     187tr 32.6% +139.95 net PF 2.47 maxDD 13.15R maxL 14
    v6 (hhll-30 SL)   169tr 39.6% +138.44 net PF 2.87 maxDD  9.27R maxL  9
    combined book (1h+15m): +196.21R net / 18.66R maxDD / net-DD 10.51
IS +61.80 / OOS +76.64 - balanced; N sweep 20-50 is a smooth plateau (robust).
For max net see v5 (pivot + 0.25 ATR buffer: +152.77 net, combined +210.53R).
"""
from __future__ import annotations


def simulate_htf_ltf_sl_hhll(
    candles_htf: list[dict],
    swings_htf: list[dict],
    candles_ltf: list[dict],
    swings_ltf: list[dict],
    fine_ltf=None,
    *,
    htf_entry_break: str = "flip",
    ltf_entry_break: str = "decisive",
    sl_mode: str = "swing",
    rr_target: float = 3.0,
    ltf_trailing: str = "swing",
    htf_breakeven: float = 0.0,
    ltf_breakeven: float = 0.0,
    htf_cap_days: int = 16,
    bias_timeline=None,
    day_gate=None,
    entry_selection: str = "stream",
    ext_stop_r: float = 1.5,
    sl_hhll_n: int = 30,
    cooldown_bars: int = 0,
) -> dict:
    """v3 ext-stop + SL = highest-high/lowest-low of the last sl_hhll_n bars."""
    from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m

    return simulate_htf_ltf_15m(
        candles_htf, swings_htf, candles_ltf, swings_ltf, fine_ltf,
        htf_entry_break=htf_entry_break,
        ltf_entry_break=ltf_entry_break,
        sl_mode=sl_mode,
        rr_target=rr_target,
        ltf_trailing=ltf_trailing,
        htf_breakeven=htf_breakeven,
        ltf_breakeven=ltf_breakeven,
        htf_cap_days=htf_cap_days,
        bias_timeline=bias_timeline,
        day_gate=day_gate,
        entry_selection=entry_selection,
        ext_stop_r=ext_stop_r,
        sl_hhll_n=sl_hhll_n,
        cooldown_bars=cooldown_bars,
    )
