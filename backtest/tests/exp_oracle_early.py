"""P3-B - READ THE ORACLE EARLY. The full matrix.

WHY THIS EXISTS
===============
HTF_ATTRIBUTION.md found the 1h window is a QUALITY ORACLE, not a
permission slice. Its verdict splits the 15m book into a 55.7%-WR cohort
(+231R) and an 8.6%-WR cohort (-134R). But that verdict is read only at
the window's EXIT - a median 1.1 days late. The user's question was
"the 1h layer needs something new, B1/B2/FLIP don't work there" and this
is the answer: the 1h leg's job is not to be a book, it is to be an
oracle, and the oracle is currently read in hindsight.

THE ONE DESIGN DECISION THAT MAKES THE MATRIX FREE
===================================================
The live-oracle arms are all POST-HOC FILTERS on the cascade's own 396
trades, scored by a CAUSAL feature: the 1h leg's realised R at the exact
instant of each 15m entry, read from the 1m fine series. The engine runs
ONCE per era. Every arm is then a boolean filter over that same trade
list. So the entire matrix - live-R sweep, age sweep, and the 2-way
interaction - costs one engine run, not forty.

This is legitimate and not a shortcut: the feature uses only prices at or
before each trade's entry timestamp, so no arm can see the future. What
it DOES mean is that arms are compared on the SAME trade universe, which
makes the comparison cleaner than re-running the engine per arm, not
dirtier.

CAUSALITY, spelled out because this session has been burned by it
=============================================================
  live_R(t) = dir * (px_1m(t) - htf_entry_px) / |htf_entry_px - htf_sl|
evaluated at t = the 15m trade's entry_ts, using the last 1m close at or
before t. At a 15m entry the 1h leg has been running for some hours and
has touched part of its own +1.5R / -1R path already. That is knowable
in real time. It is NOT the window's outcome, which is not.

PRE-REGISTERED FALSIFIER (written before the run)
================================================
The live-oracle arm must beat the same arm using ONLY information
available at window open, on BOTH eras. Window-open information is:
window direction, entry_px, sl, and the open time. If live_R adds
nothing over that, the oracle is genuinely unknowable in real time and
HTF_ATTRIBUTION's Q2 advantage is pure hindsight.

Also reported, because it is the control that matters: the same filter
applied to a WINDOW-OPEN-ONLY placebo (direction alone), and the same
trade count reached by random removal. A gate that merely deletes trades
must not be able to look like an edge.
"""
from __future__ import annotations

import bisect as bs
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

DAY = 86400.0


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
    return sum(x for x in rs if x > 0) / max(1e-9,
                                            -sum(x for x in rs if x < 0))


def row(label, rs, base_n, base_net):
    if not rs:
        return (f"    {label:<30} n=0")
    d = sum(rs) - base_net
    wr = 100.0 * sum(1 for x in rs if x > 0) / len(rs)
    return (f"    {label:<30} n={len(rs):<4} net={sum(rs):+8.1f}R  "
            f"dNet={d:+8.1f}R  WR={wr:>5.1f}%  PF={pf(rs):>5.2f}  "
            f"tm={tm(rs):+.3f}  keep={100.0*len(rs)/base_n:>4.0f}%")


def build(scope):
    """Engine once per era -> the trade list with causal features."""
    from exp_5m_confirm import load_book
    from src.btc.engines.htf_ltf.v18_streak_halt import (
        simulate_htf_ltf_streak_halt)

    data, _ = load_book(scope)
    c1h, c15, fine = data["c1h"], data["c15"], data["fine"]
    eng = simulate_htf_ltf_streak_halt(
        c1h, data["sw10"], c15, data["sw15"], fine, mode="atr_high")

    # --- 1m price series for the causal live_R lookup ---------------
    fts = [int(c["ts"]) for c in fine]
    fpx = [float(c["close"]) for c in fine]

    def px_at(t):
        i = bs.bisect_right(fts, t) - 1
        return fpx[i] if i >= 0 else None

    # --- windows: (start, end, dir_sign, entry_px, sl) ---------------
    wins = []
    for iv in eng["intervals"]:
        a, b, d, p, s = int(iv[0]), int(iv[1]), int(iv[2]), float(iv[3]), float(iv[4])
        if s == p or d == 0:
            continue
        wins.append((a, b, d, p, s))
    wins.sort()

    def win_of(ts):
        for w in wins:
            if w[0] <= ts <= w[1]:
                return w
        return None

    out = []
    for t in eng["ltf_trades"]:
        if t.get("outcome") == "open":
            continue
        ts = int(t["entry_ts"])
        w = win_of(ts)
        if w is None:
            continue
        a, b, d, p, s = w
        risk = abs(p - s)
        cur = px_at(ts)
        live_r = (d * (cur - p) / risk) if (cur is not None and risk > 0) else 0.0
        # how far the 1h leg has already travelled toward its own stop
        out.append({
            "r": float(t["r_multiple"]),
            "ts": ts,
            "live_r": live_r,
            "age_d": (ts - a) / DAY,
            "wlen_d": (b - a) / DAY,
            "dir": d,
            "swing_ok": t.get("break_kind", "?"),
        })
    return out, len(eng["intervals"])


