"""P95 - WHY DOES THE CHAMPION TAKE THE OTHER 80%? An entry-time autopsy.

THE QUESTION
    P94 found that 13-22% of the champion's trades - those outliving their
    parent window - carry 142-269% of the R, at 7-20x the book average,
    winning 24 of 24 shared half-years, with b = +4.9 to +5.25 after a
    half-year fixed effect. It failed only on M (best 0.93x), because the
    cohort is too small, and it is CIRCULAR as a rule because
    `exit_ts > window_end` is only known after the trade ran.

    So this run does NOT try to use the cohort. It asks the prior question:
    **do the other 80% have anything about them that was knowable at entry?**

WHAT COUNTS AS A REAL FINDING HERE, STATED FIRST
    An entry-time feature that separates them is worth a lot - it would make
    the cohort usable without the circularity. A feature that only separates
    them AFTER the fact is worthless and will look exactly as good as the
    cohort itself. **So every feature below is computed from bars at or
    before entry_ts and nothing else**, and the run reports the
    entry-time separation AND, for comparison, how much of the gap is
    post-hoc. A feature that only works post-hoc is labelled as such.

THE FEATURES - ALL ENTRY-TIME, ALL CAUSAL
      ATR%        trailing 96 x 15m true range over close, at entry
      dist_ma     (close - MA200)/ATR200, at entry - the P86 feature
      bars_to_window_end   how many 15m bars until the authorising window
                  closes, measured AT ENTRY. This is the one that could
                  make the cohort causal: a trade entered with many bars of
                  window left has room to outlive it, and that IS knowable
                  when the position is opened.
      hold_room   the entry's distance to its stop as a fraction of ATR -
                  how much room the trade has to run before it is stopped

FEATURES THAT ARE NOT MEASURED, ON PURPOSE
    Nothing grouped by outcome, r_multiple, exit price, or holding period.
    The cohort label itself is outcome-adjacent and is used only as the
    label to predict, never as a feature.

THE PRIOR
    If bars_to_window_end carries real signal, the cohort becomes usable and
    the circularity objection falls. If it does not, then the champion's
    80% were not mistakes in the entry decision - the outlive cohort is
    simply the subset that happened to work, and P94's number is a
    description of the book rather than a defect in it. **Both outcomes are
    worth having and they point in opposite directions.**
"""
import bisect as bs
import collections
import sys
from datetime import datetime, timezone
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

M_NULL = 193.4
ATR_BARS = 96
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def feats(c15):
    ts, cl, tr = [], [], []
    prev = None
    for c in c15:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev),
                                           abs(l - prev))
        ts.append(int(c["ts"]))
        cl.append(float(c["close"]))
        tr.append(r)
        prev = float(c["close"])
    pre = [0.0]
    for x in cl:
        pre.append(pre[-1] + x)
    ma, atr = [], []
    for i in range(len(cl)):
        lo = max(0, i - 199)
        ma.append((pre[i + 1] - pre[lo]) / (i + 1 - lo))
        seg = tr[max(0, i - ATR_BARS + 1):i + 1]
        atr.append(sum(seg) / len(seg) if seg else 0.0)
    return ts, cl, tr, ma, atr


def auc(pos, neg):
    """P(pos > neg) + 0.5 * P(tie). 0.5 = no separation."""
    if not pos or not neg:
        return float("nan")
    c = sum(1.0 for p in pos for n in neg if p > n)
    c += 0.5 * sum(1.0 for p in pos for n in neg if p == n)
    return c / (len(pos) * len(neg))


def main():
    print("=" * 100)
    print("  P95  WHY DOES THE CHAMPION TAKE THE OTHER 80%?")
    print("=" * 100)
    print("  Entry-time features only. The outlive label is the TARGET, never")
    print("  a feature. AUC 0.5 = no separation, 1.0 = perfect.")
    print("  M = %.1fR\n" % M_NULL)

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

    keys = ("atr_pct", "dist_ma", "bars_to_wend", "room")
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            res = tc.build_module()(*args, **params)
            tr = [t for t in res["ltf_trades"] if t.get("outcome") != "open"]
            if (abs(len(tr) - PIN[name][i][0]) > 2
                    or abs(net_r(tr) - PIN[name][i][1]) > 1.5):
                print("  [%s] CONTROL FAILED - STOP" % scope.upper())
                return
            c15 = args[2]
            ts, cl, trr, ma, atr = feats(c15)
            iv = [w for w in (res.get("htf_windows")
                             or res.get("intervals") or []) if len(w) >= 3]
            iv.sort(key=lambda w: int(w[0]))

            def wend_of(e, _iv=iv):
                for w in _iv:
                    if int(w[0]) <= e <= int(w[1]):
                        return int(w[1])
                return None
            OUT = {"atr_pct": ([], []), "dist_ma": ([], []),
                   "bars_to_wend": ([], []), "room": ([], [])}
            n_out = 0
            for t in tr:
                e, x = int(t["entry_ts"]), int(t["exit_ts"])
                we = wend_of(e)
                if we is None:
                    continue
                j = bs.bisect_left(ts, e)
                if j <= 0 or atr[j - 1] <= 0:
                    continue
                outlive = 1 if x > we else 0
                n_out += outlive
                a = (sum(trr[max(0, j - ATR_BARS):j]) / len(
                    trr[max(0, j - ATR_BARS):j])) / cl[j - 1] * 100.0
                dm = (cl[j - 1] - ma[j - 1]) / atr[j - 1]
                # bars of 15m until the window closes, measured AT ENTRY
                bwe = (we - e) / 900.0
                ep = float(t["entry_price"])
                room = abs(ep - float(t["sl"])) / atr[j - 1]
                for k, v in (("atr_pct", a), ("dist_ma", dm),
                             ("bars_to_wend", bwe), ("room", room)):
                    OUT[k][outlive].append(v)
            print("  --- [%s] %d trades, %d outlive (%.1f%%)"
                  % (scope.upper(), len(tr), n_out,
                     100.0 * n_out / max(1, len(tr))))
            print("      %-16s %8s %8s %8s   %s"
                  % ("feature", "AUC", "mean OUT", "mean IN", "read"))
            for k in keys:
                pos, neg = OUT[k]
                a = auc(pos, neg)
                mo = sum(pos) / len(pos) if pos else 0.0
                mn = sum(neg) / len(neg) if neg else 0.0
                read = ("separates" if a >= 0.60 or a <= 0.40
                        else "no separation")
                print("      %-16s %8.3f %8.3f %8.3f   %s"
                      % (k, a, mo, mn, read))
            print()
    print("  AUC is computed train-free: no threshold is fitted and none is")
    print("  selected, so these are descriptions of separation, not results.")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()