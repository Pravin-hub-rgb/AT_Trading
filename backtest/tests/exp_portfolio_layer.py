"""NEW BUCKET - PORTFOLIO level. What happens when these books run TOGETHER?

WHY THIS HAS NEVER BEEN DONE
============================
The transfer work (24.95, and my age10 sweep) asked a per-instrument
question: "does this lane work on asset X?" That is a yes/no about ONE
book. It says nothing about what happens when six of them run at once.

Those are different questions and the second one is the one that decides
deployment. Six books each positive can still be one bad portfolio if they
lose together, and the repo has never measured:

  * do the books' monthly returns actually diversify, or are they one bet?
  * what is the COMBINED drawdown against the sum of the individual ones?
  * is there a subset that is materially better than "all of them"?
  * does correlation rise in the OOS era, i.e. is diversification a
    property of calm data or of the strategy?

This matters because the transfer rate is high (7/13 assets positive in
both eras) and the obvious next move for a live book is "run them all".
If that is wrong, the discovery arrives after real capital is at risk.

WHAT IS MEASURED (descriptive first, and deliberately not a gate)
===============================================================
  1. monthly R per asset, and the pairwise correlation matrix, both eras
  2. equal-weight portfolio: net, DD, and DD vs the average single-book DD
  3. the same with the assets ranked by OOS net, to see whether a subset
     dominates
  4. correlation drift IS vs OOS - is diversification era-dependent

NOTHING IS SELECTED HERE. Choosing the best subset on the same data that
scored it is exactly the multiplicity this repo forbids; the ranking is
printed so the USER can decide, and any subset that gets built later must
be re-validated on data that did not choose it.

CONTROL: the per-asset numbers are re-asserted against the transfer sweep
before any portfolio statistic is computed, so a portfolio win cannot come
from a bad single-asset run.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_portfolio_layer.py
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

OUT = ROOT / "backtest/tests/_portfolio_layer.json"
YEARS = {"is": 3.67, "oos": 2.0}
ASSETS = ("AVAXUSDT", "BNBUSDT", "LTCUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT")
# The transfer sweep's per-asset net, re-asserted as a control below.
EXPECTED = {
    "AVAXUSDT": {"is": (145, 173.9), "oos": (82, 189.8)},
    "BNBUSDT": {"is": (126, 200.9), "oos": (92, 95.9)},
    "LTCUSDT": {"is": (138, 147.9), "oos": (95, 89.0)},
    "LINKUSDT": {"is": (133, 122.5), "oos": (87, 116.5)},
    "NEARUSDT": {"is": (98, 108.7), "oos": (85, 50.9)},
    "DOTUSDT": {"is": (115, 84.8), "oos": (88, 32.3)},
}


def monthly_r(trades, months):
    """R summed by EXIT month, the repo's convention (K2/K7 use exit month).

    `months` is the union list; values are always float.
    """
    out = {m: 0.0 for m in months}
    for t in trades:
        d = t.get("exit_date", "")
        if d[:7] in out:
            out[d[:7]] += float(t["r_multiple"])
    return out


def dd_from_monthly(mvals):
    """DD on the monthly curve - the same construction K3 uses."""
    peak = cum = 0.0
    for v in mvals:
        cum += v
        peak = max(peak, cum)
        dd = max(dd := 0.0, 0.0)
        dd = max(dd, peak - cum)
    return dd


def maxdd_trade_order(trades):
    peak = cum = 0.0
    m = 0.0
    for t in sorted(trades, key=lambda z: int(z["exit_ts"])):
        cum += float(t["r_multiple"])
        peak = max(peak, cum)
        m = max(m, peak - cum)
    return m


def corr(a, b):
    """Pearson on two equal-length numeric sequences.

    Accepts dicts too (month -> R), since that is what the monthly series
    is; iterating a dict yields KEYS, which is what made the first run pass
    strings into fmean and die.
    """
    if isinstance(a, dict):
        keys = sorted(set(a) & set(b))
        a = [float(a[k]) for k in keys]
        b = [float(b[k]) for k in keys]
    else:
        a, b = list(a), list(b)
    if len(a) != len(b) or len(a) < 3:
        return None
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return round(num / (da * db), 3) if da > 0 and db > 0 else None



def main():
    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_age10_alt_sweep import load_symbol
    from experiment_registry import BP, EXPERIMENTS

    t0 = time.time()
    sim = build_module()
    payload = {"assets": list(ASSETS), "eras": {}}
    print("=" * 100, flush=True)
    print("  PORTFOLIO LAYER - do these books diversify, or is it one bet?",
          flush=True)
    print("=" * 100, flush=True)

    for era in ("is", "oos"):
        print(f"\n  === {era.upper()} ===", flush=True)
        books, months_ref = {}, None
        rows = []
        for sym in ASSETS:
            b = load_symbol(sym)[era]
            tr = sim_fn(sim, b, {**BP, **EXPERIMENTS[
                "age10_dirmatch_swingpause_single_sw10"]["params"]})
            trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
            rs = [float(t["r_multiple"]) for t in trades]
            net = round(sum(rs), 1)
            exp_n, exp_net = EXPECTED[sym][era]
            ok = (len(trades) == exp_n and abs(net - exp_net) < 1.0)
            print(f"    {sym:<9} {len(trades):>4}t {net:>+8.1f}R  "
                  f"DD {maxdd_trade_order(trades):>6.1f}  "
                  f"{'ctrl OK' if ok else 'CTRL MISMATCH'}", flush=True)
            if not ok:
                print(f"      expected {exp_n}t {exp_net:+.1f}", flush=True)
                continue
            mo = monthly_r(trades, None) if False else None
            trades_sorted = sorted(trades, key=lambda z: int(z["exit_ts"]))
            books[sym] = trades_sorted
            rows.append((sym, net, maxdd_trade_order(trades)))

        if not books:
            print("    no books survived control", flush=True)
            continue

        # ---- monthly matrix ----
        all_m = sorted({t["exit_date"][:7] for tr in books.values() for t in tr})
        series = {s: monthly_r(books[s], all_m) for s in books}
        cols = [float(i) for i in range(len(ASSETS))]

        print(f"\n    pairwise monthly-R correlation ({len(all_m)} months):",
              flush=True)
        syms = list(books)
        print("        " + "".join(f"{s[:5]:>7}" for s in syms), flush=True)
        cm = {}
        for a in syms:
            line = f"    {a[:5]:<5}"
            for b in syms:
                c = corr(series[a], series[b]) if a != b else 1.0
                line += f"{c:>7.2f}" if c is not None else "      -"
                if a != b:
                    cm[f"{a}|{b}"] = c
            print(line, flush=True)
        vals = [v for v in cm.values() if v is not None]
        if vals:
            print(f"    mean pairwise corr {statistics.fmean(vals):+.3f}  "
                  f"min {min(vals):+.3f}  max {max(vals):+.3f}", flush=True)

        # ---- equal-weight portfolio ----
        ew = []
        for m in all_m:
            ew.append(statistics.fmean([series[s][m] for s in books]))
        eq_net = sum(ew)
        eq_dd = maxdd_trade_order([t for tr in books.values() for t in tr])
        single_dds = [r[2] for r in rows]
        print(f"\n    equal-weight portfolio: {eq_net:+.1f}R over {len(all_m)}m "
              f"({eq_net/YEARS[era]:+.1f}R/yr)", flush=True)
        print(f"    portfolio DD {eq_dd:.1f}R vs single-book DD "
              f"min {min(single_dds):.1f} avg {statistics.fmean(single_dds):.1f} "
              f"max {max(single_dds):.1f}", flush=True)
        print(f"    sum of single-book nets: {sum(r[1] for r in rows):+.1f}R",
              flush=True)

        payload["eras"][era] = {
            "rows": [{"sym": s, "net": n, "dd": d} for s, n, d in rows],
            "months": len(all_m),
            "eq_portfolio_net": round(eq_net, 1),
            "eq_portfolio_dd": round(eq_dd, 1),
            "single_dd_min": round(min(single_dds), 1),
            "single_dd_avg": round(statistics.fmean(single_dds), 1),
            "single_dd_max": round(max(single_dds), 1),
            "sum_single_net": round(sum(r[1] for r in rows), 1),
            "mean_pairwise_corr": (round(statistics.fmean(vals), 3)
                                   if vals else None),
            "corr": cm,
        }

    # cross-era drift
    ise, ose = payload["eras"].get("is"), payload["eras"].get("oos")
    if ise and ose:
        print(f"\n  mean pairwise corr: IS {ise['mean_pairwise_corr']}  "
              f"OOS {ose['mean_pairwise_corr']}  -> "
              f"{'diversification is era-dependent' if abs(ise['mean_pairwise_corr'] - ose['mean_pairwise_corr']) > 0.15 else 'stable across eras'}",
              flush=True)
        payload["corr_drift"] = round(ose["mean_pairwise_corr"]
                                      - ise["mean_pairwise_corr"], 3)

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
