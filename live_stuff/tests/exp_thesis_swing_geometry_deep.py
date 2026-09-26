"""Deep cross-swing FirstSwing mark geometry autopsy (Bybit BTCUSDT perp).

Read-only. Compares previous-swing FS/final mark geometry with the current
swing's start, B1, B2/FLIP signal and entry. No engine changes or path-true
policy is implied by this descriptive study.
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
from test_experiments_craze import build_module
from exp_thesis_structure_volume import load_scope, summary, CONFIGS
from src.btc.engines.htf_ltf.v18_streak_halt import _atr_pct_15m, _chop_series_1h

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_swing_geometry_deep_results_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_swing_geometry_deep_results_oos.json",
}
CHOP_THRESH = 58.0
ATR_HIGH_THRESH = 0.65


def mark_before(swing, idx):
    return sorted([m for m in (swing.get("breaks") or []) if int(m.get("idx", -1)) <= idx],
                  key=lambda m: (int(m.get("idx", -1)), m.get("kind", "")))


def first_mark(swing, kind, idx):
    return next((m for m in mark_before(swing, idx) if m.get("kind") == kind), None)


def last_mark(swing, idx):
    marks = mark_before(swing, idx)
    return marks[-1] if marks else None


def dir_num(value):
    return 1 if value in ("up", "long", "B") else -1 if value in ("down", "short", "S") else 0


def feature_stats(rows, fields):
    out = {}
    groups = (("all", rows), ("winners", [r for r in rows if r["r_multiple"] > 0]),
              ("losses", [r for r in rows if r["r_multiple"] <= 0]),
              ("runners", [r for r in rows if r["r_multiple"] >= 3.0]))
    for label, subset in groups:
        block = {}
        for field in fields:
            values = [float(r[field]) for r in subset if r.get(field) is not None]
            block[field] = None if not values else {
                "n": len(values), "mean": round(sum(values) / len(values), 4),
                "median": round(statistics.median(values), 4),
                "q10": round(sorted(values)[max(0, int(.10 * len(values)) - 1)], 4),
                "q90": round(sorted(values)[min(len(values) - 1, int(.90 * len(values)))], 4),
            }
        out[label] = block
    return out


def bar_bucket(value):
    if value is None:
        return "none"
    for lo, hi, name in ((0, 2, "0-1"), (2, 8, "2-7"), (8, 24, "8-23"),
                         (24, 48, "24-47"), (48, 96, "48-95")):
        if lo <= value < hi:
            return name
    return "96+"


def atr_at(candles, idx, n=14):
    lo = max(0, idx - n + 1)
    hi = max(float(c["high"]) for c in candles[lo:idx + 1])
    low = min(float(c["low"]) for c in candles[lo:idx + 1])
    return max(hi - low, 1e-9)


def trade_rows(trades, data):
    c15, c1h, sw15 = data["c15"], data["c1h"], data["sw15"]
    ts15 = [int(c["ts"]) for c in c15]
    hclose = [int(c["ts"]) + 3600 for c in c1h]
    chop = _chop_series_1h(c1h, lb=14)
    atr_pct = _atr_pct_15m(c15)
    by_index = {int(s.get("swing_index", -1)): (j, s) for j, s in enumerate(sw15)}
    rows = []
    for trade in trades:
        entry_idx = max(0, bisect.bisect_right(ts15, int(trade["entry_ts"])) - 1)
        si = int(trade.get("swing_no", -1))
        cur_j, cur = by_index.get(si, (-1, None))
        if cur is None or cur_j <= 0:
            continue
        prev = sw15[cur_j - 1]
        cur_marks = mark_before(cur, entry_idx)
        signal = first_mark(cur, trade.get("break_kind", "?"), entry_idx) or last_mark(cur, entry_idx)
        b1 = first_mark(cur, "B1", entry_idx)
        prev_last = last_mark(prev, entry_idx)
        prev_b1 = first_mark(prev, "B1", entry_idx)
        prev_fs_idx = int(prev.get("fs_at_idx", prev.get("confirmed_at_idx", -1)))
        seg, prev_seg = cur.get("seg", {}), prev.get("seg", {})
        cur_start_idx = int(seg.get("start_idx", entry_idx))
        cur_start_px = float(seg.get("start_px", trade["entry_price"]))
        prev_end_px = float(prev_seg.get("end_px", cur_start_px))
        prev_fs_px = float(c15[prev_fs_idx]["close"]) if 0 <= prev_fs_idx < len(c15) else None
        signal_idx = int(signal.get("idx", entry_idx)) if signal else entry_idx
        signal_px = float(signal.get("px", trade["entry_price"])) if signal else float(trade["entry_price"])
        b1_idx = int(b1.get("idx", -1)) if b1 else -1
        b1_px = float(b1.get("px", cur_start_px)) if b1 else None
        prev_last_idx = int(prev_last.get("idx", -1)) if prev_last else -1
        prev_last_px = float(prev_last.get("px", prev_end_px)) if prev_last else prev_end_px
        prev_b1_idx = int(prev_b1.get("idx", -1)) if prev_b1 else -1
        atr15 = atr_at(c15, entry_idx)
        i1h = max(0, bisect.bisect_right(hclose, int(trade["entry_ts"]) + 900) - 1)
        raw_route = "decisive" if atr_pct[entry_idx] > ATR_HIGH_THRESH else "flip"
        actual_route = trade.get("htf_regime", "?")
        signal_kind = trade.get("break_kind", "?")
        cur_dir = dir_num(cur.get("dir")); prev_dir = dir_num(prev.get("dir"))
        sig_dir = dir_num(signal.get("dir")) if signal else dir_num(trade.get("dir"))
        rows.append({
            **trade, "year": str(trade.get("entry_date", ""))[:4],
            "current_source": cur.get("source", "?"), "previous_source": prev.get("source", "?"),
            "current_dir": cur_dir, "previous_dir": prev_dir, "signal_dir": sig_dir,
            "direction_relation": "same" if cur_dir == prev_dir else "opposite" if cur_dir * prev_dir < 0 else "unknown",
            "signal_vs_current": "aligned" if sig_dir == cur_dir else "opposite" if sig_dir * cur_dir < 0 else "unknown",
            "signal_kind": signal_kind,
            "current_mark_sequence": ">".join(m.get("kind", "?") for m in cur_marks) or "none",
            "previous_final_kind": prev_last.get("kind", "none") if prev_last else "none",
            "prev_final_to_cur_start_bars": cur_start_idx - prev_last_idx if prev_last_idx >= 0 else None,
            "prev_final_to_cur_b1_bars": b1_idx - prev_last_idx if b1_idx >= 0 and prev_last_idx >= 0 else None,
            "prev_final_to_signal_bars": signal_idx - prev_last_idx if prev_last_idx >= 0 else None,
            "prev_b1_to_cur_b1_bars": b1_idx - prev_b1_idx if b1_idx >= 0 and prev_b1_idx >= 0 else None,
            "prev_fs_to_cur_start_bars": cur_start_idx - prev_fs_idx if prev_fs_idx >= 0 else None,
            "prev_fs_to_signal_bars": signal_idx - prev_fs_idx if prev_fs_idx >= 0 else None,
            "cur_start_to_b1_bars": b1_idx - cur_start_idx if b1_idx >= 0 else None,
            "b1_to_signal_bars": signal_idx - b1_idx if b1_idx >= 0 else None,
            "prev_final_to_cur_start_atr": (cur_start_px - prev_last_px) / atr15,
            "prev_final_to_cur_b1_atr": (b1_px - prev_last_px) / atr15 if b1_px is not None else None,
            "prev_final_to_signal_atr": (signal_px - prev_last_px) / atr15,
            "prev_fs_to_signal_atr": (signal_px - prev_fs_px) / atr15 if prev_fs_px is not None else None,
            "cur_start_to_b1_atr": (b1_px - cur_start_px) / atr15 if b1_px is not None else None,
            "b1_to_signal_atr": (signal_px - b1_px) / atr15 if b1_px is not None else None,
            "prev_end_to_cur_start_atr": (cur_start_px - prev_end_px) / atr15,
            "cur_mag_atr": abs(float(seg.get("end_px", cur_start_px)) - cur_start_px) / atr15,
            "prev_mag_atr": abs(prev_end_px - float(prev_seg.get("start_px", prev_end_px))) / atr15,
            "raw_route": raw_route, "actual_route": actual_route,
            "route_conflict": int(raw_route != actual_route),
            "chop_lane": "B2" if chop[i1h] > CHOP_THRESH else "FLIP",
            "signal_chop_conflict": int(signal_kind in ("B2", "FLIP") and signal_kind != ("B2" if chop[i1h] > CHOP_THRESH else "FLIP")),
            "current_source_signal_kind": f"{cur.get('source','?')}>{signal_kind}",
            "previous_source_final_kind": f"{prev.get('source','?')}>{prev_last.get('kind','none') if prev_last else 'none'}",
            "win": float(trade.get("r_multiple", 0)) > 0,
            "runner": float(trade.get("r_multiple", 0)) >= 3.0,
        })
    return rows

GEOMETRY_FIELDS = [
    "prev_final_to_cur_start_bars", "prev_final_to_cur_b1_bars", "prev_final_to_signal_bars",
    "prev_b1_to_cur_b1_bars", "prev_fs_to_cur_start_bars", "prev_fs_to_signal_bars",
    "cur_start_to_b1_bars", "b1_to_signal_bars", "prev_final_to_cur_start_atr",
    "prev_final_to_cur_b1_atr", "prev_final_to_signal_atr", "prev_fs_to_signal_atr",
    "cur_start_to_b1_atr", "b1_to_signal_atr", "prev_end_to_cur_start_atr",
    "cur_mag_atr", "prev_mag_atr",
]


def bucket_rows(rows, field, value_fn):
    groups = defaultdict(list)
    for row in rows:
        groups[value_fn(row)].append(row)
    return {str(k): summary(v) for k, v in sorted(groups.items(), key=lambda x: str(x[0]))}


def report(rows):
    return {
        "baseline": summary(rows),
        "by_direction_relation": bucket_rows(rows, "direction_relation", lambda r: r["direction_relation"]),
        "by_signal_vs_current": bucket_rows(rows, "signal_vs_current", lambda r: r["signal_vs_current"]),
        "by_previous_final_kind": bucket_rows(rows, "previous_final_kind", lambda r: r["previous_final_kind"]),
        "by_current_sequence": bucket_rows(rows, "current_mark_sequence", lambda r: r["current_mark_sequence"]),
        "by_source_signal": bucket_rows(rows, "current_source_signal_kind", lambda r: r["current_source_signal_kind"]),
        "by_previous_source_final": bucket_rows(rows, "previous_source_final_kind", lambda r: r["previous_source_final_kind"]),
        "by_prev_final_to_cur_start_bars": bucket_rows(rows, "prev_final_to_cur_start_bars", lambda r: bar_bucket(r["prev_final_to_cur_start_bars"])),
        "by_prev_final_to_signal_bars": bucket_rows(rows, "prev_final_to_signal_bars", lambda r: bar_bucket(r["prev_final_to_signal_bars"])),
        "by_prev_b1_to_cur_b1_bars": bucket_rows(rows, "prev_b1_to_cur_b1_bars", lambda r: bar_bucket(r["prev_b1_to_cur_b1_bars"])),
        "by_cur_start_to_b1_bars": bucket_rows(rows, "cur_start_to_b1_bars", lambda r: bar_bucket(r["cur_start_to_b1_bars"])),
        "by_b1_to_signal_bars": bucket_rows(rows, "b1_to_signal_bars", lambda r: bar_bucket(r["b1_to_signal_bars"])),
        "by_route_conflict": bucket_rows(rows, "route_conflict", lambda r: r["route_conflict"]),
        "by_signal_chop_conflict": bucket_rows(rows, "signal_chop_conflict", lambda r: r["signal_chop_conflict"]),
        "by_signal_kind": bucket_rows(rows, "signal_kind", lambda r: r["signal_kind"]),
        "feature_distributions": feature_stats(rows, GEOMETRY_FIELDS),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="both")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    started = time.time()
    for scope in scopes:
        data = load_scope(scope)
        sim = build_module()
        result = {}
        for key in CONFIGS:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            rows = trade_rows(trades, data)
            result[key] = report(rows)
            base = result[key]["baseline"]
            print(f"{scope.upper()} {key:38} raw={base['n']:3d} joined={len(rows):3d} "
                  f"G={base['gross_r']:+.1f} N={base['net_r']:+.1f} "
                  f"WR={base['win_rate_pct']:.1f}%", flush=True)
        output = OUT[scope]
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {output}", flush=True)
    print(f"done in {time.time() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()


