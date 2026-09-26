"""Deep HTF-layer autopsy for the Bybit BTCUSDT perpetual v18 architecture.

Every prior autopsy measured the 15m LTF trade ledger. This harness measures
the 1h HTF parent layer itself, plus the causal mapping from a parent HTF
campaign onto its child LTF trades.

Stages
  65  HTF window anatomy: close reason, duration, R, MFE/MAE, sequence
  66  Window-death reversion vs an unconditional base-rate placebo
  67  Window-age decay of child LTF value
  68  Parent HTF health (marked R) at each LTF entry
  69  B2 vs FLIP HTF window comparison at window level
  70  Competing / overlapping window arbitration
  71  Consecutive-window sequence behaviour

Read-only. The production engine and live loop are never modified.
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from engine.v18_params import SWING

OUT = {
    "is": ROOT / "live_stuff/tests/_thesis_htf_deep_atlas_is.json",
    "oos": ROOT / "live_stuff/tests/_thesis_htf_deep_atlas_oos.json",
}
CONFIGS = (
    "pure_v18_single", "pure_v18_multi",
    "literal_v18_single", "literal_v18_multi",
    "fullstack_wage10_cd0_single_sw10",
    "champion_multi_sw10", "utcsat_multi_sw10",
)
PLANS = (("htf_rr3_cap16", 3.0, 16), ("htf_rr2_cap16", 2.0, 16),
         ("htf_rr3_cap8", 3.0, 8), ("htf_rr3_cap30", 3.0, 30))
FWD_HORIZONS_H = (6, 12, 24, 48, 72)
AGE_BUCKETS_H = ((0, 6), (6, 12), (12, 24), (24, 48), (48, 336), (336, 10 ** 9))
HEALTH_BUCKETS_R = ((-10 ** 9, -0.5), (-0.5, 0.0), (0.0, 0.5),
                    (0.5, 1.0), (1.0, 3.0), (3.0, 10 ** 9))
PLACEBO_SAMPLES = 3000
PLACEBO_SEED = 991


def finite(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def stats(values):
    xs = [finite(x) for x in values if finite(x) is not None]
    if not xs:
        return {"n": 0}
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    peak = cum = dd = 0.0
    ls = ws = mls = mws = 0
    for x in xs:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
        if x > 0:
            ws += 1; ls = 0
        else:
            ls += 1; ws = 0
        mls = max(mls, ls); mws = max(mws, ws)
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    return {
        "n": len(xs), "sum_r": round(sum(xs), 4),
        "avg_r": round(sum(xs) / len(xs), 6),
        "wins": len(wins), "losses": len(losses),
        "wr_pct": round(100.0 * len(wins) / len(xs), 3),
        "avg_win": round(aw, 4), "avg_loss": round(al, 4),
        "payoff": round(aw / abs(al), 4) if al else 0.0,
        "pf": round(sum(wins) / abs(sum(losses)), 4)
        if losses and abs(sum(losses)) > 0 else None,
        "max_dd": round(dd, 4), "max_loss_streak": mls,
        "max_win_streak": mws,
        "median": round(statistics.median(xs), 6),
        "std": round(statistics.pstdev(xs), 6) if len(xs) > 1 else 0.0,
    }


def ltf_stats(trades):
    gross = [float(t.get("r_multiple") or 0.0) for t in trades]
    net = [net_r([t]) for t in trades]
    out = {"gross": stats(gross), "net": stats(net)}
    out["cost_and_funding"] = round(sum(gross) - sum(net), 4)
    out["runners"] = {str(k): sum(x >= k for x in gross) for k in (3, 5, 10)}
    return out


def params_for(key):
    if key.startswith("pure_") or key.startswith("literal_"):
        from exp_geom_pure_v18_sweep import params_for as pure_params
        return pure_params(key)
    return {**BP, **EXPERIMENTS[key]["params"]}


def load_scope(scope):
    if scope == "is":
        data = get_data()
        identity_gate(data, build_module())
        return data
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    return {"c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"])}


# ------------------------------------------------------------- HTF window layer

def build_windows(data, htf_rr, cap_days):
    """Rebuild every HTF window set exactly as the engine constructs them."""
    out = {}
    for lane, brk in (("flip", "flip"), ("decisive", "decisive"), ("b2", "b2")):
        out[lane] = simulate_btc_trades_v7(
            data["c1h"], data["sw10"], entry_break=brk, sl_mode="swing",
            rr_target=htf_rr, trailing="off", breakeven_r=0.0,
            skip_first=True, fine=data["fine"], cap_days=cap_days)
    return out


def forward_excursion(fine, fine_ts, ts, d, risk, base_px):
    """Max same-direction and opposite-direction excursion after ts, in R."""
    out = {}
    if not fine or risk <= 0:
        return out
    start = bisect.bisect_right(fine_ts, ts)
    if start >= len(fine):
        return out
    for h in FWD_HORIZONS_H:
        end = bisect.bisect_right(fine_ts, ts + h * 3600)
        if end <= start:
            continue
        best_fav = 0.0
        best_adv = 0.0
        first_fav = first_adv = None
        for k in range(start, end):
            hi = float(fine[k]["high"]); lo = float(fine[k]["low"])
            fav_r = ((hi - base_px) if d > 0 else (base_px - lo)) / risk
            adv_r = ((base_px - lo) if d > 0 else (hi - base_px)) / risk
            if fav_r > best_fav:
                best_fav = fav_r
                if first_fav is None:
                    first_fav = int(fine[k]["ts"])
            if adv_r > best_adv:
                best_adv = adv_r
                if first_adv is None:
                    first_adv = int(fine[k]["ts"])
        out["h%d" % h] = {
            "fav_r": round(best_fav, 6), "opp_r": round(best_adv, 6),
            "opp_first": int(bool(first_fav and first_adv and first_adv < first_fav)),
            "opp_ge_1r": int(best_adv >= 1.0), "opp_ge_2r": int(best_adv >= 2.0),
            "fav_ge_1r": int(best_fav >= 1.0),
        }
    return out


def window_rows(trades, fine, fine_ts, lane):
    """Enrich each HTF window with duration, R, MFE/MAE and forward excursions."""
    rows = []
    for t in trades:
        d = 1 if t.get("dir") == "long" else -1
        entry = float(t["entry_price"]); sl = float(t["sl"])
        risk = abs(entry - sl)
        entry_ts = int(t["entry_ts"])
        exit_ts = int(t.get("exit_ts") or entry_ts)
        if risk <= 0:
            continue
        start = bisect.bisect_left(fine_ts, entry_ts + 3600)
        end = bisect.bisect_right(fine_ts, exit_ts)
        mfe = mae = None
        if start < end:
            highs = [float(fine[k]["high"]) for k in range(start, end)]
            lows = [float(fine[k]["low"]) for k in range(start, end)]
            mfe = ((max(highs) - entry) * d) / risk
            mae = ((entry - min(lows)) * d) / risk
        base_px = float(fine[min(end, len(fine) - 1)]["close"]) if fine else entry
        rows.append({
            "lane": lane, "dir": t.get("dir"), "outcome": t.get("outcome"),
            "entry_ts": entry_ts, "exit_ts": exit_ts,
            "duration_h": round((exit_ts - entry_ts) / 3600.0, 4),
            "r": round(float(t.get("r_multiple") or 0.0), 6),
            "mfe_r": None if mfe is None else round(mfe, 6),
            "mae_r": None if mae is None else round(mae, 6),
            "entry_price": entry, "sl": sl, "risk": risk,
            "forward": forward_excursion(fine, fine_ts, exit_ts, d, risk, base_px),
        })
    rows.sort(key=lambda x: x["entry_ts"])
    return rows


# ------------------------------------------------------------------- Stage 65

def stage65_anatomy(windows):
    by_lane_outcome = {}
    for lane, rows in windows.items():
        bucket = defaultdict(list)
        for w in rows:
            bucket[w["outcome"]].append(w["r"])
        by_lane_outcome[lane] = {k: stats(v) for k, v in sorted(bucket.items())}
    dur = defaultdict(list); mfe = defaultdict(list); mae = defaultdict(list)
    for rows in windows.values():
        for w in rows:
            dur[w["outcome"]].append(w["duration_h"])
            if w["mfe_r"] is not None:
                mfe[w["outcome"]].append(w["mfe_r"])
                mae[w["outcome"]].append(w["mae_r"])
    flip = windows.get("flip", [])
    gaps = [(flip[i]["entry_ts"] - flip[i - 1]["exit_ts"]) / 3600.0
            for i in range(1, len(flip))]
    switches = [int(flip[i - 1]["dir"] != flip[i]["dir"]) for i in range(1, len(flip))]
    return {
        "window_counts": {lane: len(rows) for lane, rows in windows.items()},
        "by_lane_outcome": by_lane_outcome,
        "by_outcome_duration_h": {k: stats(v) for k, v in sorted(dur.items())},
        "by_outcome_mfe_r": {k: stats(v) for k, v in sorted(mfe.items())},
        "by_outcome_mae_r": {k: stats(v) for k, v in sorted(mae.items())},
        "flip_gap_h": stats(gaps),
        "flip_direction_switch_rate": round(sum(switches) / len(switches), 4) if switches else None,
    }


# ------------------------------------------------------------------- Stage 66

def base_rate_placebo(fine, fine_ts, risk_median):
    """Unconditional opposite-move rate: random timestamp, random sign."""
    if not fine or risk_median <= 0:
        return {}
    rng = random.Random(PLACEBO_SEED)
    res = {"h%d" % h: {"opp_ge_1r": 0, "opp_ge_2r": 0, "opp_r": []} for h in FWD_HORIZONS_H}
    n = 0
    last = len(fine_ts) - 1
    for _ in range(PLACEBO_SAMPLES):
        i = rng.randint(0, last)
        d = rng.choice((1, -1))
        base = float(fine[i]["close"])
        fwd = forward_excursion(fine, fine_ts, int(fine_ts[i]), d, risk_median, base)
        if not fwd:
            continue
        n += 1
        for key, cell in fwd.items():
            res[key]["opp_ge_1r"] += cell["opp_ge_1r"]
            res[key]["opp_ge_2r"] += cell["opp_ge_2r"]
            res[key]["opp_r"].append(cell["opp_r"])
    for key in res:
        res[key]["n"] = n
        res[key]["p_opp_ge_1r"] = round(res[key]["opp_ge_1r"] / max(n, 1), 4)
        res[key]["p_opp_ge_2r"] = round(res[key]["opp_ge_2r"] / max(n, 1), 4)
        res[key]["opp_r"] = stats(res[key]["opp_r"])
    return res


def stage66_reversion(windows, placebo):
    by_close = defaultdict(lambda: defaultdict(list))
    first_dir = defaultdict(list)
    for rows in windows.values():
        for w in rows:
            if not w["forward"]:
                continue
            for key, cell in w["forward"].items():
                by_close[w["outcome"]][key].append(cell)
                first_dir[w["outcome"]].append(cell["opp_first"])
    out = {"placebo_base_rate": placebo, "by_close_reason": {}}
    for close, hmap in sorted(by_close.items()):
        per_h = {}
        for key, cells in sorted(hmap.items()):
            p1 = sum(c["opp_ge_1r"] for c in cells) / len(cells)
            base_p1 = (placebo.get(key) or {}).get("p_opp_ge_1r")
            per_h[key] = {
                "n": len(cells),
                "p_opp_ge_1r": round(p1, 4),
                "p_opp_ge_2r": round(sum(c["opp_ge_2r"] for c in cells) / len(cells), 4),
                "p_opp_first": round(sum(c["opp_first"] for c in cells) / len(cells), 4),
                "opp_r": stats([c["opp_r"] for c in cells]),
                "fav_r": stats([c["fav_r"] for c in cells]),
                "placebo_p_opp_ge_1r": base_p1,
                "edge_vs_placebo": round(p1 - base_p1, 4) if base_p1 is not None else None,
            }
        out["by_close_reason"][close] = {
            "per_horizon": per_h,
            "p_opp_first_all": round(sum(first_dir[close]) / len(first_dir[close]), 4)
            if first_dir[close] else None,
        }
    return out


# ------------------------------------------------------- parent -> child mapping

def parent_health_at(fine, fine_ts, child_ts, parent_entry_ts, direction, entry_px, sl_px):
    """Marked R of a parent HTF window at the CHILD entry, using only 1m data.

    The scan must start at the parent's own entry (not the child's), otherwise
    start > end and every trade resolves to 'no_parent'.
    """
    risk = abs(entry_px - sl_px)
    if risk <= 0 or not fine:
        return None
    end = bisect.bisect_right(fine_ts, int(child_ts)) - 1
    start = bisect.bisect_left(fine_ts, int(parent_entry_ts))
    if start < 0:
        start = 0
    if end < start or end < 0:
        return None
    d = 1 if direction == "long" else -1
    highs = [float(fine[k]["high"]) for k in range(start, end + 1)]
    lows = [float(fine[k]["low"]) for k in range(start, end + 1)]
    if not highs:
        return None
    return {
        "marked_r": round(((float(fine[end]["close"]) - entry_px) * d) / risk, 6),
        "mfe_r": round(((max(highs) - entry_px) * d) / risk, 6),
        "mae_r": round(((entry_px - min(lows)) * d) / risk, 6),
    }


def map_children(windows, trades, fine, fine_ts):
    """Attach each LTF trade to its governing HTF window + causal parent health."""
    by_lane = dict(windows)
    all_sorted = sorted([w for rows in by_lane.values() for w in rows],
                        key=lambda x: x["entry_ts"])
    mapped = []
    for t in trades:
        ts = int(t["entry_ts"])
        d = 1 if t.get("dir") == "long" else -1
        lane = t.get("htf_regime", "flip")
        pool = by_lane.get(lane) or all_sorted
        best = None
        for w in pool:
            if w["entry_ts"] <= ts <= w["exit_ts"] and \
                    (1 if w["dir"] == "long" else -1) == d:
                best = w
                break
        rec = {"gross_r": float(t.get("r_multiple") or 0.0), "lane": lane,
               "age_h": None, "parent_marked_r": None, "parent_mfe_at_entry": None,
               "parent_mae_at_entry": None, "parent_outcome": None, "parent_r": None}
        if best is not None:
            health = parent_health_at(fine, fine_ts, ts, best["entry_ts"],
                                     best["dir"], best["entry_price"], best["sl"])
            rec.update({
                "age_h": round((ts - best["entry_ts"]) / 3600.0, 4),
                "parent_outcome": best["outcome"], "parent_r": best["r"],
                "parent_marked_r": health["marked_r"] if health else None,
                "parent_mfe_at_entry": health["mfe_r"] if health else None,
                "parent_mae_at_entry": health["mae_r"] if health else None,
            })
        mapped.append(rec)
    return mapped


def age_bucket(age_h):
    if age_h is None:
        return "no_parent"
    for lo, hi in AGE_BUCKETS_H:
        if lo <= age_h < hi:
            return ("%d-%dh" % (lo, hi)) if hi < 10 ** 8 else ("%dh_plus" % lo)
    return "no_parent"


def health_bucket(marked_r):
    if marked_r is None:
        return "no_parent"
    for lo, hi in HEALTH_BUCKETS_R:
        if lo <= marked_r < hi:
            return "%s_to_%s" % (lo, hi)
    return "no_parent"


def stage67_68_age_health(mapped):
    age = defaultdict(list); health = defaultdict(list); cross = defaultdict(list)
    for rec in mapped:
        ab = age_bucket(rec["age_h"]); hb = health_bucket(rec["parent_marked_r"])
        age[ab].append(rec["gross_r"]); health[hb].append(rec["gross_r"])
        cross["%s|%s" % (ab, hb)].append(rec["gross_r"])
    return {
        "by_window_age": {k: stats(v) for k, v in sorted(age.items())},
        "by_parent_health": {k: stats(v) for k, v in sorted(health.items())},
        "age_x_health": {k: stats(v) for k, v in sorted(cross.items())},
    }


# ----------------------------------------------------------------- Stages 69-71

def stage69_lane_compare(windows):
    per_lane = {}
    for lane, rows in windows.items():
        per_lane[lane] = {
            "count": len(rows), "r": stats([w["r"] for w in rows]),
            "duration_h": stats([w["duration_h"] for w in rows]),
            "mfe_r": stats([w["mfe_r"] for w in rows if w["mfe_r"] is not None]),
            "mae_r": stats([w["mae_r"] for w in rows if w["mae_r"] is not None]),
            "outcomes": dict(Counter(w["outcome"] for w in rows)),
            "win_rate_pct": round(100.0 * sum(1 for w in rows if w["r"] > 0)
                                  / max(len(rows), 1), 3)}
    return per_lane


def stage70_competing(windows):
    flip = windows.get("flip", []); b2 = windows.get("b2", [])
    out = {"flip_count": len(flip), "b2_count": len(b2), "overlap_pairs": 0,
           "same_dir_overlap": 0, "opposite_overlap": 0, "opposite_examples": []}
    for f in flip:
        for b in b2:
            if min(f["exit_ts"], b["exit_ts"]) <= max(f["entry_ts"], b["entry_ts"]):
                out["overlap_pairs"] += 1
                if f["dir"] == b["dir"]:
                    out["same_dir_overlap"] += 1
                else:
                    out["opposite_overlap"] += 1
                    if len(out["opposite_examples"]) < 10:
                        out["opposite_examples"].append({
                            "flip_dir": f["dir"], "flip_outcome": f["outcome"],
                            "flip_r": f["r"], "b2_dir": b["dir"],
                            "b2_outcome": b["outcome"], "b2_r": b["r"],
                            "overlap_h": round(
                                (min(f["exit_ts"], b["exit_ts"])
                                 - max(f["entry_ts"], b["entry_ts"])) / 3600.0, 3)})
    return out


def stage71_sequence(windows):
    out = {}
    for lane, rows in windows.items():
        r_pairs = defaultdict(list); gap_pairs = defaultdict(list)
        for i in range(1, len(rows)):
            a, b = rows[i - 1], rows[i]
            key = "%s->%s" % (a["outcome"], b["outcome"])
            r_pairs[key].append(b["r"])
            gap_pairs[key].append((b["entry_ts"] - a["exit_ts"]) / 3600.0)
        out[lane] = {
            "next_window_r": {k: stats(v) for k, v in sorted(r_pairs.items())},
            "gap_h": {k: stats(v) for k, v in sorted(gap_pairs.items())},
        }
    return out


# ------------------------------------------------------------------- runner

def analyse_config(key, data, sim, htf_rr, cap_days):
    params = params_for(key)
    params.setdefault("exp_partial_r", 0.0)
    out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
              fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    fine = data["fine"]; fine_ts = [int(c["ts"]) for c in fine]
    raw = build_windows(data, htf_rr, cap_days)
    windows = {lane: window_rows(rows, fine, fine_ts, lane)
               for lane, rows in raw.items()}
    flat = [w for rows in windows.values() for w in rows]
    risks = sorted(w["risk"] for w in flat if w["risk"] > 0)
    median_risk = risks[len(risks) // 2] if risks else 1.0
    placebo = base_rate_placebo(fine, fine_ts, median_risk)
    mapped = map_children(windows, trades, fine, fine_ts)
    matched = sum(1 for r in mapped if r["parent_marked_r"] is not None)
    return {
        "ltf": ltf_stats(trades),
        "htf_rr": htf_rr, "htf_cap_days": cap_days,
        "child_match": {"mapped": matched, "total": len(trades),
                        "coverage_pct": round(100.0 * matched / max(len(trades), 1), 3)},
        "s65_anatomy": stage65_anatomy(windows),
        "s66_reversion": stage66_reversion(windows, placebo),
        "s67_68_age_health": stage67_68_age_health(mapped),
        "s69_lane_compare": stage69_lane_compare(windows),
        "s70_competing": stage70_competing(windows),
        "s71_sequence": stage71_sequence(windows),
    }


def run_scope(scope):
    started = time.time()
    data = load_scope(scope)
    sim = build_module()
    result = {"stage": 65, "instrument": "BTCUSDT_BYBIT", "scope": scope,
              "mode": "read-only descriptive; no production or engine change",
              "variants": {}}
    for key in CONFIGS:
        result["variants"][key] = {}
        for tag, rr, cap in PLANS:
            row = analyse_config(key, data, sim, rr, cap)
            result["variants"][key][tag] = row
            g = row["ltf"]["gross"]; n = row["ltf"]["net"]
            print("  %-3s %-38s %-16s LTF %3dt gross%+8.1f net%+8.1f | win %s | map %5.1f%%"
                  % (scope.upper(), key, tag, g["n"], g["sum_r"], n["sum_r"],
                     row["s65_anatomy"]["window_counts"],
                     row["child_match"]["coverage_pct"]), flush=True)
    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("is", "oos", "both"), default="is")
    args = parser.parse_args()
    scopes = ("is", "oos") if args.scope == "both" else (args.scope,)
    for scope in scopes:
        print("=" * 118, flush=True)
        print("  DEEP HTF-LAYER AUTOPSY - BYBIT %s" % scope.upper(), flush=True)
        print("=" * 118, flush=True)
        res = run_scope(scope)
        OUT[scope].write_text(json.dumps(res, indent=2), encoding="utf-8")
        print("  wrote %s" % OUT[scope], flush=True)


if __name__ == "__main__":
    main()
