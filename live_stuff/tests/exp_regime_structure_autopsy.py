"""Stage Z1 - Market-structure regime autopsy (descriptive, entry-causal, 1h plane).

Question: which 1h market-structure variables explain (a) per-trade outcomes and
(b) the 2021-22 vs 2023-26 payoff difference? Descriptive ONLY - no gate authored
here; survivors go to a pre-registered Z2 path-true test.

Features (all causal at cutoff = entry_ts + 900, completed bars only):
  V1  chop level (engine _chop_series_1h lb=14) + trailing-200 percentile
  V2  1h Kaufman efficiency ratio ER20 / ER50
  V3  1h swing flip frequency: confirmed sw10-chain dir flips in last 48h/96h,
      mean confirmed-swing duration in last 96h
  V4  wick-vs-body MAGNITUDE (last 6/12 x 1h): % wick>body, >2x, >3x;
      median & max total_wick/(body+eps); sum wick/ATR14;
      direction-specific OPPOSING wick (upper for longs / lower for shorts)
      sum/ATR14 + % opposing>body
  V5  compression: median |body|/ATR14 (12 bars); 48h range % ; small-body %
      (body/ATR<0.5 share of last 12)
  V6  rolling multi-day volume: 1h volume -> UTC-daily sum; past 7d/14d/30d
      combined volume, trailing-90d percentile of the 7d sum (era-proof form of
      "past N days combined volume > X"), 7d vs prev-7d ratio, absolute log for
      transparency. NO download needed (1h CSV has volume both eras).

Bucketing: ordered bins; tercile features use IS-pooled edges applied to BOTH
eras (so OOS shares show real distribution shift). Chop uses engine fixed
thresholds. Pinned auto-checks: same-sign top-vs-bottom across the 4 rule cells
(champion/utcsat x IS/OOS) + monotone count. Pre-registered survivor rule:
same-sign 4/4 AND monotone in >=3/4 cells AND bucket n>=15.

Lanes: champion_multi_sw10 / utcsat_multi_sw10 / fullstack_wage10_cd0_single_sw10
(fullstack = reference, excluded from the 4/4 rule).
Read-only on the engine. Run: $env:PYTHONIOENCODING='utf-8'; python -u
live_stuff/tests/exp_regime_structure_autopsy.py
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
from exp_boundary_state_autopsy import load_scope, obs_ts
from src.btc.engines.htf_ltf.v18_streak_halt import _chop_series_1h

OUT = {
    "is": ROOT / "live_stuff/tests/_regime_structure_is.json",
    "oos": ROOT / "live_stuff/tests/_regime_structure_oos.json",
}
LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("fullstack", "fullstack_wage10_cd0_single_sw10"),
)
RULE_LANES = ("champion", "utcsat")
EPS = 1e-9


# --------------------------------------------------------------------------- helpers

def tr_at(o, h, l, c, prev_c):
    return max(h - l, abs(h - prev_c), abs(l - prev_c))


def build_arrays(c1h):
    n = len(c1h)
    ts = [int(c["ts"]) for c in c1h]
    op = [float(c["open"]) for c in c1h]
    hi = [float(c["high"]) for c in c1h]
    lo = [float(c["low"]) for c in c1h]
    cl = [float(c["close"]) for c in c1h]
    vol = [float(c.get("volume") or 0.0) for c in c1h]
    tr = [hi[0] - lo[0]] if n else []
    for i in range(1, n):
        tr.append(tr_at(op[i], hi[i], lo[i], cl[i], cl[i - 1]))
    # UTC daily volume prefix
    days = []
    dsum = []
    cur_d = None
    acc = 0.0
    for i in range(n):
        d = ts[i] // 86400
        if cur_d is None or d != cur_d:
            if cur_d is not None:
                days.append(cur_d)
                dsum.append(acc)
            cur_d = d
            acc = 0.0
        acc += vol[i]
    if cur_d is not None:
        days.append(cur_d)
        dsum.append(acc)
    pref = [0.0]
    for v in dsum:
        pref.append(pref[-1] + v)
    return {"ts": ts, "o": op, "h": hi, "l": lo, "c": cl, "vol": vol, "tr": tr,
            "days": days, "dpref": pref, "n": n}


def er_at(cl, j, n):
    if j < n or n <= 0:
        return None
    c0 = cl[j - n]
    path = 0.0
    for k in range(j - n + 1, j + 1):
        path += abs(cl[k] - cl[k - 1])
    if path <= 0:
        return None
    return abs(cl[j] - c0) / path


def atr_at(tr, j, n=14):
    if j < n - 1:
        return None
    return sum(tr[j - n + 1:j + 1]) / n


def wick_feats(o, h, l, c, j, k, atr):
    """last k bars ending at j (inclusive)."""
    up = lo_w = body = 0.0
    ratios = []
    n_small = 0
    start = j - k + 1
    if start < 1:
        return None
    up_sum = lw_sum = 0.0
    for i in range(start, j + 1):
        b = abs(c[i] - o[i])
        u = h[i] - max(o[i], c[i])
        w = min(o[i], c[i]) - l[i]
        t = u + w
        ratios.append(t / (b + EPS))
        up_sum += u
        lw_sum += w
        body += b
        if b < 0.5 * (atr or 0):
            n_small += 1
    med = statistics.median(ratios)
    mx = max(ratios)
    return {"ratios": ratios, "med": med, "max": mx, "up_sum": up_sum,
            "lw_sum": lw_sum, "small_pct": 100.0 * n_small / k}


def day_window_sum(arr, k_end_day, ndays):
    """sum of last ndays daily volumes ending at day index k_end (inclusive)."""
    days = arr["days"]
    pref = arr["dpref"]
    lo_i = max(0, k_end_day - ndays + 1)
    if k_end_day < 0 or lo_i > k_end_day:
        return None
    return pref[k_end_day + 1] - pref[lo_i]


def compute_features(trade, ctx):
    """All V1..V6 features at causal cutoff. ctx = precomputed arrays/state."""
    arr = ctx["arr"]
    cutoff = obs_ts(trade)
    ts = arr["ts"]
    j = bisect.bisect_right(ts, cutoff - 3600) - 1  # last 1h bar CLOSED by cutoff
    f = {"ok": j >= 50}
    if j < 50:
        return f
    o, h, l, c, tr = arr["o"], arr["h"], arr["l"], arr["c"], arr["tr"]
    d = 1 if trade.get("dir") == "long" else -1

    # V1 chop
    chop = ctx["chop"]
    f["chop"] = round(chop[j], 3)
    w = chop[max(0, j - 199):j + 1]
    f["chop_pct"] = round(100.0 * sum(1 for x in w if x < chop[j]) / len(w), 2)

    # V2 efficiency
    f["er20"] = None if er_at(c, j, 20) is None else round(er_at(c, j, 20), 4)
    f["er50"] = None if er_at(c, j, 50) is None else round(er_at(c, j, 50), 4)

    # V3 flip frequency (confirmed 1h swings, causal)
    ct = ctx["conf_ts"]
    k = bisect.bisect_right(ct, cutoff) - 1
    for win, key in ((48, "flips48"), (96, "flips96")):
        lo_i = bisect.bisect_left(ct, cutoff - win * 3600)
        seg = ctx["conf_dir"][lo_i:k + 1]
        flips = sum(1 for a, b in zip(seg, seg[1:]) if a != b)
        f[key] = flips if seg else None
    if k >= 0:
        lo_i = bisect.bisect_left(ctx["conf_ts"], cutoff - 96 * 3600)
        seg_dur = ctx["conf_dur"][lo_i:k + 1]
        f["dur96"] = round(statistics.mean(seg_dur), 2) if seg_dur else None
    else:
        f["dur96"] = None

    # V4 wick magnitude 6 / 12
    a = atr_at(tr, j)
    f["wick_body_med12"] = f["wick_body_max12"] = None
    f["wick_gt_body_pct12"] = f["wick_gt2x_pct12"] = f["wick_gt3x_pct12"] = None
    f["wick_atr12"] = f["opp_wick_atr12"] = f["opp_gt_body_pct12"] = None
    f["small_body_pct12"] = f["med_body_atr12"] = None
    w12 = wick_feats(o, h, l, c, j, 12, a)
    w6 = wick_feats(o, h, l, c, j, 6, a)
    if w12 and a:
        rs = w12["ratios"]
        f["wick_body_med12"] = round(w12["med"], 3)
        f["wick_body_max12"] = round(w12["max"], 3)
        f["wick_gt_body_pct12"] = round(100.0 * sum(1 for x in rs if x > 1) / len(rs), 1)
        f["wick_gt2x_pct12"] = round(100.0 * sum(1 for x in rs if x > 2) / len(rs), 1)
        f["wick_gt3x_pct12"] = round(100.0 * sum(1 for x in rs if x > 3) / len(rs), 1)
        f["wick_atr12"] = round((w12["up_sum"] + w12["lw_sum"]) / a, 3)
        opp = w12["up_sum"] if d > 0 else w12["lw_sum"]
        f["opp_wick_atr12"] = round(opp / a, 3)
        # % of bars where opposing wick > body
        cnt = 0
        for i in range(j - 11, j + 1):
            b = abs(c[i] - o[i])
            u = h[i] - max(o[i], c[i])
            w_ = min(o[i], c[i]) - l[i]
            ov = u if d > 0 else w_
            if ov > b:
                cnt += 1
        f["opp_gt_body_pct12"] = round(100.0 * cnt / 12, 1)
        f["wick_body_med6"] = round(w6["med"], 3) if w6 else None
        f["small_body_pct12"] = round(w12["small_pct"], 1)
        # V5 med body/atr
        bodies = [abs(c[i] - o[i]) for i in range(j - 11, j + 1)]
        f["med_body_atr12"] = round(statistics.median(bodies) / a, 3)

    # V5 48h range %
    s48 = j - 47
    if s48 >= 0:
        rng = max(h[s48:j + 1]) - min(l[s48:j + 1])
        f["range48_pct"] = round(100.0 * rng / c[j], 3)

    # V6 rolling multi-day volume
    days = arr["days"]
    # last UTC day fully completed by cutoff: (d+1)*86400 <= cutoff -> d <= cutoff/86400 - 1
    dmax = bisect.bisect_right(days, cutoff // 86400 - 1) - 1
    if dmax >= 6:
        v7 = day_window_sum(arr, dmax, 7)
        f["vol7d"] = round(v7, 1)
        # trailing 90d percentile of the 7d rolling sum
        rsums = []
        for kk in range(max(6, dmax - 90), dmax + 1):
            rsums.append(day_window_sum(arr, kk, 7))
        f["vol7d_pct90"] = round(100.0 * sum(1 for x in rsums if x < v7) / len(rsums), 1)
        if dmax >= 13:
            prev7 = day_window_sum(arr, dmax - 7, 7)
            f["vol7_prev7"] = round(v7 / prev7, 3) if prev7 else None
        f["vol14d"] = round(day_window_sum(arr, dmax, 14), 1) if dmax >= 13 else None
        f["vol30d"] = round(day_window_sum(arr, dmax, 30), 1) if dmax >= 29 else None
        f["log_vol7"] = round(math.log10(v7 + 1.0), 3)
    return f


def bucket_of(val, edges, labels):
    if val is None:
        return None
    for i, (lo, hi) in enumerate(edges):
        if lo <= val < hi:
            return labels[i]
    return None


# feature -> (kind, edges/None, labels) ; kind "fixed" uses edges, "tercile"
# edges filled from IS pooled data
FEATURES = {
    "chop": ("fixed", [(-1e9, 45.0), (45.0, 55.0), (55.0, 61.8), (61.8, 70.0), (70.0, 1e9)],
             ["<45", "45-55", "55-61.8", "61.8-70", ">=70"]),
    "chop_pct": ("fixed", [(-1e9, 20.0), (20.0, 50.0), (50.0, 80.0), (80.0, 1e9)],
                 ["<20", "20-50", "50-80", ">=80"]),
    "er20": ("tercile", None, None),
    "er50": ("tercile", None, None),
    "flips48": ("fixed", [(-1e9, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 1e9)],
                ["0", "1", "2", ">=3"]),
    "flips96": ("fixed", [(-1e9, 2.0), (2.0, 4.0), (4.0, 6.0), (6.0, 1e9)],
                ["<=1", "2-3", "4-5", ">=6"]),
    "dur96": ("tercile", None, None),
    "wick_body_med12": ("tercile", None, None),
    "wick_body_max12": ("tercile", None, None),
    "wick_gt_body_pct12": ("tercile", None, None),
    "wick_gt2x_pct12": ("tercile", None, None),
    "wick_gt3x_pct12": ("tercile", None, None),
    "wick_atr12": ("tercile", None, None),
    "opp_wick_atr12": ("tercile", None, None),
    "opp_gt_body_pct12": ("tercile", None, None),
    "wick_body_med6": ("tercile", None, None),
    "med_body_atr12": ("tercile", None, None),
    "small_body_pct12": ("tercile", None, None),
    "range48_pct": ("tercile", None, None),
    "vol7d": ("tercile", None, None),
    "vol7d_pct90": ("fixed", [(-1e9, 20.0), (20.0, 80.0), (80.0, 1e9)],
                    ["<20", "20-80", ">=80"]),
    "vol7_prev7": ("tercile", None, None),
    "log_vol7": ("tercile", None, None),
}


def tercile_edges(values):
    vs = sorted(v for v in values if v is not None)
    if len(vs) < 30:
        return None
    q1 = vs[len(vs) // 3]
    q2 = vs[(2 * len(vs)) // 3]
    return [(-1e9, q1), (q1, q2), (q2, 1e9)]


def fmt_bucket(b):
    if b is None:
        return "-"
    n = b["n"]
    if n == 0:
        return "  n=0 "
    return "n=%d a%+.2f" % (n, b["avgR"])


def main():
    t0 = time.time()
    print("=" * 118, flush=True)
    print("  STAGE Z1 - MARKET-STRUCTURE REGIME AUTOPSY (descriptive, entry-causal)", flush=True)
    print("=" * 118, flush=True)
    sim = build_module()
    result = {"stage": "Z1", "instrument": "BTCUSDT_BYBIT",
              "mode": "descriptive; survivor rule: same-sign 4/4 + monotone>=3/4 + n>=15",
              "scopes": {}}
    all_pool = {f: {"is": [], "oos": []} for f in FEATURES}  # (val, avgR, net) pooled

    for scope in ("is", "oos"):
        print("\n" + "=" * 118, flush=True)
        print("  [%s] loading..." % scope.upper(), flush=True)
        data = load_scope(scope)
        arr = build_arrays(data["c1h"])
        chop = _chop_series_1h(data["c1h"], lb=14)
        # confirmed swing series (causal)
        conf = []
        for s in data["sw10"]:
            ci = s.get("confirmed_at_idx")
            if ci is None or not (0 <= ci < arr["n"]):
                continue
            dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
            conf.append((arr["ts"][ci], s["dir"], float(dur)))
        conf.sort(key=lambda x: x[0])
        ctx0 = {"arr": arr, "chop": chop,
                "conf_ts": [x[0] for x in conf],
                "conf_dir": [x[1] for x in conf],
                "conf_dur": [x[2] for x in conf]}
        print("  features: %d 1h bars, %d confirmed 1h swings" % (arr["n"], len(conf)), flush=True)

        sc = {}
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            feats = []
            for t in trades:
                feats.append((t, compute_features(t, ctx0)))
            sc[lane] = {"n": len(trades), "features": {}}
            for f in FEATURES:
                for t, ft in feats:
                    v = ft.get(f)
                    if v is not None:
                        all_pool[f][scope].append((v, float(t.get("r_multiple") or 0.0),
                                                   net_r([t])))
            print("  %s: %d trades, features computed" % (lane, len(trades)), flush=True)
            sc[lane]["_feats"] = feats
        result["scopes"][scope] = sc

    # ---- tercile edges from IS pooled (all lanes)
    print("\n" + "-" * 118, flush=True)
    print("  TERCILE EDGES (IS pooled):", flush=True)
    for f, (kind, edges, labels) in FEATURES.items():
        if kind == "tercile":
            e = tercile_edge = tercile_edges([v for v, _, _ in all_pool[f]["is"]])
            if e is None:
                print("  %-20s INSUFFICIENT DATA" % f, flush=True)
                FEATURES[f] = ("tercile", None, ["Q1", "Q2", "Q3"])
            else:
                labels = ["<=%.2f" % e[0][1], "%.2f-%.2f" % (e[0][1], e[1][1]),
                          ">%.2f" % e[1][1]]
                FEATURES[f] = ("tercile", e, labels)
                print("  %-20s Q1<=%.4g  Q2<=%.4g" % (f, e[0][1], e[1][1]), flush=True)

    # ---- bucket tables per feature x cell
    def bucketize(rows_vals):
        kind, edges, labels = FEATURES[f]
        out = {lab: {"n": 0, "sumR": 0.0, "sumNet": 0.0} for lab in labels}
        for v, r, nd in rows_vals:
            lab = bucket_of(v, edges, labels)
            if lab is None:
                continue
            b = out[lab]
            b["n"] += 1
            b["sumR"] += r
            b["sumNet"] += nd
        for b in out.values():
            b["avgR"] = b["sumR"] / b["n"] if b["n"] else 0.0
            b["net"] = round(b["sumNet"], 1)
            b["sumR"] = round(b["sumR"], 1)
            b["share"] = None
        return out

    # collect per cell
    cell_data = {}  # (scope, lane, feat) -> bucket dict
    for scope in ("is", "oos"):
        for lane, _ in LANES:
            feats = result["scopes"][scope][lane].pop("_feats")
            for f in FEATURES:
                rows = []
                for t, ft in feats:
                    v = ft.get(f)
                    if v is not None:
                        rows.append((v, float(t.get("r_multiple") or 0.0), net_r([t])))
                cell_data[(scope, lane, f)] = bucketize(rows)

    print("\n" + "=" * 118, flush=True)
    print("  BUCKET TABLES  (bucket: n  avgR  netR)", flush=True)
    print("=" * 118, flush=True)
    survivor = {}
    for f in FEATURES:
        kind, edges, labels = FEATURES[f]
        print("\n-- %s  bins: %s" % (f, " | ".join(labels)), flush=True)
        for lane, _ in LANES:
            line = "   %-9s" % lane
            for scope in ("is", "oos"):
                cd = cell_data[(scope, lane, f)]
                seg = "  %s: " % scope.upper()
                for lab in labels:
                    seg += "%s  " % fmt_bucket(cd[lab])
                line += seg
            print(line, flush=True)
        # pooled era-shift (all lanes): shares + avgR
        for scope in ("is", "oos"):
            agg = {lab: [0, 0.0] for lab in labels}
            for lane, _ in LANES:
                cd = cell_data[(scope, lane, f)]
                for lab in labels:
                    agg[lab][0] += cd[lab]["n"]
                    agg[lab][1] += cd[lab]["sumR"]
            tot = sum(v[0] for v in agg.values()) or 1
            print("   pooled %-3s  %s" % (scope.upper(), "  ".join(
                "%s %d(%.0f%%) a%+.2f" % (lab, agg[lab][0], 100.0 * agg[lab][0] / tot,
                                          agg[lab][1] / agg[lab][0] if agg[lab][0] else 0.0)
                for lab in labels)), flush=True)
        # survivor auto-check on rule cells
        signs = []
        mono = 0
        min_n_ok = True
        for scope in ("is", "oos"):
            for lane in RULE_LANES:
                cd = cell_data[(scope, lane, f)]
                vals = [(lab, cd[lab]) for lab in labels if cd[lab]["n"] > 0]
                if len(vals) < 2:
                    continue
                a, b = vals[0][1], vals[-1][1]
                if a["n"] < 15 or b["n"] < 15:
                    min_n_ok = False
                signs.append(b["avgR"] - a["avgR"])
                avgs = [x[1]["avgR"] for x in vals]
                inc = all(avgs[i] <= avgs[i + 1] + 1e-9 for i in range(len(avgs) - 1))
                dec = all(avgs[i] >= avgs[i + 1] - 1e-9 for i in range(len(avgs) - 1))
                if inc or dec:
                    mono += 1
        same = bool(signs) and (all(s > 0 for s in signs) or all(s < 0 for s in signs))
        surv = same and mono >= 3 and min_n_ok
        survivor[f] = {"same_sign_4plus": same, "monotone_cells": mono,
                       "min_n_ok": min_n_ok, "survives": surv,
                       "signs": [round(s, 3) for s in signs]}
        print("   >> survivor check: same-sign=%s mono=%d/4 min_n15=%s => %s" % (
            same, mono, min_n_ok, "SURVIVES" if surv else "no"), flush=True)
        result.setdefault("survivor_checks", {})[f] = survivor[f]

    # shares into buckets for JSON
    for k, cd in cell_data.items():
        scope, lane, f = k
        tot = sum(x["n"] for x in cd.values()) or 1
        for lab, b in cd.items():
            b["share"] = round(100.0 * b["n"] / tot, 1)
        result["scopes"][scope][lane].setdefault("buckets", {})[f] = cd

    result["features"] = {f: {"kind": k, "edges": e, "labels": l}
                          for f, (k, e, l) in FEATURES.items()}
    result["elapsed_sec"] = round(time.time() - t0, 2)
    surv_all = [f for f in FEATURES if survivor[f]["survives"]]
    result["survivors"] = surv_all
    OUT["is"].write_text(json.dumps({k: v for k, v in result.items() if k != "scopes"},
                                    indent=2), encoding="utf-8")
    # write per-scope files with buckets
    for scope in ("is", "oos"):
        OUT[scope].write_text(json.dumps(
            {"stage": "Z1", "scope": scope, "instrument": "BTCUSDT_BYBIT",
             "features": result["features"],
             "survivor_checks": result["survivor_checks"],
             "survivors": surv_all,
             "scopes": {lane: {"n": result["scopes"][scope][lane]["n"],
                               "buckets": result["scopes"][scope][lane]["buckets"]}
                        for lane, _ in LANES},
             "elapsed_sec": result["elapsed_sec"]}, indent=2), encoding="utf-8")
    print("\n" + "=" * 118, flush=True)
    print("  SURVIVORS: %s" % (surv_all or "NONE"), flush=True)
    print("  elapsed %.1fs  wrote %s / %s" % (result["elapsed_sec"], OUT["is"].name,
                                              OUT["oos"].name), flush=True)


if __name__ == "__main__":
    main()
