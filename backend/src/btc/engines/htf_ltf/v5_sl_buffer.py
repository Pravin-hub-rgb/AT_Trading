"""htf_ltf v5 - Extension Stop + ATR-buffered SL (built on v1_15m).

SL placement: touchable swing-start pivot PLUS 0.25 x ATR(14) buffer beyond the
pivot (away from entry). Survives exact-level stop-hunts and pivot retests for
~0.08% extra average risk.

Research 2026-09-07 (v3-gated 15m legs, FULL window, 1m fills, 0.05%+2pt):
    v3 (pivot SL)       187tr 32.6% +139.95 net PF 2.47 maxDD 13.15R maxL 14
    v5 (pivot+0.25ATR)  179tr 34.6% +152.77 net PF 2.70 maxDD 11.22R maxL 10
    combined book (1h+15m): +210.53R net / 19.78R maxDD / net-DD 10.64
    vs v3 combined +197.71R / 22.75R / 8.69 - dominates on every metric.
IS +80.08 (maxL 7) / OOS +72.69 - IS much stronger, OOS slightly under v3.
Runner-up family: highest-high/lowest-low N-bar structure stops (see v6).
"""
from __future__ import annotations


def simulate_htf_ltf_sl_buffer(
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
    sl_buf_atr: float = 0.25,
) -> dict:
    """v3 ext-stop + SL = swing-start pivot buffered by sl_buf_atr x ATR(14)."""
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
        sl_buf_atr=sl_buf_atr,
    )
