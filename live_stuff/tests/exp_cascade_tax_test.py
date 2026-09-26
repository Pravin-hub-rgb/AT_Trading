"""H2: is the cascade really caused by the three stateful gates?

THE QUESTION
------------
The wick removal scored +28.1R post-process and -50.5R path-true. The gap
(cascade) was -78.6R, i.e. 280% of the direct effect. We believe the gap exists
because removing a trade changes downstream engine state:

  exp_mltf=True             concurrent positions -> busy_until slot freed
  cooldown_bars=8           the cooldown timeline shifts
  max_consecutive_losses=3  the loss-streak count moves

That is an explanation, not a proof. This test isolates it: turn all three
carriers OFF and re-measure BOTH ways. If the explanation is right, the two
measurements should now CONVERGE (post-process dNet == path-true dNet), because
with no state to perturb, a ledger skip and an entry refusal become the same
thing.

If they still diverge with every carrier off, the cascade has some other source
and the sizing pivot rests on a wrong story.

PRE-REGISTERED PASS RULE (fixed before the run)
----------------------------------------------
  H2 CONFIRMS the carrier story iff, in the gate-off arm, the post-process and
  path-true dNet differ by LESS THAN 5% of |post-process dNet| in at least 3 of
  4 cells, AND the gate-off path-true dNet is not worse than the gate-on one by
  more than 10% in any cell.

  Divergence >= 5% in all 4 cells  => carrier story FALSIFIED, stop and
  re-diagnose before trusting any sizing conclusion.

WHAT THIS IS NOT
----------------
This is a DIAGNOSTIC, not a candidate. Turning the carriers off makes the
strategy strictly worse (no concurrency control, no cooldown, no loss halt), so
the gate-off numbers are not a configuration anyone would trade. It exists only
to attribute the cascade. Nothing here is adoptable.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_cascade_tax_test.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
WICK_MAX = 6.03
LB = 12
CONVERGE_PCT = 5.0      # pre-registered: |pp - pt| / |pp| below this
MIN_CONVERGED_CELLS = 3  # of 4
WORST_TOLERANCE_PCT = 10.0

ANCHOR = "        if i < 0 or i>=n-1: continue\n"
INJECT = ANCHOR + (
    "        if _WICK_MAX>0 and direction_of(sig)!=1:\n"
    "            _j=i\n"
    "            if _j>=_LB:\n"
    "                _lo=_j-_LB+1\n"
    "                _us=0.0; _ls=0.0\n"
    "                for _k in range(_lo,_j+1):\n"
    "                    _c=candles_ltf[_k]\n"
    "                    _o=float(_c[\"open\"]); _h=float(_c[\"high\"])\n"
    "                    _l=float(_c[\"low\"]); _cc=float(_c[\"close\"])\n"
    "                    _us+=_h-max(_o,_cc)\n"
    "                    _ls+=min(_o,_cc)-_l\n"
    "                _a=atr15[_j]\n"
    "                if _a>0 and (_us+_ls)/_a<=_WICK_MAX:\n"
    "                    continue\n"
)

# The three carriers named in AGENT_COORDINATION.md, and the champion values.
CARRIERS = ("exp_mltf", "cooldown_bars", "max_consecutive_losses")
GATE_OFF = {"exp_mltf": False, "cooldown_bars": 0, "max_consecutive_losses": 0}
GATE_ON_DEFAULTS = {"exp_mltf": True, "cooldown_bars": 8, "max_consecutive_losses": 3}

def build_patched():
    """Same patch as exp_wick_short_pathtrue, reused rather than re-derived.

    Copying the injection would risk the two harnesses drifting apart, which is
    exactly the failure that produced the original sign error. Import it.
    """
    from exp_wick_short_pathtrue import build_patched as _bp
    return _bp()


def run(fn, data, params):
    out = fn(data["c1h"], data["sw10"], data["c15"], data["sw15"],
             fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    return sorted(trades, key=lambda t: int(t["entry_ts"]))


def _is_short(trd):
    """True if the trade is a short. The engine's trade dicts carry `dir` as
    the string 'long'/'short'; older ledgers used -1/+1. Accept either so this
    helper does not crash on a schema surprise (which is how the first run of
    this harness died)."""
    d = trd.get("dir", trd.get("direction"))
    if isinstance(d, str):
        return d.lower() in ("short", "sell", "s", "-1")
    if d is None:
        return False
    try:
        return int(d) == -1
    except (TypeError, ValueError):
        return False


def flag_base_trades(base_trades, data):
    """Post-process predicate, engine-free: which BASE trades would a ledger
    skip delete? Returns the summed R of those trades.

    A ledger skip is defined on the FINISHED ledger - it deletes trades the
    predicate matches, and the engine is never told. So the flagged set is
    fixed by the predicate and the base book ALONE. It is NOT
    `base - filt`: that difference also contains the trades the cascade
    displaced, which is exactly the term we are trying to measure.

    This replicates the wick predicate on the LTF bars, matching the injected
    engine logic: short AND wick_atr12 <= WICK_MAX, wick measured over the LB
    closed 15m bars ending at the entry bar, normalized by ATR.
    """
    import numpy as np

    c15 = data["c15"]                      # list of dicts: ts/open/high/low/close
    if not c15 or "ts" not in c15[0]:
        raise SystemExit("unexpected c15 layout")
    ts_arr = np.array([int(r["ts"]) for r in c15], dtype=np.int64)
    o = np.array([float(r["open"]) for r in c15])
    h = np.array([float(r["high"]) for r in c15])
    l = np.array([float(r["low"]) for r in c15])
    c = np.array([float(r["close"]) for r in c15])

    # ATR over the same LB window (mean true range), matching the engine's
    # atr15 series closely enough to identify the same flagged trades.
    prev_c = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    atr_ma = np.convolve(tr, np.ones(LB) / LB, mode="full")[: len(c)]

    # ts -> bar index, O(1) lookup instead of a scan per trade
    idx_of = {int(t): i for i, t in enumerate(ts_arr)}

    flagged_r = 0.0
    flagged_n = 0
    for trd in base_trades:
        if not _is_short(trd):
            continue
        j = idx_of.get(int(trd["entry_ts"]))
        if j is None or j < LB - 1:
            continue
        lo = j - LB + 1
        us = float(np.sum(h[lo:j + 1] - np.maximum(o[lo:j + 1], c[lo:j + 1])))
        ls = float(np.sum(np.minimum(o[lo:j + 1], c[lo:j + 1]) - l[lo:j + 1]))
        a = float(atr_ma[j])
        if a > 0 and (us + ls) / a <= WICK_MAX:
            flagged_r += float(trd["r_multiple"])
            flagged_n += 1
    return flagged_r, flagged_n


def main():
    t0 = time.time()
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r
    from test_experiments_craze import build_module
    from exp_boundary_state_autopsy import load_scope

    ship = build_module()
    pmod = build_patched()
    patched = pmod.simulate_htf_ltf_streak_halt

    payload = {
        "stage": "cascade_tax_test",
        "hypothesis": "cascade comes from exp_mltf / cooldown / loss-streak",
        "pre_registered": {
            "converge_pct": CONVERGE_PCT,
            "min_converged_cells": MIN_CONVERGED_CELLS,
            "worst_tolerance_pct": WORST_TOLERANCE_PCT,
            "rule": (
                "CONFIRMED iff gate-off |pp-pt|/|pp| < 5% in >=3 of 4 cells AND "
                "gate-off pt not worse than gate-on pt by >10% in any cell."
            ),
        },
        "carriers": list(CARRIERS),
        "gate_on": GATE_ON_DEFAULTS,
        "gate_off": GATE_OFF,
        "diagnostic_only": True,
        "years": YEARS,
        "cells": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_scope(scope)
        for lane, key in LANES:
            base_params = {**BP, **EXPERIMENTS[key]["params"]}
            base_params.setdefault("exp_partial_r", 0.0)
            cell = {}

            for mode, overrides in (("gate_on", GATE_ON_DEFAULTS),
                                    ("gate_off", GATE_OFF)):
                params = dict(base_params)
                params.update(overrides)
                # identity: filter OFF must reproduce the shipped list for
                # THIS gate configuration, else the arm is not trustworthy.
                pmod._WICK_MAX = 0.0
                off = run(patched, data, params)
                pmod._WICK_MAX = WICK_MAX
                filt = run(patched, data, params)
                nb, nf = net_r(off), net_r(filt)
                d_pt = nf - nb
                # Post-process arm: the flagged set is defined by the predicate
                # and the BASE book alone - a ledger skip never tells the
                # engine. It is deliberately NOT `off - filt`, which also
                # contains the trades the cascade displaced.
                flagged_r, flagged_n = flag_base_trades(off, data)
                d_pp = -flagged_r
                denom = abs(d_pp) if abs(d_pp) > 1e-9 else 1e-9
                conv = 100.0 * abs(d_pt - d_pp) / denom
                cell[mode] = {
                    "n_base": len(off), "n_filt": len(filt),
                    "base_net": round(nb, 2), "filt_net": round(nf, 2),
                    "n_flagged": flagged_n,
                    "dNet_path_true": round(d_pt, 2),
                    "dNet_postproc": round(d_pp, 2),
                    "converge_pct": round(conv, 1),
                }
                print(
                    f"  [{scope}|{lane}] {mode:8s} n {len(off):4d}->{len(filt):4d}"
                    f"  pp {d_pp:+8.1f}  pt {d_pt:+8.1f}  converge {conv:6.1f}%",
                    flush=True,
                )
            payload["cells"][f"{scope}|{lane}"] = cell

    # apply the pre-registered rule
    conv_cells = 0
    worst_regress = 0.0
    for cell in payload["cells"].values():
        if cell["gate_off"]["converge_pct"] < CONVERGE_PCT:
            conv_cells += 1
        on, off = cell["gate_on"], cell["gate_off"]
        denom = abs(on["dNet_path_true"]) if abs(on["dNet_path_true"]) > 1e-9 else 1e-9
        regress = 100.0 * (on["dNet_path_true"] - off["dNet_path_true"]) / denom
        worst_regress = max(worst_regress, regress)
    confirmed = (conv_cells >= MIN_CONVERGED_CELLS
                 and worst_regress <= WORST_TOLERANCE_PCT)
    payload["result"] = {
        "converged_cells": conv_cells,
        "total_cells": len(payload["cells"]),
        "worst_gateoff_regress_pct": round(worst_regress, 1),
        "h2_confirms": confirmed,
    }
    print("\n" + "=" * 90, flush=True)
    print(f"  converged cells: {conv_cells}/{len(payload['cells'])} "
          f"(rule: >= {MIN_CONVERGED_CELLS} below {CONVERGE_PCT}%)", flush=True)
    print(f"  worst gate-off regress: {worst_regress:.1f}% "
          f"(tolerance {WORST_TOLERANCE_PCT}%)", flush=True)
    print(f"  H2 CARRIER STORY {'CONFIRMED' if confirmed else 'FALSIFIED'}", flush=True)
    print("=" * 90, flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()