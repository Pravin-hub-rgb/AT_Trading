"""P93 - THE PARENT WINDOW'S DEATH AS AN EXIT.

FROM THE BRIEF, BIG PICKLE'S P92
    "The reference event for a position is the death of the higher-
     timeframe thesis that opened it."
    "Exit is the ratcheted 15m swing-pivot stop and nothing else - the 3R
     target at v18:592 is computed, stored, never checked. 85 trades outlive
     the 1h window that authorised them."

DESCRIPTIVE FIRST, ARM ONLY IF THE PRIOR SURVIVES
    The brief's own instruction, and it is the right one: measure the giveup
    first, and only write an arm if the giveup is NEGATIVE (i.e. the rule
    would ADD money) in at least 3 of 4 cells. FS_TIME_DECISION measured
    +85.1R mean giveup at the LTF's own FS against a population worth
    +263.7R, and survived anyway because the parent window closes on a
    different and typically LATER event. That prior is strong and against,
    and this run is built to let it kill the idea rather than to rescue it.

METHOD - THE PERMUTATION IS ON THE PER-TRADE FEATURE, NOT AN AGGREGATE
    For each trade: how much R was still open when the parent window that
    authorised it closed. Then a 200-draw block permutation that shuffles
    the WINDOW-END FEATURE across trades while leaving each trade's own R
    untouched, and asks how large a mean giveup chance alone produces.
    That is FS_TIME_DECISION's method and it is the correct one here: an
    aggregate permutation would be re-implementing P82's mistake of testing
    a difference of two large similar numbers instead of testing the
    feature.

    Grouping is by WINDOW, never by outcome. A trade's giveup is a property
    of when its window died, not of how it turned out, and no trade is ever
    assigned to a group by its r_multiple.

CAUSALITY
    Window end is known at the bar it occurs on. Exiting there is a rule a
    live system can execute, and it uses no information after that bar.

WHAT A PASS WOULD AND WOULD NOT MEAN
    It would mean the book's exits are late relative to its own thesis.
    It would NOT be adoptable without re-registration, because the rule
    removes trades into a family that CLOSED_DO_NOT_REPEAT already covers
    (exit at FS, wick, ratchet) and it would need the gray-vs-skip
    comparison the wick work showed is not optional.
"""
import collections
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

DRAWS = 2000
SEED = 20261006
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def main():
    print("=" * 100)
    print("  P93  THE PARENT WINDOW'S DEATH AS AN EXIT")
    print("=" * 100)
    print("  Descriptive first. An arm is written ONLY if the giveup is")
    print("  negative (the rule ADDS money) in >=3 of 4 cells.")
    print("  Permutation is on the per-trade feature, 2000 block draws.\n")

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    summary = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            res = tc.build_module()(*args, **params)
            tr = [t for t in res["ltf_trades"] if t.get("outcome") != "open"]
            # PIN[name] is (is_pin, oos_pin) - a tuple of tuples. Index it
            # as PIN[name][i] and NOT PIN[name][1][i]: the first attempt
            # compared the IS pin against the OOS pin, got +70.1R against
            # +325.8R, printed "CONTROL FAILED 500t +325.8R vs pin 500t
            # +325.8R" - a self-contradicting line, which is what exposed it.
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(tr), net_r(tr), *PIN[name][i]))
                return
            # the HTF windows the champion actually traded under
            iv = res.get("htf_windows") or res.get("intervals") or []
            iv = [w for w in iv if len(w) >= 3]
            iv.sort(key=lambda w: int(w[0]))
            def win_of(ts):
                for w in iv:
                    if int(w[0]) <= ts <= int(w[1]):
                        return int(w[0]), int(w[1])
                return None
            rows = []
            for t in tr:
                e, x = int(t["entry_ts"]), int(t["exit_ts"])
                w = win_of(e)
                if w is None:
                    continue
                rows.append((float(t["r_multiple"]), x, w[1], x > w[1]))
            if not rows:
                print("  --- [%s] no trades matched to a window" % scope.upper())
                continue
            outlive = [r for r in rows if r[3]]
            inside = [r for r in rows if not r[3]]
            gv = sum(r[0] for r in outlive) / len(outlive) if outlive else 0.0
            gi = sum(r[0] for r in inside) / len(inside) if inside else 0.0
            held = sum(r[0] for r in outlive)
            print("  --- [%s] %d trades, %d outlive the parent window "
                  "(%.1f%%)"
                  % (scope.upper(), len(rows), len(outlive),
                     100.0 * len(outlive) / len(rows)))
            print("      outlive: n %3d  mean R %+7.3f  total %+8.1fR"
                  % (len(outlive), gv, held))
            print("      inside : n %3d  mean R %+7.3f"
                  % (len(inside), gi))
            # permutation on the FEATURE: shuffle the outlive flag, keep R
            feats = [1.0 if r[3] else 0.0 for r in rows]
            rss = [r[0] for r in rows]
            n = len(rows)
            obs = sum(f * r for f, r in zip(feats, rss)) / max(1e-9, sum(feats))
            rnd = random.Random(SEED)
            cnt = 0
            for _ in range(DRAWS):
                idx = list(range(n))
                for s in range(0, n, 20):
                    blk = idx[s:s + 20]
                    rnd.shuffle(blk)
                    idx[s:s + 20] = blk
                sf = sum(rss[i] for i in idx if feats[i]) / max(
                    1e-9, sum(feats))
                if sf >= obs:
                    cnt += 1
            pv = cnt / float(DRAWS)
            print("      feature test: mean R of outlive trades %+.3f, "
                  "block-permutation p = %.4f" % (obs, pv))
            big = [r for r in outlive if r[0] > 10.0]
            print("      of those, trades >+10R: %d (%.1f%%), worth %+.1fR"
                  % (len(big), 100.0 * len(big) / max(1, len(outlive)),
                     sum(r[0] for r in big)))
            summary[(name, scope)] = (len(outlive), gv, gi)
            print()
    print("  Verdict on the descriptive phase:")
    neg = sum(1 for v in summary.values() if v[1] < 0)
    print("    cells where outlive-mean R is negative (rule would ADD): %d "
          "of %d" % (neg, len(summary)))
    print("    brief required >=3 of 4 -> %s"
          % ("ARM LICENSED" if neg >= 3 else "NO ARM WRITTEN"))
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()