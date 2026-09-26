"""Stage X — HTF 1h break-quality measures (Phase 1: descriptive separation).

New plane (checked vs do-not-retest lists):
  - 1h BREAK-BAR quality at window open: vol_ratio, body_atr, disp_atr
    (prior volume work = 15m entry rvol [24.31, inconsistent]; body/wick micro
    = 15m entry microstructure [death-path, closed] — 1h break-bar at WINDOW
    level was never measured)
  - b1_gap = bars between nearest preceding B1 mark (1h chain) and this break.
    DESCRIPTIVE ONLY — stale-B1 age gating is CLOSED (24.33); this is reported
    for context, never promoted as a gate.
  - risk_pct = window stop distance / entry (geometry at window level)

Method: rebuild windows exactly as the engine (atlas build_windows), attach
measures causally at window open, map every child LTF trade to its governing
window, bucket children by FIXED measure bins (pre-set thresholds, comparable
across eras). Lanes: champion_multi_sw10 + utcsat_multi_sw10, IS + OOS.

Verdict standard: a measure separates only if the SAME bin has the same-sign
edge vs the rest in both eras and both lanes (4/4 cells). Descriptive only —
survivors go to Phase 2 (path-true gate / M2-style sizing flag / combo).

Read-only. Production engine untouched.
"""
from __future__ import annotations

import bisect
import json
import math
import statistics
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

OUT = {
    "is": ROOT / "live_stuff/tests/_htf_break_measures_is.json",
    "oos": ROOT / "live_stuff/tests/_htf_break_measures_oos.json",
}
CONFIGS = ("champion_multi_sw10", "utcsat_multi_sw10")

BINS = {
    # measure -> [(label_lo, label_hi, lo, hi)]  fixed, pre-set
    "vol_ratio": [("low", "<0.75", -1e9, 0.75), ("mid", "0.75-1.25", 0.75, 1.25),
                  ("high", ">=1.25", 1.25, 1e9)],
    "body_atr": [("small", "<0.5", -1e9, 0.5), ("med", "0.5-1.0", 0.5, 1.0),
                 ("big", "1.0-1.5", 1.0, 1.5), ("huge", ">=1.5", 1.5, 1e9)],
    "disp_atr": [("tight", "<0.5", -1e9, 0.5), ("mid", "0.5-1.5", 0.5, 1.5),
                 ("wide", ">=1.5", 1.5, 1e9)],
    "risk_pct": [("narrow", "<1.0", -1e9, 1.0), ("mid", "1.0-2.0", 1.0, 2.0),
                 ("wide", ">=2.0", 2.0, 1e9)],
    "b1_gap": [("fresh", "<8", -1e9, 8.0), ("mid", "8-32", 8.0, 32.0),
               ("stale", ">=32", 32.0, 1e9)],  # descriptive only
}


def atr14(c1h, i, n=14):
    if i < n:
        return None
    trs = []
    for k in range(i - n + 1, i + 1):
        c0 = float(c1h[k - 1]["close"])
        h = float(c1h[k]["high"]); l = float(c1h[k]["low"])
        trs.append(max(h - l, abs(h - c0), abs(l - c0)))
    return sum(trs) / n


def enrich_windows(rows, c1h, breaks):
    """Attach causal break-bar measures to each window row (in place)."""
    ts_1h = [int(c["ts"]) for c in c1h]
    for w in rows:
        ets = w["entry_ts"]
        i = bisect.bisect_right(ts_1h, ets) - 1
        w["vol_ratio"] = w["body_atr"] = w["disp_atr"] = w["risk_pct"] = None
        w["b1_gap"] = None
        if 0 <= i < len(c1h):
            vol = [float(c.get("volume") or 0.0) for c in c1h]
            if i >= 24:
                base = sum(vol[i - 24:i]) / 24.0
                if base > 0:
                    w["vol_ratio"] = round(vol[i] / base, 4)
            a = atr14(c1h, i)
            if a and a > 0:
                bar = c1h[i]
                w["body_atr"] = round(abs(float(bar["close"]) - float(bar["open"])) / a, 4)
                prev_close = float(c1h[i - 1]["close"]) if i > 0 else float(bar["open"])
                w["disp_atr"] = round(abs(w["entry_price"] - prev_close) / a, 4)
        if w["entry_price"] > 0:
            w["risk_pct"] = round(100.0 * w["risk"] / w["entry_price"], 4)
        # b1_gap: bars between nearest preceding B1 mark (1h) and window break
        prior_b1 = None
        this_ts = ets
        for b in breaks:
            if b["kind"] == "B1" and b["ts"] <= this_ts:
                prior_b1 = b
            elif b["ts"] > this_ts:
                break
        if prior_b1 is not None:
            # bars of the gap: how many 1h bars between b1 bar and break bar
            j1 = bisect.bisect_right(ts_1h, prior_b1["ts"]) - 1
            j2 = bisect.bisect_right(ts_1h, this_ts) - 1
            if 0 <= j1 <= j2:
                w["b1_gap"] = float(j2 - j1)
    return rows


