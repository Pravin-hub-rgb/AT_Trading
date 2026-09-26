"""Proper prefix-invariance audit for half+delay1.

At each cutoff, both 15m and 1h swing chains are recomputed from the truncated
candles. Completed trades are compared against a full-history replay. This
checks retroactive exit/trail decisions without reusing future swing state.
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

from experiment_registry import BP, EXPERIMENTS
from test_experiments_craze import build_module
from exp_trail_slower import load_scope
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING
from src.walker import FlowCandle

OUT = {
    "is": ROOT / "live_stuff/tests/_trail_half_delay1_prefix_audit_is.json",
    "oos": ROOT / "live_stuff/tests/_trail_half_delay1_prefix_audit_oos.json",
}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10", "age10_dirmatch_swingpause_single_sw10")
ARMS = {
    "baseline": {},
    "half_delay1": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0},
    "half_delay1_strict": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0,
                           "exp_trail_delay_prevbar": 1},
}
FRACTIONS = (0.70, 0.85)


def flow(candles):
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                        high=float(c["high"]), low=float(c["low"]),
                        close=float(c["close"])) for c in candles]


def trade_key(t):
    return (int(t["entry_ts"]), 1 if t.get("dir") == "long" else -1,
            int(t.get("exit_ts") or 0), round(float(t.get("r_multiple") or 0), 6))


def prefix_data(data, cutoff):
    c15 = [c for c in data["c15"] if int(c["ts"]) <= cutoff]
    c1h = [c for c in data["c1h"] if int(c["ts"]) <= cutoff]
    fine = [c for c in data["fine"] if int(c["ts"]) <= cutoff]
    sw15 = _compute_swings(flow(c15), "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(flow(c1h), "continuous", min_bars=10)
    return c1h, sw10, c15, sw15, fine


def run_scope(sim, data, scope):
    result = {"scope": scope, "configs": {}}
    for key_name in CONFIGS:
        params = {**BP, **EXPERIMENTS[key_name]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        full = {}
        for arm, flags in ARMS.items():
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **{**params, **flags})
            full[arm] = out["ltf_trades"] if isinstance(out, dict) else out
        rows = {}
        for frac in FRACTIONS:
            cutoff = int(data["c15"][int((len(data["c15"]) - 1) * frac)]["ts"])
            pdata = prefix_data(data, cutoff)
            arm_rows = {}
            for arm, flags in ARMS.items():
                out = sim(pdata[0], pdata[1], pdata[2], pdata[3],
                          fine_ltf=pdata[4], **{**params, **flags})
                prefix = out["ltf_trades"] if isinstance(out, dict) else out
                p_done = [t for t in prefix if int(t.get("exit_ts") or 0) <= cutoff]
                f_done = [t for t in full[arm] if int(t.get("exit_ts") or 0) <= cutoff]
                pk = {trade_key(t) for t in p_done}
                fk = {trade_key(t) for t in f_done}
                arm_rows[arm] = {
                    "cutoff": cutoff, "full_completed": len(f_done),
                    "prefix_completed": len(p_done), "full_only": len(fk - pk),
                    "prefix_only": len(pk - fk),
                    "full_r": round(sum(float(t.get("r_multiple") or 0) for t in f_done), 6),
                    "prefix_r": round(sum(float(t.get("r_multiple") or 0) for t in p_done), 6),
                    "passed": fk == pk,
                }
            rows[str(frac)] = arm_rows
        result["configs"][key_name] = rows
        print(scope.upper(), key_name, "prefix complete", flush=True)
    return result


def main():
    started = time.time()
    sim = build_module()
    combined = {"instrument": "BTCUSDT_BYBIT", "fractions": list(FRACTIONS), "scopes": {}}
    for scope in ("is", "oos"):
        combined["scopes"][scope] = run_scope(sim, load_scope(scope), scope)
    combined["elapsed_sec"] = round(time.time() - started, 3)
    OUT["is"].write_text(json.dumps(combined, indent=2), encoding="utf-8")
    OUT["oos"].write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print("wrote prefix audit", flush=True)


if __name__ == "__main__":
    main()
