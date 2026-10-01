"""Stage B - Bleed Autopsy: hunt for NET-NEGATIVE buckets (4/4 cells) and verify
their REMOVAL improves the baseline (pre-registered).

GOAL (user directive): find a bucket whose NET R is negative in ALL 4 rule cells
(champion/utcsat x IS/OOS) so REMOVING it makes the baseline strictly better
(net up, trades down, avg/trade up). Opposite of Z3 (which cut a positive-but-
below-average tail at an IS cost).

PHASE 0 (done in planning): mined 74 existing Z1 buckets -> ZERO 4/4-negative
(best were era-flips: wick_atr12, flips96, vol7_prev7>1.06 ...). Hence NEW features,
HTF-chain-state heavy (plane untouched by Z).

FEATURES (30, all causal at cutoff = entry_ts + 900; j<50 -> all None):
  chain-state  chain_age_h, chain_len, chain_same, chain_r_so_far (causal sum of
               net R of prior trades in same 1h chain run), chain_wl_streak,
               last_swing_age_h, flip_age_h
  4h synth     h4_dir, h4_agree, h4_flip_age, h4_range_pos (completed 4h buckets)
  structure    struct (HH/HL=up, LH/LL=down, else mixed), swing_ret_pct
  regime       atr_pct, atr_pct_rank, day_range_pos, chop_side_dur
  time         hour6 (UTC), weekday (UTC, Mon=1..Sun=7)
  ltf state    prev_streak, prev_net_cum20, entries_24h
  dir-masked   wick_atr12/flips96/vol7_prev7/range48_pct x {long, short}
               (Z1 era-flip candidates x direction)

BUCKETING: continuous -> quartiles from IS rule-lane pool (applied to both eras);
categorical/fixed -> fixed edges.

FIND RULE (pre-registered): bucket qualifies iff in ALL 4 rule cells:
  n >= 15 AND share <= 35% AND sumNet < 0.

REMOVAL RULE (pre-registered): skip membership; PASS iff in ALL 4 cells:
  dNet > 0 (removal ADDS net) AND avgNet/trade >= baseline AND n < baseline
  AND curve_better. Phase-1 qualifiers tested first; if zero -> PASS-2
  (clearly labeled exploratory): intersections of near-miss buckets
  (neg in >=2/4, n>=15, share<=35), same FIND + REMOVAL rules.

CAUSALITY (post-run correction, 2026-09-26): the original enrich_sequential folded
final net R in ENTRY order -> still-open concurrent trades leaked future outcomes
into chain/prev state (178 trades affected; audit verify_bleed_causality.py ->
_bleed_autopsy_CLOSEDONLY.json). Fixed to closed-only (exit_ts <= cutoff).
Reported outcome under the fix: 2/4 removals PASS (wick_atr12@short, flips96@short;
masked = byte-identical before/after), chain removals FAIL (is|utcsat curve worse).

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_bleed_autopsy.py
"""
from __future__ import annotations

import bisect
import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope, obs_ts
from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import (build_arrays, bucket_of,
                                          compute_features as z1_compute,
                                          _chop_series_1h)

OUT = ROOT / "backtest/tests/_bleed_autopsy_results.json"
Z1_JSON = ROOT / "backtest/tests/_regime_structure_is.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
EPS = 1e-9

FEATURES_B: dict = {}


def _fix(name, edges, labels):
    FEATURES_B[name] = ("fixed", edges, labels)


def _t4(name):
    FEATURES_B[name] = ("tercile4", None, None)


_fix("chain_len", [(-1e9, 1.5), (1.5, 2.5), (2.5, 3.5), (3.5, 1e9)],
     ["1", "2", "3", ">=4"])
_fix("chain_same", [(-1e9, 0.5), (0.5, 1e9)], ["0", "1"])
_fix("chain_r_so_far", [(-1e9, -EPS), (-EPS, EPS), (EPS, 3.0), (3.0, 1e9)],
     ["<0", "0", "0-3", ">3"])