def flatten_breaks(swings):
    import datetime as dt
    out = []
    for s in swings:
        for b in (s.get("breaks") or []):
            t = b["time"]
            if isinstance(t, int):
                ts = t
            else:
                # match btc_config convention: naive IST string parsed as if
                # UTC then minus 19800 == candle["ts"]
                ts = int(dt.datetime.strptime(str(t), "%Y-%m-%d %H:%M:%S")
                         .replace(tzinfo=dt.timezone.utc).timestamp()) - 19800
            out.append({"ts": ts, "kind": b.get("kind"), "dir": b.get("dir"),
                        "px": b.get("px")})
    out.sort(key=lambda x: x["ts"])
    return out


def map_children_measured(windows, trades):
    by_lane = dict(windows)
    mapped = []
    for t in trades:
        ts = int(t["entry_ts"])
        d = 1 if t.get("dir") == "long" else -1
        lane = t.get("htf_regime", "flip")
        pool = by_lane.get(lane) or [w for rows in by_lane.values() for w in rows]
        best = None
        for w in pool:
            if w["entry_ts"] <= ts <= w["exit_ts"] and \
                    (1 if w["dir"] == "long" else -1) == d:
                best = w
                break
        rec = {"gross_r": float(t.get("r_multiple") or 0.0),
               "net_r": net_r([t]), "lane": lane, "parent": best}
        mapped.append(rec)
    return mapped


def bucket_table(title, mapped, measure, bins):
    print("  -- %s | %s" % (title, measure))
    rest = [m for m in mapped if m["parent"] is not None]
    if not rest:
        print("      (no mapped children)")
        return None
    overall = sum(m["net_r"] for m in rest) / len(rest)
    cells = {}
    for lab, labh, lo, hi in bins:
        sel = [m for m in rest
               if m["parent"].get(measure) is not None
               and lo <= m["parent"][measure] < hi]
        if not sel:
            continue
        ns = sum(m["net_r"] for m in sel)
        wr = 100.0 * sum(1 for m in sel if m["gross_r"] > 0) / len(sel)
        others = [m for m in rest
                  if not (m["parent"].get(measure) is not None
                          and lo <= m["parent"][measure] < hi)]
        om = sum(m["net_r"] for m in others) / len(others) if others else float("nan")
        cells[labh] = ns
        print("      %-10s n=%3d net=%+8.1f avg=%+6.3f WR=%5.1f%% | rest_avg=%+6.3f"
              % (labh, len(sel), ns, ns / len(sel), wr, om))
    return {"overall_avg": round(overall, 4), "bins": {k: round(v, 2) for k, v in cells.items()}}


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    c1h = data["c1h"]
    fine = data["fine"]
    fine_ts = [int(c["ts"]) for c in fine]
    breaks = flatten_breaks(data["sw10"])
    print("  1h chain breaks flattened:", len(breaks), flush=True)
    raw = build_windows(data, 3.0, 16)
    windows = {lane: window_rows(rows, fine, fine_ts, lane)
               for lane, rows in raw.items()}
    for lane in windows:
        enrich_windows(windows[lane], c1h, breaks)
    result = {"stage": "X", "scope": scope, "instrument": "BTCUSDT_BYBIT",
              "mode": "descriptive; b1_gap never promotable (stale-B1 closed)",
              "configs": {}}
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        mapped = map_children_measured(windows, trades)
        mapped_ok = [m for m in mapped if m["parent"] is not None]
        print("=" * 110)
        print("  %s | %s | trades=%d mapped=%.1f%%" % (
            scope.upper(), key, len(trades),
            100.0 * len(mapped_ok) / max(len(trades), 1)), flush=True)
        cfg_out = {"coverage_pct": round(100.0 * len(mapped_ok) / max(len(trades), 1), 3),
                   "measures": {}}
        for measure, bins in BINS.items():
            t = bucket_table("%s %s" % (scope.upper(), key), mapped, measure, bins)
            if t is not None:
                cfg_out["measures"][measure] = t
        # also measure availability
        avail = {m: sum(1 for x in mapped_ok if x["parent"].get(m) is not None)
                 for m in BINS}
        cfg_out["availability"] = avail
        print("  availability:", avail, flush=True)
        result["configs"][key] = cfg_out
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    started = time.time()
    result = {}
    for scope in ("is", "oos"):
        print("=" * 130, flush=True)
        print("  STAGE X PHASE 1 — 1h BREAK-QUALITY MEASURES — BYBIT %s" % scope.upper(), flush=True)
        print("=" * 130, flush=True)
        result[scope] = run_scope(scope)
        OUT[scope].write_text(json.dumps(result[scope], indent=2), encoding="utf-8")
        print("  wrote %s" % OUT[scope], flush=True)
    print("total %.1fs" % (time.time() - started), flush=True)


if __name__ == "__main__":
    main()
