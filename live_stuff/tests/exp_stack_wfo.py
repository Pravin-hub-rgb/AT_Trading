"""Stage L — WFO replication of the Stage-B arm set (chronological expanding).

Question: is the Stage-B stack pick (half+delay1+skipD) an artifact of
full-sample selection? Re-PICK the best arm on each TRAIN prefix (strictly
past data only), freeze for the test year.

Timeline (all data chronological): 2021-2026.
  OOS scope covers 2021-22, IS scope covers 2023-26; both run fully, ledgers
  merged by entry_ts (era boundary state reset identical for every arm).
  S1 train 2021      -> test 2023
  S2 train 2021-23   -> test 2024
  S3 train 2021-24   -> test 2025
  S4 train 2021-25   -> test 2026
Arms: the 8 Stage-B multi arms on champion base (frozen).
Comparators on same test windows: fixed Stage-B pick (half+delay1+skipD),
fixed baseline.
Caveat: within-scope full-period runs carry halt/streak state across year
boundaries (identical for all arms; era boundary resets for all arms).

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_stack_wfo.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality

OUT = ROOT / "live_stuff/tests/_stack_wfo_results.json"

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
REG10 = dict(exp_regime_skip=10.0)

ARMS = (
    ("baseline", {}),
    ("half+delay1", dict(HALF)),
    ("skip_decisive", dict(SKIPD)),
    ("regime10", dict(REG10)),
    ("half+delay1+skipD", {**HALF, **SKIPD}),
    ("half+delay1+reg10", {**HALF, **REG10}),
    ("skipD+reg10", {**SKIPD, **REG10}),
    ("all_three", {**HALF, **SKIPD, **REG10}),
)

STAGE_B_PICK = "half+delay1+skipD"
STEPS = [
    ("S1", 2023, "2021-2022"),
    ("S2", 2024, "2021-2023"),
    ("S3", 2025, "2021-2024"),
    ("S4", 2026, "2021-2025"),
]


def ts_of(datestr):
    return int(datetime.strptime(datestr, "%Y-%m-%d")
               .replace(tzinfo=timezone.utc).timestamp())


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {
            "c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
        }
    data = get_data()
    identity_gate(data, build_module())
    return data


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE L — CHRONOLOGICAL EXPANDING WFO ON STAGE-B ARMS (2021->2026)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    cfg = EXPERIMENTS["champion_multi_sw10"]
    params = {**BP, **cfg["params"]}
    params.setdefault("exp_partial_r", 0.0)

    ledgers = {}
    trades_by = {}
    for scope in ("oos", "is"):
        data = load_scope(scope)
        for name, flags in ARMS:
            tr = run(sim, data, params, **flags)
            ledgers.setdefault(name, []).extend(
                (int(t["entry_ts"]), net_r([t]), str(t.get("exit_date") or "")[:4]) for t in tr)
            trades_by.setdefault(name, []).extend(tr)
    for name in ledgers:
        ledgers[name].sort(key=lambda x: x[0])

    print("\narm full-2021..2026 NETs:", flush=True)
    for name, _ in ARMS:
        print(f"  {name:<20} {sum(r for _, r, _ in ledgers[name]):+8.1f} "
              f"n={len(ledgers[name])}", flush=True)

    def slice_trades(name, a_ts, b_ts):
        return [t for t in trades_by[name] if a_ts <= int(t["entry_ts"]) < b_ts]

    print(f"\n  {'step':<4} {'test yr':<8} {'train':<14} {'chosen':<20} "
          f"{'trainNET':>9} {'testNET':>9} {'stageB':>8} {'baseline':>9}", flush=True)

    wf_rows = []
    wf_path = {"chosen": [], "stageb": [], "baseline": []}
    for step, yr, train_lbl in STEPS:
        a = ts_of(f"{yr}-01-01")
        b = ts_of(f"{yr + 1}-01-01") if yr < 2026 else ts_of("2027-01-01")
        train_end = a
        best, best_net = None, -1e18
        for name, _ in ARMS:
            tn = sum(r for ts, r, _ in ledgers[name] if ts < train_end)
            if tn > best_net:
                best, best_net = name, tn
        t_ch = sum(r for ts, r, _ in ledgers[STAGE_B_PICK] if a <= ts < b)
        t_bl = sum(r for ts, r, _ in ledgers["baseline"] if a <= ts < b)
        t_best = sum(r for ts, r, _ in ledgers[best] if a <= ts < b)
        wf_path["chosen"].extend(slice_trades(best, a, b))
        wf_path["stageb"].extend(slice_trades(STAGE_B_PICK, a, b))
        wf_path["baseline"].extend(slice_trades("baseline", a, b))
        wf_rows.append(dict(step=step, test_year=yr, train=train_lbl,
                            chosen=best, train_net=round(best_net, 1),
                            test_net=round(t_best, 1), stageb=round(t_ch, 1),
                            baseline=round(t_bl, 1)))
        print(f"  {step:<4} {yr:<8} {train_lbl:<14} {best:<20} "
              f"{best_net:>+9.1f} {t_best:>+9.1f} {t_ch:>+8.1f} {t_bl:>+9.1f}",
              flush=True)

    sums = {k: round(sum(net_r([t]) for t in v), 1) for k, v in wf_path.items()}
    print("-" * 100, flush=True)
    print(f"  concatenated test-path NET: WFO-chosen {sums['chosen']:+.1f} | "
          f"fixed Stage-B pick {sums['stageb']:+.1f} | baseline {sums['baseline']:+.1f}",
          flush=True)

    print("\n  concatenated path equity quality (years=5.0):", flush=True)
    path_stats = {}
    for k, v in wf_path.items():
        m = equity_quality(v, 5.0)
        path_stats[k] = m
        print(f"    {k:<10} n={m['n']:>4} net={m.get('net', 0):+8.1f} "
              f"DD={m.get('max_dd', 0):6.1f} ulcer={m.get('ulcer', 0):7.2f} "
              f"calmar={m.get('calmar', 0):6.3f} PF={m.get('pf', 0):5.2f}",
              flush=True)

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "stack_wfo",
        "arms": [n for n, _ in ARMS],
        "stage_b_pick": STAGE_B_PICK,
        "steps": wf_rows,
        "path_sums": sums,
        "path_stats": path_stats,
        "arm_full_nets": {n: round(sum(r for _, r, _ in ledgers[n]), 1)
                          for n, _ in ARMS},
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
