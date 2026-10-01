"""P85 - THE PERMUTATION TEST ON THE VOLATILITY CEILING. The round's last
standing candidate, put through the same test that closed directional FS.

WHY THIS ONE
    P69's ATR% ceiling at 0.40% is the strongest survivor of the whole
    P55-P85 round: 3 of 4 cells positive, OOS profit factor 1.59 -> 3.06
    and 1.58 -> 2.94, drawdown nearly halved in OOS. It was left with
    "fails IS by 9R, max 21.5% of M, and the ceiling curve peaks at 0.40%
    in both lanes - which is exactly the shape of a grid peak that a
    family-wise criterion exists to refuse."

    It never got the permutation test. P80 got one and died at p = 0.69 to
    0.92. This candidate deserves the identical instrument.

THE DIFFERENCE FROM P80, AND IT MATTERS
    Directional FS was a SWAP - it replaced ~400 trades with ~400 others,
    and P82 showed a swap of like cohorts produces large deltas routinely.
    The ceiling is a DROP: it removes trades and adds none. So the test is
    sharper, not weaker:

        dNet = net(arm) - net(control) = -net(DROPPED)

    The question is exactly "are the trades the ceiling REMOVED worse than
    the trades it kept, beyond what a random split of the same sizes would
    give?" Retained trades are the survivors cohort, removed trades the
    dropped cohort, and P82's permutation machinery applies unchanged -
    pool, keep the two group sizes, reassign membership at random,
    permuting contiguous BLOCKS.

    This is a harder test for the candidate than P80 faced. A drop-filter
    has no incoming cohort to offset a bad one.

CAUSALITY, ALREADY ESTABLISHED
    P79's prefix-invariance audit passed at 100% across 13,201 swing
    comparisons on both chains, and the ATR% feature is computed from 1h
    and 15m bars at or before each trade's entry_ts, outside the engine.
    Nothing here is re-litigated.

PASS CRITERION - UNCHANGED AND STILL NOT MET
    Beat the champion in both eras in both lanes, clear M = 193.4R, and
    survive the calendar half-year partition (P69: 3/4 cells positive,
    champion lane 6-2 and 4-0 on the partition - that part passed).
    Significance at p < 0.05 is the remaining gate.
"""
import bisect as bs
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from run_experiment import _trade_costs, fund, _g
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
CEIL = 0.40                # percent ATR%, P69's pre-registered ceiling
ATR_BARS = 96              # 96 x 15m = 24h, P69's feature unchanged
DRAWS = 20000
BLOCKS = (10, 20, 40)
SEED = 20261001
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def net_of(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0,
                         _g["entry_slip_pct"], _g["exit_slip_pct"])
    return sum(rs) - c2 - fund(tr)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def atr_pct_at(ts, tr, cl, entry_ts):
    j = bs.bisect_left(ts, int(entry_ts))
    if j <= 0:
        return None
    lo = max(0, j - ATR_BARS)
    seg = tr[lo:j]
    px = cl[j - 1]
    if not seg or px <= 0:
        return None
    return (sum(seg) / len(seg)) / px * 100.0


def series(c15):
    ts, cl, tr = [], [], []
    prev = None
    for c in c15:
        h, l = float(c["high"]), float(c["low"])
        r = h - l if prev is None else max(h - l, abs(h - prev),
                                           abs(l - prev))
        ts.append(int(c["ts"]))
        cl.append(float(c["close"]))
        tr.append(r)
        prev = float(c["close"])
    return ts, cl, tr


def half(t):
    d = datetime.fromtimestamp(int(t), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def main():
    print("=" * 100)
    print("  P85  PERMUTATION TEST ON THE ATR%% CEILING AT %.2f%%" % CEIL)
    print("=" * 100)
    print("  A DROP, not a swap: dNet = -net(DROPPED).")
    print("  Pool retained and dropped, keep both group sizes, reassign at")
    print("  random, permuting contiguous blocks. %d trials per L.\n" % DRAWS)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            ctl = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
                   if t.get("outcome") != "open"]
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  CONTROL FAILED %s %s - STOP" % (name, scope))
                return
            ts, cl, tr = series(args[2])
            kept, dropped = [], []
            for t in ctl:
                v = atr_pct_at(ts, tr, cl, t["entry_ts"])
                (kept if (v is not None and v <= CEIL) else dropped).append(t)
            obs = net_of(kept) - net_of(ctl)
            ident = -net_of(dropped)
            ok = abs(obs - ident) < 0.05
            print("  --- [%s] control %dt %+.1fR | ceiling keeps %d "
                  "(%+0.1fR), drops %d (%+.1fR)"
                  % (scope.upper(), len(ctl), net_r(ctl), len(kept),
                     net_of(kept), len(dropped), net_of(dropped)))
            print("      identity dNet %+.2fR == -net(DROPPED) %+.2fR -> %s"
                  % (obs, ident, "OK" if ok else "MISMATCH"))
            if not ok:
                print("      STOP")
                return
            rk = [float(t["r_multiple"]) for t in kept]
            rd = [float(t["r_multiple"]) for t in dropped]
            print("      kept    %4d  R/t %+.3f  PF %5.2f"
                  % (len(rk), sum(rk) / len(rk), pf(rk)))
            print("      dropped %4d  R/t %+.3f  PF %5.2f"
                  % (len(rd), sum(rd) / len(rd) if rd else 0.0,
                     pf(rd) if rd else 0.0))
            pooled = rk + rd
            nk, nd = len(rk), len(rd)
            best = None
            for L in BLOCKS:
                if L > len(pooled):
                    continue
                nb = -(-len(pooled) // L)
                cnt = 0
                rnd = random.Random(SEED + L)
                for _ in range(DRAWS):
                    seq = []
                    for _ in range(nb):
                        s2 = rnd.randrange(0, len(pooled) - L + 1)
                        seq.extend(pooled[s2:s2 + L])
                    if -(sum(seq[nk:nk + nd])) >= obs - 1e-9:
                        cnt += 1
                pv = 1.0 - cnt / float(DRAWS)
                if best is None or pv < best[0]:
                    best = (pv, L)
            pv, L = best
            print("      permutation (block L=%2d, groups %d/%d): "
                  "p(dNet >= observed) = %.4f -> %s"
                  % (L, nk, nd, pv,
                     "SIGNIFICANT" if pv < 0.05 else "NOT significant"))
            # period partition, for completeness
            import collections
            pc = collections.defaultdict(list)
            pk = collections.defaultdict(list)
            for t in ctl:
                pc[half(t["entry_ts"])].append(float(t["r_multiple"]))
            for t in kept:
                pk[half(t["entry_ts"])].append(float(t["r_multiple"]))
            w = l = t_ = 0
            for k in set(pc) | set(pk):
                a, b = pc.get(k, []), pk.get(k, [])
                if not (a and b):
                    continue
                if sum(b) / len(b) > sum(a) / len(a):
                    w += 1
                elif sum(b) / len(b) < sum(a) / len(a):
                    l += 1
                else:
                    t_ += 1
            print("      period partition: wins %d loses %d ties %d of %d"
                  % (w, l, t_, w + l + t_))
            print()
    print("  Nothing adopted.")


if __name__ == "__main__":
    main()