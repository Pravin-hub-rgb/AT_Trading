"""P51 - P3 AND W2, THE TWO REMAINING FREE ITEMS, IN ONE RUN.

P3 - SCORE THE 1h LAYER'S OWN P&L.  THE QUEUE'S "HIGHEST VALUE" ITEM.
    "Every run simulates the 1h book three times (entry_break in
    {flip, decisive, b2}, v18_streak_halt.py:222-224) and throws its P&L
    away, keeping only (entry_ts, exit_ts, dir, px, sl) as window bounds.
    Nobody has ever reported what the 1h book earns standalone.
    Either the 1h book carries the edge (three-timeframe architecture is
    decoration) or the 15m layer does."
    PRE-REGISTERED CLAIM, from the queue: the cascade beats the best 1h
    standalone book on R/trade by >= 2x, in BOTH eras - if not, the
    architecture is not earning its complexity.
    PRE-REGISTERED FALSIFIER: 1h standalone positive in both eras with
    PF > 1.3 means the LTF layer adds nothing and the programme is one
    timeframe too low.
    This is nearly free - the trades already exist inside every backtest -
    and it re-ranks the rest of the queue.
    P50 already showed a hint: the truncated windows' own HTF legs came to
    -4.0R while the LTF trades inside them were worth +88.2R.

W2 - WHY DID r_touch LOSE 130R?
    "Closing at +1.5R should have helped if 25% of windows reach 3R. It
    regressed instead. Worth understanding before any duration rule is
    trusted - if the mechanism is unknowable, W1's arms are unfalsifiable."
    PRE-REGISTERED FALSIFIER: reconstruct the leg's MFE in R. If the MFE
    distribution is bimodal - a mass below 1.5R and a spike at 3.0R - then
    1.5R sits in the gap and should have been free. If MFE is smooth, 1.5R
    truncates the runners that make the book and the -130R is correct
    rather than mysterious.
    Same data, same legs, one more pass over the fine bars.
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


def line(lbl, tr):
    if not tr:
        print("      %-30s  (empty)" % lbl)
        return None
    rs = [float(x.get("r_multiple", 0) or 0) for x in tr]
    n = len(rs)
    net = sum(rs)
    rpt = net / n
    print("      %-30s %5d %+9.1fR  R/trade %+6.3f  PF %5.2f  WR %5.1f%%"
          % (lbl, n, net, rpt, pf(rs),
             100.0 * sum(1 for x in rs if x > 0) / n))
    return rpt


def main():
    print("=" * 100)
    print("  P51  P3 - WHAT DOES THE 1h LAYER EARN ON ITS OWN?")
    print("        W2 - AND WHY DID r_touch AT 1.5R LOSE 130R?")
    print("=" * 100)
    print("  P3 pre-registered: cascade must beat best 1h standalone on")
    print("  R/trade by >=2x in BOTH eras. Falsifier: 1h standalone")
    print("  positive both eras with PF > 1.3 => the LTF layer adds nothing.")
    print("  W2 pre-registered: MFE bimodal => 1.5R was free and the -130R")
    print("  is a bug. MFE smooth => 1.5R truncates the runners and -130R is")
    print("  correct.\n")
    fts = flo = fhi = None
    for key, swtag, ispin, oospin in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        print("  --- %s" % key)
        for scope, pin in (("is", ispin), ("oos", oospin)):
            a = get(scope, swtag)
            r = tc.build_module()(*a, **params)
            ltf = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
            lnet, nltf = net_r(ltf), len(ltf)
            if abs(nltf - pin[0]) > 2 or abs(lnet - pin[1]) > 1.5:
                print("    [%s] CONTROL FAILED %dt %+.1fR -- STOP"
                      % (scope, nltf, lnet))
                return
            fts = [int(c["ts"]) for c in a[4]]
            flo = [float(c["low"]) for c in a[4]]
            fhi = [float(c["high"]) for c in a[4]]
            print("    [%s] cascade %dt %+.1fR  (PIN ok)"
                  % (scope.upper(), nltf, lnet))
            print("      P3  the 1h book, standalone - simulated three times "
                  "every run and never reported")
            best = None
            for mode in ("flip", "b2", "decisive"):
                key_ = "htf_trades_%s" % mode
                tr = r.get(key_) or []
                v = line("1h standalone, %s" % mode, tr)
                if v is not None and (best is None or v > best[1]):
                    best = (mode, v)
            v = line("CASCADE (15m layer)", ltf)
            if best:
                ratio = v / best[1] if best[1] > 0 else float("inf")
                ok = "PASSES" if best[1] > 0 and ratio >= 2.0 else "FAILS"
                print("      %-30s R/trade %+6.3f  vs best 1h (%s) %+6.3f"
                      "  -> cascade is %.2fx  [%s, needs >=2x in BOTH eras]"
                      % ("cascade vs best 1h", v, best[0], best[1], ratio, ok))
                rs = [float(x.get("r_multiple", 0) or 0)
                      for x in (r.get("htf_trades_%s" % best[0]) or [])]
                print("      %-30s PF %5.2f  -> falsifier needs PF > 1.3 "
                      "with positive net in BOTH eras"
                      % ("best 1h standalone (%s)" % best[0], pf(rs)))
            # ---- W2
            print("      W2  MFE of the 1h legs, and where 1.5R sits")
            legs = list(r.get("htf_trades_flip") or []) + \
                list(r.get("htf_trades_b2") or [])
            mfe = []
            for L in legs:
                ep = float(L.get("entry_price", 0) or 0)
                sl = float(L.get("sl", 0) or 0)
                risk = abs(ep - sl)
                if risk <= 0 or ep <= 0:
                    continue
                i = bs.bisect_left(fts, int(L["entry_ts"]))
                j = bs.bisect_right(fts, int(L["exit_ts"])) - 1
                if j <= i:
                    continue
                if ep > sl:
                    best_px = max(fhi[i:j + 1])
                else:
                    best_px = min(flo[i:j + 1])
                mfe.append((best_px - ep) / risk if ep > sl
                           else (ep - best_px) / risk)
            if mfe:
                edges = [0, .5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 99]
                names = ["<0.5", "<1.0", "<1.5", "<2.0", "<2.5", "<3.0",
                         ">=3.0", "stopped"]
                print("      %-30s %5d legs, MFE p50 %.2f  p90 %.2f  max "
                      "%.2f" % ("", len(mfe), sorted(mfe)[len(mfe) // 2],
                                sorted(mfe)[int(len(mfe) * .9)], max(mfe)))
                for e, nm in zip(edges, names):
                    c = sum(1 for v in mfe
                            if (e <= v < edges[edges.index(e) + 1]))
                    if nm == "stopped":
                        c = sum(1 for v in mfe if v < 0)
                    print("      %-30s %5d  %5.1f%%"
                          % ("MFE %s" % nm, c, 100.0 * c / len(mfe)))
                below = 100.0 * sum(1 for v in mfe if v < 1.5) / len(mfe)
                at3 = 100.0 * sum(1 for v in mfe if v >= 2.99) / len(mfe)
                mid = 100.0 * sum(1 for v in mfe
                                  if 1.5 <= v < 2.99) / len(mfe)
                print("      %-30s %5.1f%% below 1.5R, %5.1f%% in the "
                      "1.5-3.0 band, %5.1f%% reaching 3R"
                      % ("mass distribution", below, mid, at3))
            print()
    print("  Nothing adopted. This is attribution, not edge.")


if __name__ == "__main__":
    main()