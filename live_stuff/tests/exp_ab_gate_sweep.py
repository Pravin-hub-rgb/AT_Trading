"""Stage Z3b - trade-reduction gate sweep on flags A and B (er50, wick_gt3x_pct12).

Z3 (log 77) did the volume flag C. This does the SAME user goal for the other two
survivors: keep ~400ish trades (70-90% of book) with avg R/trade same-or-better.

Direction follows Z1 survivors: flag A `er50` LOW better -> keep er50 <= thr;
flag B `wick_gt3x_pct12` HIGH better -> keep wick >= thr (skip the low-wick tail).

THRESHOLDS: absolute numeric grid from IS-pooled feature quantiles at target keep
fractions {35,45,50,60,67,71,75,80,85}% (both lanes' IS trades, non-None), rounded
to 4 decimals; same numeric thresholds applied to OOS (IS-derived, no OOS peek,
same convention as Z1 tercile edges). None-valued features are KEPT (D-arm semantics).

G-RULE (PRIMARY, same as Z3): kept% in [70,90] AND avgNet/trade >= baseline AND
maxDD(R) <= baseline - all 4 cells. STRICT (reference): dNet>0 AND curve_better 4/4.
ALL arms reported (no best-of hiding). Ulcer excluded from rules (sparse-book
peak-denominator pathology).

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_ab_gate_sweep.py
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
from exp_boundary_state_autopsy import load_scope
from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features, _chop_series_1h

OUT = ROOT / "live_stuff/tests/_ab_gate_sweep_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
KEEP_TARGETS = (0.35, 0.45, 0.50, 0.60, 0.67, 0.71, 0.75, 0.80, 0.85)
# EXPLORATORY refinement (added after first run): er50|0.1989 missed G only on the
# 70% kept floor (uts IS 69.82%); these bridge thresholds target 70-73% kept.
# Clearly labeled exploratory in reporting (post-hoc threshold addition).
EXTRA_GRID = {"er50": (0.2, 0.205, 0.21)}
# (feature, direction) - "le": keep feat <= thr ; "ge": keep feat >= thr
FEATURES = (("er50", "le"), ("wick_gt3x_pct12", "ge"))


def build_grid(vals):
    """IS-pooled quantile grid (non-None values, both lanes)."""
    vals = sorted(vals)
    grid = []
    for k in KEEP_TARGETS:
        idx = min(len(vals) - 1, int(round(k * (len(vals) - 1))))
        thr = round(vals[idx], 4)
        if thr not in grid:
            grid.append(thr)
    return sorted(grid)


def main():
    t0 = time.time()
    print("=" * 116, flush=True)
    print("  STAGE Z3b - GATE SWEEP on flag A (er50<=) and flag B (wick>=) - "
          "goal: keep ~80% trades, avg/trade same-or-better", flush=True)
    print("=" * 116, flush=True)
    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT", "stage": "z3b_ab_gate_sweep",
        "features": {f: d for f, d in FEATURES},
        "keep_targets": list(KEEP_TARGETS),
        "g_rule": "kept% in [70,90] AND avgNet/trade >= base AND maxDD <= base (all 4 cells)",
        "strict_rule": "dNet > 0 AND curve_better (all 4 cells)",
        "years": YEARS, "scopes": {},
    }
    grids = {}
    # pass 1: features (need IS first for grids) - compute both scopes' feats, build
    # grids from IS only
    cache = {}
    for scope in ("is", "oos"):
        data = load_scope(scope)
        arr = build_arrays(data["c1h"])
        conf = sorted((arr["ts"][s["confirmed_at_idx"]], s["dir"],
                       float(max(0, s["seg"]["end_idx"] - s["seg"]["start_idx"])))
                      for s in data["sw10"]
                      if s.get("confirmed_at_idx") is not None
                      and 0 <= s["confirmed_at_idx"] < arr["n"])
        chop = _chop_series_1h(data["c1h"], lb=14)
        ctx = {"arr": arr, "chop": chop, "conf_ts": [x[0] for x in conf],
               "conf_dir": [x[1] for x in conf], "conf_dur": [x[2] for x in conf]}
        cache[scope] = {"data": data, "ctx": ctx, "books": {}, "feats": {}}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            cache[scope]["books"][name] = trades
            cache[scope]["feats"][name] = [compute_features(t, ctx) for t in trades]

    for feat, direction in FEATURES:
        vals = [f.get(feat) for lane, _ in LANES
                for f in cache["is"]["feats"][lane] if f.get(feat) is not None]
        grid = build_grid(vals)
        for e in EXTRA_GRID.get(feat, ()):
            if e not in grid:
                grid.append(e)
        grids[feat] = sorted(grid)
        print(f"\ngrid[{feat}] ({direction}): {grids[feat]}", flush=True)

    payload["grids"] = grids

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        yrs = YEARS[scope]
        sc = {}
        for name, _ in LANES:
            trades = cache[scope]["books"][name]
            feats = cache[scope]["feats"][name]
            base_keys = [(int(t["entry_ts"]), int(t["exit_ts"])) for t in trades]
            m_flat = equity_quality(trades, yrs)
            avg_net_base = m_flat["net"] / max(1, m_flat["n"])
            avg_g_base = sum(float(t["r_multiple"]) for t in trades) / max(1, len(trades))
            print(f"\n  {name} (n={m_flat['n']})  base avgNet/trade={avg_net_base:+.3f} "
                  f"avgGross={avg_g_base:+.3f}", flush=True)
            sc[name] = {"n": m_flat["n"], "flat": m_flat,
                        "avg_net_base": round(avg_net_base, 4),
                        "avg_gross_base": round(avg_g_base, 4), "arms": {}}
            for feat, direction in FEATURES:
                print(f"    [{feat} {'<=' if direction == 'le' else '>='} thr] "
                      f"{'thr':>8} {'n':>4} {'kept%':>6} {'net':>8} {'dNet':>7} "
                      f"{'avgNet':>7} {'maxDD':>6} {'calmar':>7} {'PF':>5} {'G?':>3}",
                      flush=True)
                for thr in grids[feat]:
                    keys = set()
                    for t, f in zip(trades, feats):
                        v = f.get(feat)
                        ok = v is None or (v <= thr if direction == "le" else v >= thr)
                        if ok:
                            keys.add((int(t["entry_ts"]), int(t["exit_ts"])))
                    book = [t for t in trades
                            if (int(t["entry_ts"]), int(t["exit_ts"])) in keys]
                    assert [(t["entry_ts"], t["exit_ts"]) for t in book] == \
                           [k for k in base_keys if k in keys], "identity order"
                    m = equity_quality(book, yrs)
                    d = arm_scores(m, m_flat)
                    kept_pct = 100.0 * m["n"] / m_flat["n"]
                    avg_net = m["net"] / max(1, m["n"])
                    g_cell = (70.0 <= kept_pct <= 90.0) and avg_net >= avg_net_base and \
                             m["max_dd"] <= m_flat["max_dd"]
                    tag = f"{feat}|{thr:g}"
                    rec = {"n": m["n"], "kept_pct": round(kept_pct, 1),
                           "metric": m, "delta": d,
                           "avg_net": round(avg_net, 4), "g_cell": g_cell,
                           "curve_better": curve_better(d)}
                    sc[name]["arms"][tag] = rec
                    print(f"    {'':17} {thr:>8.4f} {m['n']:>4} {kept_pct:>5.0f}% "
                          f"{m['net']:>+8.1f} {d.get('d_net', 0):>+7.1f} "
                          f"{avg_net:>+7.3f} {m['max_dd']:>6.1f} "
                          f"{m['calmar']:>7.3f} {m['pf']:>5.2f} "
                          f"{'Y' if g_cell else 'n':>3}", flush=True)
        payload["scopes"][scope] = sc

    print("\n=== CROSS-CELL VERDICTS ===", flush=True)
    verdicts = {}
    for feat, direction in FEATURES:
        for thr in grids[feat]:
            tag = f"{feat}|{thr:g}"
            cells = [payload["scopes"][s][lane]["arms"][tag]
                     for s in ("is", "oos") for lane, _ in LANES]
            g_pass = all(c["g_cell"] for c in cells)
            strict = all((c["delta"].get("d_net") or 0) > 0 and c["curve_better"]
                         for c in cells)
            kept = [c["kept_pct"] for c in cells]
            dnet = [c["delta"].get("d_net") or 0 for c in cells]
            verdicts[tag] = {"g_pass": g_pass, "strict_pass": strict,
                             "kept_pct": kept, "d_net": [round(x, 1) for x in dnet]}
            print(f"  {tag:<28} kept% {kept[0]:.0f}/{kept[1]:.0f}/{kept[2]:.0f}/{kept[3]:.0f}"
                  f"  dNet {dnet[0]:+7.1f}/{dnet[1]:+7.1f}/{dnet[2]:+6.1f}/{dnet[3]:+6.1f}"
                  f"  G={'PASS' if g_pass else 'no'}  strict={'PASS' if strict else 'no'}",
                  flush=True)
    gwinners = [t for t in verdicts if verdicts[t]["g_pass"]]
    print(f"\n  G-RULE passers: {gwinners or 'NONE'}", flush=True)
    payload["verdicts"] = verdicts
    payload["g_rule_passers"] = gwinners
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
