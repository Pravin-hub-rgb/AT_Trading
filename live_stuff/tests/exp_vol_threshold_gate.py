"""Stage Z3 - volume-reduction gate sweep (trade-count control, user goal).

USER GOAL (pre-registered 2026-09-26, before official run): from ~500 trades get
to ~400ish (keep 70-90% of book) while average R per trade stays SAME OR BETTER.
Direction: keep trades with vol7_prev7 <= thr (7d volume vs prior-7d ratio),
skip the volume-RISING tail. Descriptive sweep already seen (read-only) - this
official run reports ALL arms, no best-of hiding.

ARMS: flat + keep<=thr for thr in {0.846, 0.90, 0.95, 1.00, 1.064, 1.10, 1.15,
1.20, 1.25, 1.30}. Post-process skip_book (D-arm pattern): removal only, trade
keys of survivors unchanged, engine untouched, identity asserted.

VERDICTS (both printed per arm):
  G-RULE (PRIMARY, user goal): kept% in [70,90] of book in all 4 cells
    (champion/utcsat x IS/OOS) AND avgNet/trade >= baseline in all 4 AND
    maxDD(R) <= baseline in all 4.
  STRICT (reference): dNet > 0 AND curve_better in all 4 cells.
Ranking: cells close to 80% kept with G-RULE pass listed first; full metric
tables printed. Ulcer reported but EXCLUDED from rules (sparse-book peak-
denominator pathology seen at aggressive cuts). avgGross (mean r_multiple) and
avgNet (net_r/n) both shown.

Caveats: post-process removal without chain re-timing (same as all prior gates);
thresholds ranked after a seen descriptive (exploratory - every arm reported);
IS nets fall at every threshold (skipped set is still net-positive in IS).

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_vol_threshold_gate.py
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
from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features, _chop_series_1h

OUT = ROOT / "live_stuff/tests/_vol_threshold_gate_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
THRS = (0.846, 0.90, 0.95, 1.00, 1.064, 1.10, 1.15, 1.20, 1.25, 1.30)


def main():
    t0 = time.time()
    print("=" * 116, flush=True)
    print("  STAGE Z3 - VOLUME-REDUCTION GATE SWEEP (goal: keep ~80% trades, "
          "avg/trade same-or-better)", flush=True)
    print("=" * 116, flush=True)
    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT", "stage": "z3_vol_threshold_gate",
        "lens": "post-process skip; identity = survivor keys unchanged",
        "thresholds": list(THRS),
        "g_rule": "kept% in [70,90] AND avgNet/trade >= base AND maxDD <= base (all 4 cells)",
        "strict_rule": "dNet > 0 AND curve_better (all 4 cells)",
        "years": YEARS, "scopes": {},
    }
    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        arr = build_arrays(data["c1h"])
        conf = sorted((arr["ts"][s["confirmed_at_idx"]], s["dir"],
                       float(max(0, s["seg"]["end_idx"] - s["seg"]["start_idx"])))
                      for s in data["sw10"]
                      if s.get("confirmed_at_idx") is not None
                      and 0 <= s["confirmed_at_idx"] < arr["n"])
        chop = _chop_series_1h(data["c1h"], lb=14)
        ctx = {"arr": arr, "chop": chop, "conf_ts": [x[0] for x in conf],
               "conf_dir": [x[1] for x in conf], "conf_dur": [x[2] for x in conf]}
        sc = {}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            feats = [compute_features(t, ctx) for t in trades]
            base_keys = [(int(t["entry_ts"]), int(t["exit_ts"])) for t in trades]
            m_flat = equity_quality(trades, yrs)
            avg_net_base = m_flat["net"] / max(1, m_flat["n"])
            avg_g_base = sum(float(t["r_multiple"]) for t in trades) / max(1, len(trades))
            print(f"\n  {name} (n={m_flat['n']})  base avgNet/trade={avg_net_base:+.3f} "
                  f"avgGross={avg_g_base:+.3f}", flush=True)
            print(f"    {'thr':>6} {'n':>4} {'kept%':>6} {'net':>8} {'dNet':>7} "
                  f"{'avgNet':>7} {'avgG':>6} {'maxDD':>6} {'calmar':>7} {'PF':>5} "
                  f"{'sort':>7} {'WR':>5} {'ddDur':>5}", flush=True)
            print(f"    {'flat':>6} {m_flat['n']:>4} {100.0:>5.0f}% "
                  f"{m_flat['net']:>+8.1f} {'--':>7} {avg_net_base:>+7.3f} "
                  f"{avg_g_base:>+6.3f} {m_flat['max_dd']:>6.1f} "
                  f"{m_flat['calmar']:>7.3f} {m_flat['pf']:>5.2f} "
                  f"{m_flat['sortino']:>7.1f} {m_flat['wr']:>4.1f}% "
                  f"{m_flat['max_dd_dur']:>5}", flush=True)
            sc[name] = {"n": m_flat["n"], "flat": m_flat,
                        "avg_net_base": round(avg_net_base, 4),
                        "avg_gross_base": round(avg_g_base, 4), "arms": {}}
            for thr in THRS:
                # keep trades with vol7_prev7 <= thr; None-features KEPT (same as D arm)
                keys = {(int(t["entry_ts"]), int(t["exit_ts"]))
                        for t, f in zip(trades, feats)
                        if f.get("vol7_prev7") is None or f["vol7_prev7"] <= thr}
                book = [t for t in trades
                        if (int(t["entry_ts"]), int(t["exit_ts"])) in keys]
                assert [(t["entry_ts"], t["exit_ts"]) for t in book] == \
                       [k for k in base_keys if k in keys], "identity: survivor order changed"
                m = equity_quality(book, yrs)
                d = arm_scores(m, m_flat)
                kept_pct = 100.0 * m["n"] / m_flat["n"]
                avg_net = m["net"] / max(1, m["n"])
                avg_g = sum(float(t["r_multiple"]) for t in book) / max(1, len(book))
                g_cell = (70.0 <= kept_pct <= 90.0) and avg_net >= avg_net_base and \
                         m["max_dd"] <= m_flat["max_dd"]
                rec = {"n": m["n"], "kept_pct": round(kept_pct, 1),
                       "metric": m, "delta": d,
                       "avg_net": round(avg_net, 4), "avg_gross": round(avg_g, 4),
                       "g_cell": g_cell, "curve_better": curve_better(d)}
                sc[name]["arms"][f"{thr:g}"] = rec
                print(f"    {thr:>6.3f} {m['n']:>4} {kept_pct:>5.0f}% "
                      f"{m['net']:>+8.1f} {d.get('d_net', 0):>+7.1f} "
                      f"{avg_net:>+7.3f} {avg_g:>+6.3f} {m['max_dd']:>6.1f} "
                      f"{m['calmar']:>7.3f} {m['pf']:>5.2f} {m['sortino']:>7.1f} "
                      f"{m['wr']:>4.1f}% {m['max_dd_dur']:>5}"
                      f"{'  [G ok]' if g_cell else ''}", flush=True)
        payload["scopes"][scope] = sc

    # ---- cross-cell verdicts per threshold
    print("\n=== CROSS-CELL VERDICTS (4 cells: champion/utcsat x IS/OOS) ===", flush=True)
    verdicts = {}
    for thr in THRS:
        t = f"{thr:g}"
        cells = [payload["scopes"][s][lane]["arms"][t]
                 for s in ("is", "oos") for lane, _ in LANES]
        g_pass = all(c["g_cell"] for c in cells)
        strict = all((c["delta"].get("d_net") or 0) > 0 and c["curve_better"]
                     for c in cells)
        kept = [c["kept_pct"] for c in cells]
        dnet = [c["delta"].get("d_net") or 0 for c in cells]
        avg_n = [c["avg_net"] for c in cells]
        verdicts[t] = {"g_pass": g_pass, "strict_pass": strict,
                       "kept_pct": kept, "d_net": [round(x, 1) for x in dnet],
                       "avg_net": avg_n}
        print(f"  thr={t:>5}  kept% {kept[0]:.0f}/{kept[1]:.0f}/{kept[2]:.0f}/{kept[3]:.0f}"
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
