"""P12 - DECAY AS A REGIME SWITCH. Full sweep: gate, flip, window flip, +4.

THE USER'S ASK
==============
"gate wagera, ya HTF bias window he change karde, ya long ki jagah short
bhi lene de, trade regime switch kare... kuch trades ke liye okay, ab
bias change karo. deep studies. main bhi ideas add karunga, aur sweep
karo - theory, hypothesis, autopsy, poora."

Testable arms, plus four of mine. All on the champion, pins reproduced
first, every arm scored against its own move-block null (P5 machinery,
M = 479.9R IS / 193.4R OOS for the whole book).

THE TECHNICAL TRAP, stated first
=================================
**A direction flip CANNOT be tested by negating r_multiple.** Flipping a
long to a short moves the stop to the other side and the target with it,
so it is a DIFFERENT trade. Negating the R would manufacture a result.

So every flip arm is a genuine PATH-TRUE REPLAY on the 1m series: enter
opposite at the same bar, stop at the mirrored risk level, target at 3R
(the book's own htf_rr), walk bar by bar, first touch wins. The control
arm uses the identical replay machinery, so the comparison is like-for-like.

ARMS - the user's three, then four of mine
==========================================
  U1  DECAY GATE      skip entries when decay >= D. P11 showed the
                      buckets descriptively; this is it as a live rule.
  U2  DECAY FLIP      take the OPPOSITE side when decay >= D. The user's
                      "long ki jagah short bhi lene de."
  U3  WINDOW FLIP     flip the 1h BIAS WINDOW's direction when decay is
                      high, so every 15m signal inside it re-routes.
                      Different object from U2.
  M1  ASYMMETRY       decay counts broken BUYING lows. Add the mirror -
                      broken selling highs. The DIFFERENCE is directional
                      imbalance, not magnitude.
  M2  VELOCITY        a jump 0 -> 0.75 is a different event from sitting
                      at 0.75. Measure the CHANGE over the last 8 bars.
  M3  DECAY x AGE     decay says structure is failing, age says how long.
                      Their interaction is where a switch would live.
  M4  DOUBLE FAILURE  flip only when decay is high AND the live 1h leg is
                      already under water - two independent pieces of
                      evidence agreeing before switching.

FALSIFIERS, PRE-REGISTERED HERE
==============================
  (a) dNet negative in either era
  (b) positive in one era, negative in the other
  (c) no arm clears its own null
  (d) gain comes purely from deleting trades, not re-routing - reported
      per arm explicitly
An autopsy producing only negatives is a valid result and is reported as
one.
"""
from __future__ import annotations

import bisect as bs
import random
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

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.1)}
BLOCK, DRAWS, SEED = 20, 10_000, 20260928
TARGET_R = 3.0
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


def legs_by_dir(sw15):
    """Confirmed legs split by direction, each with its own 'low' to
    defend: an up-leg defends its start (a low), a down-leg defends its
    start (a high). Only legs confirmed at or before t are ever used."""
    ups, dns = [], []
    for sw in sw15:
        ct = sw.get("confirmed_at_time") or ""
        if not isinstance(ct, str) or len(ct) < 19:
            continue
        try:
            cts = _dt(ct)
        except Exception:
            continue
        seg = sw.get("seg", {}) or {}
        rec = {"cts": cts, "px": float(seg.get("start_px", 0) or 0)}
        if sw.get("dir") in ("up", "B"):
            ups.append(rec)
        else:
            dns.append(rec)
    return ups, dns


def decay_pair(up, dn, t, lows, highs, ts, n=N_SWINGS):
    """(broken_up_frac, broken_dn_frac) as of t. Strictly causal."""
    j = bs.bisect_right(ts, t) - 1
    if j < 0:
        return None
    def frac(legs, series, better):
        vis = [L for L in legs if L["cts"] <= t]
        if not vis:
            return None
        rec = vis[-n:]
        br = 0
        for L in rec:
            if L["px"] <= 0:
                continue
            a = bs.bisect_left(ts, L["cts"])
            b = min(j, bs.bisect_right(ts, t) - 1)
            if b < a:
                continue
            seg = series[a:b + 1]
            if not seg:
                continue
            if better == "low" and min(seg) < L["px"]:
                br += 1
            elif better == "high" and max(seg) > L["px"]:
                br += 1
        return br / float(len(rec))
    return frac(up, lows, "low"), frac(dn, highs, "high")


def decay_at(legs, t, lows, ts, n=N_SWINGS):
    v, _ = decay_pair(legs, [], t, lows, lows, ts, n)
    return v


def replay(t, sign, fts, fhi, flo, risk, target_r=TARGET_R, horizon=None):
    """Path-true walk of a hypothetical trade in direction `sign`.
    sign=+1 long, -1 short. Mirrored stop at `risk`, target at
    `target_r*risk`. First touch on a bar wins, stop checked before
    target. Returns R, or None if the window ends unresolved."""
    a = bs.bisect_left(fts, int(t["entry_ts"]))
    b = (bs.bisect_left(fts, int(t["exit_ts"]))
         if horizon is None else min(len(fts), a + horizon))
    e = float(t["entry_price"])
    tgt = target_r * risk
    for k in range(a, min(b + 1, len(flo))):
        hi, lo = fhi[k], flo[k]
        if sign > 0:
            if lo <= e - risk:
                return -1.0
            if hi >= e + tgt:
                return target_r
        else:
            if hi >= e + risk:
                return -1.0
            if lo <= e - tgt:
                return target_r
    return None
