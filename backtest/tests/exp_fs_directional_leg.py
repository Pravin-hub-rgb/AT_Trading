"""DIRECTIONAL FS ON THE LEG BOOKS - the origin-stop run was the wrong lane.

WHY THIS FILE
    exp_directional.py measured the FS-long / FS-short arms on
    `champion_multi_sw10` and `utcsat_multi_sw10`. Both of those carry
    pivot_rule="origin" - the RETROACTIVE stop source that this repo has since
    retired as lookahead (exp_origin_lookahead.py: it is the only book still
    naming a forbidden source, and it is kept alive only so the comparison
    reproduces). Every other book, and every shipping candidate, uses "leg" or
    "leg_no_entry".

    So the P80 numbers were measured on a lane nothing ships, on a stop source
    nothing ships. Re-running the same four arms on the LEG books is the
    question that was never answered: does the directional FS trigger still
    work once the stop source is the causal one?

    Nothing about the mechanism changes - only which book it runs on. Reusing
    exp_directional's own patched _collect_signals keeps the trigger definition
    identical to P80's, so the two runs are comparable.

READ-ONLY. No engine change, no registry write.
"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

sys.path.insert(0, str(ROOT / "backtest" / "tests"))
import exp_directional as D          # reuses its patch, arms and stats helpers
import test_experiments_craze as tc
from experiment_registry import EXPERIMENTS

OUT = ROOT / "backtest" / "tests" / "_fs_directional_leg.json"

# leg-family books only. champion_multi_sw10_leg is the shipping-family book
# (+239.12R IS / +72.79R OOS); champion_single_sw10_leg is the single plane;
# utcsat_entry_minus_1 is a shipping candidate. All causal stop sources.
BOOKS = ["champion_multi_sw10_leg", "champion_single_sw10_leg",
         "utcsat_entry_minus_1", "dirmatch_multi_sw10"]
ARMS = ("control", "long", "short", "both")


def main():
    d = D.get_data()
    D.identity_gate(d, tc.build_module())
    src = D.src_data() if hasattr(D, "src_data") else None
    if src is None:
        (oc15, of15), (oc1h, of1h) = D.load_unseen("15m"), D.load_unseen("1h")
        oos_fine = D.load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
        src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
               "oos": (oc1h,
                       tc._compute_swings(of1h, "continuous", min_bars=10),
                       oc15,
                       tc._compute_swings(of15, "continuous", min_bars=50),
                       oos_fine)}

    patched = D.patched_module()._collect_signals
    sim = tc.build_module()
    res = {}
    for name in BOOKS:
        if name not in EXPERIMENTS:
            print("%s : not in registry, skipped" % name)
            continue
        params = {**D.BP, **EXPERIMENTS[name]["params"]}
        print("\n" + "=" * 96)
        print("BOOK: %s   (pivot_rule=%s)" % (name, params.get("pivot_rule")))
        print("=" * 96)
        print("%-34s | %-29s | %-29s" % ("arm", "IS  n / net / R-per / PF", "OOS  n / net / R-per / PF"))
        print("-" * 96)
        res[name] = {}
        base = {}
        for scope in ("is", "oos"):
            tr_ctl = D.run(sim, "control", src[scope], params, patched)
            base[scope] = D.net_of(tr_ctl)
            rs_c = [float(t["r_multiple"]) for t in tr_ctl]
            row = {}
            row["control"] = {"n": len(tr_ctl),
                              "net": round(base[scope], 2),
                              "r_per": round(base[scope] / max(len(tr_ctl), 1), 3),
                              "pf": round(D.pf(rs_c), 2),
                              "dNet": 0.0}
            for a in ARMS[1:]:
                tr = D.run(sim, a, src[scope], params, patched)
                rs = [float(t["r_multiple"]) for t in tr]
                net = D.net_of(tr)
                pf = D.pf(rs)
                row[a] = {"n": len(tr), "net": round(net, 2),
                          "r_per": round(net / max(len(tr), 1), 3),
                          "pf": round(pf, 2), "dNet": round(net - base[scope], 2)}
            res.setdefault(name, {})[scope] = row
        for a in ARMS:
            i, o = res[name]["is"][a], res[name]["oos"][a]
            print("%-34s | %4d /%+8.1fR /%+.3f /%5.2f | %4d /%+8.1fR /%+.3f /%5.2f"
                  % (D.LBL[a][:34], i["n"], i["net"], i["net"] / max(i["n"], 1), i["pf"],
                     o["n"], o["net"], o["net"] / max(o["n"], 1), o["pf"]))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()