_fix("chain_wl_streak", [(-1e9, -1.5), (-1.5, -0.5), (-0.5, 0.5), (0.5, 1.5),
                         (1.5, 2.5), (2.5, 1e9)],
     ["<=-2", "-1", "0", "+1", "+2", ">=+3"])
_t4("chain_age_h")
_t4("last_swing_age_h")
_t4("flip_age_h")
_fix("h4_dir", [(-1e9, 0.0), (0.0, 1e9)], ["short", "long"])
_fix("h4_agree", [(-1e9, 0.5), (0.5, 1e9)], ["0", "1"])
_t4("h4_flip_age")
_t4("h4_range_pos")
_fix("struct", [(-1e9, -0.5), (-0.5, 0.5), (0.5, 1e9)], ["down", "mixed", "up"])
_t4("swing_ret_pct")
_t4("atr_pct")
_t4("atr_pct_rank")
_t4("day_range_pos")
_t4("chop_side_dur")
_fix("hour6", [(-1e9, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 1e9)],
     ["0-6", "6-12", "12-18", "18-24"])
_fix("weekday", [(-1e9, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0),
                 (5.0, 6.0), (6.0, 1e9)], ["Mon", "Tue", "Wed", "Thu", "Fri",
                                           "Sat", "Sun"])
_fix("prev_streak", [(-1e9, -1.5), (-1.5, -0.5), (-0.5, 0.5), (0.5, 1.5),
                     (1.5, 2.5), (2.5, 1e9)],
     ["<=-2", "-1", "0", "+1", "+2", ">=+3"])
_t4("prev_net_cum20")
_fix("entries_24h", [(-1e9, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 1e9)],
     ["0", "1", "2", ">=3"])
MASKED_BASES = ("wick_atr12", "flips96", "vol7_prev7", "range48_pct")
for _b in MASKED_BASES:
    for _sg, _tag in ((1, "long"), (-1, "short")):
        FEATURES_B[f"{_b}@{_tag}"] = ("masked", _b, _sg)
TERCILE4 = [n for n, v in FEATURES_B.items() if v[0] == "tercile4"]


# ------------------------------------------------------------------ calc utils
def h4_series(arr):
    out = {}
    for i in range(arr["n"]):
        b = arr["ts"][i] // 14400
        h = out.get(b)
        if h is None:
            out[b] = [arr["o"][i], arr["h"][i], arr["l"][i], arr["c"][i]]
        else:
            h[1] = max(h[1], arr["h"][i])
            h[2] = min(h[2], arr["l"][i])
            h[3] = arr["c"][i]
    ks = sorted(out)
    dirs = [1 if out[k][3] >= out[k][0] else -1 for k in ks]
    return ks, out, dirs


def build_ctx(data, arr, chop):
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        seg = s["seg"]
        i0, i1 = seg["start_idx"], seg["end_idx"]
        sgn = 1 if s.get("dir") == "up" else -1
        dur = max(0, (i1 - i0))
        ext = max(arr["h"][i0:i1 + 1]) if sgn > 0 else min(arr["l"][i0:i1 + 1])
        ret = None
        if arr["c"][i0]:
            ret = sgn * (arr["c"][i1] - arr["c"][i0]) / arr["c"][i0] * 100.0
        conf.append({"ts": arr["ts"][ci], "dir": sgn, "dur": float(dur),
                     "ext": ext, "ret": ret})
    conf.sort(key=lambda x: x["ts"])
    hk, hohlc, hdirs = h4_series(arr)
    return {"arr": arr, "chop": chop, "conf": conf,
            "conf_ts": [x["ts"] for x in conf],
            "conf_dir": [x["dir"] for x in conf],
            "conf_dur": [x["dur"] for x in conf],
            "h4_keys": hk, "h4_ohlc": hohlc, "h4_dirs": hdirs}


