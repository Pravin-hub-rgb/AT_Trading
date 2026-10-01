"""min_bars 25 vs 50 FORENSIC + the full metrics table that was missing.

THE PUZZLE
==========
Shipped is LTF 15m / HTF 1h with min_bars_15m=50 (a 12.5h LTF swing). The
tf-family grid (log 106) also ran min_bars_15m=25 (a 6.25h LTF swing) on the
SAME timeframe pair and got a split verdict:

              min_bars 50        min_bars 25
    IS          +325.8R             +272.8R      50 wins by 53R
    OOS          +70.2R             +128.6R      25 wins by 58R

That is a clean inversion on the same asset, the same params and the same
timeframes. A swing that is 12.5h long is better in 2023-26 and worse in
2021-22. If the reason can be identified, it becomes a *conditional* rule -
"use the long swing when X, the short swing when Y" - which is worth far more
than either fixed choice.

This is NOT a threshold search dressed up as research. The questions are fixed in
advance and the rule, if any, is fitted on IS ONLY and then scored on OOS, which
it has never seen. If the rule does not transfer, the honest answer is "it is
noise" and that is the result we report.

PHASE 1 - full metrics table. The tf-family JSON stored only n/net/PF/DD. This
re-runs the whole grid capturing the complete equity_quality set, so the
comparison is made on like metrics rather than a subset.

PHASE 2 - is the inversion even real? Bootstrapped CI on the net difference and
a paired same-trade comparison. A 58R gap on ~250 trades can easily be sampling
noise; that has to be ruled out BEFORE hunting for a mechanism, or the mechanism
hunt will find a story in nothing.

PHASE 3 - autopsy. Year-by-year, and against CAUSAL regime proxies computed at
entry (trailing realised vol and trailing trend, both from 1h closes only). The
mechanism being tested is concrete: a 12.5h swing needs 12.5h of travel to form,
so it should lag in fast/choppy tape and be fine in slow trending tape.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_mb_forensic.py
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_mb_forensic.json"
TBL = ROOT / "backtest/docs/TF_METRICS_TABLE.md"
M15, M30, H1, H2 = 900, 1800, 3600, 7200
BOOT_N = 20000
SEED = 20260927

CELLS = {
    "F0_control_15m_1h": (M15, H1),
    "F1_ltf_only_30m_1h": (M30, H1),
    "F2_htf_only_15m_2h": (M15, H2),
    "F3_family_30m_2h": (M30, H2),
}
MB_VARIANTS = (("mb50_count", 50), ("mb25_duration", 25))
CELLS_FLAT = (("F0_control_15m_1h", 50), ("F0_control_15m_1h", 25),
              ("F1_ltf_only_30m_1h", 50), ("F1_ltf_only_30m_1h", 25),
              ("F2_htf_only_15m_2h", 50), ("F2_htf_only_15m_2h", 25),
              ("F3_family_30m_2h", 50), ("F3_family_30m_2h", 25))
BYBIT_BASE = {"champion": {"is": (500, 325.8), "oos": (279, 70.2)},
              "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
              "age10": {"is": (130, 435.7), "oos": (76, 43.2)}}
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"),
         ("age10", "age10_dirmatch_swingpause_single_sw10"))
# END_MARKER



# ---------------------------------------------------------------- regime proxies
def regime_series(candles_1h):
    """Causal per-1h-bar trailing volatility and trend, in percent of price.

    Trailing 24h realised vol = stdev of 1h log returns over the last 24 bars.
    Trailing trend = |close - close[-24]| / close[-24], the fraction of price
    actually travelled in one day. Both use ONLY bars at or before the current
    one, so a value attached to a trade entry uses no future information.

    These are deliberately simple and un-tuned. The question is whether a split
    EXISTS, not whether these particular proxies are the right ones; a large
    search over indicators would find a split by construction and mean nothing.
    """
    import math
    ts = [int(c["ts"]) for c in candles_1h]
    cl = [float(c["close"]) for c in candles_1h]
    out = {}
    rets = [0.0]
    for i in range(1, len(cl)):
        rets.append(math.log(cl[i] / cl[i - 1]) if cl[i - 1] > 0 else 0.0)
    for i in range(24, len(cl)):
        w = rets[i - 23:i + 1]
        m = sum(w) / len(w)
        var = sum((x - m) ** 2 for x in w) / (len(w) - 1)
        out[ts[i]] = {"vol": math.sqrt(var) * 100.0,
                      "trend": abs(cl[i] - cl[i - 24]) / cl[i] * 100.0}
    return out


def vol_terciles(proxies):
    """Fixed vol tercile edges from the IS era only, reused verbatim on OOS.

    Deriving the edges on IS and applying them to OOS is the whole point: a
    threshold that gets re-fitted per era is not a rule, it is a description.
    """
    vols = sorted(p["vol"] for p in proxies.values())
    if len(vols) < 30:
        return None
    q1, q2 = vols[len(vols) // 3], vols[2 * len(vols) // 3]
    return [("low", 0.0, q1), ("mid", q1, q2), ("high", q2, 1e9)]


def bucket_of(ts, proxies, terciles):
    """Assign a trade to a vol tercile using the fixed thresholds."""
    p = proxies.get(ts)
    if p is None:
        return None, None
    for name, lo, hi in terciles:
        if lo <= p["vol"] < hi:
            return name, p
    return None, p


def bootstrap_diff_ci(a, b, n_boot=BOOT_N, seed=SEED):
    """95% CI on mean(b) - mean(a), resampling trades independently.

    Resamples TRADES, not model outputs, so this is a straight read on whether
    an observed net gap could plausibly be sampling noise.
    """
    if len(a) < 20 or len(b) < 20:
        return {"ci95": None, "p_two_sided": None, "n_a": len(a), "n_b": len(b)}
    rng = random.Random(seed)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    diffs = []
    na, nb = len(a), len(b)
    for _ in range(n_boot):
        sa = sum(a[rng.randrange(na)] for _ in range(na)) / na
        sb = sum(b[rng.randrange(nb)] for _ in range(nb)) / nb
        diffs.append(sb - sa)
    diffs.sort()
    lo = diffs[int(0.025 * n_boot)]
    hi = diffs[int(0.975 * n_boot)]
    # two-sided bootstrap p = 2 * min(P(diff<=0), P(diff>=0)), capped at 1.
    # The naive "(count<=0 + count>=0) / n_boot" is always ~1.0 because every
    # resample satisfies one of the two, so it must not be written that way.
    pl = sum(1 for x in diffs if x <= 0) / n_boot
    pg = sum(1 for x in diffs if x >= 0) / n_boot
    p = min(1.0, 2.0 * min(pl, pg))
    return {"mean_a": round(ma, 4), "mean_b": round(mb, 4),
            "diff": round(mb - ma, 4), "ci95": [round(lo, 4), round(hi, 4)],
            "p_two_sided": round(min(1.0, p), 4), "n_a": na, "n_b": nb,
            "n_boot": n_boot, "seed": seed}


def run_all():
    """Phase 1. Run the whole grid, keep FULL equity_quality plus raw books."""
    from exp_tf_family import build_family_module, load_scope, build_planes
    from exp_sizing_combo import run as sim_fn
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS
    from src.btc.btc_routes import _compute_swings

    sim = build_family_module()
    table, books_out = {}, {}
    for scope in ("is", "oos"):
        raw = load_scope(scope)
        pl = build_planes(raw)
        px = regime_series(raw["c1h"])
        for cell, mb in CELLS_FLAT:
            ltf_s, htf_s = CELLS[cell]
            sw15 = _compute_swings(pl["f15"], "continuous", min_bars=mb)
            ltf = ({"c15": pl["c15"], "sw15": sw15} if ltf_s == M15
                   else {"c15": pl["c30"], "sw15": _compute_swings(
                       pl["f30"], "continuous", min_bars=mb)})
            flow = pl["f1h"] if htf_s == H1 else pl["f2h"]
            htf = {"c1h": pl["c1h"] if htf_s == H1 else pl["c2h"],
                   "sw20": _compute_swings(flow, "continuous", min_bars=20),
                   "sw10": _compute_swings(flow, "continuous", min_bars=10)}
            for lane, key in LANES:
                params = {**BP, **EXPERIMENTS[key]["params"]}
                trades = sim_fn(sim, {**htf, **ltf, "fine": pl["fine"]}, params,
                                htf_bar_secs=htf_s, ltf_bar_secs=ltf_s)
                m = equity_quality(trades, YEARS[scope])
                m["avg_r"] = round(m["net"] / m["n"], 4) if m["n"] else 0.0
                m["dnet_yr"] = round(m["net"] / YEARS[scope], 1)
                k = f"{scope}/mb{mb}/{cell}/{lane}"
                table[k] = m
                if cell == "F0_control_15m_1h" and lane == "champion":
                    books_out[(scope, mb)] = (trades, px)
                # identity gate: the shipped pair at shipped min_bars must
                # reproduce the published books before any of this is evidence
                if cell == "F0_control_15m_1h" and mb == 50:
                    en, ev = BYBIT_BASE[lane][scope]
                    assert m["n"] == en and abs(m["net"] - ev) < 0.5, (
                        f"CONTROL FAIL {scope}/{lane}: "
                        f"{m['n']}/{m['net']} != {en}/{ev}")
                print(f"  {k:<44} n={m['n']:>3} net={m['net']:>+8.1f} "
                      f"avgR={m['avg_r']:>+5.2f} PF={m['pf']:>5.2f} "
                      f"DD={m['max_dd']:>6.1f} wr={m['wr']:>5.1f}", flush=True)
    assert len(table) == 48, f"expected 48 grid cells, got {len(table)}"
    return table, books_out


def forensics(books_out, payload):
    """Phases 2 and 3 on the shipped 15m/1h pair, min_bars 50 vs 25."""
    from run_experiment import net_r
    for scope in ("is", "oos"):
        (t50, px), (t25, _) = books_out[(scope, 50)], books_out[(scope, 25)]
        r50 = [net_r([t]) for t in t50]
        r25 = [net_r([t]) for t in t25]
        k50 = {(int(t["entry_ts"]), int(t["exit_ts"])) for t in t50}
        k25 = {(int(t["entry_ts"]), int(t["exit_ts"])) for t in t25}
        both = k50 & k25
        F = {}
        F["paired"] = {"shared_trades": len(both),
                       "only_mb50": len(k50 - k25), "only_mb25": len(k25 - k50),
                       "net_mb50": round(sum(r50), 1), "net_mb25": round(sum(r25), 1)}
        # shared trades carry identical R, so the whole gap comes from the
        # non-shared set - that is the mechanism to explain
        idx50 = {(int(t["entry_ts"]), int(t["exit_ts"])): net_r([t]) for t in t50}
        idx25 = {(int(t["entry_ts"]), int(t["exit_ts"])): net_r([t]) for t in t25}
        F["shared_net"] = {"mb50": round(sum(idx50[k] for k in both), 1),
                           "mb25": round(sum(idx25[k] for k in both), 1)}
        F["unshared_net"] = {"mb50": round(sum(v for k, v in idx50.items() if k not in both), 1),
                             "mb25": round(sum(v for k, v in idx25.items() if k not in both), 1)}
        for nm, r in (("mb50", r50), ("mb25", r25)):
            srt = sorted(r, reverse=True)
            F.setdefault("distribution", {})[nm] = {
                "n": len(r), "mean": round(sum(r) / len(r), 4),
                "median": round(statistics.median(r), 3),
                "stdev": round(statistics.pstdev(r), 3),
                "best": round(max(r), 2), "worst": round(min(r), 2),
                "top5_sum": round(sum(srt[:5]), 1),
                "top5_share_pct": round(100.0 * sum(srt[:5]) / max(sum(r), 1e-9), 1)}
        F["bootstrap"] = bootstrap_diff_ci(r50, r25)
        F["bootstrap_swapped"] = bootstrap_diff_ci(r25, r50, seed=SEED + 1)
        yr = {}
        for nm, t in (("mb50", t50), ("mb25", t25)):
            for tr, x in zip(t, ([net_r([q]) for q in t])):
                d = str(tr.get("exit_date") or tr.get("entry_date") or "")
                if len(d) >= 4:
                    yr.setdefault(d[:4], {}).setdefault(nm, 0.0)
                    yr[d[:4]][nm] += x
        F["by_year"] = {k: {nm: round(v, 1) for nm, v in d.items()}
                        for k, d in sorted(yr.items())}
        F["by_year_n"] = {}
        for nm, t in (("mb50", t50), ("mb25", t25)):
            for tr in t:
                d = str(tr.get("exit_date") or tr.get("entry_date") or "")
                if len(d) >= 4:
                    F["by_year_n"][d[:4]] = F["by_year_n"].get(d[:4], 0) + 1
        payload.setdefault("forensic", {})[scope] = F
        globals()["_PX"] = globals().get("_PX", {})
        globals()["_PX"][scope] = px
        globals()["_IDX"] = globals().get("_IDX", {})
        globals()["_IDX"][scope] = {"mb50": idx50, "mb25": idx25}
    return payload


def regime_split(payload, px_by_scope, idx_by_scope):
    """Phase 3. Does a CAUSAL vol tercile say which min_bars to use?

    Edges are fitted on IS ONLY, then the same absolute edges are applied to OOS,
    which the rule has never seen. A rule that holds only in the era it was
    fitted on is reported as NOT transferring, however good it looks in-sample.
    """
    edges = vol_terciles(px_by_scope["is"])
    if edges is None:
        payload["regime"] = {"verdict": "too few vol points to bucket"}
        return payload
    out = {"edges": [{"name": n, "lo": round(lo, 5),
                      "hi": (None if hi > 1e8 else round(hi, 5))} for n, lo, hi in edges],
           "fitted_on": "is", "by_era": {}}
    for scope in ("is", "oos"):
        px, idx = px_by_scope[scope], idx_by_scope[scope]
        cells = {}
        for nm in ("mb50", "mb25"):
            for bk in ("low", "mid", "high"):
                cells.setdefault(bk, {}).setdefault(nm, {"n": 0, "net": 0.0})
        for nm in ("mb50", "mb25"):
            for k, x in idx[nm].items():
                b, _ = bucket_of(int(k[0]), px, edges)
                if b:
                    cells[b][nm]["n"] += 1
                    cells[b][nm]["net"] += x
        for bk, d in cells.items():
            for nm in d:
                d[nm]["net"] = round(d[nm]["net"], 1)
        out["by_era"][scope] = cells
    out["winner"] = {}
    for scope, cells in out["by_era"].items():
        w = {}
        for bk, d in cells.items():
            if d["mb50"]["n"] and d["mb25"]["n"]:
                w[bk] = {"mb50": d["mb50"]["net"], "mb25": d["mb25"]["net"],
                         "delta": round(d["mb25"]["net"] - d["mb50"]["net"], 1),
                         "n": d["mb50"]["n"]}
        out["winner"][scope] = w
    isw = {k: v["delta"] for k, v in out["winner"].get("is", {}).items()}
    oosw = {k: v["delta"] for k, v in out["winner"].get("oos", {}).items()}
    shared = sorted(set(isw) & set(oosw))
    ok = [k for k in shared if (isw[k] > 0) == (oosw[k] > 0) and abs(isw[k]) >= 5]
    out["transfer_check"] = {"buckets": shared, "sign_consistent": ok,
                             "transfers": bool(ok), "is": isw, "oos": oosw}
    out["verdict"] = (
        "A vol-tercile rule fitted on IS does NOT transfer to OOS: trailing "
        "volatility alone does not explain the 25-vs-50 preference."
        if not ok else
        f"Vol-tercile sign agrees across eras in bucket(s) {ok}. This is a "
        f"CANDIDATE, not a rule: per-bucket n is small and one agreeing bucket "
        f"out of three is roughly what chance delivers.")
    payload["regime"] = out
    return payload


def write_table(table):
    """Human-readable full metrics table, grouped so it reads at a glance."""
    cols = ["n", "net", "avg_r", "wr", "pf", "max_dd", "dnet_yr", "sortino",
            "calmar", "ulcer", "max_streak", "pos_month_pct", "worst_month",
            "pos_year_pct", "worst_year"]
    L = ["# Full LTF/HTF metrics table", "",
         "Generated by `exp_mb_forensic.py`. **net is in R** (1R = the harness's fixed",
         "per-trade unit), `avgR = net/n`, `dnet_yr = net / era years`, PF = gross win /",
         "gross loss, `wr` = win rate %, `max_dd` in R. All cells re-run with the full",
         "equity metric set; the earlier `_tf_family.json` stored only n/net/PF/DD, so",
         "cross-referencing the two is not safe.", ""]
    for mb in (50, 25):
        swing_h = mb * 15 / 60.0          # bars x 15 min -> clock hours
        tag = "SHIPPED" if mb == 50 else "variant"
        L.append(f"## min_bars_15m = {mb} - {tag} - LTF swing {swing_h:.2f}h")
        L.append("")
        for scope in ("is", "oos"):
            L.append(f"### {scope.upper()}")
            L.append("")
            L.append("| cell / lane | " + " | ".join(cols) + " |")
            L.append("|" + "---|" * (len(cols) + 1))
            for cell, m_ in CELLS_FLAT:
                if m_ != mb:
                    continue
                for lane, _k in LANES:
                    m = table.get(f"{scope}/mb{mb}/{cell}/{lane}")
                    if not m:
                        continue
                    L.append("| " + " | ".join(
                        [f"{cell} / {lane}"] + [str(m.get(c, "")) for c in cols]) + " |")
            L.append("")
    TBL.write_text("\n".join(L) + "\n", encoding="utf-8")
    return TBL
# END_MARKER


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  min_bars 25 vs 50 forensic + full metrics table", flush=True)
    print("=" * 100, flush=True)
    print("\n--- PHASE 1: full grid, full metrics ---", flush=True)
    table, books_out = run_all()

    print("\n--- PHASE 2/3: forensic on shipped 15m/1h ---", flush=True)
    from run_experiment import net_r
    px, idx = {}, {}
    for s in ("is", "oos"):
        px[s] = books_out[(s, 50)][1]
        idx[s] = {f"mb{mb}": {(int(x["entry_ts"]), int(x["exit_ts"])): net_r([x])
                              for x in books_out[(s, mb)][0]} for mb in (50, 25)}
    payload = {"stage": "mb_forensic",
               "puzzle": "shipped mb50 wins IS (+325.8 vs +272.8); mb25 wins OOS "
                         "(+70.2 vs +128.6) on the same pair and params",
               "protocol": "IS-fit, OOS-validated; grid re-run for like metrics",
               "forensic": {}}
    payload = forensics(books_out, payload)
    payload = regime_split(payload, px, idx)
    payload["table"] = table
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    p = write_table(table)
    for s in ("is", "oos"):
        f = payload["forensic"][s]
        print(f"\n[{s.upper()}] shared={f['paired']['shared_trades']} "
              f"only50={f['paired']['only_mb50']} only25={f['paired']['only_mb25']}"
              f" | net50={f['paired']['net_mb50']} net25={f['paired']['net_mb25']}")
        print(f"   shared-net 50={f['shared_net']['mb50']} 25={f['shared_net']['mb25']}"
              f" | unshared-net 50={f['unshared_net']['mb50']} 25={f['unshared_net']['mb25']}")
        b = f["bootstrap"]
        print(f"   bootstrap diff(25-50)={b['diff']} CI95={b['ci95']} p={b['p_two_sided']}")
        print(f"   by_year {f['by_year']}")
    print(f"\nregime verdict: {payload['regime'].get('verdict')}")
    for sc, w in payload["regime"].get("winner", {}).items():
        print(f"   {sc}: {w}")
    print(f"\nwrote {OUT}\n      {p} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