def line(lbl, rs, per, bn, bnet):
    if not rs:
        return f"    {lbl:<32} n=0"
    n = len(rs)
    M, nm = M_of(rs, per)
    wr = 100.0 * sum(1 for x in rs if x > 0) / n
    obs = sum(rs) - per * n
    cl = "*** CLEARS ***" if (M == M and abs(obs) > M) else "inside null"
    return (f"    {lbl:<32} n={n:<4} net={obs:+8.1f} dNet={obs-bnet:+8.1f} "
            f"WR={wr:>5.1f}% M={M:>7.1f} {cl}")


def main():
    from src.btc.btc_routes import _trade_costs
    from engine.v18_params import SYMBOL_PARAMS

    print("=" * 100)
    print("  P12  DECAY AS A REGIME SWITCH - full sweep, 7 arms")
    print("=" * 100)
    print("  Flip arms are PATH-TRUE 1m replays with a mirrored stop.")
    print("  r_multiple is never negated. Pins reproduced first.\n")

    sim = build_module()
    g = SYMBOL_PARAMS["BTCUSDT"]
    out = {}
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
        ivs = sorted((int(x[0]), int(x[1]), int(x[2]), float(x[3]), float(x[4]))
                     for x in eng["intervals"])
        rows = []
        for t in tr:
            ts = int(t["entry_ts"])
            du, dd = decay_pair(ups, dns, ts, flo, fhi, fts)
            if du is None or dd is None:
                continue
            par = next((x for x in ivs if x[0] <= ts <= x[1]), None)
            live_r, age_d = 0.0, 0.0
            if par:
                a, b, d, p, s = par
                rk = abs(p - s)
                j = bs.bisect_right(fts, ts) - 1
                px = fhi[j] if j >= 0 else p
                live_r = (d * (px - p) / rk) if rk > 0 else 0.0
                age_d = (ts - a) / 86400.0
            d1 = 1 if t["dir"] == "long" else -1
            du8 = decay_at(ups, ts - 7200, flo, fts)
            rows.append({"t": t, "d": d1, "du": du, "dd": dd,
                         "asym": du - dd, "live": live_r, "age": age_d,
                         "vel": (du - du8) if du8 is not None else 0.0,
                         "r_orig": float(t["r_multiple"]),
                         "risk": abs(float(t["entry_price"])
                                     - float(t["sl"]))})
        bnet = net_r(tr)
        out[scope] = (rows, per, bnet, len(tr), fts, fhi, flo)
        print(f"    {len(rows)} entries labelled; "
              f"{len(tr)-len(rows)} lacked enough confirmed legs\n")

    for scope in ("is", "oos"):
        rows, per, bnet, bn, fts, fhi, flo = out[scope]
        print("=" * 100)
        print(f"  [{scope}]  champion control: {bn} trades, net {bnet:+.1f}R")
        print("=" * 100)
        ctrl = []
        for r in rows:
            v = replay(r["t"], r["d"], fts, fhi, flo, r["risk"])
            if v is not None:
                ctrl.append(v)
        cl_net = sum(ctrl) - per * len(ctrl)
        print("  CONTROL: same replay machinery, same side, 3R target")
        print(f"    {'control replay':<32} n={len(ctrl):<4} net={cl_net:+8.1f}")
        for D in (0.5, 0.75, 1.01):
            print(f"\n  --- threshold decay >= {D} ---")
            print(line("U1 gate (drop)",
                       [r["r_orig"] for r in rows if r["du"] < D],
                       per, bn, bnet))
            fl = []
            for r in rows:
                v = replay(r["t"], (-r["d"] if r["du"] >= D else r["d"]),
                           fts, fhi, flo, r["risk"])
                if v is not None:
                    fl.append(v)
            print(line("U2 FLIP (opposite side)", fl, per, bn, cl_net))
            print(line("M1 asym <= +0.25",
                       [r["r_orig"] for r in rows if r["asym"] <= 0.25],
                       per, bn, bnet))
            print(line("M2 velocity <= 0 (not rising)",
                       [r["r_orig"] for r in rows if r["vel"] <= 0.0],
                       per, bn, bnet))
            print(line("M3 decay<0.5 OR age>2d",
                       [r["r_orig"] for r in rows
                        if r["du"] < 0.5 or r["age"] > 2.0], per, bn, bnet))
            print(line("M4 drop if decay high & 1h wet",
                       [r["r_orig"] for r in rows
                        if not (r["du"] >= D and r["live"] < 0.0)],
                       per, bn, bnet))
        print()
    print("=" * 100)
    print("  Compare gate arms (M1-M4, U1) against the champion's own")
    print("  r_multiple net, and U2 against the CONTROL replay row, since")
    print("  a flip is a different trade with a different exit structure.")
    print("=" * 100)


if __name__ == "__main__":
    main()

