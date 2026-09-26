"""Stage 3 — 2021 bleed forensic (descriptive autopsy, OOS + IS reference).

Question: WHAT killed champion baseline in 2021 (-26.4R / 152t), and why did
half+delay1+skipD turn it into +10.5R (104t)?

All dimensions are ENTRY-CAUSAL (trade meta frozen at entry):
  dir, htf_regime, break_kind, window_key, loss_streak_at_entry,
  bars_held bucket, monthly bleed curve.
Plus: what exactly skipD removed in 2021 (the 'decisive' ATR%>0.65 trades)
and what half+delay removed (trail-half deltas via arm diffs).

Descriptive only — no gate. Run:
  $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_2021_forensic.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import identity_gate, net_r, get_data
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "live_stuff/tests/_2021_forensic_results.json"

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)

ARMS = (
    ("baseline", {}),
    ("half+delay1", dict(HALF)),
    ("skip_decisive", dict(SKIPD)),
    ("cand", dict(HALF, **SKIPD)),
)


def load_oos():
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    return {
        "c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
        "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
    }


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def bucketize(trades, key_fn, net_fn=net_r):
    agg = defaultdict(lambda: {"n": 0, "net": 0.0, "w": 0})
    for t in trades:
        k = key_fn(t)
        a = agg[k]
        a["n"] += 1
        a["net"] += net_fn([t])
        a["w"] += 1 if float(t["r_multiple"]) > 0 else 0
    out = {}
    for k, a in sorted(agg.items()):
        out[str(k)] = {
            "n": a["n"], "net": round(a["net"], 1),
            "wr": round(100.0 * a["w"] / a["n"], 1),
        }
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE 3 — 2021 BLEED FORENSIC (champion, OOS arms + IS reference)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    data_oos = load_oos()
    data_is = get_data()
    identity_gate(data_is, sim)

    cfg = EXPERIMENTS["champion_multi_sw10"]
    params = {**BP, **cfg["params"]}
    params.setdefault("exp_partial_r", 0.0)

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "2021_forensic",
        "lens": "descriptive entry-causal dimensions",
        "arms": [n for n, _ in ARMS],
        "scopes": {},
    }

    for scope, data in (("oos", data_oos), ("is", data_is)):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        sc = {}
        for arm, flags in ARMS:
            tr = run(sim, data, params, **flags)
            by_year = defaultdict(list)
            for t in tr:
                by_year[str(t.get("exit_date", ""))[:4]].append(t)

            years = {}
            for y, yt in sorted(by_year.items()):
                net = sum(net_r([t]) for t in yt)
                entry = {
                    "n": len(yt), "net": round(net, 1),
                    "wr": round(100.0 * sum(1 for t in yt if float(t["r_multiple"]) > 0) / len(yt), 1),
                }
                if scope == "oos" and y in ("2021", "2022"):
                    entry["by_dir"] = bucketize(yt, lambda t: t.get("dir"))
                    entry["by_htf_regime"] = bucketize(yt, lambda t: t.get("htf_regime"))
                    entry["by_break_kind"] = bucketize(yt, lambda t: t.get("break_kind"))
                    entry["by_streak"] = bucketize(yt, lambda t: t.get("loss_streak_at_entry"))
                    entry["by_month"] = bucketize(
                        yt, lambda t: str(t.get("exit_date", ""))[5:7])
                    entry["by_hold"] = bucketize(
                        yt,
                        lambda t: "0-6h" if int(t.get("bars_held") or 0) <= 24
                        else "6-24h" if int(t.get("bars_held") or 0) <= 96
                        else "24-48h" if int(t.get("bars_held") or 0) <= 192
                        else "48h+")
                    big = sorted(yt, key=lambda t: float(t["r_multiple"]))[:10]
                    entry["worst10"] = [
                        {"d": t.get("entry_date"), "r": float(t["r_multiple"]),
                         "dir": t.get("dir"), "brk": t.get("break_kind"),
                         "reg": t.get("htf_regime"),
                         "bars": int(t.get("bars_held") or 0)}
                        for t in big
                    ]
                years[y] = entry
            sc[arm] = years
            line = "  ".join(f"{y}:{v['net']:+.1f}({v['n']})" for y, v in sorted(years.items()))
            print(f"  {arm:<16} {line}", flush=True)
        payload["scopes"][scope] = sc

    # 2021 arm-vs-arm: which knob did what
    print("\n=== 2021 ARM DELTAS (vs baseline, net) ===", flush=True)
    base21 = payload["scopes"]["oos"]["baseline"]["2021"]["net"]
    for arm in ("half+delay1", "skip_decisive", "cand"):
        d = payload["scopes"]["oos"][arm]["2021"]["net"] - base21
        n = payload["scopes"]["oos"][arm]["2021"]["n"]
        print(f"  {arm:<16} dNet {d:+7.1f}  n={n}", flush=True)
        payload["scopes"]["oos"][arm]["2021"]["dNet_vs_base"] = round(d, 1)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
