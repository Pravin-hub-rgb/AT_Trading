"""P22 - WHAT ARE THE 500 TRADES ACTUALLY? An autopsy, not a theory.

THE USER'S QUESTION, WHICH IS THE RIGHT ONE
==========================================
"woh toh shayad swing low break aisa kuch hai nah? like long trades lena
hai but long ke swing break huye hai aisa kuch tha yaar woh kya hai"

They want to know what the 500 trades physically ARE. Everything said so
far has been about filters ON TOP of them. Nobody has ever printed the
book and described it. So this prints it.

The mechanism, from `_collect_signals` (btc_engine.py:95):
  - A swing is a leg of price. Its `breaks` are MARKS on that swing.
  - A swing can be abandoned mid-life and re-marked:
      B1    the first break of the leg
      B2    the SECOND break of the same leg - a retry
      FLIP  the leg's direction failed and it flipped
  - selection="stream" (live-faithful) fires on the FIRST tradeable mark
    (B2 or FLIP). B1 never trades.
  - Crucially the mark can fire in a direction OPPOSITE to the swing
    ("state churn"): that is a real live signal, it is fading the
    PREVIOUS leg, and its SL is the previous leg's end pivot.
  - Then the HTF (1h) window filter runs: the signal must fall inside a
    1h window AND the signal direction must match that window's direction
    (`if sig["dir"] != d: continue`).

So the answer to "is it a swing low break" is: NO, not a low break. A
long entry is a break of structure in the UP direction, gated by a 1h
window that agrees. The user is close but has the polarity backwards.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402

KEY = "champion_multi_sw10"
PARAMS = {**BP, **EXPERIMENTS[KEY]["params"]}


def main():
    print("=" * 92)
    print("  P22  ANATOMY OF THE 500  -  what the trades actually are")
    print("=" * 92)
    d = get_data()
    identity_gate(d, tc.build_module())
    eng = tc.build_module()
    r = eng(d["c1h"], d["sw10"], d["c15"], d["sw15"], fine_ltf=d["fine"],
            **PARAMS)
    tr = [t for t in r["ltf_trades"] if t.get("outcome") != "open"]
    print(f"\n  champion {KEY}: n={len(tr)}  NET {net_r(tr):+.1f}R\n")

    print("  1. DIRECTION")
    for dname in ("long", "short"):
        s = [t for t in tr if t["dir"] == dname]
        if not s:
            continue
        rs = [float(t["r_multiple"]) for t in s]
        wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
        print(f"     {dname:>5}  n={len(s):>4}  net={sum(rs):+8.1f}R  "
              f"WR={wr:5.1f}%  R/tr={sum(rs)/len(rs):+5.2f}")

    print("\n  2. BREAK KIND  (what mark fired the entry)")
    for k, c in Counter(t["break_kind"] for t in tr).most_common():
        s = [t for t in tr if t["break_kind"] == k]
        rs = [float(t["r_multiple"]) for t in s]
        wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
        print(f"     {k:>5}  n={len(s):>4} ({100.0*len(s)/len(tr):4.1f}%)  "
              f"net={sum(rs):+8.1f}R  WR={wr:5.1f}%  R/tr={sum(rs)/len(rs):+5.2f}")

    print("\n  3. HTF WINDOW REGIME  (the 1h window the signal fell inside)")
    for k, c in Counter(t.get("htf_regime", "?") for t in tr).most_common():
        s = [t for t in tr if t.get("htf_regime") == k]
        rs = [float(t["r_multiple"]) for t in s]
        wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
        print(f"     {k:>5}  n={len(s):>4} ({100.0*len(s)/len(tr):4.1f}%)  "
              f"net={sum(rs):+8.1f}R  WR={wr:5.1f}%  R/tr={sum(rs)/len(rs):+5.2f}")

    print("\n  4. EXIT REASON")
    for k, c in Counter(t["outcome"] for t in tr).most_common():
        s = [t for t in tr if t["outcome"] == k]
        rs = [float(t["r_multiple"]) for t in s]
        print(f"     {k:>10}  n={len(s):>4} ({100.0*len(s)/len(tr):4.1f}%)  "
              f"net={sum(rs):+8.1f}R  R/tr={sum(rs)/len(rs):+5.2f}")

    print("\n  5. DIRECTION x BREAK KIND  (the cross that matters)")
    print(f"     {'':>12} {'B2':>22} {'FLIP':>22}")
    for dname in ("long", "short"):
        cells = []
        for k in ("B2", "FLIP"):
            s = [t for t in tr if t["dir"] == dname and t["break_kind"] == k]
            if s:
                rs = [float(t["r_multiple"]) for t in s]
                cells.append(f"n={len(s):>3} net={sum(rs):+7.1f}R "
                             f"({sum(rs)/len(rs):+5.2f})")
            else:
                cells.append(f"{'-':>22}")
        print(f"     {dname:>12} {cells[0]:>22} {cells[1]:>22}")

    print("\n  6. ONE REAL TRADE, printed")
    t = tr[len(tr) // 2]
    print(f"     #{t['trade_no']} {t['dir']}  break={t['break_kind']}  "
          f"regime={t.get('htf_regime')}")
    print(f"     entry {t['entry_date']} @ {t['entry_price']}")
    print(f"     stop  {t['sl']}   target {t['target']}   "
          f"risk {abs(float(t['entry_price'])-float(t['sl'])):.1f}")
    print(f"     exit  {t['exit_date']} @ {t['exit_price']}  "
          f"-> {t['outcome']}  {t['r_multiple']:+.2f}R  "
          f"held {t['bars_held']} bars")
    print()


if __name__ == "__main__":
    main()
