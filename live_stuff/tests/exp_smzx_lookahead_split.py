"""WHICH FLAG CARRIES THE sMZX EFFECT? (the look-ahead decomposition)

THE PROBLEM
===========
`sMZX` = 1.5^count(M2, ZC, X). I audited it (SMZX_LEVERAGE_AUDIT) and called
it SELECTION 4/4 because the real flags beat 49-50 of 50 random size
reassignments. That test is the matched-count random null this repo demands
before any sizing dNet is quoted - but it CANNOT separate SKILL from
LOOK-AHEAD. A feature that encodes future outcome also beats a random null.

AND M2 IS KNOWN TO ENCODE THE FUTURE. `cur_mag_atr = |seg.end_px -
seg.start_px| / atr15` uses the swing segment's END price, and
`backend_check_wd_days.py:108` asserts `fs_at_idx >= seg.end_idx` - the
swing's FS/SUS confirmation lands at or AFTER the end bar. The entry fires at
B2/flip, i.e. BEFORE the swing ends, so `end_px` does not exist at decision
time. CAPITAL_STAGE_PLAN records that a send-time replacement reproduces the
backtest flag on only 77.5% of trades (bar: 95%), fires on 0-6 trades out of
76-500, and concludes: "A send-time replacement for M2 was searched for and
does not exist" / "none of them is deployable as measured".

So the open question is narrow and answerable: how much of the effect is
M2's forward-looking geometry, and how much survives in the two flags that
are computed from closed bars at the cutoff (ZC from vol7_prev7, X from the
parent window's already-realised risk)?

THE TEST
========
Per family, alone: M2 / ZC / X, and the pair M2-free (ZC+X). Each gets the
same audit: flat book, flat-leverage control, real arm, 50-draw shuffle with
the arm's OWN multiplier multiset. Reported on bybit (the venue where the
original 4/4 was claimed) for champion and utcsat, IS and OOS.

READING IT
==========
  - If M2-alone carries the bulk of the dNet and M2-free does not, then my
    earlier SELECTION verdict was substantially a look-ahead detector and
    must be withdrawn.
  - If ZC/X alone still beat their own shuffle, there is a genuine,
    live-computable residue worth keeping - and that residue, not sMZX, is
    the thing that could ever be deployed.

Nothing here is adopted. The point is to correctly attribute a published
number before anyone builds on it.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_smzx_lookahead_decomposition.json"
SIZE = 1.5
N_SHUFFLE = 50
SEED = 20260928
ARMS = {
    "M2 only": ("M2",),
    "ZC only": ("ZC",),
    "X only": ("X",),
    "M2-free ZC+X": ("ZC", "X"),
    "all M2+ZC+X": ("M2", "ZC", "X"),
}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
YEARS = {"is": 3.67, "oos": 2.0}

def m_of(book, yrs):
    from exp_equity_quality import equity_quality
    return equity_quality(book, yrs)


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  sMZX LOOK-AHEAD SPLIT - how much of the effect is M2's future?",
          flush=True)
    print("=" * 100, flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_sizing_combo import load_scope
    from test_experiments_craze import build_module
    from experiment_registry import BP, EXPERIMENTS
    import exp_smzx_leverage_audit as AUD

    sim = build_module()
    payload = {"stage": "smzx_lookahead_split", "arms": {}, "errors": []}
    rng = random.Random(SEED)
    for scope in ("is", "oos"):
        data = load_scope(scope)
        yrs = YEARS[scope]
        ctx, windows = AUD.build_ctx(data)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = sim_fn(sim, data, params)
            m0 = m_of(trades, yrs)
            fam = AUD.flag_keys(trades, data, ctx, windows)
            print(f"\n  [{scope}/{name}] flat {m0['n']}t {m0['net']:+.1f}R "
                  f"DD {m0['max_dd']:.1f}", flush=True)
            for arm, fams in ARMS.items():
                mults = mults_subset(trades, fam, fams)
                L = sum(mults) / len(mults)
                n_flag = sum(1 for m in mults if m > 1.0)
                mB = m_of(AUD.apply_mults(trades, mults), yrs)
                mA = m_of(AUD.apply_mults(trades, [L] * len(trades)), yrs)
                nets = []
                for _ in range(N_SHUFFLE):
                    sm = mults[:]
                    rng.shuffle(sm)
                    nets.append(m_of(AUD.apply_mults(trades, sm), yrs)["net"])
                pr = sum(1 for v in nets if v <= mB["net"]) / len(nets)
                beats = sum(1 for v in nets if v >= mB["net"])
                rec = {"n_flagged": n_flag,
                       "pct_flagged": round(100.0 * n_flag / len(trades), 1),
                       "d_net": round(mB["net"] - m0["net"], 1),
                       "A_d_net": round(mA["net"] - m0["net"], 1),
                       "d_dd": round(m0["max_dd"] - mB["max_dd"], 1),
                       "shuffle_mean": round(statistics.mean(nets), 1),
                       "B_percentile": round(100.0 * pr, 1),
                       "shuffles_beating_B": beats,
                       "edge_over_shuffle": round(
                           mB["net"] - statistics.mean(nets), 1)}
                rec["SELECTION"] = (mB["net"] > mA["net"] and pr > 0.90)
                payload["arms"][f"{scope}/{name}/{arm}"] = rec
                print(f"    {arm:<14} sized {n_flag:>3} "
                      f"({rec['pct_flagged']:>4.1f}%)  dNet "
                      f"{rec['d_net']:+7.1f} (vs flat-lev {rec['A_d_net']:+7.1f})"
                      f"  dDD {rec['d_dd']:+6.1f}  pct "
                      f"{rec['B_percentile']:>5.1f}  "
                      f"{beats}/{N_SHUFFLE} beat  "
                      f"{'SELECTION' if rec['SELECTION'] else 'null'}", flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


def mults_subset(trades, fam, fams):
    out = []
    for t in trades:
        k = (int(t["entry_ts"]), int(t["exit_ts"]))
        c = sum(1 for f in fams if k in fam[f])
        out.append(SIZE ** c if c else 1.0)
    return out


if __name__ == "__main__":
    main()

