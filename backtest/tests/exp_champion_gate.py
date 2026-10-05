"""P3-D - THE USER'S ACTUAL QUESTION: what does the gate do to the 325R book?

THE HONESTY PROBLEM THIS FILE EXISTS TO FIX
===========================================
P3-C was run at `mode="atr_high"`, which is NOT the shipped config. It
produced IS +227.5R / OOS +22.7R. The user's champion is IS +325.8R /
OOS +70.2R (AGENT_COORDINATION.md:244-246, method/EXPERIMENT_LOG.md:341). Those
are different books on different settings, so P3-C says NOTHING about what
the gate does to 325R. Answering that question from P3-C's numbers would
be exactly the "shape vs meaning" mistake this session keeps making.

So this runs the gate on the CHAMPION config, whatever that is, read from
`v18_params.py` and the coordination doc rather than from memory.

A DISCOVERY THAT CHANGES THE FRAMING
====================================
v18_streak_halt.py:519-523 already contains:

    if ext_stop_r>0:
        ext=(close - pe)*d/hrisk
        if ext>ext_stop_r: continue          # ext_stop_r defaults to 1.5

**The shipped engine already has a live-R CEILING.** It refuses new 15m
entries once the 1h leg is more than 1.5R unrealised. Nobody trades there.
What the engine has NEVER had is a live-R FLOOR - it will happily open a
15m trade while the 1h leg is deep underwater.

So P3-C's finding is not a new idea competing with the champion. It is the
**missing half of a rule the champion already half-implements.** That is a
much better story than "a new gate that might double-count", and it is
checkable: the champion's own P3-C numbers (PF 3.80 IS / 0.74 OOS at
floor=+0.50) were measured WITH ext_stop_r=1.5 already active. The
inversion at high floors is therefore the ceiling and the floor fighting
each other, not the floor alone.

Every number here is reported against the champion's OWN control from this
same file, not against any number quoted from a doc.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from exp_live_gate import (build_patched, maxdd, pf, stats, tm)  # noqa: E402

# the shipped champion, as read from the repo
CHAMP = {
    "mode": "b2_vs_flip_chop",
    "chop_thresh": 61.8,
    "cooldown_bars": 20,
    "sl_buf_atr": 0.25,
    "ext_stop_r": 1.5,
    "max_consecutive_losses": 5,
}


def run():
    from exp_5m_confirm import load_book
    mod = build_patched()
    NEW = mod.simulate_htf_ltf_streak_halt

    print("=" * 96)
    print("  P3-D  THE CHAMPION BOOK  +  live_R FLOOR")
    print("=" * 96)
    print(f"  champion config: {CHAMP}")
    print("  note ext_stop_r=1.5 is ALREADY a live-R ceiling in the engine")
    print("  the floor is the missing half\n")

    books = {}
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        args = (data["c1h"], data["sw10"], data["c15"],
                data["sw15"], data["fine"])
        rs = [float(t["r_multiple"])
              for t in NEW(*args, live_r_floor=None, **CHAMP)["ltf_trades"]
              if t.get("outcome") != "open"]
        books[scope] = (args, rs)
        print(f"  [{scope}] CHAMPION CONTROL  {stats(rs)}")
    print()

    print("=" * 96)
    print("  FLOOR SWEEP ON THE CHAMPION")
    print("=" * 96)
    print(f"  {'floor':>7}  {'IS':<46} {'OOS':<46} both?")
    for f in (None, -0.50, -0.25, -0.10, 0.0, 0.10, 0.25, 0.50):
        cells, nets = [], {}
        for scope in ("is", "oos"):
            args, _ = books[scope]
            rs = [float(t["r_multiple"])
                  for t in NEW(*args, live_r_floor=f, **CHAMP)["ltf_trades"]
                  if t.get("outcome") != "open"]
            nets[scope] = sum(rs)
            cells.append(f"n={len(rs):<4} net={sum(rs):+8.1f} "
                         f"WR={100.0*sum(1 for x in rs if x>0)/max(len(rs),1):>4.1f}% "
                         f"PF={pf(rs):>5.2f} DD={maxdd(rs):>5.1f}")
        bi = sum(books["is"][1])
        bo = sum(books["oos"][1])
        di, do = nets["is"] - bi, nets["oos"] - bo
        ok = "YES" if di > 0 and do > 0 else ("no" if di < 0 and do < 0
                                              else "MIXED")
        lab = "None" if f is None else f"{f:+.2f}"
        print(f"  {lab:>7}  {cells[0]:<46} {cells[1]:<46} {ok}")
    print()

    print("=" * 96)
    print("  HEAD-TO-HEAD  control vs floor=0.00  ON THE CHAMPION")
    print("=" * 96)
    for scope in ("is", "oos"):
        args, base = books[scope]
        rs = [float(t["r_multiple"])
              for t in NEW(*args, live_r_floor=0.0, **CHAMP)["ltf_trades"]
              if t.get("outcome") != "open"]
        print(f"  [{scope}] control  {stats(base)}")
        print(f"  [{scope}] floor0   {stats(rs)}")
        print(f"           dNet {sum(rs)-sum(base):+.1f}R on a base of "
              f"{sum(base):+.1f}R  ({100.0*(sum(rs)-sum(base))/abs(sum(base)):+.0f}%)"
              f"   trades {len(base)}->{len(rs)} "
              f"({100.0*(len(rs)-len(base))/max(len(base),1):+.0f}%)")
        print()


if __name__ == "__main__":
    run()