def chain_state(cutoff, ctx):
    ct = ctx["conf_ts"]
    k = bisect.bisect_right(ct, cutoff) - 1
    if k < 0:
        return None
    d0 = ctx["conf_dir"][k]
    i = k
    while i >= 0 and ctx["conf_dir"][i] == d0:
        i -= 1
    st = i + 1
    return {"key": ct[st], "len": k - st + 1, "dir": d0,
            "age_h": (cutoff - ct[st]) / 3600.0, "k": k}


def compute_new(trade, ctx):
    arr = ctx["arr"]
    cutoff = obs_ts(trade)
    ts = arr["ts"]
    j = bisect.bisect_right(ts, cutoff - 3600) - 1
    if j < 50:
        return {"ok": False}
    f = {"ok": True}
    d = 1 if trade.get("dir") == "long" else -1
    chop = ctx["chop"]

    cs = chain_state(cutoff, ctx)
    if cs:
        f["chain_len"] = cs["len"]
        f["chain_same"] = 1 if cs["dir"] == d else 0
        f["chain_age_h"] = round(cs["age_h"], 2)
        f["_ckey"] = cs["key"]
        ct = ctx["conf_ts"]
        f["last_swing_age_h"] = round((cutoff - ct[cs["k"]]) / 3600.0, 2)
        k = cs["k"]
        flip_i = None
        while k > 0:
            if ctx["conf_dir"][k] != ctx["conf_dir"][k - 1]:
                flip_i = k
                break
            k -= 1
        f["flip_age_h"] = round((cutoff - ct[flip_i if flip_i is not None else 0])
                                / 3600.0, 2)
    else:
        for k2 in ("chain_len", "chain_same", "chain_age_h",
                   "last_swing_age_h", "flip_age_h"):
            f[k2] = None
        f["_ckey"] = None

    bmax = (cutoff - 14400) // 14400
    hk, hohlc, hdirs = ctx["h4_keys"], ctx["h4_ohlc"], ctx["h4_dirs"]
    bi = bisect.bisect_right(hk, bmax) - 1
    if bi >= 0:
        o, h, l, c = hohlc[hk[bi]]
        hd = hdirs[bi]
        f["h4_dir"] = hd
        f["h4_agree"] = 1 if hd == d else 0
        f["h4_range_pos"] = round(100.0 * (c - l) / (h - l), 1) if h > l else 50.0
        a = bi
        while a > 0 and hdirs[a] == hd:
            a -= 1
        f["h4_flip_age"] = bi - a
    else:
        for k2 in ("h4_dir", "h4_agree", "h4_range_pos", "h4_flip_age"):
            f[k2] = None

    conf = ctx["conf"]
    k = bisect.bisect_right(ctx["conf_ts"], cutoff) - 1
    if k >= 0:
        f["swing_ret_pct"] = (round(conf[k]["ret"], 3)
                              if conf[k]["ret"] is not None else None)
        ups = [x for x in conf[:k + 1] if x["dir"] > 0][-2:]
        dns = [x for x in conf[:k + 1] if x["dir"] < 0][-2:]
        if len(ups) == 2 and len(dns) == 2:
            hh = ups[1]["ext"] > ups[0]["ext"]
            hl = dns[1]["ext"] > dns[0]["ext"]
            lh = ups[1]["ext"] < ups[0]["ext"]
            ll = dns[1]["ext"] < dns[0]["ext"]
            f["struct"] = 1 if (hh and hl) else (-1 if (lh and ll) else 0)
        else:
            f["struct"] = None
    else:
        f["swing_ret_pct"] = f["struct"] = None

    a14 = sum(arr["tr"][j - 13:j + 1]) / 14.0 if j >= 13 else None
    if a14 and arr["c"][j]:
        f["atr_pct"] = round(100.0 * a14 / arr["c"][j], 3)
        w = []
        for i in range(max(13, j - 199), j + 1):
            ai = sum(arr["tr"][i - 13:i + 1]) / 14.0
            if arr["c"][i]:
                w.append(100.0 * ai / arr["c"][i])
        f["atr_pct_rank"] = round(100.0 * sum(1 for x in w if x < w[-1]) / len(w), 1) if w else None
    else:
        f["atr_pct"] = f["atr_pct_rank"] = None

    day = cutoff // 86400
    if arr["ts"][j] // 86400 == day:
        i = j
        while i >= 0 and arr["ts"][i] // 86400 == day:
            i -= 1
        hi_d = max(arr["h"][x] for x in range(i + 1, j + 1))
        lo_d = min(arr["l"][x] for x in range(i + 1, j + 1))
        f["day_range_pos"] = (round(100.0 * (arr["c"][j] - lo_d) / (hi_d - lo_d), 1)
                              if hi_d > lo_d else 50.0)
    else:
        f["day_range_pos"] = None

    side = 1 if chop[j] >= 61.8 else (0 if chop[j] >= 55 else -1)
    n = 0
    i = j
    while i >= 0:
        s2 = 1 if chop[i] >= 61.8 else (0 if chop[i] >= 55 else -1)
        if s2 != side:
            break
        n += 1
        i -= 1
    f["chop_side_dur"] = n

    tm = time.gmtime(cutoff)
    f["hour6"] = tm.tm_hour // 6
    f["weekday"] = tm.tm_wday + 1
    return f


