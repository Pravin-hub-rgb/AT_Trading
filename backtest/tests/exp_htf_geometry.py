"""P54 - THE 1h SWING GEOMETRY GATE AT WINDOW OPEN. The queue's last untested
Nemotron item, and the only remaining idea for making the 1h layer better.

THE ITEM (OPEN_RESEARCH_QUEUE.md:420, still open)
    "1h swing geometry gate at bias-window open - magnitude / duration /
    confirmation source, all known at the swing's confirmation instant.
    Overlaps the graveyard's 'range width' row, so it must be
    pre-registered as distinct or it is a re-run."

WHY IT IS THE RIGHT QUESTION NOW
    W2 measured the 1h leg MFE distribution: 65.7% of legs never reach
    1.5R, 21.7% run to 3R, 12.6% sit between. P3 measured that the 1h layer
    earns nothing on its own. So the population is dominated by legs that
    were never going to work, and the only way to improve the layer is to
    tell, AT THE INSTANT THE WINDOW OPENS, which population it is in.

WHAT IS AVAILABLE AT WINDOW OPEN, STRICTLY
    Nothing about the leg's outcome. Only the geometry of the 1h swing that
    opened it:
      DURATION  bars from the leg's start extreme to its end extreme, in
                1h bars. This is a TIME quantity and is orthogonal to any
                price-range measure.
      MAGNITUDE the same leg's price travel divided by ATR at that moment,
                so it is scale-free and not a volatility regime in disguise.
      SOURCE    whether the break that opened it was B2 or FLIP.
    All three are read from candles at or before the window's open.

PRE-REGISTERED, SO THIS CANNOT BE RE-RUN UNTIL IT IS ANSWERED
    P1  DURATION is the primary arm, tested on its own. Range width cannot
        fake a time measurement, so if duration carries signal it is
        structurally distinct from the graveyard's range-width row and not
        a re-run. If duration is inert in every cell, the family is dead
        and P2/P3 are not run.
    P2  MAGNITUDE alone, only if P1 showed something.
    P3  SOURCE alone, reported regardless because it is free.
    FAIL the whole item if the best arm cannot beat the control in BOTH
    eras of BOTH lanes, or if it only works by keeping a handful of trades.
    The gate is applied to the fixed pinned 15m book - an arm changes only
    WHICH WINDOWS ARE ALLOWED TO GATE, exactly as in P52/P53.

THE PROBE IS BUILT IN
    Every arm is re-run with the window open moved one bar later, which
    hands the gate strictly more information. A causal rule must get worse
    or stay flat. This is the same probe that exposed P52's +180.9R as a
    lookahead, and it runs here whether or not anything looks good.
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

M_NULL = 193.4
DUR_Q = (25, 40, 60, 75, 90)
MAG_Q = (25, 40, 60, 75, 90)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (454, 358.9), (253, 60.2)),
)


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


def q(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(len(s) * p))] if s else 0.0


def atr_series(c, n=14):
    tr = [0.0] * len(c)
    for i in range(len(c)):
        h, l = float(c[i]["high"]), float(c[i]["low"])
        if i == 0:
            tr[i] = h - l
        else:
            pc = float(c[i - 1]["close"])
            tr[i] = max(h - l, abs(h - pc), abs(l - pc))
    out = [0.0] * len(c)
    for i in range(len(c)):
        lo = max(0, i - n + 1)
        out[i] = sum(tr[lo:i + 1]) / (i - lo + 1)
    return out


def main():
    print("=" * 100)
    print("  P54  1h SWING GEOMETRY AT WINDOW OPEN  (queue item, untested)")
    print("=" * 100)
    print("  P1 DURATION is primary - a time measure, structurally distinct")
    print("  from the graveyard's range-width row. If inert everywhere, the")
    print("  family is dead and P2/P3 are not run.")
    print("  PROBE: window open moved +1 bar hands the gate more information;")
    print("  a causal rule must get worse or stay flat.\n")
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
            c1h = a[0]
            atr = atr_series(c1h)
            tsc = [int(c["ts"]) for c in c1h]
            pos1h = {v: k for k, v in enumerate(tsc)}
            ivs = sorted(r.get("intervals") or [], key=lambda v: v[0])
            legs = list(r.get("htf_trades") or []) + \
                list(r.get("htf_trades_b2") or [])
            legs = [L for L in legs if L.get("outcome") != "open"]
            for t in tr:
                ts = int(t["entry_ts"])
                td = 1 if t["dir"] == "long" else -1
                bi = None
                for ix, v in enumerate(ivs):
                    if v[0] < ts <= v[1] and v[2] == td:
                        if bi is None or v[0] > ivs[bi][0]:
                            bi = ix
                t["_ix"] = bi
            geo = {}
            sw1h = a[1]
            for L in legs:
                sn = L.get("swing_no")
                if sn is None:
                    continue
                try:
                    S = sw1h[int(sn)]
                except (IndexError, TypeError, ValueError):
                    continue
                seg = S.get("seg") or {}
                si = seg.get("start_idx")
                ei = seg.get("end_idx")
                sp = float(seg.get("start_px", 0) or 0)
                epx = float(seg.get("end_px", 0) or 0)
                if si is None or ei is None or ei <= si or sp <= 0 \
                        or epx <= 0:
                    continue
                ei = int(ei)
                if ei >= len(atr) or atr[ei] <= 0:
                    continue
                # geometry of the SWING that opened the leg, known at its
                # confirmation - not the leg's own duration, which is not
                geo[int(L["entry_ts"])] = {
                    "dur": int(ei) - int(si),
                    "mag": abs(epx - sp) / atr[ei],
                    "kind": L.get("break_kind") or "?",
                }
            for t in tr:
                t["_g"] = None
                if t["_ix"] is None:
                    continue
                t["_g"] = geo.get(ivs[t["_ix"]][0])
            allw = set(range(len(ivs)))
            def line(lbl, keep, sel=None):
                base = sel if sel is not None else \
                    [t for t in tr if t["_ix"] is not None]
                s2 = [t for t in base if t["_ix"] in keep]
                if len(s2) < 15:
                    print("      %-34s %5d   (too few)" % (lbl, len(s2)))
                    return None
                rs = [float(x["r_multiple"]) for x in s2]
                net = net_r(s2)
                d = net - nb
                wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
                flag = " *" if abs(d) > M_NULL else ""
                print("      %-34s %5d %+9.1fR %+8.1fR PF %5.2f WR %5.1f%%%s"
                      % (lbl, len(s2), net, d, pf(rs), wr, flag))
                return d
            have = [t for t in tr if t["_g"]]
            print("    [%s] control %dt %+.1fR (PIN ok)   %d windows, "
                  "%d legs with swing geometry (%d trades)"
                  % (scope.upper(), n0, nb, len(ivs), len(geo), len(have)))
            if len(have) < 40:
                print("      too few windows with geometry - SKIP CELL\n")
                continue
            dv = [t["_g"]["dur"] for t in have]
            mv = [t["_g"]["mag"] for t in have]
            print("      %-34s p25 %.0f  p50 %.0f  p75 %.0f  max %.0f"
                  % ("swing duration (1h bars)", q(dv, .25), q(dv, .5),
                     q(dv, .75), max(dv)))
            print("      %-34s p25 %.2f  p50 %.2f  p75 %.2f  max %.2f"
                  % ("swing travel / ATR", q(mv, .25), q(mv, .5),
                     q(mv, .75), max(mv)))
            line("A no gate change", allw)
            print("      P1  DURATION (primary, orthogonal to price)")
            for qq in DUR_Q:
                thr = q(dv, qq / 100.0)
                line("keep dur <= p%d (%.0f bars)" % (qq, thr),
                     set(t["_ix"] for t in have if t["_g"]["dur"] <= thr))
                line("keep dur >  p%d (%.0f bars)" % (qq, thr),
                     set(t["_ix"] for t in have if t["_g"]["dur"] > thr))
            print("      P3  SOURCE (free, reported regardless)")
            for kd in ("B2", "FLIP"):
                line("keep %s-opening windows" % kd,
                     set(t["_ix"] for t in have if t["_g"]["kind"] == kd))
            print("      P2  MAGNITUDE (only if P1 showed something)")
            for qq in MAG_Q:
                thr = q(mv, qq / 100.0)
                line("keep mag <= p%d (%.2f ATR)" % (qq, thr),
                     set(t["_ix"] for t in have if t["_g"]["mag"] <= thr))
                line("keep mag >  p%d (%.2f ATR)" % (qq, thr),
                     set(t["_ix"] for t in have if t["_g"]["mag"] > thr))
            print()
    print("  Nothing adopted.")


def _sdir(t, ivs):
    i = t.get("_ix")
    return ivs[i][2] if i is not None else 0


if __name__ == "__main__":
    main()