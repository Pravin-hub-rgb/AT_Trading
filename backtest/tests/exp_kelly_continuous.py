"""KELLY, PROPERLY - and the halt-rule test that explains the era split.

PART A - is the halt rule the CAUSE of the OOS autocorrelation?
==============================================================
`exp_quant_autopsy.py` found the book's independence assumption is
era-dependent: IS ACF(lag1) +0.065 inside the +/-0.0877 band, OOS +0.4981
against a +/-0.1173 band. The hypothesis offered there was that
`max_consecutive_losses=3` causes it - in IS the halt fires often and chops
the loss sequence into runs of <=3 separated by skipped entries, which
mechanically de-correlates the booked series; in OOS it fires less and the
raw correlation survives.

That hypothesis is TESTABLE and is tested here: the ACF is recomputed with
the halt DISABLED (k=0) and with it enabled. If the halt is the mechanism,
k=0 should push OOS lag-1 ACF UP (less chopping) and leave IS roughly flat.
If k=0 does nothing, the halt is innocent and the era split has some other
cause that this file does not identify.

PART B - continuous Kelly with a long-run-variance correction
=============================================================
Binary Kelly f* = 2p-1 was negative here and is the wrong functional: the
book's R distribution is heavy-tailed (17 trades >= +10R in IS carry the
book), so mean is not win rate. The correct even-odds criterion for an
arbitrary payoff distribution is

    f* = mu / sigma^2

and when the bet returns are SERIALLY CORRELATED, sigma^2 must be the
LONG-RUN variance, not the naive one. The long-run variance is the
Newey-West / Bartlett form:

    sigma_LR^2 = sigma^2 * ( 1 + 2 * sum_{k=1..K} (1 - k/n) * rho_k )

with K = floor(4*(n/100)^(2/9)), the standard automatic bandwidth. This is
the correction the arXiv:2003.02743 result is about, in its long-run-
variance form, and it is what makes PART A matter: with OOS rho_1 = +0.498
the correction is LARGE and a naive mu/sigma^2 would over-bet.

Only FRACTIONAL Kelly is reported as actionable. Full Kelly on an estimated
edge is famously over-bet, and the whole point of the autocorrelation
correction is that the estimate is uncertain.

WHAT WOULD MAKE THIS ACTIONABLE
===============================
f* must be POSITIVE in both eras, must be SMALLER when corrected than
uncorrected (confirming the correction bites), and half-Kelly must be
validated on the era that did NOT estimate it. It is not a licence to
size up: this repo's policy is that nothing ships without the user's
adoption decision, and the engine has no size channel anyway.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_kelly_continuous.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_kelly_continuous.json"
LANE = "champion_multi_sw10"
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
FRACTIONS = (1.0, 0.5, 0.25)


def acf(x, lag):
    n = len(x)
    if n <= lag + 2:
        return None
    d = [v - statistics.fmean(x) for v in x]
    den = sum(v * v for v in d)
    return sum(d[i] * d[i + lag] for i in range(n - lag)) / den if den > 0 else None


def long_run_var(x, K=None):
    """Newey-West / Bartlett long-run variance of a mean-zero series."""
    n = len(x)
    d = [v - statistics.fmean(x) for v in x]
    g0 = sum(v * v for v in d) / n
    if g0 <= 0:
        return None, None, None
    if K is None:
        K = int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    tot = 0.0
    rhos = {}
    for k in range(1, K + 1):
        r = acf(x, k)
        if r is None:
            break
        rhos[k] = r
        tot += (1.0 - k / n) * r
    return g0 * (1.0 + 2.0 * tot), K, rhos


def kelly(rs):
    """f* = mu / sigma^2, naive and long-run corrected."""
    n = len(rs)
    mu = statistics.fmean(rs)
    g0, K, rhos = long_run_var(rs)
    if not g0 or g0 <= 0:
        return None
    return {"n": n, "mu": round(mu, 5),
            "sigma2_naive": round(g0, 5),
            "bandwidth_K": K,
            "sigma2_long_run": round(g0, 5) if not rhos else None,
            "rho1": round(rhos[1], 4) if rhos and 1 in rhos else None,
            "f_naive": round(mu / g0, 4)}


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "eras": {}}
    print("=" * 100, flush=True)
    print("  KELLY (continuous, long-run corrected) + halt-rule ACF test",
          flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        print(f"\n  === {scope.upper()} ===", flush=True)
        er = {}

        # ---------- PART A: is the halt the cause? ----------
        print("  [A] ACF with the loss-halt ON (k=3) vs OFF (k=0):", flush=True)
        for k in (3, 0):
            p = {**params, "max_consecutive_losses": k}
            tr = sim_fn(sim, data, p)
            trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
            rs = [float(t["r_multiple"]) for t in trades]
            m = equity_quality(tr, 3.67 if scope == "is" else 2.0)
            a1 = acf(rs, 1)
            a2 = acf(rs, 2)
            band = 1.96 / math.sqrt(len(rs))
            er[f"halt_k{k}"] = {"n": len(trades), "net": m["net"],
                                "acf1": (None if a1 is None else round(a1, 4)),
                                "acf2": (None if a2 is None else round(a2, 4)),
                                "band": round(band, 4),
                                "acf1_outside": (a1 is not None
                                                 and abs(a1) > band)}
            tag = "  <- shipped" if k == 3 else "  (halt disabled)"
            print(f"      k={k:<2} {len(trades):>4}t {m['net']:>+8.1f}R  "
                  f"ACF1 {a1:+.4f}  ACF2 {a2:+.4f}  band +/-{band:.4f}"
                  f"  {'OUTSIDE' if abs(a1) > band else 'inside'}{tag}",
                  flush=True)
        d_h = er["halt_k0"]["acf1"] - er["halt_k3"]["acf1"]
        er["acf1_delta_halt_off"] = round(d_h, 4)
        print(f"      -> disabling the halt moves ACF1 by {d_h:+.4f}"
              f"   (halt IS the mechanism: {abs(d_h) > 0.05})", flush=True)

        # ---------- PART B: continuous Kelly ----------
        base = sim_fn(sim, data, dict(params))
        trades = base["ltf_trades"] if isinstance(base, dict) else base
        rs = [float(t["r_multiple"]) for t in trades]
        kk = kelly(rs)
        g0, K, rhos = long_run_var(rs)
        glr = g0 * (1.0 + 2.0 * sum((1.0 - kk_ / len(rs)) * r
                                    for kk_, r in rhos.items())) if rhos else g0
        f_lr = (kk["mu"] / glr) if glr > 0 else None
        print(f"\n  [B] continuous Kelly on {len(rs)} trades:", flush=True)
        print(f"      mu = {kk['mu']:+.5f}R/trade", flush=True)
        print(f"      sigma^2 naive   = {kk['sigma2_naive']:.5f}"
              f"   -> f* = {kk['f_naive']:+.4f}", flush=True)
        print(f"      bandwidth K = {K} (Newey-West automatic)", flush=True)
        print(f"      sigma^2 long-run = {glr:.5f}"
              f"   -> f* = {f_lr:+.4f}" if f_lr else "      n/a", flush=True)
        print(f"      ACF shrinks the bet fraction by "
              f"{(1 - (f_lr / kk['f_naive'])) * 100:.1f}%"
              f" (rho1 = {kk['rho1']})" if f_lr and kk["f_naive"] else "      n/a",
              flush=True)
        print("      fractional (actionable only):", flush=True)
        for f in FRACTIONS:
            print(f"        {f:<5} full  {f_lr * f:+.4f}   half "
                  f"{(f_lr * f / 2):+.4f}" if f_lr else "        n/a",
                  flush=True)
        er["kelly"] = {**kk, "sigma2_long_run": round(glr, 5),
                       "f_long_run": (round(f_lr, 4) if f_lr else None),
                       "fractions": {str(f): (round(f_lr * f, 4) if f_lr
                                              else None) for f in FRACTIONS}}
        payload["eras"][scope] = er

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
