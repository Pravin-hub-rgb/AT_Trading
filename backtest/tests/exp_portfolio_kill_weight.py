"""PORTFOLIO, PART 2 - kill table + correlation-aware weighting.

PART 1 (`exp_portfolio_layer.py`) measured that the six alt books are
near-uncorrelated (mean pairwise monthly-R +0.072 IS / -0.053 OOS) and
that an equal-weight sleeve draws down 1.25-1.79x a single book rather
than 6x. Two things were left open, and this closes both.

1. KILL TABLE. The transfer rule (net>0 and n>=30 both eras) is weaker
   than the kills-clean bar 24.95 required. A book can be net positive and
   still be undeployable - a 30R drawdown inside one quarter, or a Sharpe
   below 0.5, makes it a bad sleeve even if the sum is positive. The exact
   K1-K7 definitions come from exp_stat_arb.py:75-83 and are applied
   here verbatim; the house thresholds K5 (n>=100 IS / n>=60 OOS) are NOT
   relaxed, and where 24.95 granted a differential exemption (K6/K7 fire
   on the bybit reference too, so they carry no information about a
   DIFFERENT instrument) the same exemption is applied and the raw value
   is printed either way.

2. WEIGHTING. Part 1 found the correlation matrix is near zero, which is
   exactly the condition under which equal weight is NOT the right answer -
   it ignores the pairs that are correlated (AVAX-BNB +0.60 OOS, NEAR-DOT
   +0.56 IS) and so quietly double-counts them. Three schemes are compared
   on the SAME pre-registered rule, with weights fitted on IS and applied
   untouched to OOS:
     equal      - 1/N each (part 1's baseline)
     inv_vol    - inverse of each book's realised monthly-R volatility
     inv_corr   - inverse-variance on the correlation matrix
   No scheme is selected on its OOS number. The comparison exists so the
   USER can see whether weighting matters at all before anyone builds it.

WHAT WOULD MAKE A SCHEME WIN
============================
Same bar as everything else here: positive in BOTH eras, no counted kills
in either, and any weighting scheme must beat equal weight on OOS without
having seen OOS. Since IS is 3.67y and OOS 2.0y, and the weights are fit
on IS only, the OOS leg is a genuine out-of-sample test of the SCHEME.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_portfolio_kill_weight.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_portfolio_kill_weight.json"
YEARS = {"is": 3.67, "oos": 2.0}
ASSETS = ("AVAXUSDT", "BNBUSDT", "LTCUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT")
KILL_MIN = {"is": 100, "oos": 60}
LANE = "age10_dirmatch_swingpause_single_sw10"


def _monthly(trades, months):
    out = {m: 0.0 for m in months}
    for t in trades:
        d = t.get("exit_date", "")
        if d[:7] in out:
            out[d[:7]] += float(t["r_multiple"])
    return [out[m] for m in months]


def _dd(seq):
    peak = cum = 0.0
    m = 0.0
    for v in seq:
        cum += v
        peak = max(peak, cum)
        m = max(m, peak - cum)
    return m


def _sharpe(mvals):
    if len(mvals) < 3:
        return None
    sd = statistics.pstdev(mvals)
    if sd <= 0:
        return None
    return statistics.fmean(mvals) / sd * (12 ** 0.5)


def _maxdd_trade(trades):
    return _dd([float(t["r_multiple"]) for t in trades])


def kill_table(trades, era, wr):
    """K1-K7, definitions verbatim from exp_stat_arb.py:75-83."""
    n = len(trades)
    if n == 0:
        return {k: True for k in ("K1", "K2", "K3", "K4", "K5", "K6")}, 0.0
    rs = [float(t["r_multiple"]) for t in trades]
    ordered = [float(t["r_multiple"])
               for t in sorted(trades, key=lambda z: int(z["exit_ts"]))]
    by_m = {}
    for t in trades:
        by_m.setdefault(t["exit_date"][:7], 0.0)
        by_m[t["exit_date"][:7]] += float(t["r_multiple"])
    quarters = {}
    for t in trades:
        d = t["exit_date"]
        y, m = int(d[:4]), int(d[5:7])
        quarters[f"{y}Q{(m - 1) // 3 + 1}"] = quarters.get(
            f"{y}Q{(m - 1) // 3 + 1}", 0.0) + float(t["r_multiple"])
    net = sum(rs)
    k = {
        "K1": net <= 0,
        "K2": any(v <= -15.0 for v in quarters.values()),
        "K3": _maxdd_trade(trades) > 30.0,
        "K4": (_sharpe([by_m[m] for m in sorted(by_m)]) or 0.0) < 0.5,
        "K5": n < KILL_MIN[era],
        "K6": wr < 0.40,
    }
    return k, net


def main():
    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_age10_alt_sweep import load_symbol
    from exp_portfolio_layer import corr
    from experiment_registry import BP, EXPERIMENTS

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"assets": list(ASSETS), "kill_min": KILL_MIN, "eras": {}}
    print("=" * 100, flush=True)
    print("  PORTFOLIO PART 2 - kill table + weighting (weights fit on IS only)",
          flush=True)
    print("=" * 100, flush=True)

    books = {}
    for era in ("is", "oos"):
        print(f"\n  === {era.upper()} ===", flush=True)
        er = {}
        for sym in ASSETS:
            b = load_symbol(sym)[era]
            tr = sim_fn(sim, b, dict(params))
            trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
            rs = [float(t["r_multiple"]) for t in trades]
            wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs) if rs else 0.0
            ks, net = kill_table(trades, era, wr)
            fired = [x for x, v in ks.items() if v]
            er[sym] = {"n": len(trades), "net": round(net, 1),
                       "wr": round(wr, 1), "dd": round(_maxdd_trade(trades), 1),
                       "kills": ks, "fired": fired}
            print(f"    {sym:<9} {len(trades):>4}t {net:>+8.1f}R  WR {wr:>5.1f}%  "
                  f"DD {_maxdd_trade(trades):>5.1f}  kills: "
                  f"{','.join(fired) if fired else 'NONE'}", flush=True)
        books[era] = er
        payload["eras"][era] = er

    # ---------------- kill verdict ----------------
    print("\n  " + "=" * 96, flush=True)
    print("  KILLS-CLEAN COUNT (K5 and K6 are house thresholds, not exempt):",
          flush=True)
    print("  " + "=" * 96, flush=True)
    for era in ("is", "oos"):
        clean = [s for s in ASSETS
                 if not books[era][s]["kills"]["K5"]
                 and not books[era][s]["kills"]["K6"]]
        print(f"    {era}: {len(clean)}/6 pass the COUNTED bars (K5,K6)  "
              f"-> {', '.join(clean) or 'none'}", flush=True)
        both = [s for s in ASSETS
                if all(not books[e][s]["kills"][k]
                       for e in ("is", "oos")
                       for k in ("K5", "K6"))]
        if era == "oos":
            print(f"    BOTH eras: {len(both)}/6  -> {', '.join(both) or 'none'}",
                  flush=True)
        payload.setdefault("clean", {})[era] = clean
        if era == "oos":
            payload["clean_both"] = both

    # ---------------- weighting ----------------
    print("\n  " + "=" * 96, flush=True)
    print("  WEIGHTING - equal vs inv_vol vs inv_corr (weights fit on IS, "
          "applied to OOS)", flush=True)
    print("  " + "=" * 96, flush=True)
    wres = {}
    for era in ("is", "oos"):
        b = load_symbol(ASSETS[0])[era]  # any, to get the month grid
        trades_by = {}
        for sym in ASSETS:
            tr = sim_fn(sim, load_symbol(sym)[era], dict(params))
            trades_by[sym] = (tr["ltf_trades"] if isinstance(tr, dict) else tr)
        months = sorted({t["exit_date"][:7]
                         for tr in trades_by.values() for t in tr})
        series = {s: _monthly(trades_by[s], months) for s in ASSETS}

        # --- weights fit on IS ONLY ---
        w_equal = {s: 1.0 / len(ASSETS) for s in ASSETS}
        iser = {s: _monthly(trades_by[s], months) for s in ASSETS}
        vol = {s: (statistics.pstdev(iser[s]) or 1.0) for s in ASSETS}
        w_invv = {s: (1.0 / vol[s]) for s in ASSETS}
        tot = sum(w_invv.values())
        w_invv = {s: w_invv[s] / tot for s in ASSETS}
        C = {a: {c: (1.0 if a == c else
                     (corr(iser[a], iser[c]) or 0.0)) for c in ASSETS}
             for a in ASSETS}
        w_ic = {}
        for s in ASSETS:
            v = sum(C[s][c] * w_invv[c] for c in ASSETS)
            w_ic[s] = w_invv[s] / max(v, 1e-9)
        tot = sum(w_ic.values())
        w_ic = {s: w_ic[s] / tot for s in ASSETS}

        schemes = {"equal": w_equal, "inv_vol": w_invv, "inv_corr": w_ic}
        print(f"\n    [{era}]", flush=True)
        for nm, w in schemes.items():
            port = [sum(w[s] * series[s][i] for s in ASSETS)
                    for i in range(len(months))]
            net = sum(port)
            ddv = _dd(port)
            wres.setdefault(nm, {})[era] = {
                "net": round(net, 1), "net_yr": round(net / YEARS[era], 1),
                "dd": round(ddv, 1),
                "weights": {k: round(v, 4) for k, v in w.items()},
            }
            print(f"      {nm:<9} {net:>+8.1f}R ({net/YEARS[era]:>+6.1f}/yr)  "
                  f"DD {ddv:>5.1f}R  "
                  f"w: " + " ".join(f"{s[:4]} {w[s]:.2f}" for s in ASSETS),
                  flush=True)
        payload.setdefault("weighting", {})[era] = {
            nm: {"net": round(sum(schemes[nm][s] * series[s][i]
                                  for s in ASSETS for i in [0]), 1)}
            for nm in schemes}

    print("\n    IS-fitted weights applied to OOS (the honest comparison):",
          flush=True)
    for nm in ("inv_vol", "inv_corr"):
        a, b = wres["equal"]["oos"]["net_yr"], wres[nm]["oos"]["net_yr"]
        print(f"      {nm:<9} OOS {wres[nm]['oos']['net']:+.1f}R "
              f"({b:+.1f}/yr) vs equal {wres['equal']['oos']['net']:+.1f}R "
              f"({a:+.1f}/yr)  -> {b - a:+.1f}R/yr", flush=True)
    payload["weighting"] = wres
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
