"""Study 1 — Why does path-true always kill what descriptively works?

Decompose the actual R delta of a CLOSED filter family into:
  dR_direct   = R the gate would have kept if the chain had not shifted
  dR_chain    = everything else (entries that appear/disappear because the
                 blocked entry freed a slot, cooldown moved, halt counter moved)

Read-only, Bybit only, test-only. No production change.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope

OUT = ROOT / "backtest/tests/_thesis_chain_decomposition.json"
LANES = ("champion_multi_sw10", "utcsat_multi_sw10", "fullstack_wage10_cd0_single_sw10")

# Closed families, each with the exact engine flag used to run it path-true.
FAMILIES = {
    "weekly_acceptance": ("exp_weekly_state_action",
                          {"skip_back_inside": "skip_back_inside",
                           "accepted_now_only": "accepted_now_only"}),
    "wage_gate": ("exp_wage_h", {"6": 6, "10": 10, "12": 12, "24": 24}),
    "loss_triggered_window_kill": ("exp_window_win_kill_n",
                                   {"n2_soft": {"exp_window_win_kill_n": 2,
                                                "exp_window_win_kill_action": "soft",
                                                "exp_window_win_kill_scope": "window"},
                                    "n3_soft": {"exp_window_win_kill_n": 3,
                                                "exp_window_win_kill_action": "soft",
                                                "exp_window_win_kill_scope": "window"},
                                    "n3_hard": {"exp_window_win_kill_n": 3,
                                                "exp_window_win_kill_action": "hard",
                                                "exp_window_win_kill_scope": "window"}}),
    "htf_window_budget": ("exp_window_entry_cap", {"cap1": 1, "cap2": 2, "cap3": 3}),
}


def key(t):
    return (int(t["entry_idx"]), 1 if t.get("dir") == "long" else -1)


def r_of(t):
    return float(t.get("r_multiple") or 0.0)


def decompose(base, cand):
    """Split dNet into what the gate removed vs what the chain shift changed.

    dR_direct  = -R(removed entries)          what the gate took away
    dR_added   = +R(entries that appeared)    pure chain-shift gain
    dR_common  = R changed on COMMON entries only
    dR_total   = dR_direct + dR_added + dR_common   (exact, by construction)
    """
    b = {key(t): t for t in base}
    c = {key(t): t for t in cand}
    removed = [b[k] for k in (set(b) - set(c))]
    added = [c[k] for k in (set(c) - set(b))]
    common = set(b) & set(c)
    d_direct = -sum(r_of(t) for t in removed)
    d_added = sum(r_of(t) for t in added)
    d_common = sum(r_of(c[k]) - r_of(b[k]) for k in common)
    total = sum(r_of(t) for t in cand) - sum(r_of(t) for t in base)
    return {
        "removed_n": len(removed), "removed_r": round(-d_direct, 4),
        "removed_avg": round(sum(r_of(t) for t in removed) / len(removed), 4) if removed else None,
        "removed_runners3": sum(r_of(t) >= 3 for t in removed),
        "added_n": len(added), "added_r": round(d_added, 4),
        "added_avg": round(sum(r_of(t) for t in added) / len(added), 4) if added else None,
        "common_entries": len(common),
        "dR_direct": round(d_direct, 4),
        "dR_added_chain": round(d_added, 4),
        "dR_common_rerisked": round(d_common, 4),
        "dR_total_gross": round(total, 4),
        "identity_check": round(d_direct + d_added + d_common - total, 6),
    }


def verdict(row, base_net, cand_net):
    """Decision table from the study plan."""
    d_direct = row["dR_direct"]
    d_chain = row["dR_added_chain"] + row["dR_common_rerisked"]
    d_net = cand_net - base_net
    if d_direct > 0 and abs(d_chain) < 0.25 * abs(d_direct):
        cls = "filter_is_real_low_cascade"
        act = "candidate (cascade is small)"
    elif d_direct > 0 and d_chain < -0.25 * abs(d_direct):
        cls = "filter_real_but_cascades_hard"
        act = "candidate only if chain-aware re-test is cheap"
    elif abs(d_direct) < 0.15 * abs(d_net or 1) and d_chain < 0:
        cls = "cohort_was_illusory"
        act = "CLOSE family permanently"
    elif d_direct < 0:
        cls = "removed_bucket_already_negative"
        act = "CLOSE family permanently"
    else:
        cls = "inconclusive"
        act = "needs more data"
    return {"class": cls, "action": act, "dNet": round(d_net, 4),
            "dR_direct": round(d_direct, 4), "dR_chain": round(d_chain, 4)}


def run_scope(scope, sim):
    started = time.time()
    data = load_scope(scope)
    result = {"study": 1, "name": "chain decomposition of closed filter families",
              "instrument": "BTCUSDT_BYBIT", "scope": scope, "lanes": {}}
    for lane in LANES:
        params = {**BP, **EXPERIMENTS[lane]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        base_out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                       fine_ltf=data["fine"], **params)
        base = base_out["ltf_trades"]
        base_net = sum(net_r([t]) for t in base)
        base_gross = sum(r_of(t) for t in base)
        lane_row = {"baseline": {"n": len(base), "gross": round(base_gross, 4),
                                 "net": round(base_net, 4)},
                    "families": {}}
        for fam, (flag, arms) in FAMILIES.items():
            lane_row["families"][fam] = {}
            for arm, spec in arms.items():
                p = {**params}
                if isinstance(spec, dict):
                    p.update(spec)
                else:
                    p[flag] = spec
                out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                          fine_ltf=data["fine"], **p)
                trades = out["ltf_trades"]
                cand_net = sum(net_r([t]) for t in trades)
                dec = decompose(base, trades)
                v = verdict(dec, base_net, cand_net)
                lane_row["families"][fam][arm] = {
                    "n": len(trades),
                    "gross": round(sum(r_of(t) for t in trades), 4),
                    "net": round(cand_net, 4),
                    "decomposition": dec, "verdict": v,
                }
                print(f"  {scope.upper():3} {lane:32} {fam:26} {arm:18} "
                      f"dNet={v['dNet']:+8.1f} dDirect={v['dR_direct']:+8.1f} "
                      f"dChain={v['dR_chain']:+8.1f} rem={dec['removed_n']:3d}"
                      f"/{dec['removed_r']:+7.1f} add={dec['added_n']:3d} "
                      f"id={dec['identity_check']:+.4f} | {v['class']}", flush=True)
        result["lanes"][lane] = lane_row
    result["elapsed_sec"] = round(time.time() - started, 1)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = ap.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    sim = build_module()
    allr = {"study": 1, "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 145, flush=True)
        print(f"  STUDY 1 — CHAIN DECOMPOSITION OF CLOSED FAMILIES — BYBIT {scope.upper()}", flush=True)
        print("=" * 145, flush=True)
        allr["scopes"][scope] = run_scope(scope, sim)
    OUT.write_text(json.dumps(allr, indent=2), encoding="utf-8")
    print(f"\n  wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
