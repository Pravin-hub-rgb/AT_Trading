"""P48 - P1, NESTED SWING CONTAINMENT. The queue's last sharpest falsifier,
measured BEFORE deciding whether the engine change is worth building.

THE QUEUE ITEM
    "The chain is a strict tiling (btc_swing.py:150) and walker.py:76
    _enforce_alternation both DESTROY nested-counter-leg evidence, so the
    system cannot say 'this 15m pullback sits inside a 15m up-leg that sits
    inside a 1h up-leg'. Letting legs nest changes which marks EXIST, so it
    is not a filter. Sharpest falsifier on the list: if the containment
    cohort is a subset of the one RANGE_PEAK_GRAY already showed is the
    book's BEST (WR 41-42% vs 27.8%), nesting is re-discovering range
    position and fails 4/4 the same way."

WHY THIS RUN MEASURES INSTEAD OF PATCHING
    The full test needs btc_swing.py:150 (the stitch - each engine restarts
    on the bar AFTER the previous swing's end extreme, which is what makes
    the chain a tiling) and walker.py:76 (_enforce_alternation, which
    collapses same-kind neighbours into the more extreme mark and therefore
    deletes every inner counter-leg) both edited. That is a rebuild of which
    marks exist, and it moves the control away from the pinned 500t/+325.8R,
    so a negative result would be uninterpretable against the old book.

    But the falsifier does not need the rebuild. Containment is a property
    of the EXISTING chain: does the 15m swing that produced a trade sit
    inside the 1h leg that contains it in time? That is measurable now. If
    the cohort is already the book's best, the rebuild is not worth
    building, and the falsifier answers itself.

THE FALSIFIER IS PRE-REGISTERED AND WORKS AGAINST US
    Both possible outcomes are useful, and both are recorded in the log as
    they happen. If the containment cohort's WR is near the book's 27.8%
    or below, containment is not the edge and the rebuild is not worth
    doing. If it is near RANGE_PEAK_GRAY's 41-42%, nesting is rediscovering
    range position and will fail 4/4 exactly as predicted.

    No arm in this file is a filter and none can be adopted. It decides
    whether to build.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import _dt

LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)
RANGE_PEAK_WR = (41.0, 42.0)
BOOK_WR = 27.8


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


def parent_of(ivs, t, d):
    best = None
    for iv in ivs:
        if iv[0] < t <= iv[1] and iv[2] == d:
            if best is None or iv[0] > best[0]:
                best = iv
    return best


def line(lbl, sel, nb):
    if len(sel) < 15:
        print("      %-34s %5d   (too few)" % (lbl, len(sel)))
        return None
    rs = [float(x["r_multiple"]) for x in sel]
    net = net_r(sel)
    wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    print("      %-34s %5d %+9.1fR %+8.1fR PF %5.2f WR %5.1f%%"
          % (lbl, len(sel), net, net - nb, pf(rs), wr))
    return wr


def main():
    print("=" * 100)
    print("  P48  P1 - NESTED SWING CONTAINMENT, MEASURED BEFORE BUILDING")
    print("=" * 100)
    print("  Falsifier: if containment WR ~ %.0f-%.0f%% (RANGE_PEAK_GRAY) the"
          % RANGE_PEAK_WR)
    print("  nesting is rediscovering range position. Book WR is %.1f%%."
          % BOOK_WR)
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
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            ivs = r.get("intervals") or []
            sw = {}
            for s in a[3]:
                ct = s.get("confirmed_at_time") or ""
                if isinstance(ct, str) and len(ct) >= 19:
                    try:
                        sw[int(s.get("swing_no", -1))] = s
                    except (TypeError, ValueError):
                        pass
            for t in tr:
                ts = int(t["entry_ts"])
                td = 1 if t["dir"] == "long" else -1
                iv = parent_of(ivs, ts, td)
                if iv is None:
                    t["_c"] = "NOIV"
                    continue
                pstart, pend, pdir = iv[0], iv[1], iv[2]
                i = bs.bisect_left(fts, pstart)
                j = bs.bisect_right(fts, min(ts, pend)) - 1
                if j <= i:
                    t["_c"] = "NOIV"
                    continue
                leg_lo, leg_hi = min(flo[i:j + 1]), max(fhi[i:j + 1])
                s = sw.get(t.get("swing_no"))
                if s:
                    seg = s.get("seg") or {}
                    sp = float(seg.get("start_px", 0) or 0)
                    epx = float(seg.get("end_px", 0) or 0)
                    s_lo, s_hi = min(sp, epx), max(sp, epx)
                else:
                    ep = float(t["entry_price"])
                    s_lo, s_hi = min(ep, float(t["sl"])), max(ep, float(t["sl"]))
                if s_hi <= leg_hi and s_lo >= leg_lo:
                    span = (leg_hi - leg_lo)
                    inner = span - (s_hi - s_lo)
                    t["_c"] = "CONTAINED"
                    t["_f"] = (inner / span) if span > 0 else 0.0
                else:
                    t["_c"] = "OUTSIDE"
                    t["_f"] = 0.0
            print("    [%s] control %dt %+.1fR (PIN ok)" % (scope.upper(),
                                                            n0, nb))
            line("A whole book", tr, nb)
            for ck in ("CONTAINED", "OUTSIDE", "NOIV"):
                line(ck, [t for t in tr if t["_c"] == ck], nb)
            con = [t for t in tr if t["_c"] == "CONTAINED"]
            if len(con) >= 15:
                con.sort(key=lambda t: -t["_f"])
                k = len(con) // 2
                line("CONTAINED, inner half (deepest)",
                     con[:k], nb)
                line("CONTAINED, outer half",
                     con[len(con) - k:], nb)
            print()
    print("  Nothing adopted. This decides only whether to BUILD the nesting.")


if __name__ == "__main__":
    main()