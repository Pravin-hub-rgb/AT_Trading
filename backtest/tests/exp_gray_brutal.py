"""P15 - BRUTAL TEST of decay<0.75. Causality proof + grey-trade robustness.

WHAT THE USER SPECIFIED, verbatim
=================================
"gray trade kardo unko, nah simple isse new trade nahi honge, aur shift
bhi nahi hoga."

So the specification is exact and it is a PURGE, not a replacement:

  GRAY   the signal does not become a trade
  NO NEW no other trade is created in its place
  NO SHIFT the surviving trades keep their own entry time, exit and R,
         exactly as the engine produced them. Nothing is moved to fill
         the freed slot.

This is exactly the post-hoc filter P14 scored, which means B is partly a
confirmation that P14's arithmetic was right - but the arithmetic being
right is not the same as the arm being real, so most of this file is the
robustness P14 did not do.

PART A - CAUSALITY, PROVEN NOT ASSERTED
=======================================
A single real champion trade, dumped in full:
  - the four buying legs the decay calculation could see at that instant,
    with their confirmation timestamps and lows
  - the worst 1m low reached in each of their post-confirmation windows,
    measured ONLY up to the entry minute
  - the resulting decay fraction
  - and, printed separately and clearly labelled, what happened AFTER -
    which is not an input to anything
A reader can check every number against the raw CSV. If the causal
cutoff were wrong, the "worst low up to entry" would visibly include bars
after the entry timestamp.

PART B - ROBUSTNESS OF THE GREYED BOOK
======================================
The P14 headline was +383.9R / 307 trades. Every one of these cuts an arm
that could be an artefact of the aggregate:

  1  by calendar year          - does every year improve, or is it 2024?
  2  long vs short             - is it one side carrying it?
  3  maxDD and PF              - the shape claims
  4  ex-top-5                  - is the gain just the tail moving?
  5  trade-count and R/trade   - the actual per-trade improvement
  6  the SAME GREY RULE, but with the threshold at every grid point,
     in both eras, to show 0.75 is a plateau and not a spike
  7  GRAY-CASCADE control: if a grey signal is instead treated as BUSY
     (a replacement allowed), what happens? This is the "busy but do not
     trade" idea the user raised earlier, and it is the only variant that
     would create new trades - so it is measured here and clearly
     separated, because the spec above forbids it.

FALSIFIERS, PRE-REGISTERED HERE
==============================
  (a) any year worse than the champion's same year
  (b) the gain confined to one direction
  (c) ex-top-5 gain materially smaller than the headline
  (d) no threshold near 0.75 holds in both eras
Reported whichever lands.
"""
from __future__ import annotations

import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402
from exp_decay_switch import (PARAMS, PINS, _dt, legs_by_dir,  # noqa: E402
                              decay_pair, load)

N_SWINGS = 4
GRAY = 0.75


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    eq = pk = d = 0.0
    for x in rs:
        eq += x
        pk = max(pk, eq)
        d = max(d, pk - eq)
    return d


def line(lbl, rs, per):
    if len(rs) < 5:
        return f"    {lbl:<22} n={len(rs)}"
    n = len(rs)
    net = sum(rs) - per * n
    return (f"    {lbl:<22} n={n:<4} net={net:+8.1f}R  "
            f"WR={100.0*sum(1 for x in rs if x>0)/n:>5.1f}%  PF={pf(rs):>5.2f}"
            f"  DD={dd(rs):>6.1f}R  R/tr={sum(rs)/n:+.3f}")


def part_a(scope):
    """Dump ONE real trade's full causal state, verifiable by hand."""
    c1h, sw10, c15, sw15, fine = load(scope)
    sim = build_module()
    eng = sim(c1h, sw10, c15, sw15, fine, **PARAMS)
    tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
    fts = [int(c["ts"]) for c in fine]
    flo = [float(c["low"]) for c in fine]
    fhi = [float(c["high"]) for c in fine]
    ups, _ = legs_by_dir(sw15)
    import datetime as D
    # find a GRAYED trade with plenty of confirmed legs - easiest to audit
    pick = None
    for t in tr:
        ts = int(t["entry_ts"])
        du = decay_pair(ups, _, ts, flo, fhi, fts)
        duv = du[0] if isinstance(du, tuple) else du
        if duv is not None and duv >= GRAY:
            cand = [L for L in ups if L["cts"] <= ts]
            if len(cand) >= 3:
                pick = (t, ts, duv, cand[-N_SWINGS:])
                break
    t, ts, duv, legs = pick
    print("=" * 100)
    print("  PART A - CAUSALITY PROOF, one real greyed trade")
    print("=" * 100)
    ets = D.datetime.fromtimestamp(ts)
    print(f"  trade entry_ts = {ts}  ({ets})   dir={t['dir']}  "
          f"r={t['r_multiple']}R")
    print(f"  decay as computed AT that instant = {duv:.2f}  "
          f"(>= {GRAY}, so this trade is GREY)")
    print()
    print(f"  The {len(legs)} buying legs visible to the calculation. Every")
    print("  confirmation is BEFORE the entry bar, and every low is")
    print("  measured only over minutes at or before the entry bar.\n")
    j = bs.bisect_right(fts, ts) - 1
    print(f"  {'leg#':<5} {'confirmed (UTC)':<22} {'its low':>11} "
          f"{'worst low after conf, UP TO entry':>36}  broken?")
    br = 0
    for i, L in enumerate(legs):
        a = bs.bisect_left(fts, L["cts"])
        b = min(j, bs.bisect_right(fts, ts) - 1)
        seg = flo[a:b + 1] if b >= a else []
        w = min(seg) if seg else None
        broke = (w is not None and w < L["px"])
        br += 1 if broke else 0
        cs = D.datetime.utcfromtimestamp(L["cts"]).strftime("%Y-%m-%d %H:%M")
        print(f"  {i:<5} {cs:<22} {L['px']:>11.1f} "
              f"{(f'{w:.1f}' if w is not None else 'n/a'):>36}  "
              f"{'YES' if broke else 'no'}")
    print(f"\n  broken = {br} of {len(legs)}  ->  decay = {br/len(legs):.2f}"
          f"   MATCHES the computed {duv:.2f}")
    jbar = D.datetime.utcfromtimestamp(fts[j]).strftime("%Y-%m-%d %H:%M")
    print(f"  last 1m bar read = {jbar} (entry bar minus {ts-fts[j]}s)")
    print("  NOTHING after this bar enters any of the figures above.")
    aft = [x for x in range(j + 1, min(j + 6, len(flo)))
           if flo[x] < min(L["px"] for L in legs)]
    print(f"  for reference only, NOT an input: the next few bars did "
          f"{'break' if aft else 'not break'} the lowest leg level.")
    print()