def matrix(out, scope):
    rs_all = [t["r"] for t in out]
    bn, bnet = len(rs_all), sum(rs_all)
    print(f"  [{scope}] CONTROL  n={bn}  net={bnet:+.1f}R  "
          f"WR={100.0*sum(1 for x in rs_all if x>0)/max(bn,1):.1f}%  "
          f"PF={pf(rs_all):.2f}  tm={tm(rs_all):+.3f}")
    lr = [t["live_r"] for t in out]
    age = [t["age_d"] for t in out]
    lr_s = sorted(lr)
    print(f"    live_R at 15m entry : p10 {lr_s[len(lr_s)//10]:+.2f}  "
          f"p50 {lr_s[len(lr_s)//2]:+.2f}  "
          f"p90 {lr_s[9*len(lr_s)//10]:+.2f}")
    ag = sorted(age)
    print(f"    window age (days)   : p10 {ag[len(ag)//10]:.2f}  "
          f"p50 {ag[len(ag)//2]:.2f}  p90 {ag[9*len(ag)//10]:.2f}")

    # --- A1: live-R floor --------------------------------------------
    print(f"\n  [{scope}] A1  LIVE-ORACLE FLOOR  (take only if 1h leg already >= X)")
    for x in (-0.9, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        print(row(f"live_R >= {x:+.2f}",
                  [t["r"] for t in out if t["live_r"] >= x], bn, bnet))

    # --- A2: live-R ceiling (fade the winners) ----------------------
    print(f"\n  [{scope}] A2  LIVE-ORACLE CEILING  (skip if 1h leg already >= X)")
    for x in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
        print(row(f"live_R <  {x:+.2f}",
                  [t["r"] for t in out if t["live_r"] < x], bn, bnet))

    # --- A3: window age ----------------------------------------------
    print(f"\n  [{scope}] A3  WINDOW AGE")
    for x in (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0):
        print(row(f"age <= {x:.2f}d",
                  [t["r"] for t in out if t["age_d"] <= x], bn, bnet))
    for x in (0.5, 1.0, 1.5, 2.0, 3.0):
        print(row(f"age >  {x:.2f}d",
                  [t["r"] for t in out if t["age_d"] > x], bn, bnet))
    print()


def placebo(out, scope):
    """The control that matters: does any filter LOOK like an edge?"""
    bn = len(out)
    bnet = sum(t["r"] for t in out)
    print(f"  [{scope}] FALSIFIER CONTROLS")
    for d in (1, 2, 3):
        k = [t["r"] for t in out if t["dir"] > 0] if d == 1 else None
        if d == 1:
            print(row("window-open: dir=long only", k, bn, bnet))
        elif d == 2:
            print(row("window-open: dir=short only",
                      [t["r"] for t in out if t["dir"] < 0], bn, bnet))
    # random removal at the same trade count as the best live-R arm
    best_n = sum(1 for t in out if t["live_r"] >= 0.0)
    rng = random.Random(20260928)
    nets = []
    for _ in range(4000):
        s = rng.sample(out, min(best_n, bn))
        nets.append(sum(t["r"] for t in s))
    nets.sort()
    p95 = nets[int(0.95 * len(nets))]
    print(f"    random subsample of n={best_n} (4k draws): "
          f"mean={sum(nets)/len(nets):+.1f}R  p95={p95:+.1f}R  "
          f"max={nets[-1]:+.1f}R")
def interaction(out, scope):
    """The 2-way cells - this is where 'no cell gets skipped' pays off."""
    bn = len(out)
    bnet = sum(t["r"] for t in out)
    print(f"  [{scope}] A4  2-WAY  live_R x AGE   (net R in each cell)")
    lb = [(-9, -0.25, "a <-0.25"), (-0.25, 0.25, "b -0.25..0.25"),
          (0.25, 0.75, "c 0.25..0.75"), (0.75, 9, "d >0.75")]
    ab = [(0.0, 0.5, "young <0.5d"), (0.5, 1.5, "mid 0.5-1.5d"),
          (1.5, 3.0, "old 1.5-3d"), (3.0, 99, "ancient >3d")]
    hdr = "        " + "".join(f"{c[2]:>17}" for c in ab)
    print(hdr)
    for lo, hi, nm in lb:
        cells = []
        for alo, ahi, _ in ab:
            v = [t["r"] for t in out
                 if lo <= t["live_r"] < hi and alo <= t["age_d"] < ahi]
            cells.append(f"{sum(v):+7.1f}R n{len(v):<4}" if v
                         else f"{'-':>17}")
        print(f"    {nm:<8}" + "".join(f"{c:>17}" for c in cells))

    # per-cell trimmed mean: net R alone can be one lucky trade
    print(f"        (trimmed mean per cell)")
    print(hdr)
    for lo, hi, nm in lb:
        cells = []
        for alo, ahi, _ in ab:
            v = [t["r"] for t in out
                 if lo <= t["live_r"] < hi and alo <= t["age_d"] < ahi]
            cells.append(f"{tm(v):+7.3f} n{len(v):<4}" if v
                         else f"{'-':>17}")
        print(f"    {nm:<8}" + "".join(f"{c:>17}" for c in cells))

    # the single best cell, and whether it holds in BOTH eras (printed
    # by main, which has both eras in hand)
    best = None
    for lo, hi, _ in lb:
        for alo, ahi, _ in ab:
            v = [t["r"] for t in out
                 if lo <= t["live_r"] < hi and alo <= t["age_d"] < ahi]
            if len(v) >= 25:
                d = sum(v) - bnet * len(v) / max(bn, 1)
                if best is None or d > best[0]:
                    best = (d, lo, hi, alo, ahi, len(v), sum(v), tm(v))
    if best:
        print(f"    best cell (n>=25): live_R [{best[1]:+.2f},{best[2]:+.2f}) "
              f"age [{best[3]:.2f},{best[4]:.2f})d  n={best[5]}  "
              f"net={best[6]:+.1f}R  tm={best[7]:+.3f}  "
              f"lift={best[0]:+.1f}R vs proportional")
    print()


def main():
    print("=" * 92)
    print("  P3-B  READ THE ORACLE EARLY - full matrix, both eras")
    print("=" * 92)
    print("  live_R = 1h leg's realised R at each 15m entry (1m close, causal)")
    print("  falsifier: must beat window-open-only info on BOTH eras\n")

    res = {}
    for scope in ("is", "oos"):
        out, nwin = build(scope)
        res[scope] = out
        print(f"  [{scope}] {nwin} windows, {len(out)} 15m trades inside one")
        matrix(out, scope)
        interaction(out, scope)
        placebo(out, scope)

    # ---- cross-era: only cells that hold in BOTH count --------------
    print("=" * 92)
    print("  CROSS-ERA GATE - a real finding must hold in BOTH")
    print("=" * 92)
    is_o, oos_o = res["is"], res["oos"]
    bn_i, bn_o = len(is_o), len(oos_o)
    print(f"  arm                       IS dNet      OOS dNet    both?")
    tests = []
    for x in (-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        tests.append((f"live_R >= {x:+.2f}",
                      lambda t, x=x: t["live_r"] >= x))
    for x in (0.5, 1.0, 1.5, 2.0, 3.0):
        tests.append((f"age > {x:.2f}d", lambda t, x=x: t["age_d"] > x))
    for nm, f in tests:
        a = [t["r"] for t in is_o if f(t)]
        b = [t["r"] for t in oos_o if f(t)]
        if not a or not b:
            print(f"  {nm:<26} {'-':>10}      {'-':>10}    SKIP")
            continue
        di = sum(a) - sum(t["r"] for t in is_o) * len(a) / max(bn_i, 1)
        do = sum(b) - sum(t["r"] for t in oos_o) * len(b) / max(bn_o, 1)
        ok = "YES" if di > 0 and do > 0 else ("no" if di < 0 and do < 0
                                              else "MIXED")
        print(f"  {nm:<26} {di:+9.1f}R     {do:+9.1f}R    {ok}")
    print()


if __name__ == "__main__":
    main()

