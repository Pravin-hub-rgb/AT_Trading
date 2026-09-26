"""Stage X Phase 2 — break-quality promotions on multi lanes.

Phase 1 (exp_htf_break_measures): 4/5 1h break-quality measures era-FLIPPED
(vol_ratio, body_atr, disp_atr, b1_gap — dead). Only risk_pct (window stop
distance / entry, known causally at window open) survived:

  A PRIMARY (pre-registered): x1.5 sizing flag = parent window risk_pct < 1.0
     (top bin in 4/4 cells: IS +0.74/+0.92 avg, OOS +10.19/+8.53 avg).
     Pass = dNet > 0 AND curve_better in all 4 cells (2 lanes x 2 eras).
     Caveat pre-registered: OOS flagged n = 7/9 (small-flag caveat if n < 20).
  B EXPLORATORY gate: skip children of parent risk_pct in [1.0, 2.0)
     (below-rest avg 4/4, but band nets POSITIVE in IS -> predicted FAIL).
  C EXPLORATORY gate: skip children of parent vol_ratio < 0.75
     (IS-bad / OOS-best flip -> predicted FAIL).

Post-process only (sizing/gates do not feed back into entry decisions); the
engine is untouched. Identity: same trade-key sequence on every arm; only
r_multiple (A) or trade membership (B/C) changes. Equity lens via
equity_quality + curve_better (Stage O pattern).

RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.
Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_htf_break_sizing.py
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
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope
from exp_thesis_htf_deep_atlas import build_windows, window_rows
from exp_htf_break_measures import BINS, enrich_windows, flatten_breaks, map_children_measured
from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "live_stuff/tests/_htf_break_sizing_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))


def flagged_keys(trades, windows, measure, lo, hi):
    """(entry_ts, exit_ts) keys of trades whose parent window measure in [lo,hi)."""
    mapped = map_children_measured(windows, trades)
    keys = set()
    for t, m in zip(trades, mapped):
        p = m["parent"]
        if p is None:
            continue
        v = p.get(measure)
        if v is not None and lo <= v < hi:
            keys.add((int(t["entry_ts"]), int(t["exit_ts"])))
    return keys


def size_book(trades, keys):
    out = []
    for t in trades:
        t2 = dict(t)
        if (int(t["entry_ts"]), int(t["exit_ts"])) in keys:
            t2["r_multiple"] = round(float(t["r_multiple"]) * SIZE, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    return out


def skip_book(trades, keys):
    return [t for t in trades if (int(t["entry_ts"]), int(t["exit_ts"])) not in keys]


def main():
    t0 = time.time()
    print("=" * 110, flush=True)
    print(f"  STAGE X PHASE 2 — BREAK-QUALITY PROMOTIONS (A: x{SIZE} on parent risk_pct<1.0; "
          f"B/C exploratory gates)", flush=True)
    print("=" * 110, flush=True)
    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT", "stage": "htf_break_sizing",
        "lens": "post-process; identity = same trade keys; no automatic gate",
        "arms": {"A": f"x{SIZE} where parent risk_pct < 1.0",
                 "B": "skip parent risk_pct in [1.0,2.0)",
                 "C": "skip parent vol_ratio < 0.75"},
        "years": YEARS, "scopes": {},
    }
    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        fine_ts = [int(c["ts"]) for c in data["fine"]]
        breaks = flatten_breaks(data["sw10"])
        raw = build_windows(data, 3.0, 16)
        windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
                   for lane, rows in raw.items()}
        for lane in windows:
            enrich_windows(windows[lane], data["c1h"], breaks)
        sc = {}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            keys_a = flagged_keys(trades, windows, "risk_pct", -1e9, 1.0)
            keys_b = flagged_keys(trades, windows, "risk_pct", 1.0, 2.0)
            keys_c = flagged_keys(trades, windows, "vol_ratio", -1e9, 0.75)
            m_flat = equity_quality(trades, yrs)
            lanes = {"flat": m_flat}
            for arm, keys in (("A", keys_a), ("B", keys_b), ("C", keys_c)):
                book = size_book(trades, keys) if arm == "A" else skip_book(trades, keys)
                lanes[arm] = (equity_quality(book, yrs), len(keys))
            sc[name] = {"n": m_flat["n"]}
            print(f"\n  {name} (n={m_flat['n']})  flagged A={len(keys_a)} "
                  f"B={len(keys_b)} C={len(keys_c)}", flush=True)
            print(f"    {'arm':<5} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} curve", flush=True)
            d_flat = arm_scores(m_flat, m_flat)
            print(f"    {'flat':<5} {m_flat['n']:>4} {m_flat.get('net', 0):>+8.1f} "
                  f"{m_flat.get('max_dd', 0):>6.1f} {m_flat.get('ulcer', 0):>7.2f} "
                  f"{m_flat.get('sortino', 0):>7.2f} {m_flat.get('calmar', 0):>7.3f} "
                  f"{m_flat.get('max_streak', 0):>6} {m_flat.get('pf', 0):>6.2f}", flush=True)
            for arm in ("A", "B", "C"):
                m, nk = lanes[arm]
                d = arm_scores(m, m_flat)
                small = " SMALL-N" if nk < 20 else ""
                print(f"    {arm:<5} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
                      f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f} "
                      f"{d.get('d_net', 0):>+8.1f} {curve_better(d)}{small}", flush=True)
                sc[name][arm] = {"n_affected": nk, "metric": m, "delta": d,
                                 "curve_better": curve_better(d)}
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (per arm, per lane) ===", flush=True)
    verdicts = {}
    for name, _ in LANES:
        for arm in ("A", "B", "C"):
            d_is = payload["scopes"]["is"][name][arm]["delta"]
            d_oos = payload["scopes"]["oos"][name][arm]["delta"]
            ni = payload["scopes"]["is"][name][arm]["n_affected"]
            no = payload["scopes"]["oos"][name][arm]["n_affected"]
            v = {"n_is": ni, "n_oos": no,
                 "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                 "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
                 "curve_better_is": curve_better(d_is),
                 "curve_better_oos": curve_better(d_oos),
                 "small_n": ni < 20 or no < 20}
            v["pass"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0 and \
                        v["curve_better_is"] and v["curve_better_oos"]
            verdicts[f"{name}_{arm}"] = v
            print(f"  {name:<10} {arm}  n {ni}/{no}  dNet {v['d_net_is']:+8.1f}/"
                  f"{v['d_net_oos']:+7.1f}  dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f}  "
                  f"curve {v['curve_better_is']}/{v['curve_better_oos']}  "
                  f"PASS={v['pass']} smallN={v['small_n']}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
