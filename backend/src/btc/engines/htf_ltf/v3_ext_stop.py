"""htf_ltf v3 — Extension Stop (built on v1_15m).

Rule: while a 1h Flip cap16 window is open, same-direction 15m Decisive entries
are allowed only while the 1h leg is NOT yet ext_stop_r (default 1.5R) in
profit. Live framing: entry + 1.5 * (entry - initial SL) is a fixed level the
moment the 1h flip fills — price beyond it = no new 15m entries until the 1h
trade exits (SL / 3R target / 16d cap). Opposite-direction (fade) entries stay
blocked.

Research 2026-09-07 (FULL window, stream, 1m fills, 0.05%+2pt):
    v1 (baseline)      204tr 30.9% +127.49 net  PF 2.25  maxDD 17.52R  maxL 15
    v3 (ext stop 1.5R) 187tr 32.6% +139.95 net  PF 2.47  maxDD 13.15R  maxL 14
    IS  (< 2025-10-01): +56.3 (v1 +51.4)   OOS: +83.7 (v1 +76.1) — both improve.
Extension buckets (same-dir entries by 1h unrealized R at entry):
    -1..0R: PF 2.49 | 0..1R: PF 2.13 | 1..1.5R: PF 4.95 | 1.5..2R: PF 0.02 | >2R: PF 0.37
Fading when extended was tested and REJECTED (fade legs 13% WR, PF 0.54).
"""
from __future__ import annotations


def simulate_htf_ltf_ext_stop(
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
    htf_breakeven: float = 0.0,
    ltf_breakeven: float = 0.0,
    htf_cap_days: int = 16,
    bias_timeline=None,
    day_gate=None,
    entry_selection: str = "stream",
    ext_stop_r: float = 1.5,
    cooldown_bars: int = 0,
) -> dict:
    """v1_15m with the extension stop gate armed (ext_stop_r, default 1.5R)."""
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
        cooldown_bars=cooldown_bars,
    )
