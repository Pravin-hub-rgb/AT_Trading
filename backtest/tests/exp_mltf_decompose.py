"""exp_mltf_decompose - how much of the book is only reachable with exp_mltf on?

WHY
===
exp_best_cell_mode.py reported "MISMATCH - mode is not the rule we measured": the
new mode chop_hi_atr_lo produced 528 IS trades of which only 75 were in the
chop_HIGH/atr_low cell the mode was built for. That is expected from the code
and was not checked before running it, which is the part worth fixing.

The cause is exp_mltf. exp_knob_binds.py already established that exp_mltf is
INERT at max_positions=0 and LIVE at max_positions=1, where it removes 173 of
528 trades. So the book's trade set depends on a second layer gate that has
nothing to do with the regime router, and a cell measured on the default set is
not the same cell a mode that changes the router will see.

This measures the decomposition:

  how many signals reach the router at all, per layer
  how many survive exp_mltf
  how many survive the regime gate
  and whether the joint cell is populated differently under mltf off

so that "why did the mode not target the cell" has a number attached instead of
a guess.

Run:  cd backtest/tests
      python -u exp_mltf_decompose.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
NEW_MODE = "chop_hi_atr_lo"
OUT_JSON = Path(__file__).parent / "_mltf_decompose.json"
OUT_MD = Path(__file__).parent / "_mltf_decompose.md"


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_signal_metrics import load_era
    from experiment_registry import EXPERIMENTS
    from exp_mode_regime import joint_regime

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)
    a_thr, c_thr = base["atr_high_thresh"], base["chop_thresh"]
    print("=" * 96)
    print("MLTF DECOMPOSE - %s" % BOOK)
    print("=" * 96)
    print("book's exp_mltf = %r, max_positions in params = %r"
          % (base.get("exp_mltf"), base.get("max_positions")))
    print("target cell = chop>%s AND atrp<%s\n" % (c_thr, a_thr))

    report = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, cfg.get("swing") or "sw10")
        rows, _, _, _ = joint_regime(d)
        lut = {r["ts"]: r for r in rows}

        def cell_of(t):
            r = lut.get(int(t["entry_ts"]) - 900)
            if r is None:
                return "unknown"
            return ("chop_HIGH/atr_low" if (r["ch"] > c_thr and r["atrp"] < a_thr)
                    else "other")

        print("-" * 96)
        print(era.upper())
        print("-" * 96)
        era_rep = {}
        for mltf in (True, False):
            for mode in ("atr_high", NEW_MODE):
                p = dict(base)
                p["exp_mltf"] = mltf
                p["mode"] = mode
                out = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
                tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
                ncell = sum(1 for t in tr if cell_of(t) == "chop_HIGH/atr_low")
                rs = [net_r([t]) for t in tr]
                key = "mltf=%s %s" % ("on " if mltf else "off", mode)
                era_rep[key] = {"n": len(tr), "net": round(sum(rs), 2), "in_cell": ncell}
                print("   %-26s n=%4d  net %+8.1f   in target cell %3d (%4.1f%%)"
                      % (key, len(tr), sum(rs), ncell, 100.0 * ncell / max(1, len(tr))))
        # what mltf alone costs, holding the router fixed
        for mode in ("atr_high", NEW_MODE):
            on = era_rep["mltf=on  %s" % mode]["n"]
            off = era_rep["mltf=off %s" % mode]["n"]
            print("   exp_mltf off removes %d trades with mode=%s (%d -> %d)"
                  % (on - off, mode, on, off))
        report[era] = era_rep
        print()

    print("=" * 96)
    print("WHY THE MISMATCH HAPPENED")
    print("=" * 96)
    for era in ("is", "oos"):
        r = report[era]
        ship = r["mltf=on  atr_high"]
        new = r["mltf=on  %s" % NEW_MODE]
        print("%s: shipping takes %d trades, new mode %d, target cell is %d."
              % (era.upper(), ship["n"], new["n"], ship["in_cell"]))
        print("   the mode CANNOT be a subset of the cell - it routes %s to flip"
              % "everything outside the cell" )
        print("   but it still returns %d trades, so %d of them come from the flip branch."
              % (new["n"], new["n"] - new["in_cell"]))
    print()
    print("This is a property of the router, not a bug in the mode: a 'decisive else")
    print("flip' rule always admits flip-branch trades. Targeting the cell means")
    print("GATING it, which is a different rule - see mode=flip in the router.")

    OUT_JSON.write_text(json.dumps({"book": BOOK, "report": report}, indent=2) + "\n",
                        encoding="utf-8")
    lines = ["# exp_mltf decompose - %s" % BOOK, "",
             "Trade counts per (exp_mltf, mode), and target-cell population.", "",
             "| era | exp_mltf | mode | n | net R | in target cell |", "|---|---|---|---:|---:|---:|"]
    for era, r in report.items():
        for key, v in r.items():
            m, mode = key.split(" ", 1)
            lines.append("| %s | %s | %s | %d | %.1f | %d |" % (
                era.upper(), m.replace("mltf=", ""), mode, v["n"], v["net"], v["in_cell"]))
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s and %s" % (OUT_MD.name, OUT_JSON.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())