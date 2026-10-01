"""Stage Shapes - sizing-FUNCTION sweep: continuous vs binary multipliers (2026-09-26).

Slice 1 (24.79) showed fixed x1.5 flag combinations all PASS. This run asks the
next question: is the SHAPE of the multiplier what matters? Arms compare a
threshold binary (M2 control), a threshold-free continuous ramp on leg
magnitude, an inverse-vol (risk-parity) target on every trade, a linear
flag-count scale, and the slice-1 union control - all on the same flat books.

PRE-REGISTERED BEFORE THE RUN (2026-09-26):
  Arms (ALL reported, no best-of hiding):
    base          1x reference
    M2_15         x1.5 if cur_mag_atr >= 3.0            (control: must reproduce
                  24.78 / +152.7/+29.1 champion, +147.5/+31.3 utcsat,
                  +113.0/+21.3 age10)
    ramp_mag      mult = clamp(1 + 0.25 * (cur_mag_atr - 2.0), 1.0, 2.0)
                  threshold-free continuous ramp (mag 3->1.25, 4->1.5,
                  >=6->2.0 cap; never downsizes)
    vol_target    mult = clamp(median_book_atrpct / trade_atrpct, 0.5, 2.0)
                  inverse-vol risk parity on EVERY trade; ATR% = _atr_pct_15m
                  at the entry 15m bar. CAVEAT pre-registered: the normalizer
                  is the full-book median (descriptive constant, mild
                  hindsight in the scale, not in trade selection).
    count_linear  mult = 1 + 0.5 * count(M2,ZC,X flags), capped 2.0
                  linear alternative to slice-1's multiplicative stack (1.5^n)
    uMZX          x1.5 if ANY of M2/ZC/X                 (control: must
                  reproduce 24.79 / +165.5/+49.5 champion etc.)
  Lanes: champion / utcsat / age10 flat configs. Scopes: IS+OOS.
  PASS (per non-control arm ramp_mag, vol_target, count_linear) = dNet > 0 AND
  curve_better TRUE in ALL 6 cells (3 lanes x 2 eras).
  Identity: trade key sequence byte-identical on every arm; ONLY r_multiple
  changes (positive multipliers preserve every sign, so the loss streak and
  trade selection are untouched - sizing exemption).
  Controls M2_15 and uMZX are reproduction checks: their numbers must match
  the prior runs (mismatch = abort before verdict).
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_sizing_shapes.py
"""
from __future__ import annotations

import bisect
import json
import statistics
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
from src.btc.engines.htf_ltf.v18_streak_halt import _atr_pct_15m
from exp_thesis_swing_geometry_deep import trade_rows

from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features
from exp_htf_break_sizing import flagged_keys
from exp_htf_break_measures import flatten_breaks, enrich_windows, map_children_measured
from exp_thesis_htf_deep_atlas import build_windows, window_rows

OUT = ROOT / "backtest/tests/_sizing_shapes_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
M2_MIN_ATR = 3.0
VOL7PREV_Q1 = 0.846
RAMP_ANCHOR = 2.0
RAMP_SLOPE = 0.25
RAMP_FLOOR, RAMP_CAP = 1.0, 2.0
VT_FLOOR, VT_CAP = 0.5, 2.0
COUNT_STEP, COUNT_CAP = 0.5, 2.0

EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

