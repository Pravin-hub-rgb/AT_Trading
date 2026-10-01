"""INDEPENDENT REPLICATION of the sMZX sizing result on a DIFFERENT VENUE.

WHY THIS RUN EXISTS
===================
`SMZX_LEVERAGE_AUDIT.md` showed sMZX is real selection (4/4) rather than a
leverage trap, on Bybit. But Bybit IS and OOS are the exact slices this repo
has now inspected dozens of times, so that result is real but not yet
INDEPENDENT. The standing rule in this repo is that an arm must clear an
independent instrument before it can be called evidence.

This run re-runs the ENTIRE audit - flat book, flat-leverage control, sMZX
real, and the 50-draw size shuffle - on BINANCE PERP
(data/btc-fut, backfilled 2020-12-31 -> 2026-09-13), which is a different
venue, a different microstructure, and an instrument the sizing flags were
never fitted on. If the flags are selecting a real property of the tape,
the result must reproduce here. If it was a Bybit artefact, it dies.

WHAT IS COPIED AND WHAT IS NOT
==============================
Copied VERBATIM (a replication that re-tunes the thresholds is not a
replication):
  M2   cur_mag_atr >= 3.0
  ZC   vol7_prev7 <= 0.846
  X    parent risk_pct < 1.0
  sizing  1.5^count, r_multiple only (costs NOT scaled, as published)
  the flat-leverage control and the 50-draw shuffle
  the PASS rule: B beats A on net AND B is above the 90th percentile of the
  shuffle distribution, in every cell

NOT copied: the reference ledgers. Binance has its own trades, so there is
nothing to reproduce. The control here is instead INTERNAL - the flat book
must be non-degenerate (n >= 100, net != 0) or the cell is reported as
INSUFFICIENT rather than silently scored.

WHAT WONT BE CLAIMED EVEN IF IT PASSES
======================================
A pass here means "the flags select on a second venue too". It does NOT mean
the arm is adoptable. The known blockers are unchanged: the forward gate, and
the fact that `v18_streak_halt.py` has no size state at all, so a live size
change has no channel to execute through.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_smzx_binance_replication.json"
SIZE = 1.5
M2_MIN_ATR = 3.0
VOL7PREV_Q1 = 0.846
N_SHUFFLE = 50
SEED = 20260928
# Era windows are NOT hardcoded - they are derived from the bybit book at
# runtime (bybit_bounds) and then mirrored onto binance, so both venues are
# measured over identical market periods.
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))


def m_of(book, yrs):
    from exp_equity_quality import equity_quality
    return equity_quality(book, yrs)


def pct_rank(vals, x):
    return sum(1 for v in vals if v <= x) / max(1, len(vals))


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  sMZX INDEPENDENT REPLICATION - BINANCE PERP (data/btc-fut)",
          flush=True)
    print("=" * 100, flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import (load_binance, bybit_bounds,
                                               load_bybit)
    from test_experiments_craze import build_module
    from experiment_registry import BP, EXPERIMENTS
    import exp_smzx_leverage_audit as AUD

    sim = build_module()
    payload = {"stage": "smzx_binance_replication", "cells": {},
               "n_shuffle": N_SHUFFLE, "size": SIZE, "errors": []}
    rng = random.Random(SEED)

    # The binance 1m slice is ~119MB per era; holding both eras plus their
    # window tables in one process exhausted memory and the run died mid-OOS
    # with no traceback. So the scope is selectable and the two eras are run
    # as separate processes, each merging into the same JSON.
    import os
    want = (sys.argv[1].split(",") if len(sys.argv) > 1
            else os.environ.get("SMZX_SCOPE", "is,oos").split(","))
    if "--append" in sys.argv and OUT.exists():
        payload = json.loads(OUT.read_text(encoding="utf-8"))
        payload.setdefault("cells", {})
        payload.setdefault("errors", [])

    for scope in want:
        # Mirror the bybit era window EXACTLY onto binance. Deriving bounds
        # from the bybit book (rather than hardcoding) is what makes this a
        # replication rather than a look at whatever window binance has.
        byb = load_bybit(scope, sim)
        bounds = bybit_bounds(byb, scope)
        print(f"\n  [{scope}] bybit 15m bounds {bounds['15m']} "
              f"-> mirroring onto binance perp", flush=True)
        data = load_binance(scope, bounds)
        yrs = AUD.YEARS[scope]
        ctx, windows = AUD.build_ctx(data)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = sim_fn(sim, data, params)
            m0 = m_of(trades, yrs)
            if m0["n"] < 100:
                payload["errors"].append(f"thin book {scope}/{name}")
                print(f"  [SKIP] {scope}/{name}: n={m0['n']} < 100, "
                      f"INSUFFICIENT - not scored", flush=True)
                continue
            print(f"\n  [{scope}/{name}] binance flat: {m0['n']}t "
                  f"{m0['net']:+.1f}R DD {m0['max_dd']:.1f} "
                  f"calmar {m0.get('calmar', 0):.3f}", flush=True)
            cell = run_cell(AUD, sim_fn, trades, data, ctx, windows, m0,
                            yrs, rng, name, scope)
            payload["cells"][f"{scope}/{name}"] = cell
            report(cell, name, scope, fam=AUD.flag_keys(trades, data, ctx,
                                                        windows),
                   n=len(trades))
    cells = payload["cells"]
    payload["cells_passed"] = sum(1 for c in cells.values() if c["SELECTION"])
    payload["all_selection"] = (bool(cells) and not payload["errors"] and
                                 payload["cells_passed"] == len(cells))
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nREPLICATION: {payload['cells_passed']}/{len(cells)} cells "
          f"SELECTION")
    print(f"VERDICT: {'REPLICATED' if payload['all_selection'] else 'NOT REPLICATED'}")  # noqa: E501
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)")

def run_cell(AUD, sim_fn, trades, data, ctx, windows, m0, yrs, rng, name,
             scope):
    fam = AUD.flag_keys(trades, data, ctx, windows)
    real_m = AUD.mults_for(trades, fam)
    L = sum(real_m) / len(real_m)
    n_flag = sum(1 for m in real_m if m > 1.0)
    mB = m_of(AUD.apply_mults(trades, real_m), yrs)
    mA = m_of(AUD.apply_mults(trades, [L] * len(trades)), yrs)
    nets, dds = [], []
    for _ in range(N_SHUFFLE):
        sm = real_m[:]
        rng.shuffle(sm)
        mS = m_of(AUD.apply_mults(trades, sm), yrs)
        nets.append(mS["net"])
        dds.append(mS["max_dd"])
    pr = pct_rank(nets, mB["net"])
    cell = {
        "flat": {"n": m0["n"], "net": m0["net"], "max_dd": m0["max_dd"],
                 "calmar": m0.get("calmar")},
        "A_flat_leverage": {"L": round(L, 4), "net": mA["net"],
                            "max_dd": mA["max_dd"],
                            "calmar": mA.get("calmar"),
                            "d_net": round(mA["net"] - m0["net"], 1)},
        "B_smzx_real": {"n_flagged": n_flag,
                        "pct_flagged": round(100.0 * n_flag / len(trades), 1),
                        "net": mB["net"], "max_dd": mB["max_dd"],
                        "calmar": mB.get("calmar"),
                        "d_net": round(mB["net"] - m0["net"], 1)},
        "C_smzx_shuffled": {
            "mean_net": round(statistics.mean(nets), 1),
            "sd_net": round(statistics.pstdev(nets), 1),
            "min": round(min(nets), 1), "max": round(max(nets), 1),
            "mean_dd": round(statistics.mean(dds), 1),
            "B_percentile": round(100.0 * pr, 1),
            "n_shuffles_beating_B": sum(1 for v in nets if v >= mB["net"])},
    }
    cell["B_beats_A"] = mB["net"] > mA["net"]
    cell["B_above_p90"] = pr > 0.90
    cell["SELECTION"] = cell["B_beats_A"] and cell["B_above_p90"]
    cell["edge_over_shuffle"] = round(mB["net"] - statistics.mean(nets), 1)
    return cell


def report(cell, name, scope, fam, n):
    c = cell["C_smzx_shuffled"]
    print(f"    flags M2={len(fam['M2'])} ZC={len(fam['ZC'])} "
          f"X={len(fam['X'])}  sized {cell['B_smzx_real']['n_flagged']}/{n} "
          f"({cell['B_smzx_real']['pct_flagged']}%)", flush=True)
    print(f"    A flat lev L={cell['A_flat_leverage']['L']:.3f}  "
          f"net {cell['A_flat_leverage']['net']:+8.1f}  "
          f"DD {cell['A_flat_leverage']['max_dd']:>6.1f}  "
          f"calmar {cell['A_flat_leverage']['calmar']:.3f}", flush=True)
    print(f"    B sMZX REAL      net {cell['B_smzx_real']['net']:+8.1f}  "
          f"DD {cell['B_smzx_real']['max_dd']:>6.1f}  "
          f"calmar {cell['B_smzx_real']['calmar']:.3f}  "
          f"(dNet {cell['B_smzx_real']['d_net']:+.1f})", flush=True)
    print(f"    C SHUFFLED       net {c['mean_net']:+8.1f} "
          f"+-{c['sd_net']:.1f}  DD {c['mean_dd']:.1f}", flush=True)
    print(f"    >>> B at {c['B_percentile']}th pct; "
          f"{c['n_shuffles_beating_B']}/{N_SHUFFLE} shuffles beat it; edge "
          f"over mean {cell['edge_over_shuffle']:+.1f}R  => "
          f"{'SELECTION' if cell['SELECTION'] else 'LEVERAGE/DEAD'}", flush=True)


if __name__ == "__main__":
    main()