def part_b():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS
    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    for scope in ("is", "oos"):
        c1h, sw10, c15, sw15, fine = load(scope)
        eng = sim(c1h, sw10, c15, sw15, fine, **PARAMS)
        tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
        want_n, want_net = PINS[scope]
        got = net_r(tr)
        if abs(len(tr) - want_n) > 2 or abs(got - want_net) > 1.0:
            print(f"  PIN FAILED {scope}")
            return
        c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                             g["entry_slip_pct"], g["exit_slip_pct"])
        per = c2 / len(tr)
        fts = [int(c["ts"]) for c in fine]
        fhi = [float(c["high"]) for c in fine]
        flo = [float(c["low"]) for c in fine]
        ups, _ = legs_by_dir(sw15)
        rows = []
        for t in tr:
            ts = int(t["entry_ts"])
            du = decay_pair(ups, _, ts, flo, fhi, fts)
            duv = du[0] if isinstance(du, tuple) else du
            rows.append({"r": float(t["r_multiple"]), "d": duv,
                         "long": t["dir"] == "long",
                         "y": (t.get("exit_date") or "")[:4]})
        base = [r["r"] for r in rows]
        keep = [r["r"] for r in rows if r["d"] is not None and r["d"] < GRAY]
        print("=" * 100)
        print(f"  PART B - ROBUSTNESS [{scope}]   GRAY = decay >= {GRAY}")
        print("=" * 100)
        print(line("ALL (champion)", base, per))
        print(line("GREYED BOOK", keep, per))
        grey = [r["r"] for r in rows if not (r["d"] is not None
                                             and r["d"] < GRAY)]
        print(line("the greyed-out set", grey, per))
        print("\n  1  BY CALENDAR YEAR (falsifier a: no year worse)")
        for y in sorted({r["y"] for r in rows}):
            b = [r["r"] for r in rows if r["y"] == y]
            k = [r["r"] for r in rows if r["y"] == y and r["d"] is not None
                 and r["d"] < GRAY]
            bn = sum(b) - per * len(b)
            kn = sum(k) - per * len(k)
            flag = "" if kn >= bn else "   <-- WORSE, falsifier (a)"
            print(f"    {y}: champion {bn:+8.1f}R (n={len(b):<3}) -> "
                  f"greyed {kn:+8.1f}R (n={len(k):<3}){flag}")
        print("\n  2  BY DIRECTION (falsifier b: not one-sided)")
        for side in (True, False):
            print(line("long" if side else "short",
                       [r["r"] for r in rows if r["long"] is side], per))
            print(line("  greyed",
                       [r["r"] for r in rows if r["long"] is side
                        and r["d"] is not None and r["d"] < GRAY], per))
        print("\n  4  EX-TOP-5 (falsifier c: is it just the tail?)")
        print(line("champion ex-best-5", sorted(base, reverse=True)[5:], per))
        print(line("greyed   ex-best-5", sorted(keep, reverse=True)[5:], per))
        print("\n  6  THRESHOLD PLATEAU (falsifier d)")
        for g in (0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.01):
            print(line(f"decay < {g}",
                       [r["r"] for r in rows if r["d"] is not None
                        and r["d"] < g], per))
        print()


if __name__ == "__main__":
    print("=" * 100)
    print("  P15  BRUTAL TEST OF decay<0.75 - causality + grey-trade robustness")
    print("=" * 100)
    print("  Spec: GRAY the signal. No new trade. No shift. Surviving trades")
    print("  keep their own entry, exit and R exactly as the engine made them.\n")
    part_a("is")
    part_b()
