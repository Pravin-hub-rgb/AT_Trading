"""Stage ZCX - the M2-FREE sizing combo (ZC x X only, causal arms only).

WHY THIS EXISTS
---------------
The capital queue (CAPITAL_STAGE_PLAN.md) holds five sizing levers: M2, uMZX,
sMZX, ramp_mag, count_linear. Four of them (M2, ramp_mag, and the M2 component
of uMZX/sMZX/count_linear) key off `cur_mag_atr`, which uses `seg.end_px`.
`backend_check_wd_days.py:108` asserts `fs_at_idx >= seg.end_idx`, so a swing's
end price is confirmed AT OR AFTER the end bar - it is not knowable when the
order is sent. exp_m2_sendtime_feature.py then showed the send-time
redefinition of that magnitude flags 0-1.3% of trades (vs 12-25% in backtest),
so the signal effectively vanishes. All of that is settled; this run does not
revisit it.

THE GAP THIS RUN FILLS
----------------------
ZC (vol7_prev7 <= 0.846) and X (parent risk_pct < 1.0) are the other two flags
behind the queue combos - and they are NOT built on the swing magnitude:

  ZC reads a 7-day-vs-prior-7-day volume ratio from the 1h volume series.
  X  reads the parent window's configured risk_pct.

Neither touches `seg.end_px`. But exp_sizing_combo.py only ever tested
combinations that CONTAIN M2 (uMZ, uMZX, sMZ, sMZX). A repository-wide search
for a ZC/X-only union or count arm returns nothing - the causal pair has never
been tested on its own. ZC standalone carries MORE flags than M2 on champion IS
(166 vs 128, from _sizing_shapes_results.json), so the untested arm is not
obviously the weaker one.

Pre-registered BEFORE the run (2026-09-26):
  Arms (all reported, no best-of hiding):
    base  1x reference
    ZC    x1.5 on ZC keys            (control - must reproduce 24.79/24.82)
    X     x1.5 on X keys             (control)
    uZX   x1.5 when ZC OR X          (union, M2-free)
    sZX   x1.5^count on ZC/X         (stack, M2-free)
  Lanes: champion / utcsat / age10 flat configs. Scopes: IS + OOS.
  PASS (per causal combo arm: uZX, sZX) = dNet > 0 AND curve_better TRUE in
  ALL 6 cells (3 lanes x 2 eras) - same strictness as M2's flat gate.
  Flag coverage sanity: 5-40% of trades. Below that there is no selection;
  above it the result is the M1 leverage trap (CHECKLIST 24.58).
  Identity: trade key sequence (entry_ts, exit_ts) byte-identical on every arm;
  ONLY r_multiple differs. Sizing never changes which trades fire, so the
  post-process is path-true by construction - no engine rerun needed.

  Honest note on ZC's known defect: it was DROPPED as a standalone for
  portability (24.82 - a Bybit-volume-derived ratio threshold did not transfer
  to Binance, binance IS curve FALSE). That objection applies to the ZC
  threshold as such, not to this union. This run is therefore NOT a
  recommendation to re-adopt ZC; if ZC alone fails to transfer, a passing uZX
  would need a fresh cross-venue run before any adoption. Reported as-is.

RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.
No engine edit, no production change.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_zx_causal_combo.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

# audited primitives, imported from the paths exp_sizing_combo.py used (24.79/24.82)
from experiment_registry import BP, EXPERIMENTS
from test_experiments_craze import build_module
from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features
from exp_htf_break_sizing import flagged_keys
from exp_htf_break_measures import flatten_breaks, enrich_windows
from exp_thesis_htf_deep_atlas import build_windows, window_rows

# ledger references from exp_sizing_combo.EXPECT_FLAT (asserted, not re-derived)
from exp_sizing_combo import EXPECT_FLAT, LANES, YEARS, apply_arm, load_scope, run

OUT = ROOT / "backtest/tests/_zx_causal_combo_results.json"
SIZE = 1.5
VOL7PREV_Q1 = 0.846
RISK_PCT_MAX = 1.0

ARMS = (
    ("base", (), "union"),
    ("ZC", ("ZC",), "union"),
    ("X", ("X",), "union"),
    ("uZX", ("ZC", "X"), "union"),
    ("sZX", ("ZC", "X"), "stack"),
)
COMBO_ARMS = ("uZX", "sZX")

ARM_DESC = {
    "base": "1x reference",
    "ZC": f"x{SIZE} on vol7_prev7 <= {VOL7PREV_Q1}",
    "X": f"x{SIZE} on parent risk_pct < {RISK_PCT_MAX}",
    "uZX": f"x{SIZE} when ZC OR X (M2-free union)",
    "sZX": f"x{SIZE}^count on ZC/X (M2-free stack)",
}

COV_LO, COV_HI = 0.05, 0.40


def flag_coverage_ok(n_aff, n_total):
    """Pre-registered 5-40% band. Below = no selection; above = M1 leverage trap."""
    if not n_total:
        return False
    return COV_LO <= n_aff / n_total <= COV_HI


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE ZCX - M2-FREE CAUSAL SIZING COMBO (ZC x X, flat books)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "zx_causal_combo",
        "lens": ("post-process sizing on FLAT books; identity = same trade keys; "
                 "ZC and X only - neither reads seg.end_px"),
        "arms": ARM_DESC,
        "years": YEARS, "scopes": {},
        "pre_registered": (
            "PASS per causal combo arm (uZX, sZX) = dNet>0 AND curve_better TRUE "
            "in all 6 cells (3 lanes x 2 eras), AND flag coverage 5-40%"),
        "m2_excluded": True,
        "baseline_reference": "champion 500/+325.8 IS, 279/+70.2 OOS; utcsat 453/+279.5, "
                              "253/+60.2; age10 130/+435.7, 76/+43.2 (asserted)",
        "known_defect": ("ZC standalone was dropped for cross-venue portability (24.82). "
                         "A passing uZX/sZX would still require a fresh cross-venue run "
                         "before adoption."),
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]

        arr = build_arrays(data["c1h"])
        conf = []
        for s in data["sw10"]:
            ci = s.get("confirmed_at_idx")
            if ci is None or not (0 <= ci < arr["n"]):
                continue
            dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
            conf.append((arr["ts"][ci], s["dir"], float(dur)))
        conf.sort(key=lambda x: x[0])
        from exp_regime_structure_autopsy import _chop_series_1h
        chop = _chop_series_1h(data["c1h"], lb=14)
        ctx0 = {"arr": arr, "chop": chop,
                "conf_ts": [x[0] for x in conf],
                "conf_dir": [x[1] for x in conf],
                "conf_dur": [x[2] for x in conf]}

        fine_ts = [int(c["ts"]) for c in data["fine"]]
        breaks = flatten_breaks(data["sw10"])
        raw = build_windows(data, 3.0, 16)
        windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
                   for lane, rows in raw.items()}
        for lane in windows:
            enrich_windows(windows[lane], data["c1h"], breaks)

        sc = {}
        for name, key in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = run(sim, data, params)
            m_flat = equity_quality(trades, yrs)

            exp_n, exp_net = EXPECT_FLAT[name][scope]
            assert m_flat["n"] == exp_n, (
                f"flat ledger n mismatch {name}/{scope}: {m_flat['n']} != {exp_n}")
            assert abs(m_flat["net"] - exp_net) < 0.5, (
                f"flat ledger net mismatch {name}/{scope}: {m_flat['net']} != {exp_net}")
            print(f"  [ledger-ok] {name}/{scope}: n={m_flat['n']} "
                  f"net={m_flat['net']:+.1f}", flush=True)

            feats = [compute_features(t, ctx0) for t in trades]
            k_zc = {(int(t["entry_ts"]), int(t["exit_ts"]))
                    for t, f in zip(trades, feats)
                    if f.get("vol7_prev7") is not None
                    and f["vol7_prev7"] <= VOL7PREV_Q1}
            k_x = flagged_keys(trades, windows, "risk_pct", -1e9, RISK_PCT_MAX)
            fam_keys = {"ZC": k_zc, "X": k_x}
            print(f"    flags ZC={len(k_zc)} X={len(k_x)} of {len(trades)}", flush=True)

            arms_out = {}
            for arm, fams, mode in ARMS:
                if arm == "base":
                    m, n_aff = m_flat, 0
                else:
                    book = apply_arm(trades, fam_keys, fams, mode)
                    n_aff = sum(1 for t in trades
                                if any((int(t["entry_ts"]), int(t["exit_ts"])) in fam_keys[f]
                                       for f in fams))
                    m = equity_quality(book, yrs)
                d = arm_scores(m, m_flat)
                cb = curve_better(d)
                cov = flag_coverage_ok(n_aff, len(trades))
                tag = "" if arm == "base" else (" COV-OK" if cov else " COV-BAD")
                print(f"    {arm:<5} n={m['n']:>4} net={m.get('net',0):>+8.1f} "
                      f"DD={m.get('max_dd',0):>6.1f} ulc={m.get('ulcer',0):>7.2f} "
                      f"calm={m.get('calmar',0):>6.2f} PF={m.get('pf',0):>5.2f} "
                      f"dNet={d.get('d_net',0):>+8.1f} nAff={n_aff:>4} "
                      f"curve={cb}{tag}", flush=True)
                arms_out[arm] = {"n_affected": n_aff, "metric": m, "delta": d,
                                 "curve_better": cb, "coverage_ok": cov}
            sc[name] = {"n": m_flat["n"],
                        "flag_counts": {"ZC": len(k_zc), "X": len(k_x)},
                        "arms": arms_out, "identity_ok": True}
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (6 cells per arm) ===", flush=True)
    verdicts = {}
    for arm, _f, _m in ARMS:
        if arm == "base":
            continue
        for name, _ in LANES:
            a_is = payload["scopes"]["is"][name]["arms"][arm]
            a_oos = payload["scopes"]["oos"][name]["arms"][arm]
            d_is, d_oos = a_is["delta"], a_oos["delta"]
            cov = a_is["coverage_ok"] and a_oos["coverage_ok"]
            v = {"desc": ARM_DESC[arm],
                 "n_aff_is": a_is["n_affected"], "n_aff_oos": a_oos["n_affected"],
                 "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                 "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
                 "curve_better_is": curve_better(d_is),
                 "curve_better_oos": curve_better(d_oos),
                 "coverage_ok": cov}
            v["cell_pass"] = ((v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0
                              and v["curve_better_is"] and v["curve_better_oos"]
                              and cov)
            verdicts[f"{arm}_{name}"] = v
            print(f"  {arm:<5} {name:<9} nAff {v['n_aff_is']:>3}/{v['n_aff_oos']:<3} "
                  f"dNet {v['d_net_is']:+7.1f}/{v['d_net_oos']:+6.1f} "
                  f"curve {int(v['curve_better_is'])}/{int(v['curve_better_oos'])} "
                  f"cov={int(cov)} cell={v['cell_pass']}", flush=True)
    payload["verdicts"] = verdicts

    payload["pass_all_6"] = {}
    for arm in [a for a, _f, _m in ARMS if a != "base"]:
        payload["pass_all_6"][arm] = all(
            verdicts[f"{arm}_{n}"]["cell_pass"] for n, _ in LANES)
    combo_pass = all(payload["pass_all_6"][a] for a in COMBO_ARMS)
    payload["combo_pass_all_arms"] = combo_pass
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    for arm in [a for a, _f, _m in ARMS if a != "base"]:
        print(f"  {arm:<5} 6/6 = {payload['pass_all_6'][arm]}   {ARM_DESC[arm]}", flush=True)
    print("=" * 100, flush=True)
    print(f"  M2-FREE CAUSAL COMBO: {'PASS 6/6' if combo_pass else 'NOT ALL PASS'}",
          flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
