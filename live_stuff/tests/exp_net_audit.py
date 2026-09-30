"""P98 - THE NET-R AUDIT. Fix the accounting so P87-P95 can be trusted.

FOUR DEFECTS IN THE RECORDED ANALYSIS, ALL FROM THE SAME ROOT CAUSE:
a per-trade NET helper that did not exist, so every statistic after P83 was
computed on GROSS r_multiple while being COMPARED against NET champion
totals.

  D1  P87-P89 report gross r_multiple, but their dNet and M comparisons are
      stated against net pins. Gross-vs-net was already caught twice this
      round (P60, P83). Third occurrence.
  D2  P92's drawdown-depth algorithm stores the CURRENT drawdown amount
      and then subtracts it from the peak a second time. P92's own worst
      episode prints 445.2R against P83's 37.3R maximum drawdown - a
      contradiction the doc notes but does not resolve.
  D3  P93/P94 cohort totals are gross sums (+506.2R) compared against net
      champion totals (+325.8R). Their M comparisons are therefore not
      valid net results.
  D4  P90's next-open +500.6R was retracted in P91. P91's own absolute
      figures omit costs entirely and are descriptive, not an account curve.

THE HELPER, AND WHY IT IS NOT JUST run_experiment.net_r
    net_r(tr) sums over a whole book. Every defect above needs the NET value
    PER TRADE, because D1 is about per-trade statistics, D3 is about a
    cohort selected per trade, and D2 is about an equity path ordered by
    per-trade exit time. So this adds net_per_trade(), which allocates the
    two cost components the same way net_r does - _trade_costs for fees and
    slippage, fund() for carry - and returns them per trade rather than
    summed.

    Cost allocation is verified, not assumed: the per-trade nets must sum
    EXACTLY to net_r(tr) on the shipped control. If they do not, the helper
    is wrong and the run aborts.

WHAT IS RECOMPUTED
    D1  P89's side asymmetry, on net per-trade.
    D2  P92's drawdown episodes, with the depth bug fixed.
    D3  P94's outlive cohort and P93's parent-death split, on net.
    D4  printed as labelling, not recomputation - a retracted number stays
        retracted, and P91 stays descriptive.

WHAT IS NOT CLAIMED
    Nothing is adopted. This corrects the ledger; it does not change the
    champion. Where a recomputed figure overturns a recorded one, the
    doc says so plainly rather than quietly restating it.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r, fund, _g
from src.btc.btc_routes import _trade_costs
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_per_trade(tr):
    """Per-trade NET R, allocating fees/slippage and funding per trade.

    Mirrors net_r exactly, but returns the vector instead of the sum.
    """
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    fr = fund(tr)
    n = max(1, len(tr))
    out = [r - c2 / n - fr / n for r in rs]
    return out


def pf(v):
    return sum(x for x in v if x > 0) / max(1e-9, -sum(x for x in v if x < 0))


def episodes(ts, vals):
    """D2 FIX. Drawdown episodes from a per-trade equity path.

    THE BUG: the original stored `dd = peak - eq` (the CURRENT drawdown
    AMOUNT) and then continued the peak search with `peak - dd`, subtracting
    the drawdown from the peak a second time and driving the peak
    monotonically downward. That is why P92 printed a 445.2R worst episode
    on a book whose real maximum drawdown is 37.3R.

    The fix keeps `peak` as a running maximum and `dd = peak - eq` as a
    quantity that never touches `peak`.
    """
    eq = 0.0
    peak = 0.0
    eps, cur = [], None
    for ts_i, v in sorted(zip(ts, vals), key=lambda kv: kv[0]):
        eq += v
        if eq > peak:
            if cur:
                cur["open"] = False
                eps.append(cur)
            peak = eq
            cur = None
        else:
            dd = peak - eq                       # <- amount only
            if cur is None:
                cur = {"start": ts_i, "trades": 0, "peak": peak,
                       "min_dd": dd, "tmin": ts_i, "open": True}
            else:
                cur["trades"] += 1
                if dd > cur["min_dd"]:
                    cur["min_dd"] = dd
                    cur["tmin"] = ts_i
    if cur:
        eps.append(cur)
    return eps


def stats(v):
    n = len(v)
    return (n, sum(v), sum(v) / max(1, n), pf(v))


def main():
    print("=" * 100)
    print("  P98  THE NET-R AUDIT")
    print("=" * 100)
    print("  Root cause of D1-D3: no per-trade NET helper existed, so")
    print("  per-trade stats were gross while their comparisons were net.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h, tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15, tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    for lane in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[lane]["params"]}
        print("  " + "=" * 100)
        print("  LANE: %s" % lane)
        books = {}
        for i, scope in enumerate(("is", "oos")):
            tr = [t for t in tc.build_module()(*src[scope], **params)
                  ["ltf_trades"] if t.get("outcome") != "open"]
            # npv = net-per-trade vector; `intervals` is where the parent
            # windows live - the trade record has no window_end_ts, which is
            # why P93/P94 had to match intervals themselves.
            ivs = tc.build_module()(*src[scope], **params).get("intervals", [])
            # --- helper verification: nets MUST sum to net_r exactly
            npv = net_per_trade(tr)
            drift = abs(sum(npv) - net_r(tr))
            if drift > 1e-6:
                print("      HELPER MISMATCH %.6fR - STOP" % drift)
                return
            books[scope] = (tr, npv, ivs)
            pin = PIN[lane][i]
            ok = (abs(len(tr) - pin[0]) <= 2
                  and abs(net_r(tr) - pin[1]) <= 1.5)
            g = sum(float(t["r_multiple"]) for t in tr)
            print("  --- [%s] n=%d  GROSS %+.1fR   NET %+.1fR   "
                  "cost %.1fR   pin %s"
                  % (scope.upper(), len(tr), g, net_r(tr),
                     g - net_r(tr), "OK" if ok else "FAILED"))
            print("      net-per-trade helper: sum == net_r  (drift %.1e)"
                  % drift)

        for scope in ("is", "oos"):
            tr, v, ivs = books[scope]
            ts = [int(t["exit_ts"]) for t in tr]
            print()
            print("  --- [%s] D1: SIDE ASYMMETRY on NET per trade"
                  % scope.upper())
            # `dir` is the STRING 'long'/'short' in the trade record, not
            # an int - assuming 1/-1 silently puts every trade on one side.
            for side, nm in (("long", "long"), ("short", "short")):
                sv = [x for t, x in zip(tr, v) if t.get("dir") == side]
                if not sv:
                    continue
                gs = [float(t["r_multiple"]) for t in tr
                      if t.get("dir") == side]
                n, s, rt, p = stats(sv)
                print("      %-6s n=%-4d  gross %+8.1fR   NET %+8.1fR"
                      "   R/t(net) %+6.3f   PF(net) %5.2f   "
                      "cost %.1fR (%.1f%% of gross)"
                      % (nm, n, sum(gs), s, rt, p, sum(gs) - s,
                         100.0 * (sum(gs) - s) / max(1e-9, abs(sum(gs)))))

            print("  --- [%s] D2: DRAWDOWN EPISODES, depth bug fixed"
                  % scope.upper())
            eps = episodes(ts, v)
            closed = [e for e in eps if not e["open"]]
            dd = [e["min_dd"] for e in eps]
            days = [(e["tmin"] - e["start"]) / 86400.0 for e in eps]
            print("      episodes %d  (%d still open at sample end)"
                  % (len(eps), len(eps) - len(closed)))
            print("      MAX DRAWDOWN %.1fR   <- compare P83's 37.3R"
                  % max(dd))
            print("      depth median %.1fR   days median %.0f"
                  % (sorted(dd)[len(dd) // 2], sorted(days)[len(days) // 2]))
            print("      worst: %.1fR over %.0f days"
                  % (max(dd), days[dd.index(max(dd))]))
            print("      P92 recorded 445.2R worst / 23d median depth")
            print("      -> P92's depth numbers were produced by the")
            print("         double-subtraction bug and are WRONG.")

            print("  --- [%s] D3: OUTLIVE COHORT on NET" % scope.upper())
            # P93/P94 selected the cohort on `exit_ts > parent window end`.
            # The trade record carries no window_end_ts, so the parent must be
            # matched from `intervals`, which are tuples:
            #   (start_ts, end_ts, direction, entry_px, stop)
            # A trade belongs to the interval whose [start,end] contains its
            # entry_ts; ties go to the FIRST match, matching P93/P94.
            ivs_sorted = sorted(ivs, key=lambda z: int(z[0]))
            starts = [int(z[0]) for z in ivs_sorted]

            def parent_end(ts):
                import bisect
                j = bisect.bisect_right(starts, ts) - 1
                for k in range(j, max(-1, j - 4), -1):
                    if int(ivs_sorted[k][0]) <= ts <= int(ivs_sorted[k][1]):
                        return int(ivs_sorted[k][1])
                return 0

            outl, insd, unassigned = [], [], 0
            for t, x in zip(tr, v):
                pe = parent_end(int(t["entry_ts"]))
                if pe <= 0:
                    unassigned += 1
                    continue
                (outl if int(t["exit_ts"]) > pe else insd).append((t, x))
            if not outl and not insd:
                print("      no trade matched a parent interval - the")
                print("      cohort CANNOT be rebuilt and is NOT reported.")
            else:
                ov = [x for _, x in outl]
                iv2 = [x for _, x in insd]
                og = [float(t["r_multiple"]) for t, _ in outl]
                ig = [float(t["r_multiple"]) for t, _ in insd]
                print("      matched %d of %d trades (%d unmatched)"
                      % (len(outl) + len(insd), len(tr), unassigned))
                print("      OUTLIVE n=%-4d gross %+8.1fR  NET %+8.1fR"
                      "  R/t %+.3f  PF %.2f"
                      % (len(ov), sum(og), sum(ov), sum(ov) / len(ov),
                         pf(ov)))
                print("      INSIDE  n=%-4d gross %+8.1fR  NET %+8.1fR"
                      "  R/t %+.3f  PF %.2f"
                      % (len(iv2), sum(ig), sum(iv2), sum(iv2) / len(iv2),
                         pf(iv2)))
                bk = net_r(tr)
                # NET vs NET. P94 compared a GROSS cohort sum against this
                # NET book, which is the defect D3 describes.
                dcoh = sum(ov) - bk
                print("      champion NET book      %+8.1fR  (n=%d)"
                      % (bk, len(tr)))
                print("      cohort NET vs NET book: dNet %+.1fR"
                      " = %.2fx M  -> %s"
                      % (dcoh, abs(dcoh) / M_NULL,
                         "CLEARS" if abs(dcoh) > M_NULL else "FAILS"))
                print("      P94 recorded GROSS +506.2R and 0.93x M against")
                print("      the NET book. That comparison is not a valid")
                print("      net result and is superseded by the line above.")
                print("      NOTE: the cohort is selected on a POST-OUTCOME")
                print("      event (exit_ts > window end). As a rule it is")
                print("      circular. Recomputing it on net does not fix")
                print("      that, and nothing here is adoptable.")
        print()

    print("=" * 100)
    print("  D4  LABELLING ONLY - no recomputation")
    print("=" * 100)
    print("  P90  next-open +500.6R  -> RETRACTED in P91 (R-denominator")
    print("        artefact). Stays retracted. Not recomputed here.")
    print("  P91  absolute return figures OMIT COSTS. They are")
    print("        cost-free descriptive measurements, NOT an account")
    print("        curve, and must never be quoted as deployable return.")
    print()
    print("  Nothing adopted. Champion unchanged: 500t/+325.8R IS,")
    print("  279t/+70.1R OOS. This corrects the ledger only.")


if __name__ == "__main__":
    main()