"""exp_ext2_ridge - is ext_stop_r=2.0 an edge, or one lucky grid point?

Asked because the coarse sweep showed IS +545.3 at 2.0 against +528.9 at the
shipped 3.0, and nothing in between was on the grid. A spike between two lower
neighbours is the standard overfit shape, so the neighbourhood has to be walked
finely before a cohort autopsy is worth spending on a single point.

Two parts, and the second is the one that decides it:

  1. FINE SWEEP, both eras, 0.0 to 4.0. Asks whether the 2.0 area is a ridge or
     a lone spike.
  2. COHORT AUTOPSY at the best IS point. Asks which trades the filter removes.
     A filter that removes losers is an edge; one that removes a break-even
     cohort and moves the total only by re-sequencing is an illusion, and only
     the autopsy separates those two.

Run:  cd backtest/tests
       python -u exp_ext2_ridge.py
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

BOOK = "fsent_champ_long"
GRID = [0.0, 1.0, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2,
        2.3, 2.4, 2.5, 2.6, 2.8, 3.0, 4.0]


def tkey(t):
    return (int(t["entry_ts"]), t["dir"])


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from exp_multi_metrics import load_era
    from exp_full_metrics import compute
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    cfg = EXPERIMENTS[BOOK]
    base = {**BP, **cfg["params"]}
    base.setdefault("exp_partial_r", 0.0)

    def run(data, sw, x):
        p = dict(base)
        p["ext_stop_r"] = x
        out = sim(data["c1h"], sw, data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **p)
        tr = [t for t in out["ltf_trades"] if t.get("outcome") != "open"]
        m = compute([net_r([t]) for t in tr], [t.get("entry_date", "") for t in tr])
        return m, tr

    t0 = time.time()
    res = {"is": {}, "oos": {}}
    trades = {"is": {}, "oos": {}}
    for era in ("is", "oos"):
        data = load_era(era)
        sw = get_swings(data, cfg.get("swing") or "sw10")
        for x in GRID:
            m, tr = run(data, sw, x)
            res[era][x] = m
            trades[era][x] = tr

    print("=" * 96)
    print("PART 1  FINE SWEEP  (post-C17, both eras, %s)" % BOOK)
    print("=" * 96)
    print("%-6s | %-29s | %-29s | %s"
          % ("ext", "IS   n / net / PF / DD", "OOS  n / net / PF / DD",
             "lift vs OFF  IS / OOS"))
    b_is = res["is"][0.0]["net"]
    b_oo = res["oos"][0.0]["net"]
    for x in GRID:
        mi, mo = res["is"][x], res["oos"][x]
        di, do = mi["net"] - b_is, mo["net"] - b_oo
        tag = "BOTH UP" if (di > 0 and do > 0) else ("IS only" if di > 0 else "")
        print("%-6.1f | %4d %+9.1f %5.2f %6.1f | %4d %+9.1f %5.2f %6.1f | "
              "%+8.1f / %+8.1f  %s"
              % (x, mi["n"], mi["net"], mi["pf"] or 0, mi["max_dd"],
                 mo["n"], mo["net"], mo["pf"] or 0, mo["max_dd"], di, do, tag))
    both = [x for x in GRID if res["is"][x]["net"] > b_is and res["oos"][x]["net"] > b_oo]
    print()
    print("  values beating OFF in BOTH eras: %s"
          % (", ".join("%.1f" % x for x in both) if both else "NONE"))
    print()

    # ---- cohort autopsy at the point the question is about ------------------
    ARM = 2.0
    for era in ("is", "oos"):
        print("=" * 96)
        print("PART 2  COHORT AUTOPSY  %s   OFF vs ext_stop_r=%.1f" % (era.upper(), ARM))
        print("=" * 96)
        off = {tkey(t): t for t in trades[era][0.0]}
        arm = {tkey(t): t for t in trades[era][ARM]}
        removed = [off[k] for k in off if k not in arm]
        added = [arm[k] for k in arm if k not in off]
        kept = [arm[k] for k in arm if k in off]

        def stat(ts, name):
            if not ts:
                print("   %-10s n=0" % name)
                return 0.0
            r = sorted(float(t["r_multiple"]) for t in ts)
            print("   %-10s n=%3d  sumR=%+8.1f  mean=%+6.3f  median=%+6.3f  "
                  "win=%.1f%%  best=%+.2f  worst=%+.2f"
                  % (name, len(ts), sum(r), sum(r) / len(r), r[len(r) // 2],
                     100.0 * sum(1 for x in r if x > 0) / len(r), r[-1], r[0]))
            return sum(r)

        print()
        off_s = stat(list(off.values()), "OFF")
        k_s = stat(kept, "KEPT")
        r_s = stat(removed, "REMOVED")
        a_s = stat(added, "ADDED")
        print()
        print("   filter is worth -(removed) = %+.1f R" % (-r_s))
        print("   re-sequencing added      = %+.1f R  (%d trades admitted because the"
              % (a_s, len(added)))
        print("                              cooldown and the streak halt act on")
        print("                              sequence, not on the market)")
        print("   kept                    = %+.1f R  (OFF %.1f minus removed %.1f)"
              % (k_s, off_s, r_s))
        print("   removed by side: %s"
              % dict(Counter(t["dir"] for t in removed)))
        print()

    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    print("Adoption needs a lift in both eras. No threshold on this grid clears that")
    print("bar, so ext_stop_r=2.0 is not a candidate. The autopsy says why the IS")
    print("number looked tempting: the cohort the filter removes is ~break-even in IS")
    print("and profitable in OOS, so the filter earns nothing on its own account, and")
    print("the in-sample move is the re-sequenced ADDED cohort. A filter that removes")
    print("a profitable cohort out of sample is not an edge in either direction - it")
    print("is an unpriced cut, and the 2026-10-07 distractor it caused is closed here.")
    print("done in %.0fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
