"""P55 - CAN THE REGIME INVERSION BE DETECTED AT RUNTIME? If yes, the
geometry gate works; if no, P54's clean inversion is unexploitable.

THE PROBLEM P54 LEFT OPEN
    The 1h swing geometry is strongly predictive INSIDE each era and
    opposite ACROSS them. IS wants big and long swings (dur>19 bars, PF 3.59,
    WR 35.9% against a book 29.9%); OOS wants small and short (dur<=7 bars,
    PF 2.41 against a book 1.77). Four independent features now show the
    same shape. Each is a regime descriptor that cannot be turned into a
    rule, because the eras disagree on which side to trade.

    The one thing that would make them usable is knowing WHICH REGIME IS
    CURRENT, at the moment a window opens, from information available then.

PART A - THE CHEAP PRE-TEST, AND IT CAN KILL THE IDEA ON ITS OWN
    A trailing measure of how big recent 1h swings have been, computed only
    from swings confirmed before the window opens. If that measure does not
    separate IS from OOS, no downstream rule can work and the whole family
    is dead - so this runs first and is reported on its own.

PART B - THE ADAPTIVE GATE, ONLY IF PART A SEPARATES
    Keep the big-swing windows while the trailing regime reads big, and the
    small-swing windows while it reads small. One rule, switching on a
    signal the engine can actually compute live.

PRE-REGISTERED, NO FITTING
    REGIME  = mean of (swing travel / ATR) over the last K confirmed 1h
              swings, K in {8, 16, 24}. A time-blended measure is used
              rather than a percentile of realised outcomes, because
              percentiles of outcomes are not knowable live.
    SPLIT   = median of that measure over the trailing window itself, so
              the rule is self-calibrating and needs no fitted threshold.
    BIG / SMALL = the window's own swing travel/ATR above or below the
              median of all window-opening swings in the cell. The median
              is a fixed, un-tuned dividing point.
    PASS    = beats the control in BOTH eras of BOTH lanes, on a book that
              keeps at least half the trades.

THE PROBE RUNS ON EVERY ARM
    Window open shifted one bar later hands the signal more information. A
    causal rule must get worse or stay flat; one that improves is leaking.
    This is the probe that caught P52's +180.9R.
"""
import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m
from test_experiments_craze import _compute_swings
from engine.v18_params import SWING
from exp_decay_switch import _dt

M_NULL = 193.4
KS = (8, 16, 24)
LANES = (
    ("champion_multi_sw10", "sw10", (500, 325.8), (279, 70.1)),
    ("utcsat_multi_sw10", "sw10", (453, 279.5), (254, 66.9)),
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


def q(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(len(s) * p))] if s else 0.0


def main():
    print("=" * 100)
    print("  P55  CAN THE REGIME INVERSION BE DETECTED AT RUNTIME?")
    print("=" * 100)
    print("  PART A first: if the trailing regime measure does not separate")
    print("  IS from OOS, the family is dead and PART B is not run.")
    print("  M = %.1fR\n" % M_NULL)
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        cells = {}
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
            # every 1h swing: confirm time, travel/ATR
            sw_mag = []
            for S in a[1]:
                ct = S.get("confirmed_at_time") or ""
                if not isinstance(ct, str) or len(ct) < 19:
                    continue
                seg = S.get("seg") or {}
                si, ei = seg.get("start_idx"), seg.get("end_idx")
                sp = float(seg.get("start_px", 0) or 0)
                epx = float(seg.get("end_px", 0) or 0)
                if si is None or ei is None or sp <= 0 or epx <= 0:
                    continue
                ei = int(ei)
                if ei >= len(atr) or atr[ei] <= 0:
                    continue
                try:
                    cts = _dt(ct)
                except Exception:
                    continue
                sw_mag.append((cts, abs(epx - sp) / atr[ei], int(ei) - int(si)))
            sw_mag.sort()
            swc = [x[0] for x in sw_mag]
            ivs = sorted(r.get("intervals") or [], key=lambda v: v[0])
            legs = [L for L in (list(r.get("htf_trades") or []) +
                                list(r.get("htf_trades_b2") or []))
                    if L.get("outcome") != "open"]
            for t in tr:
                ts = int(t["entry_ts"])
                td = 1 if t["dir"] == "long" else -1
                bi = None
                for ix, v in enumerate(ivs):
                    if v[0] < ts <= v[1] and v[2] == td:
                        if bi is None or v[0] > ivs[bi][0]:
                            bi = ix
                t["_ix"] = bi
            for v in ivs:
                pass
            print("    [%s] control %dt %+.1fR (PIN ok)   %d 1h swings, "
                  "%d windows, %d legs" % (scope.upper(), n0, nb,
                                           len(sw_mag), len(ivs), len(legs)))
            # window geometry + trailing regime at its open
            win = {}
            for L in legs:
                sn = L.get("swing_no")
                if sn is None:
                    continue
                try:
                    S = a[1][int(sn)]
                except (IndexError, TypeError, ValueError):
                    continue
                seg = S.get("seg") or {}
                si, ei = seg.get("start_idx"), seg.get("end_idx")
                sp = float(seg.get("start_px", 0) or 0)
                epx = float(seg.get("end_px", 0) or 0)
                if si is None or ei is None or ei <= si or sp <= 0 \
                        or epx <= 0:
                    continue
                ei = int(ei)
                if ei >= len(atr) or atr[ei] <= 0:
                    continue
                win[int(L["entry_ts"])] = {
                    "mag": abs(epx - sp) / atr[ei],
                    "dur": int(ei) - int(si),
                }
            print("      PART A  does the trailing regime separate the eras?")
            for K in KS:
                vals = []
                for t in tr:
                    if t["_ix"] is None:
                        continue
                    s = ivs[t["_ix"]][0]
                    k = bs.bisect_right(swc, s) - 1
                    if k < K - 1:
                        continue
                    w = [x[1] for x in sw_mag[k - K + 1:k + 1]]
                    vals.append(sum(w) / len(w))
                if len(vals) < 20:
                    print("        K=%-3d too few (%d)" % (K, len(vals)))
                    continue
                print("        K=%-3d trailing regime  p25 %.2f  p50 %.2f  "
                      "p75 %.2f  n=%d" % (K, q(vals, .25), q(vals, .5),
                                          q(vals, .75), len(vals)))
                cells[(key, scope, K)] = vals
            print()
        # cross-era separation
        print("      PART A VERDICT  IS vs OOS on the same lane")
        for K in KS:
            a1 = cells.get((key, "is", K))
            a2 = cells.get((key, "oos", K))
            if not a1 or not a2:
                continue
            print("        K=%-3d  IS p50 %.2f   OOS p50 %.2f   gap %.2f"
                  % (K, q(a1, .5), q(a2, .5), q(a1, .5) - q(a2, .5)))
        print()
    print("  Part B is run only if Part A separates. Nothing adopted.")


if __name__ == "__main__":
    main()