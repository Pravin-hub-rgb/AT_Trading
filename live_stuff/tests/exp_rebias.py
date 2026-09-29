"""P13 - RE-BIAS ON OPPOSITE-SWING CONFIRMATION (what the user actually meant)

THE CORRECTION, stated first because I got it wrong
===================================================
P12 tested a blind flip: at the same entry bar, take the opposite side
because decay is high. The user did not mean that. They meant:

  "HTF says GO LONG. I watch the LTF and the buying swings' lows are
   breaking - the long is finished. I WAIT for the next SELLING SWING
   TO CONFIRM. When it does, I take a position in it. Then when the
   selling swings' highs start breaking, the trend is turning back and
   I trade with the original HTF direction again."

That is a STATE MACHINE, not a flip:

    ALIGNED  HTF bias and LTF structure agree. Trade as shipped.
    FLIPPED  HTF still says one way, but the opposing LTF leg has
             CONFIRMED and its own structure is still INTACT. Trade the
             opposing side.
    back to ALIGNED when the FLIPPED leg's own level breaks.

Why P12 could not have found this: P12 flipped at the SAME BAR on
magnitude alone with no confirmation (-216R at 12.6% WR). P13 flips only
AFTER an opposing leg confirms, and only while that leg's structure
holds - a different entry bar and a different reason.

ON THE "YOU CANNOT NEGATE r_multiple" WARNING
=============================================
The user is right that this was over-engineered clutter, and it cost
time. A `-r` screen is a reasonable approximation and would have returned
the same negative for P12: the book was right 26% of the time, so
inverting it loses whatever the exit structure. The mirrored-stop replay
is kept here only because it already exists and costs nothing. The
correction is recorded rather than argued.

MEASURED AT EACH CHAMPION ENTRY t
=================================
  window opens at W with direction d_htf
  scan W..t for CONFIRMED LTF legs in direction -d_htf
  if one exists and its own defending level is still INTACT at t,
      state = FLIPPED, correct action is the opposite side
  if its level is already broken, back to ALIGNED

Arms: R1 any opposing leg intact; R2 only if confirmed <12h / <36h ago;
R3 only if decay also high (both evidences agree); and a CONTROL that is
the same replay with no flip, so the arms have something to beat.

FALSIFIERS, PRE-REGISTERED HERE
==============================
  (a) negative dNet in either era
  (b) sign disagreement across eras
  (c) no arm clears its own null
Reported whichever lands.
"""
from __future__ import annotations

import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402,F401
from run_experiment import get_data, identity_gate, net_r  # noqa: E402,F401
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import (PARAMS, PINS, M_of, legs_by_dir,  # noqa: E402
                              decay_pair, replay, load)

N_SWINGS = 4


