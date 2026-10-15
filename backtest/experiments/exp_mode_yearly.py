"""Year-by-year, because a book that nets well over five years can still be one
bad year holding up four good ones - which is exactly the objection raised
about fsent_champ_long_htf15_union (worst IS year 12.28R against the shipped
book's 99.41R).

Runs four candidates on fsent_champ_short plus the htf15 pair:
  - the shipped baseline
  - session          (what was registered)
  - flip_quality     (strictly better on net, per-trade quality AND trade count)
  - union            (what was registered, on htf15 - the volume case)
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

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_equity_quality import net_r                             # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

YEARS = {"is": 3.67, "oos": 2.0}

# (label, book, mode override or None)
RUNS = [
    ("champ_short SHIPPED", "fsent_champ_short", None),
    ("  + session", "fsent_champ_short", "session"),
    ("  + flip_quality", "fsent_champ_short", "flip_quality"),
    ("  + hmm", "fsent_champ_short", "hmm"),
    ("htf15 SHIPPED", "fsent_champ_long_htf15", None),
    ("  + union", "fsent_champ_long_htf15", "union"),
]

_T = len(RUNS) * 2
_D = 0
_T0 = time.time()


def prog(lbl):
    global _D
    _D += 1
    el = time.time() - _T0
    eta = (el / _D) * (_T - _D)
    pct = 100.0 * _D / _T
    msg = "[%3.0f%%] %s %5.0fs elapsed, ~%4.0fs left" % (
        pct, "#" * int(pct / 2.5), el, eta)
    sys.stdout.write("\r  " + msg + "   " + lbl)
    sys.stdout.flush()


def trades_of(sim, data, book, mode):
    cfg = EXPERIMENTS[book]
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    params = dict(cfg["params"])
    if mode:
        params["mode"] = mode
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"],
             fine_ltf=data["fine"], **{**dict(repin.re_.BP), **params})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return [t for t in tr if t.get("outcome") != "open"]


def main() -> int:
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}
    out = {}
    rows = []
    for lbl, book, mode in RUNS:
        for era in ("is", "oos"):
            prog("%s %s" % (lbl.strip(), era))
            tr = trades_of(sim, eras[era], book, mode)
            nets = [net_r([t]) for t in tr]
            yr = {}
            for t, x in zip(tr, nets):
                y = str(t.get("exit_date") or t.get("entry_date") or "")[:4]
                if y:
                    yr[y] = yr.get(y, 0.0) + x
            n = len(nets)
            tot = sum(nets)
            rows.append({
                "label": lbl, "book": book, "mode": mode, "era": era,
                "n": n, "net": round(tot, 2),
                "r_per_trade": round(tot / n, 3) if n else 0.0,
                "trades_per_year": round(n / YEARS[era], 1),
                "years": {y: round(v, 2) for y, v in sorted(yr.items())},
                "worst_year": round(min(yr.values()), 2) if yr else 0.0,
                "n_years": len(yr),
            })
    print("\n")

    for era in ("is", "oos"):
        print("=" * 112)
        print("%s   (%.2f years)" % (era.upper(), YEARS[era]))
        print("=" * 112)
        sel = [r for r in rows if r["era"] == era]
        allYears = sorted({y for r in sel for y in r["years"]})
        print("%-20s %6s %9s %9s %8s  %s"
              % ("", "n", "net", "R/trade", "tr/yr", "  ".join("%9s" % y for y in allYears)))
        print("-" * 112)
        for r in sel:
            cells = "  ".join(("%9.2f" % r["years"][y]) if y in r["years"] else "        -"
                              for y in allYears)
            print("%-20s %6d %9.2f %9.3f %8.1f  %s"
                  % (r["label"], r["n"], r["net"], r["r_per_trade"],
                     r["trades_per_year"], cells))
        print()
        for r in sel:
            flag = ""
            if r["worst_year"] < 50:
                flag = "   <-- a year this thin is not a book"
            print("  %-20s worst year %8.2f over %d years%s"
                  % (r["label"], r["worst_year"], r["n_years"], flag))
        print()

    out = {"years": YEARS, "rows": rows}
    (HERE / "mode_census_yearly.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote mode_census_yearly.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())