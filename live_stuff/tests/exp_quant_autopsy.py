"""QUANT AUTOPSY - autocorrelation, variance ratio, and Kelly sizing.

WHY THESE THREE, AND WHY NEVER DONE HERE
=========================================
Every sizing experiment in this repo was a MULTIPLIER on something already
known: sMZX used 1.5^count, vol-targeting used inverse-vol, the campaign
work used caps. None of them asked what the mathematically optimal bet
size IS. Kelly's criterion is that quantity, and it has never been
computed on this book.

Kelly also makes the autocorrelation question load-bearing. The classical
result K* = 2p-1 (Barmish/O'Brien/Burke, arXiv:2003.02743) assumes i.i.d.
bets, and that paper's whole contribution is that when bets are TEMPORALLY
CORRELATED the optimal fraction changes - and it explicitly notes this is a
different problem from the cross-sectional correlation portfolio theory
already handles. So:

    if trade P&L is autocorrelated, flat sizing is not neutral.
    It is one specific bet fraction, and it is probably not K*.

The autocorrelation also repairs the previous file's tautological streak
test. That one decomposed the sequence into runs, and a run decomposition
of a binary series always alternates - it measured the definition. The
correct statistic is the ACF of the P&L SERIES: P(trade N+1 loses | trade N
lost) against the base rate, read off lag-1 autocorrelation.

THE THREE MEASURES
==================
1. ACF(lag 1..10) of the trade R series, with a +/-1.96/sqrt(n) band.
   Outside the band = the book is not a sequence of independent bets, so
   K* = 2p-1 does not apply to it.

2. Lo-MacKinlay VARIANCE RATIO on the same series. VR(q) = Var(q-step
   returns) / (q * Var(1-step)). VR=1 is the random-walk null; VR>1 means
   positive autocorrelation / trending; VR<1 mean reversion. This is the
   formal test of whether ANY serial structure exists to exploit.

3. KELLY, correctly hedged. Full Kelly on an estimated edge is famously
   over-bet, so only FRACTIONAL Kelly is worth acting on. The point of the
   run is the COMPARISON between the shipped flat sizing and the
   Kelly-implied fraction - not a recommendation to bet more.

WHAT A RESULT WOULD AND WOULD NOT MEAN
======================================
ACF inside the band and VR ~ 1 => the book is close to i.i.d., flat sizing
is close to right, and the line is closed. That is a worthwhile clean
negative: the FIRST principled check of the book's independence assumption.

ACF OUTSIDE the band => sizing is a real lever nobody has pulled, and the
correct next step is fractional Kelly validated on the era that did NOT
estimate it. It is NOT a licence to size up on IS.

CAUSALITY
=========
Every input is a CLOSED trade's final R, used only to characterise the
historical series. That is legal for a sizing rule (fit on past R, applied
to the next bet) and ILLEGAL if any feature is allowed to pick WHICH trade
to take. Nothing in this file selects trades.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_quant_autopsy.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_quant_autopsy.json"
LANE = "champion_multi_sw10"
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
MAXLAG = 10
def acf(x, lag):
    """Sample autocorrelation of a series, mean already removed."""
    n = len(x)
    if n <= lag + 2:
        return None
    m = statistics.fmean(x)
    d = [v - m for v in x]
    den = sum(v * v for v in d)
    if den <= 0:
        return None
    return sum(d[i] * d[i + lag] for i in range(n - lag)) / den


def variance_ratio(x, q):
    """Lo-MacKinlay VR(q): Var(q-step sums) / (q * Var(1-step)).

    Under a random walk VR(q) = 1 for every q.
    """
    n = len(x)
    if n < 4 * q + 1:
        return None
    m = statistics.fmean(x)
    d = [v - m for v in x]
    one = sum(v * v for v in d) / (n - 1)
    if one <= 0:
        return None
    qsum = [sum(d[i:i + q]) for i in range(n - q + 1)]
    qm = statistics.fmean(qsum)
    qv = sum((s - qm) ** 2 for s in qsum) / (len(qsum) - 1)
    return qv / (q * one)


def kelly_fraction(rs):
    """Full-Kelly f for an even-money binary: f* = 2p - 1.

    p is the realised win rate, which is an UPPER bound on the true p
    whenever the book is autocorrelated. Recorded so the number is not
    mistaken for a recommendation.
    """
    n = len(rs)
    if n == 0:
        return None
    p = sum(1 for r in rs if r > 0) / n
    return {"win_rate": round(p, 4), "f_full": round(2 * p - 1, 4),
            "f_half": round((2 * p - 1) / 2, 4),
            "f_quarter": round((2 * p - 1) / 4, 4)}


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "maxlag": MAXLAG, "eras": {}}
    print("=" * 100, flush=True)
    print("  QUANT AUTOPSY - ACF, variance ratio, Kelly (never done here)",
          flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        tr = sim_fn(sim, data, dict(params))
        trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
        rs = [float(t["r_multiple"]) for t in trades]
        n = len(rs)
        exp_n, exp_net = BYBIT_BASE[scope]
        ctl = equity_quality(tr, 3.67 if scope == "is" else 2.0)
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R net "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        band = 1.96 / math.sqrt(n)
        print(f"    n={n}  +/-1.96/sqrt(n) band = +/-{band:.4f}", flush=True)
        a = [acf(rs, k) for k in range(1, MAXLAG + 1)]
        out_b = [k + 1 for k, v in enumerate(a) if v is not None and abs(v) > band]
        print("    ACF of trade R (the CORRECT streak test):", flush=True)
        for k, v in enumerate(a):
            if v is None:
                continue
            print(f"      lag {k+1:<2} {v:+.4f}"
                  f"{'  <-- outside band' if abs(v) > band else ''}", flush=True)

        vr = {q: variance_ratio(rs, q) for q in (2, 4, 8, 16)}
        print("    Variance ratio (1.0 = random walk):", flush=True)
        for q, v in vr.items():
            tag = ("" if v is None else
                   "  <-> >1 trending" if v > 1.15 else
                   "  <-> <1 mean-reverting" if v < 0.85 else "")
            print(f"      VR({q:<2}) {v if v is None else round(v, 3)}{tag}",
                  flush=True)

        kk = kelly_fraction(rs)
        print(f"    Kelly: win rate {kk['win_rate']:.4f}  f_full "
              f"{kk['f_full']:+.4f}  f_half {kk['f_half']:+.4f}  "
              f"f_quarter {kk['f_quarter']:+.4f}", flush=True)
        print(f"    shipped is FLAT 1.0x = {1.0/max(kk['f_full'], 1e-9):.2f}x "
              f"the full-Kelly fraction", flush=True)

        payload["eras"][scope] = {
            "n": n, "band": round(band, 4),
            "acf": [None if v is None else round(v, 4) for v in a],
            "lags_outside_band": out_b,
            "variance_ratio": {str(q): (None if v is None else round(v, 3))
                               for q, v in vr.items()},
            "kelly": kk,
        }

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
