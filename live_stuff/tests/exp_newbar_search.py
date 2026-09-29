"""P14 - SEARCH UNDER THE USER'S NEW BAR. Small, robust, better-shaped.

THE BAR CHANGED, AND THE OLD ONE WAS THE WRONG QUESTION
=======================================================
Every result today was scored against P5's null: M = 479.9R IS / 193.4R
OOS. The user's response was the correct one - that bar is asking "is
this skill?" when the question is "is this a better book?" - and they set
a new, achievable bar:

    IS net      >= 280R     (down from 325.8R, a 14% give-up)
    OOS net     >  +70.1R   (must NOT lose out of sample)
    trades      <= 380      (down from 500, a 24% give-up)
    and prefer: better maxDD, better PF, higher WR, fewer trades

This is not a weakening, it is the correct target given M. A 500-trade
book CANNOT clear 480R, so demanding it guarantees every arm fails and
teaches nothing. A smaller book has a smaller M, which is exactly why
shrinking is the only route to a resolvable result - and shrinkage was
worth +383.9R IS / +78.5R OOS at 307 trades in P12's U1 arm, which I
dismissed for firing my own "trade deletion" falsifier. Under this bar
that arm is the shape the user asked for. That was my mis-framing, not
a real refutation.

WHAT IS SWEPT
=============
Seven causal features, computed once at every entry:
    decay   fraction of the last 4 confirmed buying 15m legs whose lows
            are broken (P11) - the user's own signal
    asym    decay_up - decay_down, a directional version (P12's M1)
    nest1h  where the entry sits in its HTF window's lifetime (P1-P,
            which found the largest two-era gradient in days)
    age     window age in days
    live_r  the 1h leg's unrealised R at entry - the P3/P4 family
    risk    |entry - sl| / ATR15
    hour    UTC hour of day

Single thresholds for each, then every PAIR of the surviving singles,
because a 14%+24% budget is large enough that a mild filter on two axes
may beat a brutal filter on one. Nothing is adopted here; the output is
the full ranked table under the new bar, including everything that fails,
because a search that only shows hits is a search that has already
overfitted itself.

NO LOOKAHEAD: every feature is computed from state at or before the entry
bar. Entry and exit are never touched - this is a filter over the
champion's own trades, so r_multiple is used as-is and no replay is
involved.
"""
from __future__ import annotations

import bisect as bs
import sys
from itertools import combinations
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
from exp_decay_switch import PARAMS, PINS, _dt, legs_by_dir, decay_pair  # noqa: E402

N_SWINGS = 4
BAR_IS, BAR_OOS, BAR_N = 280.0, 70.1, 380


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


def atr15(c15, lb=14):
    tr = []
    for i, c in enumerate(c15):
        h, l = float(c["high"]), float(c["low"])
        if i == 0:
            tr.append(h - l)
        else:
            pc = float(c15[i - 1]["close"])
            tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    out = []
    for i in range(len(c15)):
        j = max(0, i - lb + 1)
        out.append(sum(tr[j:i + 1]) / (i - j + 1))
    return out


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    eq = pk = d = 0.0
    for x in rs:
        eq += x
        pk = max(pk, eq)
        d = max(d, pk - eq)
    return d


