"""Per-criterion pass/fail count across the thirteen-book battery.

`exp_gate_eval.py` answers "does this book clear every gate". This one answers
"which criterion is actually doing the rejecting", because a gate sequence that
eliminates thirteen of thirteen books is either correct or broken, and the way to
tell is to see whether one criterion is rejecting on a technicality.

Same thresholds, same sources, read from the same files. It imports the gate
script rather than restating the rules so the two cannot drift apart.
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import exp_gate_eval as G  # noqa: E402


def main():
    t1, t2, t3, t4 = G.load("t1"), G.load("t2"), G.load("t3"), G.load("t4")
    vs = json.load(io.open(os.path.join(HERE, "verified_suite.json"), encoding="utf-8"))

    rows = []
    per_crit = {}
    for name, code in G.CODES.items():
        v_is, v_oos = vs[name]["is"], vs[name]["oos"]
        sp = G.t1_span(t1[name])
        folds = [x for x in t2[name] if x.get("reg_test_net") is not None]
        sl = t3[name]["is"]["slippage"]
        n0 = sl[0]["n"]
        n1000 = [s for s in sl if s["bps"] == 1000][0]["n"]

        crit = {
            "G1 tail10 IS": v_is["tail10"] > 0,
            "G1 tail10 OOS": v_oos["tail10"] > 0,
            "G1 top10 IS": v_is["top10pct"] < G.TH["g1_top10pct"],
            "G1 top10 OOS": v_oos["top10pct"] < G.TH["g1_top10pct"],
            "G2 span IS": sp["is"] < G.TH["g2_span"],
            "G2 span OOS": sp["oos"] < G.TH["g2_span"],
            "G2 cliff": not (sp["is_cliff"] or sp["oos_cliff"]),
            "G2 walkfwd": (sum(1 for x in folds if x["test_net"] > x["reg_test_net"])
                           + sum(1 for x in folds if x["test_net"] == x["reg_test_net"])) >= G.TH["g2_folds"],
            "G3 BE slip IS": G.break_even(t3[name]["is"]["slippage"]) >= G.TH["g3_be_is"],
            "G3 BE slip OOS": G.break_even(t3[name]["oos"]["slippage"]) >= G.TH["g3_be_oos"],
            "G3 cost 3x": t3[name]["is"]["cost"][-1]["net"] > 0 and t3[name]["oos"]["cost"][-1]["net"] > 0,
            "G3 lost<50%": 100.0 * (n0 - n1000) / n0 < 50,
            "G4 dd>25R": t4[name]["is"]["frac_paths_dd_over_25"] < G.TH["g4_dd25"],
            "G4 dd>50R": (t4[name]["is"]["frac_paths_dd_over_50"] <= G.TH["g4_dd50"]
                          and t4[name]["oos"]["frac_paths_dd_over_50"] <= G.TH["g4_dd50"]),
            "G4 worst50 OOS": v_oos["roll"]["50"][1] > 0,
            "G4 DDpct IS": t4[name]["is"]["obs_dd_rank_pct"] < G.TH["g4_dd_pct"],
            "G4 DDpct OOS": t4[name]["oos"]["obs_dd_rank_pct"] < G.TH["g4_dd_pct"],
        }
        for k, v in crit.items():
            d = per_crit.setdefault(k, [0, 0])
            d[1] += 1
            if v:
                d[0] += 1
        rows.append((sum(1 for v in crit.values() if v), code, crit))

    rows.sort(reverse=True)
    print("%-7s %7s  %s" % ("book", "pass", "failures"))
    print("-" * 84)
    for p, code, crit in rows:
        fail = [k for k, v in crit.items() if not v]
        print("%-7s %3d/18  %s" % (code, p, ", ".join(fail) if fail else "- none -"))

    print("\n%-18s %s" % ("criterion", "books passing"))
    print("-" * 84)
    for k, (a, b) in sorted(per_crit.items(), key=lambda x: x[1][0]):
        print("%-18s %2d/13%s" % (k, a, "   <-- rejects everyone" if a == 0 else ""))


if __name__ == "__main__":
    main()