"""Window age and window length - the two questions the floor work left open.

WHY THESE TWO, AND WHY NOW
--------------------------
The floor sweep was run, produced a result, and then got swallowed by a bug hunt
that turned out to be my own false claim. The result was never written up. It is
also not the question W1 asks, so both belong here.

THE FLOOR, THE CORRECT WAY ROUND. With the causality question settled - the 2700 is
exact arithmetic, not a tuning value, and LOWERING it is a lookahead - the only
legitimate direction is UP. Raising the floor means waiting longer before a new
window is tradeable, which cannot admit anything the causal gate rejected. So the
sweep runs upward only, and the shipped 2700 is the baseline rather than a rung.

W1 - WINDOW DURATION AS A FEATURE. The queue asks whether how long a window has
been open carries information, and gives its own falsifier: "a median age shift with
no change in realised R means age is not a feature." So the test is not "does age
correlate with the outcome" but "does splitting trades by age change realised R".
If the halves are equal, age is a label and not a lever, and that is the answer.
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from progress import Announce, Bar, step          # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402

HTF_CLOSE = 3600
LTF_CLOSE = 900
FLOORS = (2700, 3600, 5400, 7200, 10800, 14400)
AGES_H = (12, 36, 96, 240)          # window age buckets in hours


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def collect(sim, E, book, swing, over):
    out = []
    for era in ("is", "oos"):
        d = E[era]
        e = EXPERIMENTS[book]
        p = {**EXPERIMENTS["fsent_champ_long"]["params"], **(e.get("params") or {})}
        p = {**p, **over}
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **p)
        for t in sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                        key=lambda t: int(t["entry_ts"])):
            out.append(t)
    return out


def leak(trades):
    return sum(1 for t in trades
               if int(t["window_start"]) + HTF_CLOSE - (int(t["entry_ts"]) + LTF_CLOSE) > 0)


def main():
    with step("loading candles + building engine", "~40s"):
        sim = build_family_module()
        E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    BOOKS = [("champ_long", "fsent_champ_long", "sw10"),
             ("mcloff", "fsent_champ_long_mcloff", "sw10"),
             ("mcloff_htf15", "fsent_champ_long_mcloff_htf15", "htf15"),
             ("sig_multi", "fsent_sig_multi", "sw10")]

    # ---------------------------------------------------------------- floors
    bar = Bar(len(BOOKS) * len(FLOORS), "floor sweep")
    print("\n" + "=" * 100)
    print("1. WINDOW FLOOR - raised only. Lowering it is a lookahead; raising it cannot add one.")
    print("=" * 100)
    print("  %-14s %-9s %5s %9s %8s %8s  %s"
          % ("floor", "book", "n", "net", "ddIS", "ddOOS", "neg cells"))
    for label, book, swing in BOOKS:
        for f in FLOORS:
            tr = collect(sim, E, book, swing, {"exp_window_floor_s": f})
            rs = [net_r([t]) for t in tr]
            per = defaultdict(list)
            for t, r in zip(tr, rs):
                per[cell(t["entry_ts"])].append(r)
            neg = sorted(c for c in per if sum(per[c]) < 0)
            dd = {}
            for nm, era in (("IS", "is"), ("OOS", "oos")):
                sub = [net_r([t]) for t in collect(sim, E, book, swing,
                                                   {"exp_window_floor_s": f})] \
                    if False else None
            isr = [net_r([t]) for t in tr if cell(t["entry_ts"])]
            dd_is = _dd([net_r([t]) for t in tr])
            print("  %-14d %-9s %5d %+9.1f %8s %8s  %s%s"
                  % (f, label, len(tr), sum(rs), "", "",
                     ",".join(neg) or "NONE", "  <- shipped" if f == 2700 else ""))
            out.setdefault("floor", {})["%s|%d" % (label, f)] = dict(
                n=len(tr), net=round(sum(rs), 2), neg=neg)
            bar.update("%s f=%d" % (label, f))
    bar.close("done")

    # ------------------------------------------------------- W1 window age
    bar2 = Bar(len(BOOKS), "age analysis")
    print("\n" + "=" * 100)
    print("2. W1 - IS WINDOW AGE A FEATURE?  (queue falsifier: equal R in both halves = not a feature)")
    print("=" * 100)
    print("    age = how long the window had been open when the trade was taken")
    print("  %-14s %-10s %5s %9s %9s %9s" % ("book", "age bucket", "n", "net", "R/trade", "win%"))
    for label, book, swing in BOOKS:
        tr = collect(sim, E, book, swing, {})
        rows = []
        for t in tr:
            age = (int(t["entry_ts"]) - int(t["window_start"])) / 3600.0
            rows.append((age, net_r([t])))
        print("  %-14s %-10s %5d %+9.1f %9.3f %8.1f%%"
              % (label, "ALL", len(rows), sum(r for _a, r in rows),
                 sum(r for _a, r in rows) / len(rows),
                 100.0 * sum(1 for _a, r in rows if r > 0) / len(rows)))
        med = sorted(a for a, _r in rows)[len(rows) // 2]
        print("    median window age at entry: %.1f h (%.1f d)" % (med, med / 24.0))
        for lo, hi in zip(AGES_H, AGES_H[1:] + (10 ** 6,)):
            sub = [r for a, r in rows if lo <= a < hi]
            if not sub:
                continue
            print("  %-14s %-10s %5d %+9.1f %9.3f %8.1f%%"
                  % ("", "%d-%dh" % (lo, hi) if hi < 10 ** 6 else "%dh+" % lo,
                     len(sub), sum(sub), sum(sub) / len(sub),
                     100.0 * sum(1 for r in sub if r > 0) / len(sub)))
        out.setdefault("age", {})[label] = dict(
            median_age_h=round(med, 1),
            buckets={("%d-%d" % (lo, hi)): dict(
                n=len([1 for a, _r in rows if lo <= a < hi]),
                net=round(sum(r for a, r in rows if lo <= a < hi), 2))
                for lo, hi in zip(AGES_H, AGES_H[1:] + (10 ** 6,))})
        bar2.update(label)
    bar2.close("done")

    with open("_window_age_and_floor.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("\n  wrote _window_age_and_floor.json")
    return 0


def _dd(rs):
    c = pk = m = 0.0
    for x in rs:
        c += x
        pk = max(pk, c)
        m = max(m, pk - c)
    return m


if __name__ == "__main__":
    sys.exit(main())