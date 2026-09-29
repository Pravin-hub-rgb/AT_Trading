"""P11 AUTOPSY - STRUCTURAL DECAY: when buying swings' lows start breaking,
is the trend actually changing?

THE USER'S HYPOTHESIS, stated precisely
=======================================
"prev kuch swings buying ke hai, aur ab in swings ke jab lows break hone
lage toh research karo ki ab trend might be changing."

Concrete, testable, and - as far as the repo goes - novel. Grep for
broken_low / lows_broken / higher_lows_fail / structural_decay /
break_of_low / prior_swing_low returns ZERO hits in the BTC engine and
tests. ADX gates closed, regime gates closed, efficiency-ratio gates
closed. Nothing has ever looked at the FAILURE OF PRIOR SWING LOWS as the
signal. The repo describes the 15m book's edge as "a property of 15m
swing structure"; this asks whether the structure is decaying.

THE MEASUREMENT, and the causality argument, which is the whole point
======================================================================
At a given 15m bar t:

  1. Take the last N CONFIRMED 15m swings that were BUYING (up), where
     confirmed means confirmed_at_time <= t. A swing that has not
     finished confirming is not used. No-lookahead, enforced by filter
     rather than convention.
  2. Each such swing's low is its start_px (an up-leg starts at a low).
  3. Count how many of those lows price traded BELOW at any point between
     that swing's confirmation and t. Only 1m lows at or before t.
     No-lookahead.
  4. decay = broken / N.

  decay 0 = every prior buying swing's low still holds -> structure intact
  decay 1 = every one taken out                       -> structure gone

This is the standard reading of a trend losing its footing, computed
from the repo's own swing objects rather than from a new segmentation.

WHAT IS ASKED OF IT
===================
  A. Does decay predict FORWARD movement? MFE/MAE per bucket, in R.
  B. Does decay predict the CHAMPION's trades? R split by the decay
     bucket live at each entry.
  C. Does the BIAS WINDOW direction agree with the decay sign? When
     decay is high, are the book's longs the wrong side? This is the
     user's actual worry - "trend might be changing" while the book is
     still long.
  D. Every bucket scored against its OWN move-block reshuffle null, the
     P5 machinery, because a descriptive ordering is not a finding.

FALSIFIERS, PRE-REGISTERED HERE
===============================
  (a) no monotone ordering of forward MAE in BOTH eras
  (b) an IS ordering that inverts in OOS
  (c) no bucket clears its own null
Reported whichever lands. This is an AUTOPSY - it describes, it does not
propose a gate - so a negative result is worth as much as a positive one.
"""
from __future__ import annotations

import bisect as bs
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.1)}
BLOCK, DRAWS, SEED = 20, 10_000, 20260928
N_SWINGS = 4


def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, build_module())
    return (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])