def build(scope):
    from src.btc.btc_routes import _trade_costs
    c1h, sw10, c15, sw15, fine = load(scope)
    eng = sim_holder[0](c1h, sw10, c15, sw15, fine, **PARAMS)
    tr = [t for t in eng["ltf_trades"] if t.get("outcome") != "open"]
    want_n, want_net = PINS[scope]
    got = net_r(tr)
    if abs(len(tr) - want_n) > 2 or abs(got - want_net) > 1.0:
        raise SystemExit(f"PIN FAILED {scope}: {len(tr)}/{got:+.1f}")
    from engine.v18_params import SYMBOL_PARAMS
    g = SYMBOL_PARAMS["BTCUSDT"]
    c2, _ = _trade_costs(tr, g["fee_pct"], 0.0,
                         g["entry_slip_pct"], g["exit_slip_pct"])
    per = c2 / len(tr)
    fts = [int(c["ts"]) for c in fine]
    fhi = [float(c["high"]) for c in fine]
    flo = [float(c["low"]) for c in fine]
    ups, dns = legs_by_dir(sw15)
    ivs = sorted((int(x[0]), int(x[1]), int(x[2]), float(x[3]), float(x[4]))
                 for x in eng["intervals"])
    atr = atr15(c15)
    rows = []
    for t in tr:
        ts = int(t["entry_ts"])
        du, dd_ = decay_pair(ups, dns, ts, flo, fhi, fts)
        duv = du[0] if isinstance(du, tuple) else du
        ddv = du[1] if isinstance(du, tuple) else None
        par = next((x for x in ivs if x[0] <= ts <= x[1]), None)
        nest, age, live = 0.5, 0.0, 0.0
        if par:
            a, b, d, p, s = par
            nest = (ts - a) / float(b - a) if b > a else 0.5
            age = (ts - a) / 86400.0
            rk = abs(p - s)
            j = bs.bisect_right(fts, ts) - 1
            live = (d * (fhi[j] - p) / rk) if (rk > 0 and j >= 0) else 0.0
        k = min(int(t["entry_idx"]), len(atr) - 1)
        rk2 = abs(float(t["entry_price"]) - float(t["sl"]))
        rows.append({
            "r": float(t["r_multiple"]),
            "decay": duv if duv is not None else 0.5,
            "asym": (duv - ddv) if (duv is not None and ddv is not None) else 0.0,
            "nest1h": nest, "age": age, "live": live,
            "risk": rk2 / atr[k] if atr[k] > 0 else 0.0,
            "hour": (ts % 86400) // 3600,
        })
    return rows, per, len(tr), net_r(tr)


sim_holder = [None]

# (label, feature, keep-rule)  keep-rule(rows) -> bool
SINGLES = []
for thr in (0.25, 0.5, 0.75, 1.01):
    SINGLES.append((f"decay<{thr}", "decay", lambda r, t=thr: r["decay"] < t))
for thr in (-0.5, -0.25, 0.0, 0.25):
    SINGLES.append((f"asym<={thr}", "asym", lambda r, t=thr: r["asym"] <= t))
for thr in (0.25, 0.4, 0.55, 0.7):
    SINGLES.append((f"nest1h>{thr}", "nest1h", lambda r, t=thr: r["nest1h"] > t))
for thr in (0.5, 1.0, 2.0, 3.0, 5.0):
    SINGLES.append((f"age>{thr}d", "age", lambda r, t=thr: r["age"] > t))
for thr in (0.0, 0.5, 1.0, 2.0):
    SINGLES.append((f"live_r>{thr}", "live", lambda r, t=thr: r["live"] > t))
for thr in (2.0, 3.0, 4.0, 6.0):
    SINGLES.append((f"risk<{thr}", "risk", lambda r, t=thr: r["risk"] < t))
for h in range(0, 24, 3):
    SINGLES.append((f"hour!={h}", "hour", lambda r, t=h: r["hour"] != t))


def score(rows, per, keep):
    rs = [r["r"] for r in rows if keep(r)]
    if len(rs) < 20:
        return None
    return {"n": len(rs), "net": sum(rs) - per * len(rs),
            "wr": 100.0 * sum(1 for x in rs if x > 0) / len(rs),
            "pf": pf(rs), "dd": dd(rs), "tr": sum(rs) / len(rs)}


