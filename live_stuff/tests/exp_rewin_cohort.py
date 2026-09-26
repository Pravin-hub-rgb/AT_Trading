"""Stage P — same-window second entry AFTER a WIN (cohort study, IS + OOS).

EXPERIMENT_SUMMARY last untested family: winner exits (trail/partial/window),
then a fresh signal in the SAME still-live HTF window re-enters; partially
covered by baseline re-arming, never isolated as a cohort study.

Descriptive (no gate): group trades by window_key; a trade is
  rewin  : an earlier trade in the SAME window exited (exit_ts <= entry_ts)
           with r_multiple > 0 before it
  relic  : same but the earlier same-window trade(s) LOST (r <= 0)
  first  : no completed earlier same-window trade
Report per cohort: n / net / WR / avgR / 3R+ count, both eras, cand lanes,
plus book contribution (drop-cohort delta) and era stability.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_rewin_cohort.py
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
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality

OUT = ROOT / "live_stuff/tests/_rewin_cohort_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
)


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


def classify(trades):
    """Tag each trade with cohort label; returns list of (trade, label)."""
    by_win = defaultdict(list)
    for t in trades:
        wk = t.get("window_key")
        if wk:  # falsy window_key -> never grouped (would merge unrelated trades)
            by_win[str(wk)].append(t)
    labels = {id(t): "first" for t in trades}
    for w, ts in by_win.items():
        ts_sorted = sorted(ts, key=lambda x: int(x["entry_ts"]))
        for i, t in enumerate(ts_sorted):
            prior = [p for p in ts_sorted[:i] if int(p["exit_ts"]) <= int(t["entry_ts"])]
            if not prior:
                labels[id(t)] = "first"
            elif any(float(p["r_multiple"]) > 0 for p in prior):
                labels[id(t)] = "rewin"
            else:
                labels[id(t)] = "relic"
    return [(t, labels[id(t)]) for t in trades]


def cohort_stats(rows):
    n = len(rows)
    if not n:
        return None
    nets = [net_r([r]) for r in rows]
    wins = sum(1 for r in nets if r > 0)
    return {
        "n": n,
        "net": round(sum(nets), 1),
        "wr": round(100.0 * wins / n, 1),
        "avgR": round(sum(float(r["r_multiple"]) for r in rows) / n, 3),
        "runner_n": sum(1 for r in rows if float(r["r_multiple"]) >= 3.0),
    }


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE P — SAME-WINDOW SECOND ENTRY AFTER A WIN (cohort study, IS+OOS)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "rewin_cohort",
        "lens": "descriptive cohort study; no gate",
        "years": YEARS, "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = run(sim, data, params, **flags)
            tagged = classify(trades)
            cohorts = {lbl: [t for t, l in tagged if l == lbl]
                       for lbl in ("first", "rewin", "relic")}
            stats = {lbl: cohort_stats(v) for lbl, v in cohorts.items()}
            # multi-window second entries (2nd+ trade regardless of prior outcome)
            drop_rewin = [t for t, l in tagged if l != "rewin"]
            m_full = equity_quality(trades, yrs)
            m_drop = equity_quality(drop_rewin, yrs)
            sc[name] = {
                "n": len(trades),
                "cohorts": {k: v for k, v in stats.items() if v},
                "book_full": m_full,
                "book_drop_rewin": m_drop,
                "d_drop_rewin": round(m_drop.get("net", 0) - m_full.get("net", 0), 1),
            }
            print(f"\n  {name} (n={len(trades)})", flush=True)
            print(f"    {'cohort':<8} {'n':>4} {'net':>8} {'WR%':>6} {'avgR':>7} {'3R+':>4}",
                  flush=True)
            for lbl in ("first", "rewin", "relic"):
                s = stats.get(lbl)
                if s:
                    print(f"    {lbl:<8} {s['n']:>4} {s['net']:>+8.1f} {s['wr']:>6.1f} "
                          f"{s['avgR']:>+7.3f} {s['runner_n']:>4}", flush=True)
            print(f"    drop rewin: book net {m_full.get('net', 0):+.1f} -> "
                  f"{m_drop.get('net', 0):+.1f} (delta {sc[name]['d_drop_rewin']:+.1f}), "
                  f"DD {m_full.get('max_dd', 0):.1f} -> {m_drop.get('max_dd', 0):.1f}",
                  flush=True)
        payload["scopes"][scope] = sc

    print("\n=== REWIN COHORT ERA COMPARISON ===", flush=True)
    for name, _, _ in LANES:
        a = payload["scopes"]["is"][name]["cohorts"].get("rewin")
        b = payload["scopes"]["oos"][name]["cohorts"].get("rewin")
        fa = payload["scopes"]["is"][name]["cohorts"].get("first")
        fb = payload["scopes"]["oos"][name]["cohorts"].get("first")
        print(f"  {name:<10} rewin IS {a} | OOS {b}", flush=True)
        print(f"  {'':<10} first IS n={fa['n']} avgR={fa['avgR']} | "
              f"OOS n={fb['n']} avgR={fb['avgR']}", flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