def M_of(rs, per_cost, block=BLOCK, draws=DRAWS, seed=SEED):
    n = len(rs)
    if n < 10:
        return float("nan"), float("nan")
    nb = max(1, n // block)
    span = max(1, n - block + 1)
    rng = random.Random(seed)
    nets = []
    for _ in range(draws):
        tot = 0.0
        for _ in range(nb):
            s = rng.randrange(0, span) if n > block else 0
            for i in range(s, s + block):
                tot += rs[i] - per_cost
        nets.append(tot)
    absn = sorted(abs(x) for x in nets)
    return absn[int(0.95 * len(absn))], sum(nets) / len(nets)


def _dt(ts):
    import datetime as _d
    return int(_d.datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S").timestamp())


def buying_legs(sw15):
    """Confirmed buying (up) 15m legs, in chain order, with their lows.

    Only legs whose confirmation time parsed successfully are used; a leg
    is only visible to the decay calculation AFTER it has confirmed, which
    is what makes the signal causal.
    """
    out = []
    for i, sw in enumerate(sw15):
        if sw.get("dir") not in ("up", "B"):
            continue
        ct = sw.get("confirmed_at_time") or ""
        if not isinstance(ct, str) or len(ct) < 19:
            continue
        try:
            cts = _dt(ct)
        except Exception:
            continue
        seg = sw.get("seg", {}) or {}
        out.append({"i": i, "cts": cts,
                    "low": float(seg.get("start_px", sw.get("start_px", 0))),
                    "end": int(sw.get("end_idx", 0))})
    return out


def decay_at(legs, t, lows_1m, ts_1m, n=N_SWINGS):
    """Fraction of the last n CONFIRMED buying legs whose low is broken
    as of time t. Strictly causal: legs confirmed after t are excluded, and
    only 1m lows at or before t are read."""
    vis = [L for L in legs if L["cts"] <= t]
    if not vis:
        return None, 0
    recent = vis[-n:]
    j = bs.bisect_right(ts_1m, t) - 1
    if j < 0:
        return None, 0
    broken = 0
    for L in recent:
        a = bs.bisect_left(ts_1m, L["cts"])
        b = min(j, bs.bisect_right(ts_1m, t) - 1)
        if b < a:
            continue
        seg = lows_1m[a:b + 1]
        if seg and min(seg) < L["low"]:
            broken += 1
    return broken / float(len(recent)), len(recent)


def fwd_excursion(px_now, risk, t, hi_1m, lo_1m, ts_1m, bars):
    """Signed MFE/MAE in R over the next `bars` 15m bars. Future by
    construction - this is the DEPENDENT variable, never a feature."""
    a = bs.bisect_right(ts_1m, t)
    b = a + bars * 15
    if a >= len(ts_1m) or b > len(ts_1m):
        return None, None
    seg_h = hi_1m[a:b]
    seg_l = lo_1m[a:b]
    if not seg_h or risk <= 0:
        return None, None
    return (max(seg_h) - px_now) / risk, (px_now - min(seg_l)) / risk


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 96)
    print("  P11 AUTOPSY  STRUCTURAL DECAY - are prior buying swings' lows")
    print("              failing a warning that the trend is changing?")
    print("=" * 96)
    print(f"  decay = broken / {N_SWINGS} last CONFIRMED buying 15m legs, causal.")
    print("  Forward excursion is the dependent variable, never a feature.")
    print("  Pins reproduced first.\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    winners = []
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
        legs = buying_legs(sw15)
        print(f"    {len(legs)} confirmed buying 15m legs in the chain")

        # ---- A: forward excursion by decay, at every trade entry ------
        print(f"\n  [{scope}] A  DECAY vs FORWARD MOVEMENT (from each trade entry)")
        print(f"    {'decay':<10} {'n':>4} {'fwdMFE':>8} {'fwdMAE':>8} "
              f"{'edge':>8}")
        rows = []
        for t in tr:
            ts = int(t["entry_ts"])
            dv, nl = decay_at(legs, ts, flo, fts)
            if dv is None or nl < 2:
                continue
            rk = abs(float(t["entry_price"]) - float(t["sl"]))
            mfe, mae = fwd_excursion(float(t["entry_price"]), rk, ts,
                                     fhi, flo, fts, 32)
            if mfe is None:
                continue
            rows.append({"d": dv, "mfe": mfe, "mae": mae,
                         "r": float(t["r_multiple"]),
                         "long": 1 if t["dir"] == "long" else -1})
        if not rows:
            print("    not enough confirmed legs to measure")
            continue
        dd = sorted(r["d"] for r in rows)
        print(f"    decay distribution: p10 {dd[len(dd)//10]:.2f}  "
              f"p50 {dd[len(dd)//2]:.2f}  p90 {dd[9*len(dd)//10]:.2f}")
        for lab, lo, hi in (("0.00", -1e-9, 1e-9), ("0.25", 1e-9, 0.5),
                            ("0.50", 0.5, 0.75), ("0.75", 0.75, 1.01)):
            sel = [x for x in rows if lo < x["d"] <= hi]
            if len(sel) < 8:
                continue
            n = len(sel)
            print(f"    decay={lab:<7} {n:>4} {sum(x['mfe'] for x in sel)/n:>+8.2f}"
                  f" {sum(x['mae'] for x in sel)/n:>+8.2f} "
                  f"{(sum(x['mfe'] for x in sel)-sum(x['mae'] for x in sel))/n:>+8.2f}")

        # ---- B: the champion's own trades by decay --------------------
        print(f"\n  [{scope}] B  THE CHAMPION'S TRADES BY DECAY AT ENTRY")
        print(f"    {'decay':<10} {'n':>4} {'net':>9} {'WR':>7} {'M':>9} "
              f"{'nullmean':>9}  verdict")
        for lab, lo, hi in (("0.00", -1e-9, 1e-9), ("0.25", 1e-9, 0.5),
                            ("0.50", 0.5, 0.75), ("0.75", 0.75, 1.01)):
            sel = [x for x in rows if lo < x["d"] <= hi]
            if len(sel) < 10:
                continue
            rs = [x["r"] for x in sel]
            obs = sum(rs) - per * len(rs)
            M, nm = M_of(rs, per)
            if M != M:
                continue
            wr = 100.0 * sum(1 for z in rs if z > 0) / len(rs)
            cl = abs(obs) > M
            if cl:
                winners.append(f"{scope} decay {lab}")
            print(f"    decay={lab:<7} {len(rs):>4} {obs:>+9.1f} {wr:>6.1f}% "
                  f"{M:>9.1f} {nm:>+9.1f}  "
                  f"{'*** CLEARS ***' if cl else 'inside null'}")

        # ---- C: is the book long into decaying structure? ------------
        print(f"\n  [{scope}] C  IS THE BOOK LONG WHILE THE STRUCTURE DECAYS?")
        hi_d = [x for x in rows if x["d"] >= 0.5]
        lo_d = [x for x in rows if x["d"] < 0.5]
        for nm2, sel in (("decay < 0.5", lo_d), ("decay >= 0.5", hi_d)):
            if not sel:
                continue
            n = len(sel)
            lg = sum(1 for x in sel if x["long"] > 0)
            print(f"    {nm2:<14} n={n:<4} long={100.0*lg/n:>5.1f}%  "
                  f"longR={sum(x['r'] for x in sel if x['long']>0):+8.1f}  "
                  f"shortR={sum(x['r'] for x in sel if x['long']<0):+8.1f}")
        print()

    print("=" * 96)
    print("  DECAY BUCKETS THAT CLEAR THEIR OWN NULL")
    print("=" * 96)
    for w in winners:
        print(f"    {w}")
    if not winners:
        print("    NONE.")
    print("=" * 96)


if __name__ == "__main__":
    main()
