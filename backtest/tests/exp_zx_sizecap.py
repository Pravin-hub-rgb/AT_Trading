"""Stage ZCX-SIZECAP - can a capped multiplier rescue ZCX's curve_better failure?

WHY
---
`exp_zx_cross_venue.py` (24.86) found uZX / sZX profitable on BOTH venues - dNet
positive in 22 of 24 Binance cells - but NOT 6/6. The single failing gate is
`curve_better`, and it fails on the two LARGE IS books (champion 187 flagged,
utcsat 169) while the small age10 book passes on all four arms.

So the failure is curve SHAPE, not absent profit. This is the one direction in
the whole queue that is both send-time computable and profitable, so it is worth
one bounded sizing experiment: if 1.5x is simply too hot, a smaller cap might
keep the dNet while flattening the curve.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
-------------------------------------------
  Method: post-process sizing. Per AGENT_COORDINATION.md "Sizing exemption",
    sizing changes R per trade and never WHICH trades are taken, so the trade
    list is identical and this is a real measurement, not an upper bound.
    No engine rerun required.
  Caps:  1.00 (base sanity) / 1.10 / 1.20 / 1.25 / 1.30 / 1.40 / 1.50 (ref)
  Arms:  uZX (union) and sZX (stack) - flag definitions frozen from 24.86.
  Venues: bybit (CONTROL, must reproduce 24.86) and binance-perp (TEST).
  Control: bybit base ledgers + bybit uZX@1.50 dNet must reproduce 24.86, or
    abort - a control mismatch means the harness is wrong, not the venue.
  ARM PASS = dNet > 0 AND curve_better in ALL 6 cells, on the TEST venue.
  CROSS-VENUE CONSISTENCY = the same cap passes all 6 cells on BOTH venues.

  Nothing is retuned after the run. If no cap passes, the family is closed.

  PREDICTION RECORDED BEFORE RUNNING (this is the point of writing it down):
  `apply_arm` scales r_multiple, so the whole arm equity curve scales with the
  multiplier. Therefore d_max_dd and d_ulcer should scale as (cap - 1) and
  d_calmar should be ~INVARIANT (net and dd both scale, their ratio does not).
  `curve_better` needs d_max_dd>0.5 OR d_ulcer>0.5 OR d_calmar>0.05 - absolute
  thresholds. So if dNet and the curve deltas really are linear in the cap,
  then EVERY cap below 1.5 scores SMALLER curve deltas and 1.50 is the ONLY
  setting that can pass. The failure would then not be "1.5x is too hot" but
  "the flagged cohort does not contain the drawdown-maker at any size".
  The `linearity` block below measures this instead of asserting it.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_zx_sizecap.py
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

OUT = ROOT / "backtest/tests/_zx_sizecap.json"
SIZE_REF = 1.5          # 24.86 reference multiplier
VOL7PREV_Q1 = 0.846     # frozen from Bybit, NOT re-derived per venue
RISK_PCT_MAX = 1.0
CAPS = (1.00, 1.10, 1.20, 1.25, 1.30, 1.40, 1.50)

# bybit control refs from 24.85/24.86
BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
BYBIT_UZX_REF = {"champion": (124.0, 33.6), "utcsat": (130.6, 41.1),
                 "age10": (115.5, 5.1)}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
COMBO_ARMS = (("uZX", ("ZC", "X"), "union"),
              ("sZX", ("ZC", "X"), "stack"))


def apply_cap(trades, fam_keys, fams, mode, cap):
    """Same semantics as exp_sizing_combo.apply_arm with a free multiplier.

    Identity assert mirrors the audited one: sizing must not change WHICH
    trades are taken, only their R. The sign assert covers the sizing
    exemption's condition 1 - the loss streak counts losses, not R.
    """
    out = []
    for t in trades:
        k = (int(t["entry_ts"]), int(t["exit_ts"]))
        cnt = sum(1 for f in fams if k in fam_keys[f])
        t2 = dict(t)
        if cnt:
            mult = cap if mode == "union" else cap ** cnt
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    assert [float(t["r_multiple"]) > 0 for t in out] == \
           [float(t["r_multiple"]) > 0 for t in trades], "loss sign changed"
    return out


def run_venue(venue, data, sim, sim_fn, years):
    """Sweep every cap on every lane for one venue bundle."""
    from experiment_registry import BP, EXPERIMENTS
    from exp_regime_structure_autopsy import build_arrays, compute_features
    from exp_htf_break_sizing import flagged_keys
    from exp_htf_break_measures import flatten_breaks, enrich_windows
    from exp_thesis_htf_deep_atlas import build_windows, window_rows
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    from exp_regime_structure_autopsy import _chop_series_1h

    arr = build_arrays(data["c1h"])
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        dur = max(1, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
        conf.append((arr["ts"][ci], s["dir"], float(dur)))
    conf.sort(key=lambda x: x[0])
    chop = _chop_series_1h(data["c1h"], lb=14)
    ctx0 = {"arr": arr, "chop": chop,
            "conf_ts": [x[0] for x in conf], "conf_dir": [x[1] for x in conf],
            "conf_dur": [x[2] for x in conf]}

    fine_ts = [int(c["ts"]) for c in data["fine"]]
    breaks = flatten_breaks(data["sw10"])
    raw = build_windows(data, 3.0, 16)
    windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
               for lane, rows in raw.items()}
    for lane in windows:
        enrich_windows(windows[lane], data["c1h"], breaks)

    res = {}
    for name, key in LANES:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        trades = sim_fn(sim, data, params)
        m_base = equity_quality(trades, years)
        feats = [compute_features(t, ctx0) for t in trades]
        k_zc = {(int(t["entry_ts"]), int(t["exit_ts"])) for t, f in zip(trades, feats)
                if f.get("vol7_prev7") is not None and f["vol7_prev7"] <= VOL7PREV_Q1}
        k_x = flagged_keys(trades, windows, "risk_pct", -1e9, RISK_PCT_MAX)
        fam = {"ZC": k_zc, "X": k_x}

        # best-trade-removed base, for the robustness gate
        best_i = max(range(len(trades)), key=lambda i: float(trades[i]["r_multiple"]))
        m_base_nb = equity_quality([t for i, t in enumerate(trades) if i != best_i], years)

        arms_out = {}
        for arm, fams, mode in COMBO_ARMS:
            n_aff = sum(1 for t in trades
                        if any((int(t["entry_ts"]), int(t["exit_ts"])) in fam[f] for f in fams))
            per_cap = {}
            for cap in CAPS:
                if cap == 1.00:
                    book, m = trades, m_base
                else:
                    book = apply_cap(trades, fam, fams, mode, cap)
                    m = equity_quality(book, years)
                d = arm_scores(m, m_base)
                cb = curve_better(d)
                # robustness: does the sign survive removing the single best trade?
                best_j = max(range(len(book)), key=lambda i: float(book[i]["r_multiple"]))
                m_nb = equity_quality([t for i, t in enumerate(book) if i != best_j], years)
                d_nb = arm_scores(m_nb, m_base_nb)
                per_cap[f"{cap:.2f}"] = {
                    "d_net": d.get("d_net"),
                    "d_max_dd": d.get("d_max_dd"),
                    "d_ulcer": d.get("d_ulcer"),
                    "d_calmar": d.get("d_calmar"),
                    "d_pf": d.get("d_pf"),
                    "d_uw_pct": d.get("d_uw_pct"),
                    "curve_better": cb,
                    "d_net_no_best": d_nb.get("d_net"),
                    "robust": (d_nb.get("d_net") or 0) > 0,
                }
            arms_out[arm] = {"n_affected": n_aff, "mode": mode, "caps": per_cap}
        res[name] = {"n": m_base["n"], "net": m_base["net"],
                     "flag_counts": {"ZC": len(k_zc), "X": len(k_x)},
                     "base_best_r": round(float(trades[best_i]["r_multiple"]), 3),
                     "arms": arms_out}
    return res


def linearity(payload):
    """Test the recorded prediction: are curve deltas linear in (cap - 1)?"""
    out = {}
    for venue in ("bybit", "binance"):
        rows = []
        for scope in ("is", "oos"):
            for name, _ in LANES:
                for arm, _, _ in COMBO_ARMS:
                    caps = payload["scopes"][venue][scope][name]["arms"][arm]["caps"]
                    ref = caps["1.50"]
                    for cf, cv in caps.items():
                        if cf == "1.50" or not (ref["d_max_dd"] or 0):
                            continue
                        cap = float(cf)
                        pred = (cap - 1.0) / (SIZE_REF - 1.0)
                        rows.append({
                            "cell": f"{venue}/{scope}/{name}/{arm}/{cf}",
                            "d_max_dd": cv["d_max_dd"],
                            "ratio_actual": round((cv["d_max_dd"] or 0) / ref["d_max_dd"], 3),
                            "ratio_predicted_linear": round(pred, 3),
                        })
        out[venue] = rows
    summ = {}
    for venue, rows in out.items():
        devs = [abs(r["ratio_actual"] - r["ratio_predicted_linear"]) for r in rows
                if r["d_max_dd"] is not None]
        summ[venue] = {
            "n": len(devs),
            "mean_abs_dev_from_linear": round(sum(devs) / len(devs), 4) if devs else None,
            "max_abs_dev_from_linear": round(max(devs), 4) if devs else None,
            "verdict": ("linear" if devs and max(devs) < 0.15 else "nonlinear"),
        }
    return {"summary": summ, "detail": out}


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  ZCX-SIZECAP - can a capped multiplier rescue curve_better?", flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import (
        load_bybit, bybit_bounds, load_binance)

    sim = build_module()
    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "zx_sizecap",
        "control_instrument": "BTCUSDT_BYBIT (established loaders)",
        "test_instrument": "BINANCE_FAPI_BTCUSDT_PERP (data/btc-fut, 24.82)",
        "lens": ("post-process sizing on FLAT books; trade keys identical; "
                 "no engine rerun (sizing exemption)"),
        "caps": list(CAPS), "size_ref": SIZE_REF,
        "arms": {a: f"x{{cap}} on {' OR '.join(f)} ({m})" for a, f, m in COMBO_ARMS},
        "years": years, "scopes": {"bybit": {}, "binance": {}},
        "pre_registered": {
            "arm_pass": "dNet>0 AND curve_better in ALL 6 cells on the TEST venue",
            "cross_venue": "the SAME cap passes all 6 cells on BOTH venues",
            "control": "bybit base ledgers + bybit uZX@1.50 dNet reproduce 24.86",
            "no_retune": "nothing is retuned after the run",
        },
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        byb = load_bybit(scope, sim)
        r_byb = run_venue("bybit", byb, sim, sim_fn, years[scope])
        for name, _ in LANES:
            exp_n, exp_net = BYBIT_BASE[name][scope]
            got = r_byb[name]
            assert got["n"] == exp_n, (
                f"CONTROL FAIL bybit/{scope}/{name} n: {got['n']} != {exp_n}")
            assert abs(got["net"] - exp_net) < 0.5, (
                f"CONTROL FAIL bybit/{scope}/{name} net: {got['net']} != {exp_net}")
        for name, (d_is_ref, d_oos_ref) in BYBIT_UZX_REF.items():
            a = r_byb[name]["arms"]["uZX"]["caps"]["1.50"]["d_net"]
            ref = d_is_ref if scope == "is" else d_oos_ref
            assert abs(a - ref) < 2.0, (
                f"CONTROL FAIL bybit/{scope}/{name} uZX@1.5 dNet: {a} != {ref} "
                f"(24.86) - harness is wrong, not the venue")
        print(f"  [control-ok] bybit/{scope}: base ledgers + uZX@1.5 reproduce 24.86",
              flush=True)
        payload["scopes"]["bybit"][scope] = r_byb

        bounds = bybit_bounds(byb, scope)
        bin_ = load_binance(scope, bounds)
        r_bin = run_venue("binance", bin_, sim, sim_fn, years[scope])
        payload["scopes"]["binance"][scope] = r_bin

        print("  binance cap sweep:", flush=True)
        for arm, _, _ in COMBO_ARMS:
            print(f"    {arm} (nAff={r_bin[LANES[0][0]]['arms'][arm]['n_affected']})",
                  flush=True)
            for cf in [f"{c:.2f}" for c in CAPS]:
                cells = [payload["scopes"]["binance"][scope][n]["arms"][arm]["caps"][cf]
                         for n, _ in LANES]
                npass = sum(1 for c in cells
                            if (c["d_net"] or 0) > 0 and c["curve_better"])
                dds = [c["d_max_dd"] for c in cells]
                print(f"      cap={cf}  {npass}/6 curve  dMaxDD={dds}", flush=True)

    # ---- verdicts -------------------------------------------------------
    pass_by_cap = {}
    for cap in [f"{c:.2f}" for c in CAPS]:
        for venue in ("binance", "bybit"):
            ok = all(
                (payload["scopes"][venue][s][n]["arms"][a]["caps"][cap]["d_net"] or 0) > 0
                and payload["scopes"][venue][s][n]["arms"][a]["caps"][cap]["curve_better"]
                for s in ("is", "oos") for n, _ in LANES for a, _, _ in COMBO_ARMS)
            pass_by_cap.setdefault(cap, {})[venue] = ok
    payload["pass_by_cap"] = pass_by_cap
    payload["any_cap_passes_binance"] = any(v["binance"] for v in pass_by_cap.values())
    payload["any_cap_passes_both"] = any(
        v["binance"] and v["bybit"] for v in pass_by_cap.values())

    def curve_cells(venue, cap):
        return sum(1 for s in ("is", "oos") for n, _ in LANES
                   for a, _, _ in COMBO_ARMS
                   if payload["scopes"][venue][s][n]["arms"][a]["caps"][cap]["curve_better"])

    payload["curve_cells_by_cap"] = {
        cap: {v: curve_cells(v, cap) for v in ("bybit", "binance")}
        for cap in pass_by_cap}
    payload["linearity"] = linearity(payload)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    print("  PASS BY CAP (binance / bybit):", flush=True)
    for cap, v in pass_by_cap.items():
        print(f"    cap={cap}  binance={v['binance']}  bybit={v['bybit']}  "
              f"curve-cells={payload['curve_cells_by_cap'][cap]}", flush=True)
    print("  LINEARITY TEST (predicted: d_max_dd linear in cap-1):", flush=True)
    for venue, s in payload["linearity"]["summary"].items():
        print(f"    {venue:<8} n={s['n']:<4} mean_dev={s['mean_abs_dev_from_linear']} "
              f"max_dev={s['max_abs_dev_from_linear']}  -> {s['verdict']}", flush=True)
    print("=" * 100, flush=True)
    print(f"  ANY CAP PASSES (binance): "
          f"{'YES' if payload['any_cap_passes_binance'] else 'NO'}", flush=True)
    print(f"  ANY CAP PASSES (both venues): "
          f"{'YES' if payload['any_cap_passes_both'] else 'NO'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
