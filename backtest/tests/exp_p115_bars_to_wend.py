"""P115 - is bars_to_wend causal, or is P95's 0.847 AUC the arithmetic identity?

P95 reported AUC 0.843-0.867 for bars_to_wend separating trades that outlive their
HTF window from those that do not. The label is exit_ts > window_end, which is
hold > bars_to_wend. The feature and the label share a variable, so part of that
0.85 may be bookkeeping rather than signal.

Pre-registered here, before the run, so a null cannot be reinterpreted afterwards.

  label                                        reads              verdict
  1  bwe -> bars_held > 96                     pure duration       >=0.60 real
                                                              ~0.50 identity
  2  bwe -> r_multiple > 0                     profitability,      duration-free
                                               duration-free
  3  bwe -> |move| / ATR > 1.0                 size-free edge

  STOP RULE: if (1) is ~0.50, stop. (2) and (3) then answer a dead question.
  Acceptable outcome: (1) ~ 0.50 means P95's 0.847 was arithmetic and P94/P95
  dies as a rule, descriptive only. That is a publishable result, not a failure.

Run on BOTH books. P95 ran on champion_multi_sw10, which after 3f91c2c resolves to
pivot_rule="origin". bwe is built from window intervals and entry timestamps, which
C16 does not touch, so the feature should be identical on both books. If the AUC
still moves, it moved because the trade set and its R changed, not because the
feature improved.

Run: python -u exp_p115_bars_to_wend.py     (about 4 min)
"""
import sys
import bisect as bs
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r, get_data
import test_experiments_craze as tc
import exp_inside80 as I80
from test_4_new_concepts import load_unseen, load_fine_1m

AUC = I80.auc                      # same estimator P95 used
feats = I80.feats
KEEP_HOLD = 96

BOOKS = (("champion_multi_sw10", "ORIGIN  (P95's book)"),
         ("champion_multi_sw10_leg", "LEG  (shipping)"))


def _oos_args():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            load_fine_1m(c15o[0]["ts"], c15o[-1]["ts"]))


def collect(res, tr, c15):
    ts, cl, trr, ma, atr = feats(c15)
    iv = [w for w in (res.get("htf_windows") or res.get("intervals") or [])
          if len(w) >= 3]
    iv.sort(key=lambda w: int(w[0]))

    def wend_of(e):
        for w in iv:
            if int(w[0]) <= e <= int(w[1]):
                return int(w[1])
        return None

    P = {1: ([], []), 2: ([], []), 3: ([], [])}
    holds, bwes, skipped = [], [], 0
    for t in tr:
        e = int(t["entry_ts"])
        we = wend_of(e)
        if we is None:
            skipped += 1
            continue
        j = bs.bisect_left(ts, e)
        if j <= 0 or atr[j - 1] <= 0:
            skipped += 1
            continue
        held = int(t.get("exit_idx", j)) - int(t.get("entry_idx", j))
        bwe = (we - e) / 900.0
        move = abs(float(t["exit_price"]) - float(t["entry_price"])) / atr[j - 1]
        holds.append(held)
        bwes.append(bwe)
        for k, y in ((1, 1 if held > KEEP_HOLD else 0),
                     (2, 1 if float(t["r_multiple"]) > 0 else 0),
                     (3, 1 if move > 1.0 else 0)):
            P[k][y].append(bwe)
    return P, holds, bwes, skipped


def main():
    d = get_data()
    is_args = (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])
    print("=" * 96)
    print("  P115  IS bars_to_wend CAUSAL, OR IS P95's 0.847 AUC THE IDENTITY?")
    print("=" * 96)
    print("  pre-registered: (1) >= 0.60 real, ~0.50 identity. STOP if (1) ~ 0.50.")
    print("  labels are not defined from the feature.\n")

    for name, tag in BOOKS:
        print("-" * 96)
        print("  BOOK: %s   %s" % (name, tag))
        sim = tc.build_module()
        params = {**BP, **EXPERIMENTS[name]["params"]}
        for scope in ("is", "oos"):
            args = is_args if scope == "is" else _oos_args()
            res = sim(*args, **params)
            tr = [t for t in res["ltf_trades"] if t.get("outcome") != "open"]
            P, holds, bwes, skipped = collect(res, tr, args[2])
            print("  [%s] %d trades  netNET %+.1fR"
                  % (scope.upper(), len(tr), net_r(tr)))
            print("        bwe       mean %.1f bars  median %.1f  max %.1f  (skipped %d)"
                  % (sum(bwes) / len(bwes), sorted(bwes)[len(bwes) // 2],
                     max(bwes), skipped))
            print("        bars_held mean %.1f  median %d  p90 %d"
                  % (sum(holds) / len(holds), sorted(holds)[len(holds) // 2],
                     sorted(holds)[int(0.9 * len(holds))]))
            for k, label in ((1, "hold > %d bars" % KEEP_HOLD),
                             (2, "r_multiple > 0"),
                             (3, "|move| / ATR > 1.0")):
                pos, neg = P[k]
                a = AUC(pos, neg)
                v = "SEPARATES" if abs(a - 0.5) >= 0.10 else "no separation (identity)"
                print("        (%d) bwe -> %-20s AUC %.3f  n=%d/%d  %s"
                      % (k, label, a, len(pos), len(pos) + len(neg), v))
            print()
        print()

    print("=" * 96)
    print("  P95 UNIT CHECK")
    print("=" * 96)
    print("  P95 quotes bars_to_wend 458.8 bars. At 15m that is %.2f days, not 76."
          % (458.8 * 15 / 60.0 / 24.0))


if __name__ == "__main__":
    main()