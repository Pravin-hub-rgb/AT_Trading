"""htf_ltf v4 — CHOP regime gate on the 1h Flip entries (built on v1_15m).

Rule: compute the Choppiness Index (default 14-bar) on the 1h series at each
HTF flip entry bar; skip the whole window when CHOP > chop_max.

VERDICT (2026-09-07, proper engine integration, busy-chain included): REJECTED.
    v1 combined (htf+ltf net):      +57.76 + 127.49 = +185.25R
    v4 lb14 chop<=55 combined:      +44.29 + 121.51 = +165.80R  (-19.5R)
    v4 lb14 chop<=61.8 combined:    +55.50 + 121.82 = +177.32R  (-7.9R)
    v4 lb20 chop<=55 combined:      +33.58 +  87.02 = +120.60R  (-64.7R)
    v4 lb14<=61.8 + v3 ext1.5:      +132.12 vs v3 alone +139.95  (-7.8R)
The earlier post-hoc estimate (+20.4R saved) was a busy-chain artifact: dropping
"choppy" windows frees the 1h engine to re-enter earlier and skips windows whose
LATER flips were profitable. IS and OOS both degrade. Kept as an isolated
variant (repo convention) — do not ship.

Orthogonal to v3's extension stop: pass ext_stop_r > 0 to combine both gates.

References: v1 204tr +127.49 net DD 17.52R | v3 (ext 1.5) 187tr +139.95 DD 13.15R.
"""
from __future__ import annotations
import math
from typing import Optional


def chop_series(candles_htf: list[dict], lb: int = 14) -> list[float]:
    """Choppiness Index per bar (lookback lb): 100*log10(sum TR / range)/log10(lb).

    ~0 = strong one-way trend, 100 = pure range. Neutral 50 when range is 0.
    """
    n = len(candles_htf)
    if n == 0:
        return []
    tr = [0.0] * n
    for i in range(n):
        c = candles_htf[i]
        if i == 0:
            tr[i] = float(c["high"]) - float(c["low"])
        else:
            pc = float(candles_htf[i - 1]["close"])
            tr[i] = max(
                float(c["high"]) - float(c["low"]),
                abs(float(c["high"]) - pc),
                abs(float(c["low"]) - pc),
            )
    pref = [0.0] * (n + 1)
    for i in range(n):
        pref[i + 1] = pref[i] + tr[i]
    out = [50.0] * n
    for i in range(n):
        lo_i = max(0, i - lb + 1)
        s_tr = pref[i + 1] - pref[lo_i]
        seg = candles_htf[lo_i:i + 1]
        hi = max(float(x["high"]) for x in seg)
        lo = min(float(x["low"]) for x in seg)
        rng = hi - lo
        if rng > 0 and s_tr > 0:
            out[i] = 100.0 * math.log10(s_tr / rng) / math.log10(lb)
    return out


def simulate_htf_ltf_chop(
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
    chop_lb: int = 14,
    chop_max: float = 61.8,
    ext_stop_r: float = 0.0,
) -> dict:
    """v1_15m with 1h entries gated by CHOP(chop_lb) <= chop_max.

    ext_stop_r > 0 additionally arms the v3 extension stop (gates combine).
    """
    from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m

    chop = chop_series(candles_htf, chop_lb)
    gate = (lambda i: chop[i] <= chop_max) if (chop_max > 0 and chop) else None
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
        htf_entry_gate=gate,
    )