def _intact(L, t, lows, highs, ts, better):
    """Is this leg's own defending level still unbroken as of t?"""
    j = bs.bisect_right(ts, t) - 1
    a = bs.bisect_left(ts, L["cts"])
    b = min(j, bs.bisect_right(ts, t) - 1)
    if b < a or L["px"] <= 0:
        return True
    seg = (lows if better == "low" else highs)[a:b + 1]
    if not seg:
        return True
    broken = (min(seg) < L["px"]) if better == "low" else (max(seg) > L["px"])
    return not broken


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 98)
    print("  P13  RE-BIAS ON OPPOSITE-SWING CONFIRMATION (the real idea)")
    print("=" * 98)
    print("  Not a blind flip. Switch only AFTER an opposing LTF leg")
    print("  confirms, and only while its own structure holds.\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    res = {}
    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)
        eng = sim(c1h, sw10, c15, sw15, fine, **PARAMS)
        tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got = net_r(tr)
        ok = abs(len(tr) - want_n) <= 2 and abs(got - want_net) <= 1.0
        print(f"  [{scope}] PIN n={len(tr)} netNET={got:+.1f} "
              f"(want {want_n}/{want_net:+.1f}) -> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            print("  PIN FAILED - refusing.")
            return
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        per = c2 / len(tr)
        fts = [int(c["ts"]) for c in fine]
        fhi = [float(c["high"]) for c in fine]
        flo = [float(c["low"]) for c in fine]
        ups, dns = legs_by_dir(sw15)
        ivs = sorted((int(x[0]), int(x[1]), int(x[2]))
                     for x in eng["intervals"])
        rows = []
        for t in tr:
            ts = int(t["entry_ts"])
            par = next((x for x in ivs if x[0] <= ts <= x[1]), None)
            if par is None:
                continue
            wa, wb, d_htf = par
            opp = dns if d_htf > 0 else ups
            better = "high" if d_htf > 0 else "low"
            cand = [L for L in opp if wa < L["cts"] <= ts]
            d1 = 1 if t["dir"] == "long" else -1
            risk = abs(float(t["entry_price"]) - float(t["sl"]))
            if not cand:
                rows.append({"t": t, "d": d1, "flip": False, "age": None,
                             "du": None, "risk": risk})
                continue
            L = cand[-1]
            du = decay_pair(ups, dns, ts, flo, fhi, fts)
            duv = du[0] if isinstance(du, tuple) else du
            rows.append({"t": t, "d": d1,
                         "flip": _intact(L, ts, flo, fhi, fts, better),
                         "age": (ts - L["cts"]) / 3600.0,
                         "du": duv, "risk": risk})
        res[scope] = (rows, per, fts, fhi, flo, len(tr))
        nf = sum(1 for r in rows if r["flip"])
        print(f"    {len(rows)} entries; {nf} in a FLIPPED state "
              f"({100.0*nf/max(len(rows),1):.1f}%)\n")

    for scope in ("is", "oos"):
        rows, per, fts, fhi, flo, bn = res[scope]
        print("=" * 98)
        print(f"  [{scope}]  {bn} trades")
        print("=" * 98)
        ctrl = [v for v in (replay(r["t"], r["d"], fts, fhi, flo, r["risk"])
                            for r in rows) if v is not None]
        cn = sum(ctrl) - per * len(ctrl)
        print(f"    {'CONTROL replay (no flip)':<38} n={len(ctrl):<4} "
              f"net={cn:+8.1f}")
        for lbl, pred in (
                ("R1 flip if opposing leg intact",
                 lambda r: r["flip"]),
                ("R2a + opposing leg confirmed <12h ago",
                 lambda r: r["flip"] and r["age"] is not None and r["age"] < 12),
                ("R2b + opposing leg confirmed <36h ago",
                 lambda r: r["flip"] and r["age"] is not None and r["age"] < 36),
                ("R3a + decay also >= 0.50",
                 lambda r: r["flip"] and r["du"] is not None and r["du"] >= 0.5),
                ("R3b + decay also >= 0.75",
                 lambda r: r["flip"] and r["du"] is not None and r["du"] >= 0.75)):
            rs = [v for v in (replay(r["t"], (-r["d"] if pred(r) else r["d"]),
                                     fts, fhi, flo, r["risk"])
                              for r in rows) if v is not None]
            if not rs:
                continue
            n = len(rs)
            obs = sum(rs) - per * n
            M, _ = M_of(rs, per)
            wr = 100.0 * sum(1 for x in rs if x > 0) / n
            cl = "*** CLEARS ***" if (M == M and abs(obs) > M) else "inside null"
            print(f"    {lbl:<38} n={n:<4} net={obs:+8.1f} "
                  f"dNet={obs-cn:+8.1f} WR={wr:>5.1f}% M={M:>7.1f} {cl}")
        print()
    print("=" * 98)
    print("  dNet is against the CONTROL replay, not the champion - a")
    print("  re-bias is a different trade with a different exit structure.")
    print("=" * 98)


if __name__ == "__main__":
    main()
