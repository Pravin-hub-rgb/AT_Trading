"""P119 - is the cap-1 survivor effect concurrency, or just tail concentration?

P117 measured, on the leg book:

    IS   uncapped 499 / +239.1R   R/t 0.479
         cap-1    388 / +111.6R   R/t 0.288     -40%
    OOS  uncapped 280 /  +72.8R   R/t 0.260
         cap-1    219 /  -11.8R   R/t -0.054    sign flip

Capping concurrency to 1 deletes 111 IS / 61 OOS trades and the survivors are
markedly worse per trade. The naive reading is "the champion's edge is in the
overlaps", which would be a real strategy statement.

But that shape is IDENTICAL to every tail-concentration result in this programme.
MASTER_CANDIDATES_V2 measured the top 5% of tail at 144.8% IS / 221.7% OOS. A cap
that deletes trades will always look like concentration if the book is already
concentrated.

PRE-REGISTERED, before the run:

  H1  EX-TOP-5%. Strip the top 5% of trades by r_multiple from BOTH arms.
      If survivors' ex-top-5% R/t is materially EQUAL between the two arms, the
      cap-1 degradation is tail concentration, not a concurrency effect, and the
      finding must say so.

  H2  HALF-YEAR PARTITION. Split each arm by entry timestamp into halves.
      A genuine concurrency effect should appear in BOTH halves. A concentration
      effect will be carried by whichever half holds the fat tail.

  H3  DIRECTION SPLIT. On the leg book, capping concurrency to 1 collapses the
      short side: +81.5R -> +5.9R OOS, against longs +26.9R -> +10.4R.

      HISTORY. This was labelled "R-multiple only, not independent evidence" on
      2026-10-01, on the grounds that P91 had shown R misleads on shorts. P121
      then RETRACTED P91's central claim as a sign-convention error - for a short,
      (exit-entry)/entry is the negative of PnL, so P91 read profitable shorts as
      losses. See FILL_ABSOLUTE_P91.md. There is no absolute-vs-R divergence on
      shorts, so the caveat rested on a false premise and has been removed.

      Standing caveat is the narrower true one: the absolute figure for the
      cap-1 short arm has still not been computed, so the collapse is established
      in R only. That is a gap in coverage, not a reason to doubt the result.

  FALSIFIER: if ex-top-5% arms converge AND the half-year split does not agree,
  the concurrency reading is dead and this is concentration.

Run: python -u exp_p119_cap1_tail.py     (about 3 min)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest", "backtest/tests", "backtest/sweeps", "backtest/engine", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import EXPERIMENTS, BP
from run_experiment import net_r, get_data
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen, load_fine_1m

BOOK = "champion_multi_sw10_leg"
PIN_OOS = (280, 72.8)
PIN_IS = (499, 239.1)


def _oos_args():
    c15o, f15o = load_unseen("15m")
    c1ho, f1ho = load_unseen("1h")
    return (c1ho, tc._compute_swings(f1ho, "continuous", min_bars=10),
            c15o, tc._compute_swings(f15o, "continuous", min_bars=50),
            load_fine_1m(c15o[0]["ts"], c15o[-1]["ts"]))


def r_per_trade(tr):
    r = [float(t["r_multiple"]) for t in tr]
    return sum(r) / len(r) if r else 0.0


def ex_top(tr, frac=0.05):
    """Strip the top `frac` by r_multiple. Returns (kept, n_stripped, R_stripped)."""
    s = sorted(tr, key=lambda t: float(t["r_multiple"]), reverse=True)
    k = max(1, int(len(s) * frac))
    return s[k:], k, sum(float(t["r_multiple"]) for t in s[:k])


def halves(tr):
    s = sorted(tr, key=lambda t: int(t["entry_ts"]))
    m = len(s) // 2
    return s[:m], s[m:]


def main():
    d = get_data()
    is_args = (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])
    oos_args = _oos_args()
    params = {**BP, **EXPERIMENTS[BOOK]["params"]}
    sim = tc.build_module()

    print("=" * 94)
    print("  P119  IS THE cap-1 SURVIVOR EFFECT CONCURRENCY, OR TAIL CONCENTRATION?")
    print("=" * 94)
    print("  pre-registered: if ex-top-5% arms converge and the half-year split")
    print("  disagrees, the concurrency reading is DEAD.\n")

    arms = {}
    for scope in ("is", "oos"):
        args = is_args if scope == "is" else oos_args
        for cap in (0, 1):
            p = dict(params)
            if cap:
                p["exp_max_concurrent"] = cap
            arms[(scope, cap)] = [
                t for t in sim(*args, **p)["ltf_trades"]
                if t.get("outcome") != "open"]
        print("-" * 94)
        print("  [%s]  uncapped %d / %+.1fR      cap-1 %d / %+.1fR"
              % (scope.upper(), len(arms[(scope, 0)]), net_r(arms[(scope, 0)]),
                 len(arms[(scope, 1)]), net_r(arms[(scope, 1)])))
    print()

    go, gi = arms[("oos", 0)], arms[("is", 0)]
    ok = (abs(len(go) - PIN_OOS[0]) <= 2 and abs(net_r(go) - PIN_OOS[1]) <= 3.0
          and abs(len(gi) - PIN_IS[0]) <= 2 and abs(net_r(gi) - PIN_IS[1]) <= 3.0)
    print("  PIN GATE: IS %d/%+.1f  OOS %d/%+.1f  %s"
          % (len(gi), net_r(gi), len(go), net_r(go),
             "PASS" if ok else "*** ABORT - not the shipping book ***"))
    if not ok:
        print("\n  GATE FAILED. Stopping before any interpretation.\n")
        return

    print("\n" + "=" * 94)
    print("  H1  EX-TOP-5%  --  does the gap survive removing the fat tail?")
    print("=" * 94)
    print("  %-4s %-10s %6s %9s %10s %11s %12s"
          % ("scope", "arm", "n", "R/t", "ex-top n", "ex-top R/t", "tail R"))
    ex = {}
    for scope in ("is", "oos"):
        for cap, tag in ((0, "uncapped"), (1, "cap-1")):
            kept, k, tail = ex_top(arms[(scope, cap)])
            ex[(scope, cap)] = (r_per_trade(kept), tail, r_per_trade(arms[(scope, cap)]))
            print("  %-4s %-10s %6d %9.3f %10d %11.3f %12.1f"
                  % (scope.upper(), tag, len(arms[(scope, cap)]),
                     r_per_trade(arms[(scope, cap)]), len(kept),
                     r_per_trade(kept), tail))
        dfull = ex[(scope, 0)][2] - ex[(scope, 1)][2]
        dex = ex[(scope, 0)][0] - ex[(scope, 1)][0]
        conv = abs(dex) < 0.5 * abs(dfull) and dfull != 0
        print("       gap full-book %+.3f    gap ex-top5%% %+.3f    %s"
              % (dfull, dex, "CONVERGES -> concentration" if conv
                 else "gap PERSISTS -> not explained by tail"))
    print()

    print("=" * 94)
    print("  H2  HALF-YEAR PARTITION  --  does the gap appear in BOTH halves?")
    print("=" * 94)
    agree = True
    for scope in ("is", "oos"):
        print("  [%s]" % scope.upper())
        for cap, tag in ((0, "uncapped"), (1, "cap-1")):
            a, b = halves(arms[(scope, cap)])
            print("    %-10s  H1 %4d trades R/t %+.3f     H2 %4d trades R/t %+.3f"
                  % (tag, len(a), r_per_trade(a), len(b), r_per_trade(b)))
        ua, ub = halves(arms[(scope, 0)])
        ca, cb = halves(arms[(scope, 1)])
        g1 = r_per_trade(ua) - r_per_trade(ca)
        g2 = r_per_trade(ub) - r_per_trade(cb)
        print("    gap H1 %+.3f    gap H2 %+.3f    %s"
              % (g1, g2, "AGREE" if (g1 > 0) == (g2 > 0) else "*** DISAGREE ***"))
        if (g1 > 0) != (g2 > 0):
            agree = False
    print()

    print("=" * 94)
    print("  H3  DIRECTION SPLIT  --  P91's lesson applied to the cap-1 arm")
    print("=" * 94)
    for scope in ("is", "oos"):
        for cap, tag in ((0, "uncapped"), (1, "cap-1")):
            tr = arms[(scope, cap)]
            lo = [t for t in tr if str(t.get("dir", "")).lower().startswith("l")]
            sh = [t for t in tr if str(t.get("dir", "")).lower().startswith("s")]
            print("  %-4s %-10s  long %4d %+8.1fR    short %4d %+8.1fR"
                  % (scope.upper(), tag, len(lo),
                     sum(float(t["r_multiple"]) for t in lo), len(sh),
                     sum(float(t["r_multiple"]) for t in sh)))
    print()

    print("=" * 94)
    print("  VERDICT")
    print("=" * 94)
    print("  half-year halves agree: %s" % ("YES" if agree else "NO - inconsistent"))
    print("\n  r_multiple is dimensionless. P91's divergence was absolute PnL vs R")
    print("  on the SHORT side, so that is where an absolute check would live.")


if __name__ == "__main__":
    main()