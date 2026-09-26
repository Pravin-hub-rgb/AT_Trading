"""Bybit-only structure + volume autopsy.

Descriptive combinations not covered by the earlier simple volume/route/era
harnesses: era x causal volume state, B1/B2/FLIP mark geometry, swing-to-swing
anchors/distances, and route disagreement. No production change.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import statistics
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
from test_4_new_concepts import load_unseen, load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import _atr_pct_15m, _chop_series_1h
from engine.v18_params import SWING

OUT = {"is": ROOT / "live_stuff/tests/_thesis_structure_volume_results_is.json",
       "oos": ROOT / "live_stuff/tests/_thesis_structure_volume_results_oos.json"}
CONFIGS = ("fullstack_wage10_cd0_single_sw10", "champion_multi_sw10", "utcsat_multi_sw10")
CHOP_THRESH = 58.0
ATR_HIGH_THRESH = 0.65


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        from src.btc.btc_routes import _compute_swings
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        fine = load_fine_1m(c15[0]["ts"], c15[-1]["ts"])
        return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h, "sw15": sw15, "sw10": sw10, "fine": fine}
    data = get_data()
    identity_gate(data, build_module())
    return data


def causal_volume(candles, window):
    vols = [float(c.get("volume") or 0.0) for c in candles]
    pct = [50.0] * len(vols)
    ratio = [1.0] * len(vols)
    for i in range(len(vols)):
        lo = max(0, i - window)
        if i - lo < 8:
            continue
        prior = vols[lo:i]
        avg = sum(prior) / len(prior)
        ratio[i] = vols[i] / avg if avg > 0 else 1.0
        pct[i] = 100.0 * sum(v <= vols[i] for v in prior) / len(prior)
    return {"volume": vols, "pct": pct, "ratio": ratio}


def bar_index(candles, entry_ts, step):
    ts = [int(c["ts"]) for c in candles]
    return max(0, bisect.bisect_right(ts, int(entry_ts) - step) - 1)


def atr(candles, i, n=14):
    lo = max(0, i - n + 1)
    hi = max(float(c["high"]) for c in candles[lo:i + 1])
    low = min(float(c["low"]) for c in candles[lo:i + 1])
    return max(hi - low, 1e-9)


def mark_time(mark):
    return int(mark.get("time_epoch", mark.get("ts", 0)) or 0)


def build_marks(swings):
    out = []
    for sw in swings:
        for m in sw.get("breaks") or []:
            idx = int(m.get("idx", -1))
            out.append({"swing": sw, "idx": idx, "time": m.get("time", ""),
                        "kind": m.get("kind", ""), "dir": m.get("dir", ""),
                        "px": float(m.get("px", 0.0))})
    return sorted(out, key=lambda x: (x["idx"], x["time"], x["kind"]))


def trade_features(trades, data, scope):
    c15, c1h, sw15 = data["c15"], data["c1h"], data["sw15"]
    v15 = causal_volume(c15, 96)
    v1h = causal_volume(c1h, 24)
    hts = [int(c["ts"]) + 3600 for c in c1h]
    chop = _chop_series_1h(c1h, lb=14)
    atr_pct_series = _atr_pct_15m(c15)
    marks = build_marks(sw15)
    mark_idx = {m["idx"]: m for m in marks}
    by_swing = defaultdict(list)
    for m in marks:
        by_swing[int(m["swing"].get("swing_index", -1))].append(m)
    rows = []
    for t in trades:
        i15 = bar_index(c15, int(t["entry_ts"]), 900)
        i1h = max(0, bisect.bisect_right(hts, int(t["entry_ts"]) + 900) - 1)
        si = int(t.get("swing_no", -1))
        entry = float(t["entry_price"])
        current = next((s for s in sw15 if int(s.get("swing_index", -1)) == si), None)
        smarks = by_swing.get(si, [])
        sig = mark_idx.get(i15, {})
        if sig.get("swing") is None and current is not None:
            sig = {"swing": current, "idx": i15, "kind": t.get("break_kind", "?"),
                   "dir": "up" if t.get("dir") == "long" else "down", "px": entry}
        smarks_before = [m for m in smarks if m["idx"] <= i15]
        kinds = [m["kind"] for m in smarks_before]
        prev = None
        for j, s in enumerate(sw15):
            if s is current:
                if j > 0:
                    prev = sw15[j - 1]
                break
        seg = (current or {}).get("seg", {})
        prevseg = (prev or {}).get("seg", {})
        entry = float(t["entry_price"])
        atr15 = atr(c15, i15)
        # The engine's actual atr_high route: decisive when 15m ATR% > 0.65.
        atr_pct = atr_pct_series[i15]
        route_expected = "decisive" if atr_pct > ATR_HIGH_THRESH else "flip"
        chop_lane = "B2" if chop[i1h] > CHOP_THRESH else "FLIP"
        signal_lane = "B2" if t.get("break_kind") == "B2" else "FLIP" if t.get("break_kind") == "FLIP" else "DEC"
        signal_chop_conflict = int(signal_lane in ("B2", "FLIP") and signal_lane != chop_lane)
        cur_start = float(seg.get("start_px", 0.0) or 0.0)
        cur_end = float(seg.get("end_px", 0.0) or 0.0)
        prev_end = float(prevseg.get("end_px", 0.0) or 0.0)
        prev_start = float(prevseg.get("start_px", 0.0) or 0.0)
        fs_idx = int((sig.get("swing", {}).get("fs_at_idx", -1) if sig else -1))
        b1 = next((m for m in smarks_before if m["kind"] == "B1"), None)
        b2 = next((m for m in smarks_before if m["kind"] == "B2"), None)
        flip = next((m for m in smarks_before if m["kind"] == "FLIP"), None)
        route = t.get("htf_regime", "?")
        rows.append({
            **t, "scope": scope, "i15": i15, "year": str(t.get("entry_date", ""))[:4],
            "vol15": v15["volume"][i15], "rvol15": v15["ratio"][i15], "pct15": v15["pct"][i15],
            "vol1h": v1h["volume"][i1h], "rvol1h": v1h["ratio"][i1h], "pct1h": v1h["pct"][i1h],
            "chop": chop[i1h], "route": route, "route_expected": route_expected,
            "route_conflict": int(route != route_expected),
            "chop_lane": chop_lane, "signal_lane": signal_lane,
            "signal_chop_conflict": signal_chop_conflict,
            "kind": t.get("break_kind", "?"), "swing_no": si,
            "swing_dir": seg.get("dir", "?"), "swing_source": seg.get("source", "?"),
            "mark_sequence": ">".join(kinds) if kinds else "?",
            "marks_before": len(smarks_before), "b1": int(b1 is not None), "b2": int(b2 is not None), "flip": int(flip is not None),
            "fs_age_bars": i15 - fs_idx if fs_idx >= 0 else None,
            "b1_to_entry_bars": i15 - int(b1["idx"]) if b1 else None,
            "b1_b2_bars": int(b2["idx"] - b1["idx"]) if b1 and b2 else None,
            "b1_flip_bars": int(flip["idx"] - b1["idx"]) if b1 and flip else None,
            "entry_minus_prev_end_atr": (entry - prev_end) / atr15 if prev_end else None,
            "entry_minus_cur_start_atr": (entry - cur_start) / atr15 if cur_start else None,
            "swing_mag_atr": abs(cur_end - cur_start) / atr15 if cur_start and cur_end else None,
            "prev_swing_mag_atr": abs(prev_end - prev_start) / atr15 if prev_end and prev_start else None,
            "win": float(t.get("r_multiple", 0.0)) > 0,
            "runner": float(t.get("r_multiple", 0.0)) >= 3.0,
        })
    return rows


def summary(rows):
    if not rows:
        return {"n": 0}
    gross = [float(r.get("r_multiple", 0.0)) for r in rows]
    net = [net_r([dict(r)]) for r in rows]
    gw = [x for x in gross if x > 0]
    gl = [x for x in gross if x <= 0]
    nw = [x for x in net if x > 0]
    nl = [x for x in net if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in net:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x > 0: ws += 1; ls = 0
        else: ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    pf = sum(nw) / abs(sum(nl)) if nl and sum(nl) else None
    years = defaultdict(lambda: {"n": 0, "gross_r": 0.0, "net_r": 0.0})
    for r, g, n in zip(rows, gross, net):
        y = str(r.get("year") or r.get("entry_date", ""))[:4]
        years[y]["n"] += 1; years[y]["gross_r"] += g; years[y]["net_r"] += n
    return {
        "n": len(rows), "gross_r": round(sum(gross), 3), "net_r": round(sum(net), 3),
        "gross_avg_r": round(sum(gross) / len(rows), 4),
        "net_avg_r": round(sum(net) / len(rows), 4),
        "wins": sum(x > 0 for x in gross), "losses": sum(x <= 0 for x in gross),
        "win_rate_pct": round(100.0 * sum(x > 0 for x in gross) / len(rows), 3),
        "avg_gross_win": round(sum(gw) / len(gw), 4) if gw else 0.0,
        "avg_gross_loss": round(sum(gl) / len(gl), 4) if gl else 0.0,
        "avg_net_win": round(sum(nw) / len(nw), 4) if nw else 0.0,
        "avg_net_loss": round(sum(nl) / len(nl), 4) if nl else 0.0,
        "gross_pf": round(sum(gw) / abs(sum(gl)), 4) if gl else None,
        "net_pf": round(pf, 4) if pf is not None else None,
        "max_net_dd": round(dd, 4), "max_loss_streak": mls, "max_win_streak": mws,
        "runners_3r": sum(x >= 3.0 for x in gross), "runners_5r": sum(x >= 5.0 for x in gross),
        "runners_10r": sum(x >= 10.0 for x in gross), "runner_r": round(sum(x for x in gross if x >= 3.0), 3),
        "yearly": {k: {**v, "gross_r": round(v["gross_r"], 3), "net_r": round(v["net_r"], 3)} for k, v in sorted(years.items())},
    }


def bucket(rows, key_fn, order=None):
    groups = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)
    keys = order or sorted(groups, key=str)
    return {str(k): summary(groups[k]) for k in keys if k in groups}


def report_config(name, rows):
    return {
        "baseline": summary(rows),
        "by_year": bucket(rows, lambda r: r["year"]),
        "by_direction": bucket(rows, lambda r: r.get("dir", "?")),
        "by_signal_kind": bucket(rows, lambda r: r.get("kind", "?")),
        "by_mark_sequence": bucket(rows, lambda r: r.get("mark_sequence", "?")),
        "by_marks_before": bucket(rows, lambda r: r.get("marks_before", 0)),
        "by_b1_b2_timing": bucket(rows, lambda r: "none" if r.get("b1_b2_bars") is None else ("0-2" if r["b1_b2_bars"] <= 2 else "3-8" if r["b1_b2_bars"] <= 8 else "9-24" if r["b1_b2_bars"] <= 24 else "25+")),
        "by_b1_flip_timing": bucket(rows, lambda r: "none" if r.get("b1_flip_bars") is None else ("0-2" if r["b1_flip_bars"] <= 2 else "3-8" if r["b1_flip_bars"] <= 8 else "9-24" if r["b1_flip_bars"] <= 24 else "25+")),
        "by_fs_age": bucket(rows, lambda r: "none" if r.get("fs_age_bars") is None else ("0-4" if r["fs_age_bars"] <= 4 else "5-12" if r["fs_age_bars"] <= 12 else "13-48" if r["fs_age_bars"] <= 48 else "49+")),
        "by_b1_entry_age": bucket(rows, lambda r: "none" if r.get("b1_to_entry_bars") is None else ("0-2" if r["b1_to_entry_bars"] <= 2 else "3-8" if r["b1_to_entry_bars"] <= 8 else "9-24" if r["b1_to_entry_bars"] <= 24 else "25+")),
        "by_chop_lane": bucket(rows, lambda r: r.get("chop_lane", "?")),
        "by_signal_lane": bucket(rows, lambda r: r.get("signal_lane", "?")),
        "by_signal_chop_conflict": bucket(rows, lambda r: r.get("signal_chop_conflict", 0)),
        "by_route_expected": bucket(rows, lambda r: r.get("route_expected", "?")),
        "by_actual_route": bucket(rows, lambda r: r.get("route", "?")),
        "by_route_conflict": bucket(rows, lambda r: r.get("route_conflict", 0)),
        "by_rvol15": bucket(rows, lambda r: "<0.75" if r["rvol15"] < .75 else "0.75-1" if r["rvol15"] < 1 else "1-1.5" if r["rvol15"] < 1.5 else "1.5-2" if r["rvol15"] < 2 else "2+"),
        "by_rvol1h": bucket(rows, lambda r: "<0.75" if r["rvol1h"] < .75 else "0.75-1" if r["rvol1h"] < 1 else "1-1.5" if r["rvol1h"] < 1.5 else "1.5-2" if r["rvol1h"] < 2 else "2+"),
        "by_pct15": bucket(rows, lambda r: "<25" if r["pct15"] < 25 else "25-50" if r["pct15"] < 50 else "50-75" if r["pct15"] < 75 else "75-90" if r["pct15"] < 90 else "90+"),
        "by_era_volume": bucket(rows, lambda r: f"{r['year']}:{'low' if r['rvol15'] < .75 else 'mid' if r['rvol15'] < 1.5 else 'high'}"),
        "by_prev_end_distance": bucket(rows, lambda r: "none" if r.get("entry_minus_prev_end_atr") is None else "<-1" if r["entry_minus_prev_end_atr"] < -1 else "-1..0" if r["entry_minus_prev_end_atr"] < 0 else "0..1" if r["entry_minus_prev_end_atr"] < 1 else "1+"),
        "by_current_start_distance": bucket(rows, lambda r: "none" if r.get("entry_minus_cur_start_atr") is None else "<-1" if r["entry_minus_cur_start_atr"] < -1 else "-1..0" if r["entry_minus_cur_start_atr"] < 0 else "0..1" if r["entry_minus_cur_start_atr"] < 1 else "1+"),
        "by_swing_magnitude": bucket(rows, lambda r: "none" if r.get("swing_mag_atr") is None else "<1" if r["swing_mag_atr"] < 1 else "1-2" if r["swing_mag_atr"] < 2 else "2-4" if r["swing_mag_atr"] < 4 else "4+"),
        "by_previous_swing_magnitude": bucket(rows, lambda r: "none" if r.get("prev_swing_mag_atr") is None else "<1" if r["prev_swing_mag_atr"] < 1 else "1-2" if r["prev_swing_mag_atr"] < 2 else "2-4" if r["prev_swing_mag_atr"] < 4 else "4+"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    started = time.time()
    all_result = {"stage": 24, "instrument": "BTCUSDT_BYBIT", "scopes": {}}
    for scope in scopes:
        print("=" * 110, flush=True)
        print(f"  STRUCTURE + VOLUME AUTOPSY — BYBIT {scope.upper()}", flush=True)
        print("=" * 110, flush=True)
        data = load_scope(scope)
        sim = build_module()
        result = {}
        for key in CONFIGS:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            rows = trade_features(trades, data, scope)
            result[key] = report_config(key, rows)
            b = result[key]["baseline"]
            print(f"  {key:38} n={b['n']:4d} G={b['gross_r']:+8.1f} N={b['net_r']:+8.1f} WR={b['win_rate_pct']:5.1f}% PFg={b['gross_pf'] or 0:5.2f} DDn={b['max_net_dd']:6.1f}", flush=True)
        all_result["scopes"][scope] = result
        out_path = OUT[scope]
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {out_path}", flush=True)
    all_result["elapsed_sec"] = round(time.time() - started, 2)
    print(f"done in {all_result['elapsed_sec']:.1f}s", flush=True)


if __name__ == "__main__":
    main()

