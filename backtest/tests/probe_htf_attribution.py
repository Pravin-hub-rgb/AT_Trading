"""P3-A - does the 1h bias window earn ANY of the cascade's R?

THE USER'S OBSERVATION, the sharpest thing said today
=====================================================
"the 15m layer does not trade inside a PROFITABLE htf bias - it trades
inside a window that is DEAD 70% of the time, and we still get +325R.
so either the 1h window contributes none of that 325R, or we are
missing something."

That is testable, and it is P3's falsifier in plain language.
BIAS_WINDOW_THEORY.md showed the 1h book standalone is ~zero (mean
+0.08R IS / -0.09R OOS, median exactly -1.00R). So the cascade's R must
come from the 15m layer. But "the 1h legs are coin-flips" is NOT the
same as "the 1h window adds nothing" - the window could still be a
useful PERMISSION SLICE even if the legs it selects are bad.

  Q1  1h book standalone, all 3 mark modes x era (P3 proper - the full
      set, so "which 1h book is best" is answered, not assumed).
  Q2  Cascade R split by parent window outcome. If the 'sl' windows
      (69-74%) carry the book's R, the window DIRECTION is not the edge.
  Q3  Is the gate even binding? Cascade vs the 15m book ungated. If
      ungated ~= gated, the 1h layer is decoration and every result in
      the repo is really a 15m result.

Read-only. No new data. No forward slice.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))


def tm(x):
    """20% trimmed mean - the repo's standard robust centre."""
    if not x:
        return 0.0
    x = sorted(x)
    k = max(1, len(x) // 20)
    if len(x) <= k:
        return sum(x) / len(x)
    return sum(x[:-k]) / (len(x) - k)


def pf(rs):
    w = sum(x for x in rs if x > 0)
    l = -sum(x for x in rs if x < 0)
    return w / max(1e-9, l)


def line(label, rs):
    n = len(rs)
    wr = 100.0 * sum(1 for x in rs if x > 0) / max(n, 1)
    print(f"    {label:<26} n={n:<4} net={sum(rs):+8.1f}R  "
          f"WR={wr:>5.1f}%  PF={pf(rs):>5.2f}  tm={tm(rs):+.3f}")


def main():
    from exp_5m_confirm import load_book
    from engine.v18_params import SWING
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.engines.htf_ltf.v18_streak_halt import (
        simulate_htf_ltf_streak_halt)
    from src.walker import FlowCandle

    print("=" * 88)
    print("  P3-A  DOES THE 1h WINDOW EARN ANY OF THE CASCADE'S R?")
    print("=" * 88)
    print("  Premise: 1h standalone is ~zero (BIAS_WINDOW_THEORY.md).")
    print("  Is the window still a USEFUL permission slice, or decoration?\n")

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c1h, c15, f15, fine = (data["c1h"], data["c15"],
                               data["f15"], data["fine"])
        flow1h = [FlowCandle(date=c["date"], open=float(c["open"]),
                             high=float(c["high"]), low=float(c["low"]),
                             close=float(c["close"])) for c in c1h]

        # ---- Q1: 1h standalone, all three mark modes ---------------
        print(f"  [{scope}]  Q1  1h HTF BOOK STANDALONE")
        for mode in ("flip", "decisive", "b2"):
            sw = data["sw20"] if mode == "b2" else data["sw10"]
            tr = simulate_btc_trades_v7(c1h, sw, entry_break=mode,
                                        sl_mode="swing", rr_target=3.0,
                                        trailing="off", breakeven_r=0.0,
                                        skip_first=True, fine=fine,
                                        cap_days=16)
            tr = tr if isinstance(tr, list) else list(tr)
            cl = [t for t in tr if t.get("outcome") != "open"]
            line(f"1h standalone {mode}",
                 [float(t["r_multiple"]) for t in cl])
        print()

        # ---- Q3: is the gate binding? cascade vs UNGATED 15m --------
        eng = simulate_htf_ltf_streak_halt(
            c1h, data["sw10"], c15, data["sw15"], fine, mode="atr_high")
        lb = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
        rl = [float(t["r_multiple"]) for t in lb]
        print(f"  [{scope}]  Q3  IS THE 1h GATE BINDING?")
        line("cascade (1h-GATED)", rl)
        # same 15m engine, no HTF window at all
        raw = simulate_btc_trades_v7(c15, data["sw15"],
                                     entry_break="decisive", sl_mode="swing",
                                     rr_target=3.0, trailing="off",
                                     breakeven_r=1.0, skip_first=True,
                                     fine=fine, cap_days=999)
        raw = raw if isinstance(raw, list) else list(raw)
        rw = [float(t["r_multiple"]) for t in raw
              if t.get("outcome") != "open"]
        line("15m alone (UNGATED)", rw)
        if rl and rw:
            print(f"    -> gate costs {100.0*(len(rw)-len(rl))/len(rw):.1f}% "
                  f"of trades, "
                  f"{sum(rw):+.1f}R -> {sum(rl):+.1f}R "
                  f"({sum(rl)-sum(rw):+.1f}R)")

        # ---- Q2: split cascade R by parent window outcome -----------
        # engine already resolved parent_intervals = (start, end, dir)
        # intervals are 5-tuples (start, end, dir, px, sl) - line 243
        piv = sorted((int(iv[0]), int(iv[1])) for iv in eng["intervals"])

        def parent(ts):
            for a, b in piv:
                if a <= ts <= b:
                    return a
            return None

        oc_of = {int(t["entry_ts"]): t.get("outcome", "?")
                 for t in eng["htf_trades"]}
        by = defaultdict(list)
        for t in lb:
            k = parent(int(t["entry_ts"]))
            by[oc_of.get(k, "outside") if k is not None
               else "outside_window"].append(float(t["r_multiple"]))
        tot = sum(rl) or 1.0
        print(f"  [{scope}]  Q2  CASCADE R BY PARENT WINDOW OUTCOME")
        for k in sorted(by, key=lambda z: -abs(sum(by[z]))):
            v = by[k]
            wr = 100.0 * sum(1 for x in v if x > 0) / max(len(v), 1)
            print(f"    window={k:<16} n={len(v):<4} net={sum(v):+8.1f}R  "
                  f"WR={wr:>5.1f}%  share={100.0*sum(v)/tot:>6.1f}%  "
                  f"tm={tm(v):+.3f}")
        print()


if __name__ == "__main__":
    main()
