"""P18 - SYMMETRIC DECAY. Was the up-only version half the signal?

THE USER'S QUESTION
===================
"woh cheez joh hai nah swing lows breaks for buying swing and highs for
selling bhi karre ho right"

**They are right that both are computed and right that only one was used.**
`decay_pair()` in exp_decay_switch.py:165 returns
`(broken_up_frac, broken_dn_frac)` - buying legs defended by their lows,
selling legs defended by their highs. P11 and P15 reported ONLY the
first component. The second was computed and then discarded, and M1
(asymmetry = up − dn) was the one arm that came out with a big IS number
and the wrong OOS sign.

So three different decay definitions exist and only one has been properly
scored under P16's bar:

  UP-ONLY   broken buying lows.            <- what P11/P15 used
  SYMMETRIC broken buying lows AND selling highs, summed. "How much of
             the recent structure, in either direction, has failed."
             This is direction-AGNOSTIC and is arguably the more honest
             reading of "the trend is changing": a trend can die from
             either side, and a rally that loses every selling leg's high
             is just as much a structural failure as a selloff that loses
             every buying leg's low.
  ASYMMETRIC up - down.                   <- P12's M1, the only lead

WHY THIS MATTERS FOR THE USER'S ACTUAL GOAL
===========================================
The user wants a SMOOTH book. P16 found exactly 3 arms survive, and none
of them is a decay arm - `decay<0.75` was killed by the 2025 year floor
in P15. If a symmetric or asymmetric decay clears the same bar, it is
directly comparable to the P16 recommendation and the choice can be made
on one consistent criterion rather than across two experiments scored
under two different bars.

P16'S BAR, unchanged, so the comparison is honest
================================================
  IS net >= 300R   R/trade >= 1.00   trades <= 420   OOS net > +70.1R
  every IS year >= the champion's SAME year          <- the 2025 fix
  rank: worst_year, then max losing streak, then r_std

FALSIFIERS, PRE-REGISTERED
==========================
  (a) an arm better than the P16 recommendation on the bar but carrying
      an hour-of-day term - reported, not recommended, since hour filters
      have already been shown to be how a grid manufactures results
  (b) no arm clears the year floor, in which case all three decay
      definitions are closed together and the P16 recommendation stands
      unchallenged
  (c) symmetric beats up-only in BOTH eras - then P15's rejection of
      decay<0.75 was an artefact of using half the signal, and the year
      regression needs re-examining
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from test_experiments_craze import build_module  # noqa: E402
from exp_decay_switch import PARAMS, PINS, decay_pair, load  # noqa: E402
from exp_newbar_search import build, sim_holder  # noqa: E402
from exp_smooth_search import (streak, rstd, dd, pf, evaluate, passes,  # noqa: E402
                               MIN_NET, MIN_RPT, MAX_N)
from run_experiment import net_r  # noqa: E402


def label(args, sc):
    """Attach up / down decay to every trade, computed on the 1m series."""
    import bisect as bs
    c1h, sw10, c15, sw15, fine = args
    eng = sim_holder[0](c1h, sw10, c15, sw15, fine, **PARAMS)
    tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
    fts = [int(c["ts"]) for c in fine]
    fhi = [float(c["high"]) for c in fine]
    flo = [float(c["low"]) for c in fine]
    from exp_decay_switch import legs_by_dir
    ups, dns = legs_by_dir(sw15)
    rows = []
    for t in tr:
        ts = int(t["entry_ts"])
        du, dd = decay_pair(ups, dns, ts, flo, fhi, fts)
        up = du if isinstance(du, tuple) else du
        dn = dd if isinstance(du, tuple) else 0.0
        up = 0.5 if up is None else up
        dn = 0.0 if dn is None else dn
        rows.append({"r": float(t["r_multiple"]),
                     "y": (t.get("exit_date") or "")[:4],
                     "up": up, "sym": up + dn, "asym": up - dn})
    return rows


def main():
    print("=" * 100)
    print("  P18  SYMMETRIC DECAY - was the up-only version half the signal?")
    print("=" * 100)
    print("  UP-ONLY    broken buying lows            (what P11/P15 used)")
    print("  SYMMETRIC  broken buying lows + selling highs")
    print("  ASYMMETRIC up - down                     (P12's M1, the lead)")
    print("  Scored on P16's unchanged bar so the comparison is honest.\n")
    sim_holder[0] = build_module()
    D = {}
    for sc in ("is", "oos"):
        args = load(sc)
        tr = sim_holder[0](*args, **PARAMS)["ltf_trades"]
        tr = [t for t in tr if t.get("outcome") != "open"]
        want_n, want_net = PINS[sc]
        got = net_r(tr)
        if abs(len(tr) - want_n) > 2 or abs(got - want_net) > 1.0:
            print(f"  PIN FAILED {sc}: {len(tr)}/{got:+.1f}")
            return
        rows = label(args, sc)
        from src.btc.btc_routes import _trade_costs
        from engine.v18_params import SYMBOL_PARAMS
        g = SYMBOL_PARAMS["BTCUSDT"]
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"],
                             g["exit_slip_pct"])
        per = c2 / len(tr)
        D[sc] = (rows, per, len(tr), got)
        print(f"  [{sc}] PIN ok  n={len(tr)}  netNET={got:+.1f}R  "
              f"({len(rows)} labelled)")

    champ = evaluate(D["is"][0], D["is"][1], lambda r: True)
    cy = champ["years"]
    print(f"\n  CHAMPION  R/tr={champ['rpt']:+.3f} PF={champ['pf']:.2f} "
          f"DD={champ['dd']:.1f} std={champ['std']:.2f} "
          f"streak={champ['streak']} worstY={champ['worst']:+.1f}")
    print("  by year " + "  ".join(f"{y}:{v:+.1f}"
                                   for y, v in sorted(cy.items())))

    print("\n" + "=" * 100)
    print(f"  {'arm':<22} {'n':>4} {'net':>8} {'R/tr':>6} {'PF':>5} "
          f"{'DD':>6} {'std':>5} {'strk':>4} {'worstY':>7} | "
          f"{'OOS n':>5} {'OOS net':>8}  bar")
    print("=" * 100)
    arms = []
    for t in (0.25, 0.5, 0.75, 1.01):
        arms.append((f"up < {t}", "up", t))
    for t in (0.5, 0.75, 1.0, 1.25, 1.5):
        arms.append((f"sym < {t}", "sym", t))
    for t in (-0.5, -0.25, 0.0, 0.25):
        arms.append((f"asym < {t}", "asym", t))
    hits = []
    for lbl, feat, t in arms:
        rule = lambda r, f=feat, tt=t: r[f] < tt
        a = evaluate(D["is"][0], D["is"][1], rule)
        o = evaluate(D["oos"][0], D["oos"][1], rule)
        ok = passes(a, o, cy)
        if ok:
            hits.append((lbl, a, o))
        if a and o:
            print(f"    {lbl:<22} {a['n']:>4} {a['net']:>8.1f} "
                  f"{a['rpt']:>6.3f} {a['pf']:>5.2f} {a['dd']:>6.1f} "
                  f"{a['std']:>5.2f} {a['streak']:>4} {a['worst']:>+7.1f} | "
                  f"{o['n']:>5} {o['net']:>8.1f}  {'BAR-OK' if ok else '-'}")
    print(f"\n  {len(hits)} of {len(arms)} decay arms clear P16's bar.")
    if not hits:
        print("  -> falsifier (b): all three decay definitions are closed")
        print("     together and the P16 recommendation stands unchallenged.")
    else:
        hits.sort(key=lambda z: (-z[1]["worst"], z[1]["streak"], z[1]["std"]))
        print("  CLEARING, ranked by smoothness:")
        for lbl, a, o in hits:
            print(f"    {lbl:<22} n={a['n']} net={a['net']:+.1f}R "
                  f"R/tr={a['rpt']:+.3f} PF={a['pf']:.2f} std={a['std']:.2f} "
                  f"streak={a['streak']} worstY={a['worst']:+.1f} "
                  f"OOS={o['net']:+.1f}R")
    print("=" * 100)


if __name__ == "__main__":
    main()
