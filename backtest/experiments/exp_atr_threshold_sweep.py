"""E2 - VOLATILITY NORMALISATION: is the regime threshold tuned to BTC's volatility?

WHY THIS EXPERIMENT EXISTS
--------------------------
E1's premise is that 86 of 93 active books run one regime filter, `atr_high`,
and its threshold is 0.65. That number was chosen against BTC.

The cross-asset run (docs/method/CROSS_ASSET_TIER4.md, 2026-10-14) then found 6
of 6 books profitable on ETH perp and 5 of 6 BETTER than on BTC over the same
calendar window. ETH is not BTC's volatility regime. Two readings, and this
experiment is designed to tell them apart:

  (a) the edge is regime-blind and the ETH result is incidental, or
  (b) part of the edge comes from where 0.65 sits relative to the instrument's
      own ATR distribution, in which case the threshold is a BTC-fitted
      constant and should move.

An earlier sweep already ran 0.20-0.60 on both eras and found 9/9 positive -
a plateau, not a spike. That RETIRED the "grid peak" objection recorded in the
registry, but a plateau spanning 0.20-0.60 says nothing about 0.60-0.80, and it
was measured on `fsent_champ_long` only, under one era split.

This sweeps the region ABOVE the shipped value, on three books, both eras, and
reports the shape rather than picking a winner.

WHAT THIS IS NOT
----------------
Not a promotion. Not a registry edit. It prints a curve. A threshold that wins
here needs its own experiment and its own OOS reveal.

PIPELINE DISCIPLINE (backtest/docs/pipeline/README.md)
-----------------------------------------------------
Identity gate first - the book's own params must reproduce its pin. Both eras.
Nothing promoted.

Output: atr_threshold_sweep_results.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "atr_threshold_sweep_results.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from experiment_registry import EXPERIMENTS                      # noqa: E402

# Above the shipped 0.65, plus a short dip below it for shape. 0.80 and 0.90 are
# included deliberately: if the edge is regime-blind they should be flat, and if
# they collapse then 0.65 was doing work the registry never said it did.
GRID = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]

BOOKS = ["fsent_champ_long", "fsent_champ_long_htf15", "fsent_champ_long_htffs"]

TOTAL = len(BOOKS) * (len(GRID) + 1) * 2
_DONE = 0
_T0 = time.time()


def progress(label: str) -> None:
    global _DONE
    _DONE += 1
    pct = 100.0 * _DONE / TOTAL
    el = time.time() - _T0
    eta = (el / _DONE) * (TOTAL - _DONE) if _DONE else 0.0
    print("\r  [%3d%%] %-40s %-36s %5.1fs elapsed, ~%4.0fs left   "
          % (pct, "#" * int(pct / 2.5), label[:36], el, eta),
          end="", flush=True)


def sweep_key(book: str) -> str:
    return "htf15" if book.endswith("htf15") else "sw10"


def main() -> int:
    print("E2 - atr_high_thresh sweep above the shipped 0.65")
    print("3 books x %d thresholds x 2 eras + identity gate" % len(GRID))
    print("estimated ~%d min\n" % (TOTAL * 10 // 60))
    t0 = time.time()

    sim = craze.build_module()
    print("loading eras ...", flush=True)
    from exp_signal_metrics import load_era
    eras = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0), flush=True)

    out = {"grid": GRID, "books": BOOKS, "identity": {}, "rows": {}}

    print("=" * 96)
    print("IDENTITY GATE")
    print("=" * 96)
    gate_ok = True
    for book in BOOKS:
        cfg = dict(EXPERIMENTS[book])
        cfg["swing"] = sweep_key(book)
        cfg["basis"] = "fine"
        pin = cfg.get("pins") or {}
        for era in ("is", "oos"):
            m = repin.measure(sim, eras[era], cfg)
            progress("%s | OWN | %s" % (book, era))
            wn = pin.get("n") if era == "is" else pin.get("oos_n")
            wt = pin.get("net") if era == "is" else pin.get("oos_net")
            ok = m["n"] == wn and abs(m["net"] - wt) < 0.01
            gate_ok = gate_ok and ok
            print("  %-30s %-4s n=%-5d net=%9.2f pin %9.2f  %s"
                  % (book, era, m["n"], m["net"], wt,
                     "OK" if ok else "*** MISMATCH ***"))
            out["identity"]["%s|%s" % (book, era)] = {"ok": ok}
    print()
    if not gate_ok:
        print("!! GATE FAILED - stopping.")
        RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
        return 1
    print("gate passed.\n")

    for book in BOOKS:
        base = dict(EXPERIMENTS[book])
        base["swing"] = sweep_key(book)
        base["basis"] = "fine"
        rows = {}
        print("=" * 108)
        print("%s   (shipped threshold %.2f)" % (book, base["params"]["atr_high_thresh"]))
        print("=" * 108)
        print("  %-7s | %6s %10s %8s %10s %8s  %s"
              % ("thr", "n", "IS net", "PF", "OOS net", "PF", "note"))
        print("  " + "-" * 82)
        for thr in GRID:
            cfg = dict(base)
            cfg["params"] = dict(base["params"], atr_high_thresh=thr)
            r = {}
            for era in ("is", "oos"):
                r[era] = repin.measure(sim, eras[era], cfg)
                progress("%s | %.2f | %s" % (book, thr, era))
            rows["%.2f" % thr] = r
            ship = abs(thr - base["params"]["atr_high_thresh"]) < 1e-9
            note = "SHIPPED" if ship else ""
            if r["is"]["net"] > 0 and r["oos"]["net"] > 0 and not ship:
                note = "both +"
            # 7 format specs: thr, n, IS net, PF, OOS n, OOS net, note. An
            # earlier version had 6 specs for 7 args and raised TypeError on the
            # first row - which is why the log stopped at the identity gate.
            print("  %-7.2f | %6d %10.2f %8.2f %6d %10.2f  %s"
                  % (thr, r["is"]["n"], r["is"]["net"], r["is"].get("pf") or 0,
                     r["oos"]["n"], r["oos"]["net"], note))
        out["rows"][book] = rows
        vals = [r["oos"]["net"] for r in rows.values()]
        isv = [r["is"]["net"] for r in rows.values()]
        print("  IS  %d/%d positive, range %.1f .. %.1f"
              % (len([v for v in isv if v > 0]), len(isv), min(isv), max(isv)))
        print("  OOS %d/%d positive, range %.1f .. %.1f"
              % (len([v for v in vals if v > 0]), len(vals), min(vals), max(vals)))
        print()

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    print("\nNOTHING PROMOTED. A threshold that wins needs its own experiment,")
    print("its own registry entry and its own OOS reveal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())