def main():
    print("=" * 100)
    print("  P14  SEARCH UNDER THE NEW BAR")
    print("=" * 100)
    print(f"  BAR:  IS net >= {BAR_IS:.0f}R   AND  OOS net > {BAR_OOS:.1f}R")
    print(f"        AND  IS trades <= {BAR_N}")
    print("  A shrunk book has a smaller M, which is why shrinking is the")
    print("  only route to a resolvable result at this sample size.\n")
    sim_holder[0] = build_module()
    D = {}
    for sc in ("is", "oos"):
        rows, per, n, bnet = build(sc)
        D[sc] = (rows, per, bnet, n)
        print(f"  [{sc}] PIN ok  n={n}  netNET={bnet:+.1f}R")

    # ---- singles ----
    res = []
    for lbl, feat, rule in SINGLES:
        a = score(D["is"][0], D["is"][1], rule)
        b = score(D["oos"][0], D["oos"][1], rule)
        if not a or not b:
            continue
        res.append((lbl, a, b))
    print(f"\n  {len(res)} single arms scored\n")
    print("=" * 100)
    print("  SINGLES THAT MEET THE BAR")
    print("=" * 100)
    print(f"  {'arm':<18} {'IS n':>5} {'IS net':>8} {'IS WR':>7} {'IS PF':>6} "
          f"{'IS DD':>7} | {'OOS n':>6} {'OOS net':>8} {'OOS WR':>7} {'OOS PF':>6}")
    hits = []
    for lbl, a, b in res:
        if a["net"] >= BAR_IS and b["net"] > BAR_OOS and a["n"] <= BAR_N:
            hits.append((lbl, a, b))
            print(f"  {lbl:<18} {a['n']:>5} {a['net']:>8.1f} {a['wr']:>6.1f}% "
                  f"{a['pf']:>6.2f} {a['dd']:>7.1f} | {b['n']:>6} {b['net']:>8.1f} "
                  f"{b['wr']:>6.1f}% {b['pf']:>6.2f}")
    if not hits:
        print("  (none)")
    print("\n  TOP 12 BY OOS NET, regardless of the bar:")
    for lbl, a, b in sorted(res, key=lambda z: -z[2]["net"])[:12]:
        ok = "BAR-OK" if (a["net"] >= BAR_IS and b["net"] > BAR_OOS
                          and a["n"] <= BAR_N) else ""
        print(f"  {lbl:<18} {a['n']:>5} {a['net']:>8.1f} {a['pf']:>6.2f} | "
              f"{b['n']:>6} {b['net']:>8.1f} {b['pf']:>6.2f}  {ok}")

    # ---- pairs of singles ----
    print("\n" + "=" * 100)
    print("  PAIRS  (every combination of singles, both eras, bar enforced)")
    print("=" * 100)
    phits = []
    for (l1, f1, r1), (l2, f2, r2) in combinations(SINGLES, 2):
        if f1 == f2:
            continue
        rule = lambda r, a=r1, b=r2: a(r) and b(r)
        a = score(D["is"][0], D["is"][1], rule)
        b = score(D["oos"][0], D["oos"][1], rule)
        if not a or not b:
            continue
        if a["net"] >= BAR_IS and b["net"] > BAR_OOS and a["n"] <= BAR_N:
            phits.append((f"{l1} + {l2}", a, b))
    phits.sort(key=lambda z: -(min(z[1]["net"] / BAR_IS,
                                   z[2]["net"] / BAR_OOS)))
    print(f"  {len(phits)} pairs meet the bar. Top 15 by worst-era ratio:\n")
    print(f"  {'pair':<40} {'IS n':>5} {'IS net':>8} {'IS PF':>6} {'IS DD':>7}"
          f" | {'OOS n':>6} {'OOS net':>8} {'OOS PF':>6}")
    for lbl, a, b in phits[:15]:
        print(f"  {lbl:<40} {a['n']:>5} {a['net']:>8.1f} {a['pf']:>6.2f} "
              f"{a['dd']:>7.1f} | {b['n']:>6} {b['net']:>8.1f} {b['pf']:>6.2f}")
    print("\n  CAUTION: this is a grid searched on the same two eras used to")
    print("  score it. Meeting the bar here is a CANDIDATE, not a result.")
    print("  Nothing here is adoptable until the forward slice at n>=50.")
    print("=" * 100)


if __name__ == "__main__":
    main()
