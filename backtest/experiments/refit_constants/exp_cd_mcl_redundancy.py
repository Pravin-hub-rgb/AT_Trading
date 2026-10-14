"""
ARE cooldown_bars AND max_consecutive_losses REDUNDANT?  A 2-factor design.

THE HYPOTHESIS

Both gates block entries after a loss:

    cooldown_bars   skip entries for N bars after a loss  (a TIME window)
    max_consec      every N consecutive losses, discard one signal (a COUNT)

The owner put it plainly: "If there is cool down, we shouldn't be adding any more
gate to it. Cool down either alone, cool down, or either alone MCL." If cooldown
already covers the loss after a loss, then stacking mcl on top adds a second
blockade on the same event and can only remove more trades - and the MCL matrix
already showed the trades mcl removes are net POSITIVE in all four books.

So the question is not "is mcl harmful" in the abstract. It is: does mcl earn its
place GIVEN that cooldown is already switched on?

WHAT IS RUN

    cd  in {0, 4, 8, 12, 20}      the book's own pin is 8
    mcl in {0, 3}                  mcl=0 is the gate OFF, not "none of everything"

    5 x 2 x 4 books x 2 eras = 80 runs, NET of fees/slip/funding.

The four cells that answer the redundancy question directly:

    cd=8  mcl=0    cooldown alone          <- is this all we need?
    cd=8  mcl=3    cooldown + halt         <- THE CURRENT PIN
    cd=0  mcl=0    neither
    cd=0  mcl=3    halt alone              <- is mcl a viable gate by itself?

DISCIPLINE

  IS decides. OOS is computed and printed but the verdict column comes from IS
  only. Two factors, four books, no grid search - every cell is a single knob
  change from the shipped pin, so there is nothing here to overfit.
  Results are cached; --force recomputes.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_cd_mcl_redundancy.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from exp_mcl_matrix import metrics, load_era, LADDER_BOOKS  # noqa: E402

CDS = [0, 4, 8, 12, 20]
MCLS = [0, 3]
INSTRUMENT = "BTCUSDT_BYBIT"


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cache = HERE / "cd_mcl_redundancy_results.json"

    if cache.exists() and "--force" not in sys.argv:
        out = json.loads(cache.read_text(encoding="utf-8"))
        print("\n  loaded cache (%s).  --force to recompute" % cache.name)
    else:
        out = {"stage": "cd_mcl_redundancy", "cds": CDS, "mcls": MCLS, "eras": {}}
        for era in ("is", "oos"):
            print("  computing %s ..." % era.upper())
            d = load_era(era)
            res = {}

            def run(book, cd, mcl):
                cfg = EXPERIMENTS[book]
                p = {**BP, **cfg["params"]}
                p.setdefault("exp_partial_r", 0.0)
                p["cooldown_bars"] = cd
                p["max_consecutive_losses"] = mcl
                sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
                r = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
                return r["ltf_trades"] if isinstance(r, dict) else r

            for b in LADDER_BOOKS:
                cell = {}
                for cd in CDS:
                    for mcl in MCLS:
                        cell["%d|%d" % (cd, mcl)] = metrics(run(b, cd, mcl))
                res[b] = cell
                print("    %-28s done" % b)
            out["eras"][era] = res
        cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("  cached -> %s" % cache.name)

    T = out["eras"]

    # ---------------- the 2x2 ------------------------------------------------
    print()
    print("=" * 122)
    print("THE 2x2  -  is the second gate earning its place?   (NET, IS decides)")
    print("=" * 122)
    print("  %-24s %-16s %6s %9s %8s %7s %7s %8s" %
          ("book", "cell", "n", "NET", "DD", "MaxCL", "PF", "NET/DD"))
    print("  " + "-" * 100)
    cells = [("cd=8  mcl=0", "cooldown alone", 8, 0),
             ("cd=8  mcl=3", "both  (THE PIN)", 8, 3),
             ("cd=0  mcl=3", "halt alone", 0, 3),
             ("cd=0  mcl=0", "neither", 0, 0)]
    for b in LADDER_BOOKS:
        for label, _, cd, mcl in cells:
            r = T["is"][b]["%d|%d" % (cd, mcl)]
            print("  %-24s %-16s %6d %+9.2f %8.2f %7d %7.2f %8.1f"
                  % (b if label == cells[0][0] else "", label, r["n"], r["net"],
                     r["dd"], r["mc"], r["pf"], r["net_dd"]))
        print("  " + "-" * 100)

    # ---------------- the direct verdict ------------------------------------
    print()
    print("=" * 122)
    print("VERDICT  -  given cooldown is ALREADY on (cd=8), does mcl add anything?")
    print("=" * 122)
    print("  %-24s %12s %12s %10s %10s %10s" %
          ("book", "cd only", "cd+halt", "dNET", "dDD", "dMaxCL"))
    print("  " + "-" * 72)
    worse = 0
    for b in LADDER_BOOKS:
        a = T["is"][b]["8|0"]
        c = T["is"][b]["8|3"]
        dn, dd_, dm = c["net"] - a["net"], c["dd"] - a["dd"], c["mc"] - a["mc"]
        if dn < 0:
            worse += 1
        print("  %-24s %+12.2f %+12.2f %+10.2f %+10.2f %+10d"
              % (b, a["net"], c["net"], dn, dd_, dm))
    print()
    print("  stacking mcl on top of cooldown LOWERS net in %d of 4 books on IS."
          % worse)

    # ---------------- cooldown curve at each mcl ----------------------------
    for mcl in MCLS:
        print()
        print("  COOLDOWN CURVE at mcl=%d  (NET, IS)   %s"
              % (mcl, " <- the pin" if mcl == 3 else ""))
        print("    %-24s %s" % ("book", "".join("%10s" % ("cd=%d" % cd) for cd in CDS)))
        for b in LADDER_BOOKS:
            vals = [T["is"][b]["%d|%d" % (cd, mcl)]["net"] for cd in CDS]
            best = CDS[max(range(len(vals)), key=lambda i: vals[i])]
            cells_s = "".join(
                ("%10.2f%s" % (v, "*" if cd == best else " "))
                for cd, v in zip(CDS, vals))
            print("    %-24s %s" % (b, cells_s))
        print("    * = best cd at this mcl")

    # ---------------- risk view ---------------------------------------------
    print()
    print("=" * 122)
    print("RISK VIEW  -  MaxConsecL and MaxDD across the 2x2 (IS).  Owner cares here.")
    print("=" * 122)
    print("  %-24s %-14s %8s %8s" % ("book", "cell", "MaxCL", "MaxDD"))
    for b in LADDER_BOOKS:
        for label, _, cd, mcl in cells:
            r = T["is"][b]["%d|%d" % (cd, mcl)]
            print("  %-24s %-14s %8d %8.2f"
                  % (b if label == cells[0][0] else "", label, r["mc"], r["dd"]))
        print("  " + "-" * 48)

    # ---------------- does mcl work WITHOUT cooldown? -----------------------
    print()
    print("=" * 122)
    print("IS mcl A VIABLE GATE ON ITS OWN?  (cd=0, so nothing else is blocking)")
    print("=" * 122)
    print("  %-24s %11s %11s %11s %11s" % ("book", "neither", "halt alone", "dNET", "dNET OOS"))
    for b in LADDER_BOOKS:
        a = T["is"][b]["0|0"]
        c = T["is"][b]["0|3"]
        ao = T["oos"][b]["0|0"]
        co = T["oos"][b]["0|3"]
        print("  %-24s %+11.2f %+11.2f %+11.2f %+11.2f"
              % (b, a["net"], c["net"], c["net"] - a["net"], co["net"] - ao["net"]))
    print()
    print("  If the IS and OOS columns disagree in sign, the gate does not generalise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())