"""Stage Combo - combination matrix on the three surviving sizing flags (2026-09-26).

Cross-cutting gap (EXPERIMENT_SUMMARY Comparison, 24.77): "combinations
(M2 + ONE Z flag + X/Y) are UNTESTED - any combo needs its own pre-registered
run." This is that run, on the flat books.

Flags (each validated individually on flat books, sizing exemption applies):
  M2 = cur_mag_atr >= 3.0            (flat PASS 6/6, 24.78)
  ZC = vol7_prev7 <= 0.846           (Z arm C, 4/4, best OOS of the Z family)
  X  = parent window risk_pct < 1.0  (PASS 4/4, smallest edge)

PRE-REGISTERED BEFORE THE RUN (2026-09-26):
  Arms (ALL reported, no best-of hiding):
    base   1x reference
    M2     x1.5 on M2 keys                      (single-flag control)
    ZC     x1.5 on ZC keys                      (single-flag control)
    X      x1.5 on X keys                       (single-flag control)
    uMZ    x1.5 when M2 OR ZC                   (union mode)
    uMZX   x1.5 when M2 OR ZC OR X              (union mode)
    sMZ    x1.5^count on M2/ZC                  (stacked multiplicative)
    sMZX   x1.5^count on M2/ZC/X                (stacked multiplicative)
  Lanes: champion / utcsat / age10 flat configs (NO arm flags). Scopes: IS+OOS.
  PASS (per combo arm: uMZ, uMZX, sMZ, sMZX) = dNet > 0 AND curve_better
  TRUE in ALL 6 cells (3 lanes x 2 eras) - M2 flat's strictness.
  Identity: trade key sequence (entry_ts, exit_ts) byte-identical on every
  arm; ONLY r_multiple differs (sizing exemption: sizing never changes which
  trades fire, so post-process = path-true by construction).
  Flag paths: M2 from trade_rows (24.78 path); ZC from
  exp_regime_structure_autopsy.compute_features (Stage Z2 path); X from
  exp_htf_break_sizing.flagged_keys (Stage X path).
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_sizing_combo.py
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

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING
from exp_thesis_swing_geometry_deep import trade_rows

from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features
from exp_htf_break_sizing import flagged_keys
from exp_htf_break_measures import flatten_breaks, enrich_windows, map_children_measured
from exp_thesis_htf_deep_atlas import build_windows, window_rows

OUT = ROOT / "backtest/tests/_sizing_combo_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
M2_MIN_ATR = 3.0
VOL7PREV_Q1 = 0.846

EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)

# arm -> (families used, mode union|stack)
ARMS = (
    ("base", (), "union"),
    ("M2", ("M2",), "union"),
    ("ZC", ("ZC",), "union"),
    ("X", ("X",), "union"),
    ("uMZ", ("M2", "ZC"), "union"),
    ("uMZX", ("M2", "ZC", "X"), "union"),
    ("sMZ", ("M2", "ZC"), "stack"),
    ("sMZX", ("M2", "ZC", "X"), "stack"),
)
COMBO_ARMS = ("uMZ", "uMZX", "sMZ", "sMZX")

ARM_DESC = {
    "base": "1x reference",
    "M2": f"x{SIZE} on cur_mag_atr >= {M2_MIN_ATR}",
    "ZC": f"x{SIZE} on vol7_prev7 <= {VOL7PREV_Q1}",
    "X": f"x{SIZE} on parent risk_pct < 1.0",
    "uMZ": f"x{SIZE} when M2 OR ZC (union)",
    "uMZX": f"x{SIZE} when M2 OR ZC OR X (union)",
    "sMZ": f"x{SIZE}^count on M2/ZC (stack)",
    "sMZX": f"x{SIZE}^count on M2/ZC/X (stack)",
}


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


def apply_arm(trades, fam_keys, fams, mode):
    """Return book with multipliers applied; identity = same key sequence."""
    out = []
    for t in trades:
        k = (int(t["entry_ts"]), int(t["exit_ts"]))
        cnt = sum(1 for f in fams if k in fam_keys[f])
        t2 = dict(t)
        if cnt:
            mult = SIZE if mode == "union" else SIZE ** cnt
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print(f"  STAGE COMBO - SIZING COMBINATION MATRIX (M2 x ZC x X, union vs stack, flat books)",
          flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "sizing_combo",
        "lens": "post-process sizing on FLAT books; identity = same trade keys; no automatic gate",
        "arms": ARM_DESC,
        "years": YEARS, "scopes": {},
        "pre_registered": "PASS per combo arm = dNet>0 AND curve_better TRUE in all 6 cells (3 lanes x 2 eras)",
        "baseline_reference": "champion 500/+325.8 IS, 279/+70.2 OOS; utcsat 454/+358.9, 253/+60.2; age10 130/+435.7, 76/+43.2 (asserted)",
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]

        # --- ZC context (Stage Z2 path) ---
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

        # --- X context (Stage X path) ---
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
                f"flat ledger n mismatch {name}/{scope}: "
                f"{m_flat['n']} != {exp_n} - not the flat reference book")
            assert abs(m_flat["net"] - exp_net) < 0.5, (
                f"flat ledger net mismatch {name}/{scope}: "
                f"{m_flat['net']} != {exp_net} - not the flat reference book")
            print(f"  [ledger-ok] {name}/{scope}: n={m_flat['n']} "
                  f"net={m_flat['net']:+.1f} matches reference", flush=True)

            # --- flag keys (three paths) ---
            rows = trade_rows(trades, data)
            row_keys = {(int(r["entry_ts"]), int(r["exit_ts"])) for r in rows}
            k_m2 = {(int(r["entry_ts"]), int(r["exit_ts"])) for r in rows
                    if (r.get("cur_mag_atr") or 0) >= M2_MIN_ATR}
            feats = [compute_features(t, ctx0) for t in trades]
            k_zc = {(int(t["entry_ts"]), int(t["exit_ts"]))
                    for t, f in zip(trades, feats)
                    if f.get("vol7_prev7") is not None
                    and f["vol7_prev7"] <= VOL7PREV_Q1}
            k_x = flagged_keys(trades, windows, "risk_pct", -1e9, 1.0)
            fam_keys = {"M2": k_m2, "ZC": k_zc, "X": k_x}

            cnt_hist = {0: 0, 1: 0, 2: 0, 3: 0}
            for t in trades:
                k = (int(t["entry_ts"]), int(t["exit_ts"]))
                c = sum(1 for f in ("M2", "ZC", "X") if k in fam_keys[f])
                cnt_hist[c] += 1

            print(f"\n  {name} (n={m_flat['n']})  flagged M2={len(k_m2)} "
                  f"ZC={len(k_zc)} X={len(k_x)}  hist0-3={cnt_hist}  "
                  f"rows {len(row_keys)}/{len(trades)}", flush=True)
            print(f"    {'arm':<7} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} curve",
                  flush=True)
            arms_out = {}
            for arm, fams, mode in ARMS:
                if arm == "base":
                    book = trades
                    n_aff = 0
                else:
                    book = apply_arm(trades, fam_keys, fams, mode)
                    n_aff = sum(1 for t in trades
                                if any((int(t["entry_ts"]), int(t["exit_ts"])) in fam_keys[f]
                                       for f in fams))
                m = equity_quality(book, yrs)
                d = arm_scores(m, m_flat)
                cb = curve_better(d)
                small = " SMALL-N" if 0 < n_aff < 20 else ""
                print(f"    {arm:<7} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
                      f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f} "
                      f"{d.get('d_net', 0):>+8.1f} {cb}{small}", flush=True)
                arms_out[arm] = {"n_affected": n_aff, "metric": m, "delta": d,
                                 "curve_better": cb}
            sc[name] = {
                "n": m_flat["n"],
                "flag_counts": {"M2": len(k_m2), "ZC": len(k_zc), "X": len(k_x)},
                "flag_hist": cnt_hist,
                "rows_covered": f"{len(row_keys)}/{len(trades)}",
                "arms": arms_out,
                "identity_ok": True,
            }
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (per arm, per lane) ===", flush=True)
    verdicts = {}
    for arm, _f, _m in ARMS:
        for name, _ in LANES:
            a_is = payload["scopes"]["is"][name]["arms"][arm]
            a_oos = payload["scopes"]["oos"][name]["arms"][arm]
            d_is, d_oos = a_is["delta"], a_oos["delta"]
            v = {"desc": ARM_DESC[arm],
                 "n_aff_is": a_is["n_affected"], "n_aff_oos": a_oos["n_affected"],
                 "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                 "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
                 "curve_better_is": curve_better(d_is),
                 "curve_better_oos": curve_better(d_oos)}
            v["cell_pass"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0 and \
                             v["curve_better_is"] and v["curve_better_oos"]
            verdicts[f"{arm}_{name}"] = v
            print(f"  {arm:<7} {name:<10} nAff {v['n_aff_is']:>3}/{v['n_aff_oos']:<3} "
                  f"dNet {v['d_net_is']:+8.1f}/{v['d_net_oos']:+7.1f} "
                  f"dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f} "
                  f"curve {int(v['curve_better_is'])}/{int(v['curve_better_oos'])} "
                  f"cell={v['cell_pass']}", flush=True)
    payload["verdicts"] = verdicts

    payload["pass_all_6"] = {}
    for arm in [a for a, _f, _m in ARMS if a != "base"]:
        cells = [verdicts[f"{arm}_{n}"]["cell_pass"] for n, _ in LANES]
        payload["pass_all_6"][arm] = all(cells)
        print(f"  PASS 6/6 {arm}: {payload['pass_all_6'][arm]}  ({ARM_DESC[arm]})",
              flush=True)
    combo_pass = all(payload["pass_all_6"][a] for a in COMBO_ARMS)
    payload["combo_pass_all_arms"] = combo_pass

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nPRE-REGISTERED RULE (per combo arm uMZ/uMZX/sMZ/sMZX): "
          f"{'ALL PASS' if combo_pass else 'NOT ALL PASS - see per-arm above'}",
          flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