def enrich_sequential(trades, feats):
    """CAUSAL (closed-only): a prior trade contributes only when exit_ts <= cutoff.

    The original version folded each trade's FINAL net R at ENTRY order, which with
    exp_mltf=True leaked still-open trades' outcomes into chain_r_so_far /
    chain_wl_streak / prev_streak / prev_net_cum20 (audit: verify_bleed_causality.py
    counted 203 prior-open observations across 178 trades). Same bug class the
    loss-streak work already fixed ("only trades exited by the candidate entry
    timestamp may contribute").
    """
    order = sorted(range(len(trades)), key=lambda i: int(trades[i]["entry_ts"]))
    nets = [net_r([trades[i]]) for i in range(len(trades))]
    exits = [int(trades[i].get("exit_ts") or trades[i]["entry_ts"])
             for i in range(len(trades))]
    ck_closed: dict = {}          # chain key -> [(exit_ts, netR)]
    g_closed: list = []           # [(exit_ts, netR)] global, for prev_* ltf state
    g_entries, recent = [], []

    for i in order:
        if not feats[i].get("ok"):
            continue
        cutoff = obs_ts(trades[i])
        ck = feats[i].get("_ckey")

        done = sorted(e for e in ck_closed.get(ck, []) if e[0] <= cutoff)
        cr = sum(nd for _, nd in done)
        cs = 0
        for _, nd in done:
            w = 1 if nd > 0 else -1
            cs = w if cs == 0 or ((cs > 0) != (w > 0)) else cs + w
        feats[i]["chain_r_so_far"] = round(cr, 2)
        feats[i]["chain_wl_streak"] = cs

        gdone = sorted(e for e in g_closed if e[0] <= cutoff)
        feats[i]["prev_net_cum20"] = round(sum(nd for _, nd in gdone[-20:]), 2)
        gstreak = 0
        for _, nd in gdone:
            w = 1 if nd > 0 else -1
            gstreak = (w if gstreak == 0 or ((gstreak > 0) != (w > 0))
                       else gstreak + w)
        feats[i]["prev_streak"] = gstreak

        while g_entries and g_entries[0] < cutoff - 86400:
            g_entries.pop(0)
        feats[i]["entries_24h"] = len(g_entries)

        nd = nets[i]
        ck_closed.setdefault(ck, []).append((exits[i], nd))
        g_closed.append((exits[i], nd))
        recent.append(nd)
        if len(recent) > 20:
            recent.pop(0)
        g_entries.append(int(trades[i]["entry_ts"]))
    return nets


def fmt(b):
    if b is None or b["n"] == 0:
        return "n=0"
    return "n=%d a%+.2f net%+.1f" % (b["n"], b["sumNet"] / b["n"], b["sumNet"])


def find_rule(bucket_of_cell):
    """bucket_of_cell: dict (scope,lane) -> (n, share, sumNet); returns pass."""
    if len(bucket_of_cell) < 4:
        return False
    return all(n >= 15 and sh <= 35.0 + 1e-9 and sn < 0
               for n, sh, sn in bucket_of_cell.values())


