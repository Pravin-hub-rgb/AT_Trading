"""WICK 1h DEEP INVESTIGATION - the three open items from the (a13) audit.

(a13) established: the 1h wick gate reproduces, the cohort is robust (6/6
ex-best), but 6.026 sits AT a sign-flip cliff, the flip point differs by era
(IS ~6.3, OOS ~7.5), and age10's cohort is positive at EVERY threshold. The
ruling was HOLD pending these three answers.

  Q1 STABILITY - sweep 5.0 -> 8.0 in 0.1 steps. Is there ANY threshold that is
     negative in both eras for champion+utcsat? If the two eras' flip points
     only barely overlap, there is no stable rule and the gate cannot be
     specified without picking a number per era, which is a fitted rule.
     Also records, per cell, the EXACT flip point (last threshold still
     negative) so the two eras can be compared directly.

  Q2 AGE10 ANATOMY - why is its cohort positive? Four sub-questions:
       (a) is the +2.0R concentrated in one or two trades, or spread?
       (b) how does the age10 cohort compare to age10's own book on WR/PF?
       (c) where does age10 sit in the wick_atr12 distribution vs the others -
           is the 6.026 cutoff even biting the same part of the distribution?
       (d) is age10 the outlier, or is it the ONLY lane that is "single" while
           champion/utcsat are "multi" - i.e. is this a lane-class effect
           rather than a wick effect?

  Q3 LANE DENSITY - trades/year and book avgR per lane, to test whether cohort
     negativity tracks book density rather than the wick feature.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
  No new gates, no new thresholds chosen after seeing results. The question is
  descriptive: does a stable window exist, and what explains age10.
  Controls: bybit base ledgers must reproduce the 24.85 references.
  Any threshold quoted as "stable" must be negative in BOTH eras for
  champion AND utcsat simultaneously.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_wick1h_deep.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from run_experiment import net_r

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_wick1h_deep.json"
FINE = tuple(round(5.0 + 0.1 * i, 2) for i in range(31))   # 5.0 .. 8.0
STAGEB_THR = 6.026
# Stage B reference (from exp_bleed_autopsy / the other agent's parity block).
# The deep harness now ASSERTS these before reporting anything.
PARITY_REF = {
    "is/champion": (74, -28.056935), "is/utcsat": (62, -25.673556),
    "oos/champion": (35, -19.780510), "oos/utcsat": (36, -23.774610),
}
LANE_CLASS = {"champion": "multi", "utcsat": "multi", "age10": "single"}

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)
# END_MARKER



def build_ctx(data):
    from exp_regime_structure_autopsy import build_arrays, _chop_series_1h
    arr = build_arrays(data["c1h"])
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        conf.append((arr["ts"][ci], s["dir"],
                     float(max(1, s["seg"]["end_idx"] - s["seg"]["start_idx"]))))
    conf.sort(key=lambda x: x[0])
    return {"arr": arr, "chop": _chop_series_1h(data["c1h"], lb=14),
            "conf_ts": [x[0] for x in conf], "conf_dir": [x[1] for x in conf],
            "conf_dur": [x[2] for x in conf]}


def short_rows(trades, feats):
    """(net, wick_atr12) for every SHORT trade with a usable feature."""
    out = []
    for t, f in zip(trades, feats):
        if t.get("dir") == "long":
            continue
        w = f.get("wick_atr12")
        if w is None:
            continue
        out.append((net_r([t]), float(w)))
    return out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  WICK 1h DEEP - stability window, age10 anatomy, lane density",
          flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_regime_structure_autopsy import compute_features
    from experiment_registry import BP, EXPERIMENTS

    sim = build_module()
    payload = {"stage": "wick1h_deep", "fine_sweep": list(FINE),
               "stageb_thr": STAGEB_THR, "cells": {}, "fine": {},
               "anatomy": {}, "density": {}}

    for scope in ("is", "oos"):
        data = load_bybit(scope, sim)
        ctx = build_ctx(data)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            trades = sim_fn(sim, data, params)
            n, net = len(trades), net_r(trades)
            en, ev = BYBIT_BASE[name][scope]
            assert n == en and abs(net - ev) < 0.5, f"CONTROL {scope}/{name}"
            feats = [compute_features(t, ctx) for t in trades]
            rows = short_rows(trades, feats)
            book_avg = net / n
            payload["density"][f"{scope}/{name}"] = {
                "lane_class": LANE_CLASS[name], "n_all": n, "net": round(net, 2),
                "book_avg_r": round(book_avg, 4),
                "trades_per_year": round(n / YEARS[scope], 1),
                "n_short": len(rows),
                "short_pct": round(100.0 * len(rows) / n, 1)}
            print(f"\n{scope}/{name} [{LANE_CLASS[name]}] n={n} net={net:+.1f} "
                  f"bookAvgR={book_avg:+.3f} short={len(rows)} "
                  f"({100.0*len(rows)/n:.0f}%) {n/YEARS[scope]:.0f}t/yr", flush=True)

            last_neg = None
            for thr in FINE:
                # Stage B's bucket_of is STRICT (v < thr). Using <= added one
                # trade per IS cell and broke parity; strict < reproduces it.
                c = [r for r in rows if r[1] < thr]
                s = sum(r[0] for r in c)
                payload["fine"][f"{scope}/{name}/{thr}"] = {
                    "thr": thr, "n": len(c), "sum_net": round(s, 3),
                    "pct_of_short": round(100.0 * len(c) / len(rows), 1)}
                if s < 0:
                    last_neg = thr
            payload["cells"][f"{scope}/{name}"] = {"flip_thr_last_negative": last_neg}
            print(f"   flip (last negative thr in {FINE[0]}-{FINE[-1]}): {last_neg}",
                  flush=True)

            c = [r for r in rows if r[1] < STAGEB_THR]
            un = [r for r in rows if r[1] >= STAGEB_THR]
            if c:
                s = sum(r[0] for r in c)
                srt = sorted((r[0] for r in c), reverse=True)
                best = srt[0]
                a = {
                    "n_cohort": len(c), "sum_net": round(s, 3),
                    "avg_r": round(s / len(c), 4),
                    "cohort_wr": round(sum(1 for x in srt if x > 0) / len(srt), 4),
                    "book_short_avg_r": round(
                        sum(r[0] for r in rows) / len(rows), 4),
                    "sum_net_ex_best": round(s - best, 3),
                    "top3_contrib": round(sum(srt[:3]), 3),
                    "n_winners": sum(1 for x in srt if x > 0),
                    "n_losers": sum(1 for x in srt if x <= 0),
                    "unflagged_avg_r": (round(sum(r[0] for r in un) / len(un), 4)
                                        if un else None),
                }
                w = sorted(r[1] for r in rows)
                a["wick_pct_of_short"] = {
                    "p10": round(w[int(0.1 * len(w))], 3),
                    "p50": round(w[len(w) // 2], 3),
                    "p90": round(w[int(0.9 * len(w))], 3)}
                payload["anatomy"][f"{scope}/{name}"] = a
                print(f"   cohort n={a['n_cohort']} sum={a['sum_net']:+.2f} "
                      f"avgR={a['avg_r']:+.3f} vs shortBook="
                      f"{a['book_short_avg_r']:+.3f} | exBest="
                      f"{a['sum_net_ex_best']:+.2f} top3={a['top3_contrib']:+.2f}",
                      flush=True)
                print(f"   wick dist p10={a['wick_pct_of_short']['p10']} "
                      f"p50={a['wick_pct_of_short']['p50']} "
                      f"p90={a['wick_pct_of_short']['p90']}", flush=True)

    # ---- PARITY CONTROL - hard abort, per the house rule -----------------
    # (a13) reported every verdict even though this control FAILED, which broke
    # the house rule "a control mismatch means the harness is wrong, not the
    # venue". The control is now an assert: if Stage B parity does not hold,
    # NOTHING below is computed or printed.
    if PARITY_REF:
        for kk, (en, es) in PARITY_REF.items():
            n_got = payload["anatomy"][kk]["n_cohort"]
            s_got = payload["anatomy"][kk]["sum_net"]
            ok = (n_got == en and abs(s_got - es) < 1e-3)
            payload["parity"] = payload.get("parity", {})
            payload["parity"][kk] = {
                "n": n_got, "n_expected": en,
                "sum_net": s_got, "sum_expected": es, "match": ok}
            assert ok, (
                f"STAGE B PARITY FAIL {kk}: n {n_got} vs {en}, "
                f"sum {s_got} vs {es} - harness wrong, aborting before verdicts")
    print("  [control-ok] Stage B parity exact in all "
          f"{len(PARITY_REF)} cells", flush=True)

    # ---- Q1 STABILITY ---------------------------------------------------
    # BUG FIX (found by the other agent): this dict used `c` as the key while
    # iterating over BOTH s and c, so the IS value was silently overwritten by
    # the OOS value and the window was OOS-only. Key on (scope, lane) like the
    # all6 block below, which was already correct.
    stable = []
    for thr in FINE:
        ck = {f"{s}/{c}": payload["fine"][f"{s}/{c}/{thr}"]["sum_net"] < 0
              for s in ("is", "oos") for c in ("champion", "utcsat")}
        if all(ck.values()):
            stable.append(thr)
    all6 = []
    for thr in FINE:
        ck = {f"{s}/{c}": payload["fine"][f"{s}/{c}/{thr}"]["sum_net"] < 0
              for s in ("is", "oos") for c in ("champion", "utcsat", "age10")}
        if all(ck.values()):
            all6.append(thr)

    print("\n" + "=" * 100, flush=True)
    print("  Q1 STABILITY", flush=True)
    for k, v in payload["cells"].items():
        print(f"    {k:16} [{v['flip_thr_last_negative']}]  flip = last negative thr",
              flush=True)
    def blocks(vals):
        """Contiguous runs, so a HOLE inside the window is visible, not hidden."""
        out, cur = [], []
        for v in vals:
            if cur and abs(v - cur[-1]) > 0.11:
                out.append((cur[0], cur[-1]))
                cur = []
            cur.append(v)
        if cur:
            out.append((cur[0], cur[-1]))
        return [f"{a:.1f}-{b:.1f}" for a, b in out]

    print(f"    stable window (champion+utcsat, BOTH eras): "
          f"{' | '.join(blocks(stable)) if stable else 'NONE'} "
          f"({len(stable)} steps; blocks shown, holes explicit)", flush=True)
    print(f"    stable window (ALL 6 cells): "
          f"{all6[0] if all6 else None} .. {all6[-1] if all6 else None} "
          f"({len(all6)} steps)", flush=True)

    # ---- Q2 AGE10 -------------------------------------------------------
    print("\n  Q2 AGE10 ANATOMY (at thr 6.026)", flush=True)
    for k, a in payload["anatomy"].items():
        print(f"    {k:16} n={a['n_cohort']:>3} sum={a['sum_net']:>+7.2f} "
              f"exBest={a['sum_net_ex_best']:>+7.2f} top3={a['top3_contrib']:>+7.2f} "
              f"W/L={a['n_winners']}/{a['n_losers']} "
              f"wickP50={a['wick_pct_of_short']['p50']}", flush=True)

    print("\n  Q3 LANE DENSITY", flush=True)
    for k, d in payload["density"].items():
        print(f"    {k:16} [{d['lane_class']:6}] {d['trades_per_year']:>6.1f}t/yr "
              f"bookAvgR={d['book_avg_r']:>+7.3f} short={d['short_pct']:>5.1f}%",
              flush=True)

    payload["verdicts"] = {
        "stable_window_ck_u": stable, "stable_window_all6": all6,
        "has_stable_window": bool(stable),
        "has_stable_window_all6": bool(all6),
        "flip_points": {k: v["flip_thr_last_negative"]
                        for k, v in payload["cells"].items()},
    }
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
