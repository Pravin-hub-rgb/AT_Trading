"""P47 - WHAT EXACTLY IS THE TIGHT-STOP HALF SEEING? A decomposition.

THE QUESTION
    P45 found the book splits hard by stop distance: 251 tight-stop trades
    make +300.0R of a +325.8R book. The obvious reading is price action -
    a tight stop means the 15m swing low is close to entry, a wide stop
    means price entered deep into the leg. But there is a competing
    explanation that has not been ruled out, and if it is the real one then
    the whole thing is a volatility proxy wearing a price-action costume.

HYPOTHESIS H1 - IT IS JUST VOLATILITY
    stop distance = |entry - sl| / entry. In a high-ATR regime a swing low
    is simply further from entry in percentage terms. If tight/wide is
    mostly "low ATR vs high ATR", the split is a volatility filter, the
    volatility state is already known to the engine, and the edge is not
    new. This is testable directly: correlate the split variable against
    ATR at entry.

HYPOTHESIS H2 - IT SURVIVES NORMALISATION
    If the gradient survives dividing by ATR, the quantity is genuinely
    price action - "this pullback went deep into the leg" - and not a
    volatility regime. This is the version worth having.

HYPOTHESIS H3 - IT IS POSITION WITHIN THE LEG, NOT STOP WIDTH
    A wide stop and a late entry can look identical. Measure where the
    entry sits inside its own swing leg as a fraction, which is scale-free
    by construction, and bucket that instead.

THE TEST THAT DECIDES ANY OF IT
    P45's own weakness was that "half" was chosen after seeing the
    distribution. Here every threshold is swept and the question is not
    "does a good split exist" but "does ANY threshold produce a dNet whose
    null 95th percentile is exceeded", using M = 193.4R from the register.
    A gradient that no threshold can monetise is a label.
"""
import bisect as bs
import math
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
GRID = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70)
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


def atr_series(c15, n=14):
    tr = [0.0] * len(c15)
    for i in range(len(c15)):
        h, l = float(c15[i]["high"]), float(c15[i]["low"])
        if i == 0:
            tr[i] = h - l
        else:
            pc = float(c15[i - 1]["close"])
            tr[i] = max(h - l, abs(h - pc), abs(l - pc))
    out = [0.0] * len(c15)
    for i in range(len(c15)):
        lo = max(0, i - n + 1)
        out[i] = sum(tr[lo:i + 1]) / (i - lo + 1)
    return out


def corr(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx <= 0 or sy <= 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def bucket(v, edges, names):
    for e, nm in zip(edges, names):
        if v <= e:
            return nm
    return names[-1]


def line(lbl, sel, nb):
    if len(sel) < 15:
        return None
    rs = [float(x["r_multiple"]) for x in sel]
    net = net_r(sel)
    d = net - nb
    hit = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    flag = " *" if abs(d) > M_NULL else ""
    print("      %-26s %5d %+9.1fR %+8.1fR PF %5.2f WR %5.1f%%%s"
          % (lbl, len(sel), net, d, pf(rs), hit, flag))
    return d


def main():
    print("=" * 100)
    print("  P47  DECOMPOSING THE TIGHT-STOP CONCENTRATION   (M = %.1fR)" % M_NULL)
    print("=" * 100)
    best = {}
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
            c15 = a[2]
            atr = atr_series(c15)
            ts15 = [int(c["ts"]) for c in c15]
            pos = {v: k for k, v in enumerate(ts15)}
            sw = {}
            for s in a[3]:
                sn = s.get("swing_no")
                if sn is None:
                    sn = s.get("swing_index")
                ct = s.get("confirmed_at_time") or ""
                if isinstance(ct, str) and len(ct) >= 19:
                    try:
                        sw[int(sn)] = s
                    except (TypeError, ValueError):
                        pass
            _miss = [t for t in tr if t.get("swing_no") not in sw]
            if _miss:
                print("      !! swing_no lookup MISSED %d/%d - leg position "
                      "buckets are all-default and meaningless"
                      % (len(_miss), len(tr)))
            for t in tr:
                ep = float(t["entry_price"])
                t["_r"] = abs(ep - float(t["sl"])) / ep * 100.0
                i = pos.get(int(t["entry_ts"]))
                t["_atr"] = atr[i] if i is not None and atr[i] > 0 else 0.0
                t["_rat"] = (abs(ep - float(t["sl"])) / t["_atr"]) \
                    if t["_atr"] > 0 else 0.0
                s = sw.get(t.get("swing_no"))
                if s:
                    seg = s.get("seg") or {}
                    sp = float(seg.get("start_px", 0) or 0)
                    epx = float(seg.get("end_px", 0) or 0)
                    lo = min(sp, epx)
                    hi = max(sp, epx)
                    t["_pos"] = ((ep - lo) / (hi - lo)) if hi > lo else 0.5
                else:
                    t["_pos"] = 0.5
            print("    [%s] control %dt %+.1fR (PIN ok)" % (scope.upper(),
                                                            n0, nb))
            ok = [t for t in tr if t["_atr"] > 0 and t["_pos"] is not None]
            print("      H1  is stop width just volatility?")
            print("      %-26s %5s %8s" % ("corr(stop%%, ATR) =", "",
                                         "%.4f" % corr([t["_r"] for t in ok],
                                                        [t["_atr"] / float(
                                                            t["entry_price"]) * 100
                                                            for t in ok])))
            print("      %-26s %5s %8s" % ("corr(stop%%, ATRnorm) =", "",
                                         "%.4f" % corr([t["_r"] for t in ok],
                                                        [t["_rat"] for t in ok])))
            print("      RAW stop%% buckets (P45's split, made explicit)")
            ed = [0.6, 1.0, 1.5, 2.0, 3.0, 99.0]
            nm = ["<=0.6", "<=1.0", "<=1.5", "<=2.0", "<=3.0", ">3.0"]
            for e, n2 in zip(ed, nm):
                line("stop%% " + n2,
                     [t for t in tr if bucket(t["_r"], ed, nm) == n2], nb)
            print("      H2  ATR-NORMALISED stop, 0.1-0.4x ATR")
            ed2 = [0.6, 0.9, 1.2, 1.5, 2.0, 99.0]
            nm2 = ["<=0.6", "<=0.9", "<=1.2", "<=1.5", "<=2.0", ">2.0"]
            for n2 in nm2:
                line("stop/ATR " + n2,
                     [t for t in tr if bucket(t["_rat"], ed2, nm2) == n2], nb)
            print("      H3  POSITION WITHIN THE LEG (scale-free)")
            ed3 = [0.20, 0.40, 0.60, 0.80, 99.0]
            nm3 = ["<=0.2", "<=0.4", "<=0.6", "<=0.8", ">0.8"]
            for n2 in nm3:
                line("legpos " + n2,
                     [t for t in tr if bucket(t["_pos"], ed3, nm3) == n2], nb)
            print("      THRESHOLD SWEEP on stop/ATR - does ANY cut clear M?")
            wins = 0
            for g in GRID:
                d = line("keep stop/ATR <= %.2f" % g,
                         [t for t in tr if t["_rat"] <= g], nb)
                if d is not None and abs(d) > M_NULL:
                    wins += 1
            print("      thresholds clearing M on this cell: %d/%d"
                  % (wins, len(GRID)))
            k = (key, scope)
            best[k] = max([abs(line("", [t for t in tr if t["_rat"] <= g], nb)
                          or 0) for g in GRID])
            print()
    print("  * = |dNet| exceeds M = %.1fR" % M_NULL)
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()