def main():
    t0 = time.time()
    print("=" * 116, flush=True)
    print("  STAGE B - BLEED AUTOPSY: net-negative bucket hunt (4/4) + removal test", flush=True)
    print("=" * 116, flush=True)
    z1 = json.loads(Z1_JSON.read_text(encoding="utf-8"))
    z1_fd = z1["features"]
    sim = build_module()
    payload = {"stage": "B", "instrument": "BTCUSDT_BYBIT",
               "find_rule": "n>=15 AND share<=35 AND sumNet<0 in ALL 4 cells",
               "removal_rule": "dNet>0 AND avgNet>=base AND n<base AND curve_better in ALL 4 cells",
               "years": YEARS, "cells": {}}
    pools = {f: [] for f in TERCILE4}
    cells = {}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] loading ===", flush=True)
        data = load_scope(scope)
        arr = build_arrays(data["c1h"])
        chop = _chop_series_1h(data["c1h"], lb=14)
        ctx = build_ctx(data, arr, chop)
        print(f"  {arr['n']} 1h bars, {len(ctx['conf'])} confirmed swings, "
              f"{len(ctx['h4_keys'])} 4h buckets", flush=True)
        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            trades = sorted(trades, key=lambda t: int(t["entry_ts"]))
            feats = [compute_new(t, ctx) for t in trades]
            nets = enrich_sequential(trades, feats)
            for t, f in zip(trades, feats):
                z = z1_compute(t, ctx)
                f["_z1"] = z
            for t, f in zip(trades, feats):
                if not f.get("ok"):
                    continue
                d = 1 if t.get("dir") == "long" else -1
                for name in FEATURES_B:
                    spec = FEATURES_B[name]
                    if spec[0] == "masked":
                        f[name] = f["_z1"].get(spec[1]) if d == spec[2] else None
                f.pop("_z1", None)
                if scope == "is":
                    for tf in TERCILE4:
                        v = f.get(tf)
                        if v is not None:
                            pools[tf].append(v)
            yrs = YEARS[scope]
            cells[(scope, lane)] = {"trades": trades, "feats": feats,
                                    "nets": nets,
                                    "flat": equity_quality(trades, yrs)}
            print(f"  {lane}: {len(trades)} trades done", flush=True)
    cells_ref.update(cells)

    print("\nTERCILE4 EDGES (IS pooled rule lanes):", flush=True)
    for f in TERCILE4:
        vs = sorted(v for v in pools[f] if v is not None)
        if len(vs) < 40:
            FEATURES_B[f] = ("tercile4", None, ["Q1", "Q2", "Q3", "Q4"])
            print(f"  {f:18} INSUFFICIENT ({len(vs)})", flush=True)
            continue
        q1, q2, q3 = vs[len(vs) // 4], vs[len(vs) // 2], vs[3 * len(vs) // 4]
        FEATURES_B[f] = ("tercile4",
                         [(-1e9, q1), (q1, q2), (q2, q3), (q3, 1e9)],
                         ["<=%s" % fmtv(q1), "%s-%s" % (fmtv(q1), fmtv(q2)),
                          "%s-%s" % (fmtv(q2), fmtv(q3)), ">%s" % fmtv(q3)])
        print(f"  {f:18} Q1<={q1:.4g} Q2<={q2:.4g} Q3<={q3:.4g}", flush=True)

    for name in [n for n, s in FEATURES_B.items() if s[0] == "masked"]:
        fd = z1_fd.get(FEATURES_B[name][1])
        if not fd or not fd.get("edges"):
            print(f"  {name}: no Z1 edges - DROPPED", flush=True)
            del FEATURES_B[name]
        else:
            base, sign = FEATURES_B[name][1], FEATURES_B[name][2]
            FEATURES_B[name] = ("masked", fd["edges"], fd["labels"], base, sign)
    payload["features"] = {n: {"kind": s[0], "edges": list(s[1]) if s[1] else None,
                               "labels": list(s[2]) if s[2] else None}
                           for n, s in FEATURES_B.items()}

    # ---- bucket matrix
    print("\n" + "=" * 116, flush=True)
    print("  BUCKET MATRIX  (n / avgNet / netR)", flush=True)
    print("=" * 116, flush=True)
    matrix = {}
    for (scope, lane), C in cells.items():
        for name, spec in FEATURES_B.items():
            edges, labels = spec[1], spec[2]
            agg = {lab: {"n": 0, "sumR": 0.0, "sumNet": 0.0} for lab in labels}
            for t, f, nd in zip(C["trades"], C["feats"], C["nets"]):
                if not f.get("ok"):
                    continue
                v = f.get(name)
                if v is None:
                    continue
                lab = bucket_of(v, edges, labels)
                if lab is None:
                    continue
                b = agg[lab]
                b["n"] += 1
                b["sumR"] += float(t.get("r_multiple") or 0.0)
                b["sumNet"] += nd
            for b in agg.values():
                b["net"] = round(b["sumNet"], 1)
                b["sumR"] = round(b["sumR"], 1)
                b["share"] = round(100.0 * b["n"] / max(1, len(C["trades"])), 1)
            matrix[(scope, lane, name)] = agg
    for name in FEATURES_B:
        labels = FEATURES_B[name][2]
        print(f"\n-- {name}  bins: {' | '.join(labels)}", flush=True)
        for lane, _ in LANES:
            for scope in ("is", "oos"):
                agg = matrix[(scope, lane, name)]
                line = f"   {lane:9} {scope.upper():3}: "
                for lab in labels:
                    line += f"[{lab} {fmt(agg[lab])}] "
                print(line, flush=True)

    # ---- FIND rule
    def bucket_cells(name, lab):
        out = {}
        for scope in ("is", "oos"):
            for lane, _ in LANES:
                b = matrix[(scope, lane, name)][lab]
                out[(scope, lane)] = (b["n"], b["share"], b["sumNet"])
        return out

    qualifiers = []
    for name, spec in FEATURES_B.items():
        for lab in spec[2]:
            bc = bucket_cells(name, lab)
            if find_rule(bc):
                qualifiers.append({"name": name, "label": lab,
                                   "cells": {f"{s}|{l}": list(v)
                                             for (s, l), v in bc.items()}})
    print("\n" + "=" * 116, flush=True)
    print(f"  PHASE-1 QUALIFIERS (neg 4/4, n>=15, share<=35): "
          f"{len(qualifiers)}", flush=True)
    for q in qualifiers:
        c = q["cells"]
        print(f"   {q['name']}|{q['label']}  nets " +
              " ".join(f"{c[k][2]:+.1f}" for k in
                       ("is|champion", "is|utcsat", "oos|champion", "oos|utcsat")),
              flush=True)
    payload["qualifiers_phase1"] = qualifiers

    # ---- REMOVAL test
    def removal_test(name, lab, tag):
        edges, labels = FEATURES_B[name][1], FEATURES_B[name][2]
        rows, ok = {}, True
        for scope in ("is", "oos"):
            for lane, _ in LANES:
                C = cells[(scope, lane)]
                excl = 0
                keep_t = []
                for t, f in zip(C["trades"], C["feats"]):
                    bad = False
                    if f.get("ok") and f.get(name) is not None:
                        if bucket_of(f[name], edges, labels) == lab:
                            bad = True
                    if bad:
                        excl += 1
                    else:
                        keep_t.append(t)
                assert excl + len(keep_t) == len(C["trades"])
                m = equity_quality(keep_t, YEARS[scope])
                flat = C["flat"]
                d = arm_scores(m, flat)
                avg_n = m["net"] / max(1, m["n"])
                avg_b = flat["net"] / max(1, flat["n"])
                cell_ok = ((d.get("d_net") or 0) > 0 and avg_n >= avg_b
                           and m["n"] < flat["n"] and curve_better(d))
                ok = ok and cell_ok
                rows[f"{scope}|{lane}"] = {
                    "excl": excl, "n": m["n"], "base_n": flat["n"],
                    "net": round(m["net"], 1), "base_net": round(flat["net"], 1),
                    "d_net": round(d.get("d_net") or 0.0, 1),
                    "avg_net": round(avg_n, 3), "base_avg": round(avg_b, 3),
                    "max_dd": round(m["max_dd"], 1),
                    "base_max_dd": round(flat["max_dd"], 1),
                    "calmar": round(m["calmar"], 3),
                    "base_calmar": round(flat["calmar"], 3),
                    "curve_better": curve_better(d), "cell_pass": cell_ok}
        print(f"\n  REMOVAL [{tag}] {name} | {lab}  -> {'PASS' if ok else 'FAIL'}",
              flush=True)
        for k in ("is|champion", "is|utcsat", "oos|champion", "oos|utcsat"):
            r = rows[k]
            print(f"     {k:14} n {r['base_n']}->{r['n']}  net {r['base_net']:+.1f}->"
                  f"{r['net']:+.1f} (d{r['d_net']:+.1f})  avg {r['base_avg']:+.3f}->"
                  f"{r['avg_net']:+.3f}  DD {r['base_max_dd']}->{r['max_dd']}  "
                  f"calmar {r['base_calmar']}->{r['calmar']}  curve "
                  f"{r['curve_better']}  {'ok' if r['cell_pass'] else 'FAIL'}",
                  flush=True)
        return {"name": name, "label": lab, "rule": tag, "pass": ok, "cells": rows}

    removals = []
    for q in qualifiers:
        removals.append(removal_test(q["name"], q["label"], "phase1"))
    payload["removals_phase1"] = removals

    # ---- PASS-2 (only if phase1 empty)
    if not qualifiers:
        cands = []
        for name, spec in FEATURES_B.items():
            for lab in spec[2]:
                bc = bucket_cells(name, lab)
                if len(bc) < 4:
                    continue
                negs = sum(1 for n, sh, sn in bc.values() if sn < 0)
                if negs >= 2 and all(n >= 15 and sh <= 35.0 + 1e-9
                                     for n, sh, sn in bc.values()):
                    pooled = sum(sn for _, _, sn in bc.values())
                    cands.append((negs, pooled, name, lab))
        cands.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
        cands = cands[:40]
        print(f"\n  PASS-2 candidates (neg>=2/4, n>=15, share<=35): {len(cands)}",
              flush=True)
        # precompute per-cell masks + nets for candidates
        masks = {}
        for (name, lab) in ((c[2], c[3]) for c in cands):
            edges, labels = FEATURES_B[name][1], FEATURES_B[name][2]
            for scope in ("is", "oos"):
                for lane, _ in LANES:
                    C = cells[(scope, lane)]
                    masks[(name, lab, scope, lane)] = [
                        bool(f.get("ok") and f.get(name) is not None
                             and bucket_of(f[name], edges, labels) == lab)
                        for f in C["feats"]]
        pair_quals = []
        tested = 0
        for (n1, p1, a1, l1), (n2, p2, a2, l2) in itertools.combinations(cands, 2):
            if a1 == a2:
                continue
            tested += 1
            bc = {}
            good = True
            for scope in ("is", "oos"):
                for lane, _ in LANES:
                    m1 = masks[(a1, l1, scope, lane)]
                    m2 = masks[(a2, l2, scope, lane)]
                    C = cells[(scope, lane)]
                    cnt, s = 0, 0.0
                    for i in range(len(m1)):
                        if m1[i] and m2[i]:
                            cnt += 1
                            s += C["nets"][i]
                    bc[(scope, lane)] = (cnt, 100.0 * cnt / max(1, len(C["trades"])), s)
            if find_rule(bc):
                pair_quals.append({"name": f"{a1}|{l1} AND {a2}|{l2}",
                                   "cells": {f"{s}|{l}": list(v)
                                             for (s, l), v in bc.items()}})
        print(f"  PASS-2 pairs tested: {tested}; qualifiers: {len(pair_quals)}",
              flush=True)
        payload["pass2"] = {"candidates": [{"name": c[2], "label": c[3],
                                            "neg_cells": c[0], "pooled_net": round(c[1], 1)}
                                           for c in cands],
                            "pairs_tested": tested,
                            "qualifiers": pair_quals}
        for pq in pair_quals:
            a1l, a2l = pq["name"].split(" AND ")
            (a1, l1), (a2, l2) = a1l.rsplit("|", 1), a2l.rsplit("|", 1)
            # intersection removal: exclude if BOTH members
            removals.append(removal_pair(a1, l1, a2, l2, "pass2"))
        payload["removals_pass2"] = [r for r in removals if r["rule"] == "pass2"]

    print("\n" + "=" * 116, flush=True)
    passed = [r for r in removals if r["pass"]]
    print(f"  REMOVAL PASS: {len(passed)} / {len(removals)} tested", flush=True)
    payload["removal_pass_count"] = len(passed)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    payload["matrix"] = {f"{s}|{l}|{n}": m for (s, l, n), m in matrix.items()}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


def removal_pair(a1, l1, a2, l2, tag):
    e1, lb1 = FEATURES_B[a1][1], FEATURES_B[a1][2]
    e2, lb2 = FEATURES_B[a2][1], FEATURES_B[a2][2]
    rows, ok = {}, True
    for scope in ("is", "oos"):
        for lane, _ in LANES:
            C = cells_ref[(scope, lane)]
            keep_t, excl = [], 0
            for t, f in zip(C["trades"], C["feats"]):
                in1 = (f.get("ok") and f.get(a1) is not None
                       and bucket_of(f[a1], e1, lb1) == l1)
                in2 = (f.get("ok") and f.get(a2) is not None
                       and bucket_of(f[a2], e2, lb2) == l2)
                if in1 and in2:
                    excl += 1
                else:
                    keep_t.append(t)
            m = equity_quality(keep_t, YEARS[scope])
            flat = C["flat"]
            d = arm_scores(m, flat)
            avg_n = m["net"] / max(1, m["n"])
            avg_b = flat["net"] / max(1, flat["n"])
            cell_ok = ((d.get("d_net") or 0) > 0 and avg_n >= avg_b
                       and m["n"] < flat["n"] and curve_better(d))
            ok = ok and cell_ok
            rows[f"{scope}|{lane}"] = {
                "excl": excl, "n": m["n"], "base_n": flat["n"],
                "net": round(m["net"], 1), "base_net": round(flat["net"], 1),
                "d_net": round(d.get("d_net") or 0, 1),
                "avg_net": round(avg_n, 3), "base_avg": round(avg_b, 3),
                "max_dd": round(m["max_dd"], 1), "base_max_dd": round(flat["max_dd"], 1),
                "calmar": round(m["calmar"], 3), "base_calmar": round(flat["calmar"], 3),
                "curve_better": curve_better(d), "cell_pass": cell_ok}
    print(f"\n  REMOVAL [{tag}] {a1}|{l1} AND {a2}|{l2} -> {'PASS' if ok else 'FAIL'}",
          flush=True)
    for k in ("is|champion", "is|utcsat", "oos|champion", "oos|utcsat"):
        r = rows[k]
        print(f"     {k:14} n {r['base_n']}->{r['n']}  net {r['base_net']:+.1f}->"
              f"{r['net']:+.1f} (d{r['d_net']:+.1f})  avg {r['base_avg']:+.3f}->"
              f"{r['avg_net']:+.3f}  DD {r['base_max_dd']}->{r['max_dd']}  "
              f"{'ok' if r['cell_pass'] else 'FAIL'}", flush=True)
    return {"name": f"{a1}|{l1} AND {a2}|{l2}", "label": "pair", "rule": tag,
            "pass": ok, "cells": rows}


def fmtv(v):
    return ("%.4g" % v)


cells_ref = {}


if __name__ == "__main__":
    main()