# control reproduction targets (dNet IS/OOS), from 24.78 (M2_15) and 24.79 (uMZX)
EXPECT_CONTROL = {
    "M2_15": {"champion": (152.7, 29.1), "utcsat": (147.5, 31.3), "age10": (113.0, 21.3)},
    "uMZX": {"champion": (165.5, 49.5), "utcsat": (171.3, 56.8), "age10": (145.9, 19.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)

ARMS = ("base", "M2_15", "ramp_mag", "vol_target", "count_linear", "uMZX")
TESTED = ("ramp_mag", "vol_target", "count_linear")

ARM_DESC = {
    "base": "1x reference",
    "M2_15": f"x{SIZE} if cur_mag_atr >= {M2_MIN_ATR} (control)",
    "ramp_mag": f"clamp(1 + {RAMP_SLOPE}*(cur_mag_atr - {RAMP_ANCHOR}), {RAMP_FLOOR}, {RAMP_CAP})",
    "vol_target": f"clamp(median_book_atrpct / trade_atrpct, {VT_FLOOR}, {VT_CAP})",
    "count_linear": f"1 + {COUNT_STEP}*count(M2,ZC,X) cap {COUNT_CAP}",
    "uMZX": f"x{SIZE} if any(M2,ZC,X) (control)",
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


def arm_mult(arm, mag, atr_pct, med_atrpct, cnt):
    if arm == "base":
        return 1.0
    if arm == "M2_15":
        return SIZE if (mag or 0) >= M2_MIN_ATR else 1.0
    if arm == "ramp_mag":
        return min(RAMP_CAP, max(RAMP_FLOOR, 1 + RAMP_SLOPE * ((mag or 0) - RAMP_ANCHOR)))
    if arm == "vol_target":
        if not atr_pct:
            return 1.0
        return min(VT_CAP, max(VT_FLOOR, med_atrpct / atr_pct))
    if arm == "count_linear":
        return min(COUNT_CAP, 1 + COUNT_STEP * cnt)
    if arm == "uMZX":
        return SIZE if cnt >= 1 else 1.0
    raise ValueError(arm)


def apply_arm(trades, mags, atr_pcts, cnts, med, arm):
    out = []
    n_aff = 0
    for t, mag, ap, cnt in zip(trades, mags, atr_pcts, cnts):
        mult = arm_mult(arm, mag, ap, med, cnt)
        t2 = dict(t)
        if mult != 1.0:
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
            n_aff += 1
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    return out, n_aff


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE SHAPES - SIZING-FUNCTION SWEEP (binary vs ramp vs vol-target vs count)",
          flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "sizing_shapes",
        "lens": "post-process sizing on FLAT books; identity = same trade keys; no automatic gate",
        "arms": ARM_DESC,
        "years": YEARS, "scopes": {},
        "pre_registered": "PASS per tested arm (ramp_mag, vol_target, count_linear) = dNet>0 AND curve_better TRUE in all 6 cells (3 lanes x 2 eras)",
        "controls": "M2_15 must reproduce 24.78; uMZX must reproduce 24.79 (abort on mismatch > 1.0 dNet)",
        "baseline_reference": "champion 500/+325.8 IS, 279/+70.2 OOS; utcsat 454/+358.9, 253/+60.2; age10 130/+435.7, 76/+43.2 (asserted)",
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]

        # ZC context (Stage Z2 path)
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

        # X context (Stage X path)
        fine_ts = [int(c["ts"]) for c in data["fine"]]
        breaks = flatten_breaks(data["sw10"])
        raw = build_windows(data, 3.0, 16)
        windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
                   for lane, rows in raw.items()}
        for lane in windows:
            enrich_windows(windows[lane], data["c1h"], breaks)

        # ATR% series for vol_target (per 15m bar)
        atr_pct_series = _atr_pct_15m(data["c15"])
        ts15 = [int(c["ts"]) for c in data["c15"]]

        sc = {}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
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

            rows = trade_rows(trades, data)
            assert len(rows) == len(trades), (
                f"trade_rows coverage {len(rows)}/{len(trades)} - features incomplete")
            mag_by_key = {(int(r["entry_ts"]), int(r["exit_ts"])):
                          (r.get("cur_mag_atr") or 0) for r in rows}
            mags = [mag_by_key[(int(t["entry_ts"]), int(t["exit_ts"]))] for t in trades]
            atr_pcts = []
            for t in trades:
                ei = max(0, bisect.bisect_right(ts15, int(t["entry_ts"])) - 1)
                v = atr_pct_series[ei] if 0 <= ei < len(atr_pct_series) else None
                atr_pcts.append(float(v) if v else None)
            med_atrpct = statistics.median([a for a in atr_pcts if a])

            feats = [compute_features(t, ctx0) for t in trades]
            k_zc = {(int(t["entry_ts"]), int(t["exit_ts"]))
                    for t, f in zip(trades, feats)
                    if f.get("vol7_prev7") is not None
                    and f["vol7_prev7"] <= VOL7PREV_Q1}
            k_x = flagged_keys(trades, windows, "risk_pct", -1e9, 1.0)
            k_m2 = {(int(t["entry_ts"]), int(t["exit_ts"])) for t, m in zip(trades, mags)
                    if m >= M2_MIN_ATR}
            cnts = [sum(1 for ks in (k_m2, k_zc, k_x)
                        if (int(t["entry_ts"]), int(t["exit_ts"])) in ks)
                    for t in trades]

            print(f"\n  {name} (n={m_flat['n']})  med_atrpct={med_atrpct:.4f}  "
                  f"flags M2={len(k_m2)} ZC={len(k_zc)} X={len(k_x)}  "
                  f"cnt-hist { {c: cnts.count(c) for c in sorted(set(cnts))} }", flush=True)
            print(f"    {'arm':<13} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} curve",
                  flush=True)
            arms_out = {}
            for arm in ARMS:
                book, n_aff = apply_arm(trades, mags, atr_pcts, cnts, med_atrpct, arm)
                m = equity_quality(book, yrs)
                d = arm_scores(m, m_flat)
                cb = curve_better(d)
                small = " SMALL-N" if 0 < n_aff < 20 else ""
                print(f"    {arm:<13} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
                      f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f} "
                      f"{d.get('d_net', 0):>+8.1f} {cb}{small}", flush=True)
                arms_out[arm] = {"n_affected": n_aff, "metric": m, "delta": d,
                                 "curve_better": cb}
            sc[name] = {
                "n": m_flat["n"], "med_atrpct": round(med_atrpct, 5),
                "flag_counts": {"M2": len(k_m2), "ZC": len(k_zc), "X": len(k_x)},
                "cnt_hist": {str(c): cnts.count(c) for c in sorted(set(cnts))},
                "arms": arms_out, "identity_ok": True,
            }
        payload["scopes"][scope] = sc

    print("\n=== CONTROL REPRODUCTION CHECK ===", flush=True)
    ctrl_ok = True
    for arm, per_lane in EXPECT_CONTROL.items():
        for name, (e_is, e_oos) in per_lane.items():
            d_is = payload["scopes"]["is"][name]["arms"][arm]["delta"].get("d_net") or 0
            d_oos = payload["scopes"]["oos"][name]["arms"][arm]["delta"].get("d_net") or 0
            ok = abs(d_is - e_is) <= 1.0 and abs(d_oos - e_oos) <= 1.0
            ctrl_ok = ctrl_ok and ok
            print(f"  {arm:<9} {name:<10} got {d_is:+8.1f}/{d_oos:+7.1f} "
                  f"want {e_is:+8.1f}/{e_oos:+7.1f}  {'OK' if ok else 'MISMATCH'}",
                  flush=True)
    payload["controls_ok"] = ctrl_ok

    print("\n=== CROSS-ERA VERDICT (per arm, per lane) ===", flush=True)
    verdicts = {}
    for arm in ARMS:
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
            print(f"  {arm:<13} {name:<10} nAff {v['n_aff_is']:>3}/{v['n_aff_oos']:<3} "
                  f"dNet {v['d_net_is']:+8.1f}/{v['d_net_oos']:+7.1f} "
                  f"dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f} "
                  f"curve {int(v['curve_better_is'])}/{int(v['curve_better_oos'])} "
                  f"cell={v['cell_pass']}", flush=True)
    payload["verdicts"] = verdicts

    payload["pass_all_6"] = {}
    for arm in ARMS:
        cells = [verdicts[f"{arm}_{n}"]["cell_pass"] for n, _ in LANES]
        payload["pass_all_6"][arm] = all(cells)
        mark = " (tested)" if arm in TESTED else " (control)"
        print(f"  PASS 6/6 {arm}{mark}: {payload['pass_all_6'][arm]}", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nPRE-REGISTERED (ramp_mag/vol_target/count_linear): "
          f"{'ALL PASS' if all(payload['pass_all_6'][a] for a in TESTED) else 'NOT ALL PASS'}"
          f" | controls: {'OK' if ctrl_ok else 'MISMATCH - distrust verdict'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
