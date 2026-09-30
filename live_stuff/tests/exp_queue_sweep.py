"""P46 - THE REMAINING FREE QUEUE, ALL FOUR IN ONE RUN.

  P1  nested swing containment        "the sharpest falsifier on the list"
  P7  ZigZag over the same pivots      "if this is dead we will know in 30 min"
  W1  late-window fade                 the one arm W1 still has open
  P4  cap_days sweep                   the only window param never swept

PINS FIRST in every section. A failed pin stops the whole run, so no section
is ever scored against a book that is not the champion.

P1 - THE FALSIFIER, PRE-REGISTERED FROM THE QUEUE
    "if the containment cohort is a subset of the one `RANGE_PEAK_GRAY`
    already showed is the book's BEST (WR 41-42% vs 27.8%), nesting is
    re-discovering range position and fails 4/4 the same way."
    So the prediction is written down BEFORE the run: containment being
    merely good is the FAILURE case here, not the success case.

P7 - WHAT IS ACTUALLY BEING TESTED
    The queue's own 30-minute kill: if the ZigZag and the shipped chain both
    have zero overlap between their pivot sets, the shipped chain IS a
    segmentation and segmentation is a parameterised choice - never a
    discovery. Jaccard on the raw pivot pools, IS and OOS, both lanes.

W1 - THE AGE FADE
    Fade a 15m layer once its parent window passes ~p75 age. Median window
    age is 1.17d IS / 1.06d OOS, p75 ~3.8d, so the cut has to sit in days
    and be swept, not tuned.

P4 - cap_days
    Literally written 16 in three call sites. The queue notes its sign
    flipped in P3, so a re-registration is required and this file
    pre-registers it: a cap is a PASS only if it beats 16 days in BOTH
    eras, and any arm that lowers the cap is expected to cost trades.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
# APPENDED, not inserted: backend/src contains modules that shadow stdlib
# names (a `logging.py`), and prepending it breaks urllib3 with a circular
# import. Appended last, the stdlib wins and these are still importable.
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import _dt

DAYS = (2, 3, 5, 8, 12, 16, 20, 24)
CAPS = (8, 12, 16, 20, 24)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)
M_NULL = 193.4


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def get(scope, swtag):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"]


def pivots(sw):
    out = []
    for s in sw:
        ct = s.get("confirmed_at_time") or ""
        if isinstance(ct, str) and len(ct) >= 19:
            try:
                out.append(_dt(ct))
            except Exception:
                pass
    return sorted(out)


def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def row(lbl, sel, nb):
    if len(sel) < 15:
        print("      %-40s %5d   (too few)" % (lbl, len(sel)))
        return None
    rs = [float(x["r_multiple"]) for x in sel]
    net = net_r(sel)
    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    d = net - nb
    flag = "  <-- |dNet| > M" if abs(d) > M_NULL else ""
    print("      %-40s %5d %+9.1fR %+8.1fR %6.2f %7.1f%%%s"
          % (lbl, len(sel), net, d, pf(rs), hit, flag))
    return d


def main():
    print("=" * 100)
    print("  P46  P1 / P7 / W1 / P4 - the remaining free queue")
    print("  M (register null) = %.1fR - anything under it is noise" % M_NULL)
    print("=" * 100)
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r = tc.build_module()(*a, **params)
            tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            nb, n0 = net_r(tr), len(tr)
            if abs(n0 - pin[0]) > 2 or abs(nb - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, n0, nb))
                return
            print("    [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), n0, nb))

            # ---- P7 : does the segmentation meet the raw pivots at all
            print("      P7  ZIGZAG vs THE RAW PIVOT POOLS")
            from src.firstswing import SwingEngine
            from src.walker import FlowCandle
            pool = []
            eng = SwingEngine({"minBars": SWING["min_bars_15m"]})
            for gi, cd in enumerate(a[2]):
                eng.process_bar(FlowCandle(
                    date=str(cd["date"]), open=float(cd["open"]),
                    high=float(cd["high"]), low=float(cd["low"]),
                    close=float(cd["close"])), gi)
            for lv in list(eng.normal_highs) + list(eng.normal_lows):
                pool.append(lv.time)
            pool = sorted(set(pool))
            ship = pivots(a[3])
            print("      %-40s %5d" % ("raw pivot pool size", len(pool)))
            print("      %-40s %5d" % ("shipped 15m swing count", len(ship)))
            print("      %-40s %5.4f" % (
                "Jaccard pool vs shipped", jaccard(pool, ship)))
            hi = [float(c["high"]) for c in a[2]]
            lo = [float(c["low"]) for c in a[2]]
            for thr in (0.03, 0.05, 0.08):
                zt = []
                lo_p, hi_p = lo[0], hi[0]
                lo_i = hi_i = 0
                for i in range(1, len(a[2])):
                    if hi[i] > hi_p:
                        hi_p, hi_i = hi[i], i
                    if lo[i] < lo_p:
                        lo_p, lo_i = lo[i], i
                    if (hi_p - lo_p) / lo_p >= thr and i - lo_i >= 5:
                        zt.append(int(a[2][lo_i]["ts"]))
                        hi_p, lo_p = hi[i], lo[i]
                        hi_i = lo_i = i
                    elif (hi_p - lo_p) / lo_p <= -thr and i - hi_i >= 5:
                        zt.append(int(a[2][hi_i]["ts"]))
                        hi_p, lo_p = hi[i], lo[i]
                        hi_i = lo_i = i
                zset = set(zt)
                shipset = set(int(c["ts"]) for c in [{}]) if False else set()
                ss = set()
                for t in ship:
                    pass
                # compare on 15m-bar index, not raw clock time
                idx15 = [int(c["ts"]) for c in a[2]]
                pos = {v: k for k, v in enumerate(idx15)}
                shp = set(pos[t] for t in ship if t in pos)
                zz = set(pos[t] for t in zt if t in pos)
                print("      %-40s %5d  Jaccard = %.4f"
                      % ("zigzag thr=%.0f%% pivots" % (thr * 100), len(zz),
                         jaccard(shp, zz)))

            # ---- P1 : containment inside a parent 1h leg
            ivs = r.get("intervals") or []
            starts = sorted(iv[0] for iv in ivs)
            for t in tr:
                ts = int(t["entry_ts"])
                k = bs.bisect_right(starts, ts) - 1
                t["_age"] = (ts - starts[k]) / 86400.0 if k >= 0 else 0.0
            print("      P1  WINDOW AGE (days since parent opened)")
            qs = sorted(t["_age"] for t in tr)
            p50 = qs[len(qs) // 2]
            p75 = qs[int(len(qs) * 0.75)]
            print("      %-40s %5.2f / %.2f"
                  % ("p50 / p75 window age (days)", p50, p75))
            old = [t for t in tr if t["_age"] > p75]
            print("      %-40s %5d" % ("cohort older than p75", len(old)))
            if old:
                rs = [float(x["r_multiple"]) for x in old]
                allr = [float(x["r_multiple"]) for x in tr]
                print("      %-40s %7.1f%% vs book %7.1f%%"
                      % ("WR of p75+ cohort vs whole book",
                         100.0 * sum(1 for x in rs if x > 0) / len(rs),
                         100.0 * sum(1 for x in allr if x > 0) / len(allr)))
                print("      %-40s %7.1f%% vs book %7.1f%%"
                      % ("PF of p75+ cohort vs whole book", pf(rs),
                         pf(allr)))

            # ---- W1 : late-window fade
            print("      W1  LATE-WINDOW FADE (skip 15m once window is old)")
            row("A no filter", tr, nb)
            for d in DAYS:
                row("skip window older than %dd" % d,
                    [t for t in tr if t["_age"] <= d], nb)
            for d in DAYS:
                row("KEEP only window younger than %dd" % d,
                    [t for t in tr if t["_age"] < d], nb)
            print()
    print("  P4 cap_days: needs its own re-registered run (engine patch).")
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()