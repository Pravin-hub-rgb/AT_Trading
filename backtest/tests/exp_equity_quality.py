"""Equity-curve quality study — key arms from the 2026-09-24 batch.

Re-runs baseline / half / half+delay1 / delay_r_1.5 / skip_decisive ON
on champion + utcsat + age10, IS + OOS, and scores the NET equity path:

  maxDD, maxDD duration (trades), time underwater %, ulcer index,
  sortino (trade-level downside), calmar (net/maxDD), recovery factor,
  monthly win %, worst month, yearly min, PF, max consecutive losses.

Purpose: judge arms by curve shape / robustness and report raw P&L deltas separately.
Identity gate green on IS before any arm runs. Sequential only.
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_equity_quality_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

CONFIGS = (
    "champion_multi_sw10",
    "utcsat_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)

# Pre-frozen focus arms (no post-hoc selection of extras)
ARMS = (
    ("baseline", {}),
    ("half", dict(exp_trail_half=1)),
    ("half+delay1", dict(exp_trail_half=1, exp_trail_delay_r=1.0)),
    ("delay_r_1.5", dict(exp_trail_delay_r=1.5)),
    ("skip_decisive", dict(exp_skip_decisive=1)),
)


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        # sw20 was missing here until 2026-10-02. Every registry book whose
        # "swing" is sw20 raised KeyError('sw20') on OOS - 19 books - so they
        # were silently unmeasurable out of sample while their sw10 twins were
        # fine. get_data() builds sw20 with SWING["min_bars_1h"]; the OOS branch
        # has to build it the same way or the two scopes measure different books.
        sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
        # htf15: the 1h series at min_bars=15 that fsent_champ_long_htf15 points
        # at. This loader is exp_fastcheck's OOS path, and the sw20 note above
        # says exactly what happens when a swing key is missing here instead:
        # every book using it raises KeyError on OOS while IS passes. htf15 is
        # built on both eras for that reason - it must exist in exp_signal_metrics
        # (IS), here (OOS) and run_experiment.get_data (IS), and the assertion
        # below fails loudly rather than letting that recur silently.
        htf15 = _compute_swings(f1h, "continuous", min_bars=15)
        return {
            "c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10, "sw20": sw20,
            "htf15": htf15,
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


def equity_quality(trades, years):
    """Full NET equity-curve quality. trades chronological (engine order)."""
    if not trades:
        return {"n": 0, "net": 0.0}
    nets = [net_r([t]) for t in trades]
    n = len(nets)
    total = sum(nets)

    # peak / DD / underwater (trade-indexed)
    peak = cum = max_dd = 0.0
    dd_start = max_dd_start = max_dd_end = -1
    uw = max_uw = 0
    uw_pct_sum = 0
    for i, x in enumerate(nets):
        prev = cum
        cum += x
        if cum > peak:
            peak = cum
            dd_start = i
            uw = 0
        else:
            uw += 1
            max_uw = max(max_uw, uw)
            uw_pct_sum += 1
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
            max_dd_start = dd_start
            max_dd_end = i
    max_dd_dur = (max_dd_end - max_dd_start + 1) if max_dd >= 0 else 0
    uw_pct = 100.0 * uw_pct_sum / n

    # ulcer: mean of (dd/peak)^2 over points where peak>0, scaled
    #
    # The 1e-9 guard is not enough. A book that takes its first profits early
    # and then gives them back can leave `peak` at a tiny positive number while
    # `cum` has fallen well below it. The ratio then explodes: on
    # fsent_champ_long_htfesmcl4 the peak after trade 3 is 0.068 and cum reaches
    # -4.825, so (peak-cum)/peak is 7195% and the squared term is 5.2e7. That one
    # point carried the whole book to ulcer 365.75 while every other book sat
    # between 3.8 and 12. The same series recomputed from its own dd column
    # gives 5.89.
    #
    # The peak is floored at a fraction of the book's own total so a
    # near-zero early peak cannot become a denominator. Points whose peak is
    # below that floor are not counted rather than counted with a clamped
    # denominator, so an early losing run simply contributes nothing to the
    # average instead of contributing a fabricated one.
    peak = cum = 0.0
    ulcer_sq = 0.0
    ulcer_n = 0
    peak_floor = abs(total) * 0.01 if total else 0.0
    for x in nets:
        cum += x
        peak = max(peak, cum)
        if peak > peak_floor and peak > 1e-9:
            ulcer_sq += (100.0 * (peak - cum) / peak) ** 2
            ulcer_n += 1
    ulcer = math.sqrt(ulcer_sq / ulcer_n) if ulcer_n else 0.0

    # sortino: downside dev of trade nets vs 0 target
    downside = [min(0.0, x) for x in nets]
    dvar = sum(x * x for x in downside) / n
    dsdev = math.sqrt(dvar)
    sortino = (total / dsdev) if dsdev > 1e-12 else 0.0

    # calmar / recovery (period total / maxDD)
    calmar = (total / years) / max_dd if max_dd > 1e-9 else 0.0
    recovery = total / max_dd if max_dd > 1e-9 else 0.0

    # PF
    wins = sum(x for x in nets if x > 0)
    losses = -sum(x for x in nets if x < 0)
    pf = (wins / losses) if losses > 1e-9 else float("inf")

    # consecutive losses
    streak = max_streak = 0
    for x in nets:
        if x < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    # monthly / yearly from exit_date
    months = defaultdict(float)
    years_m = defaultdict(float)
    for t, x in zip(trades, nets):
        d = str(t.get("exit_date") or t.get("entry_date") or "")
        if len(d) >= 7:
            months[d[:7]] += x
        if len(d) >= 4:
            years_m[d[:4]] += x
    m_vals = list(months.values())
    y_vals = list(years_m.values())
    pos_m = sum(1 for v in m_vals if v > 0)
    pos_y = sum(1 for v in y_vals if v > 0)

    wr = 100.0 * sum(1 for x in nets if x > 0) / n

    return {
        "n": n,
        "net": round(total, 4),
        "wr": round(wr, 2),
        "pf": round(pf, 4) if pf != float("inf") else 999.0,
        "max_dd": round(max_dd, 4),
        "max_dd_dur": max_dd_dur,
        "uw_pct": round(uw_pct, 2),
        "max_uw": max_uw,
        "ulcer": round(ulcer, 4),
        "sortino": round(sortino, 4),
        "calmar": round(calmar, 4),
        "recovery": round(recovery, 4),
        "max_streak": max_streak,
        "months_n": len(m_vals),
        "pos_month_pct": round(100.0 * pos_m / len(m_vals), 1) if m_vals else 0.0,
        "worst_month": round(min(m_vals), 3) if m_vals else 0.0,
        "best_month": round(max(m_vals), 3) if m_vals else 0.0,
        "years_n": len(y_vals),
        "pos_year_pct": round(100.0 * pos_y / len(y_vals), 1) if y_vals else 0.0,
        "worst_year": round(min(y_vals), 3) if y_vals else 0.0,
        "yearly": {k: round(v, 3) for k, v in sorted(years_m.items())},
        "net_per_yr": round(total / years, 3),
    }


def arm_scores(m, base):
    """Delta of quality metrics vs baseline (positive = better for this field)."""
    if base is None or base.get("n", 0) == 0:
        return {}
    better_dd = base["max_dd"] - m["max_dd"]  # >0 = shallower DD
    better_ulcer = base["ulcer"] - m["ulcer"]
    better_uw = base["uw_pct"] - m["uw_pct"]
    better_dur = base["max_dd_dur"] - m["max_dd_dur"]
    return {
        "d_net": round(m["net"] - base["net"], 4),
        "d_net_yr": round(m["net_per_yr"] - base["net_per_yr"], 4),
        "d_max_dd": round(better_dd, 4),
        "d_ulcer": round(better_ulcer, 4),
        "d_uw_pct": round(better_uw, 4),
        "d_dd_dur": better_dur,
        "d_sortino": round(m["sortino"] - base["sortino"], 4),
        "d_calmar": round(m["calmar"] - base["calmar"], 4),
        "d_pos_month_pct": round(m["pos_month_pct"] - base["pos_month_pct"], 2),
        "d_pf": round(m["pf"] - base["pf"], 4),
    }


def curve_better(delta, net_floor=0.0):
    """Equity-lens pass: curve improved AND net not hurt (or net up)."""
    if not delta:
        return False
    # core: shallower DD + better ulcer OR much better calmar, net not negative
    curve_up = (
        delta.get("d_max_dd", 0) > 0.5
        or delta.get("d_ulcer", 0) > 0.5
        or delta.get("d_calmar", 0) > 0.05
    )
    net_ok = delta.get("d_net", 0) >= net_floor
    return curve_up and net_ok


def run_scope(scope, sim, data):
    years = YEARS[scope]
    result = {"scope": scope, "years": years, "configs": {}}
    print(f"\n=== equity quality [{scope.upper()}] years={years} ===", flush=True)
    for key in CONFIGS:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        params.setdefault("exp_partial_r", 0.0)
        rows = {}
        base_m = None
        print(f"\n  {key}", flush=True)
        print(
            f"    {'arm':<16} {'n':>4} {'net':>8} {'DD':>6} {'DDd':>4} "
            f"{'uw%':>5} {'ulcer':>7} {'sort':>7} {'calmar':>7} "
            f"{'m+%':>5} {'streak':>6} {'PF':>6}",
            flush=True,
        )
        for name, flags in ARMS:
            tr = run(sim, data, params, **flags)
            m = equity_quality(tr, years)
            if base_m is None:
                base_m = m
            delta = arm_scores(m, base_m)
            rows[name] = {**m, "delta_vs_base": delta, "flags": flags}
            print(
                f"    {name:<16} {m['n']:>4} {m['net']:>+8.1f} {m['max_dd']:>6.1f} "
                f"{m['max_dd_dur']:>4} {m['uw_pct']:>5.1f} {m['ulcer']:>7.2f} "
                f"{m['sortino']:>7.2f} {m['calmar']:>7.3f} "
                f"{m['pos_month_pct']:>5.1f} {m['max_streak']:>6} {m['pf']:>6.2f}",
                flush=True,
            )
        result["configs"][key] = rows
    return result


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  EQUITY-CURVE QUALITY STUDY — baseline vs wider-trail vs skip_decisive", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    # confirm kwargs exist
    import inspect
    sig = inspect.signature(sim)
    for kw in ("exp_trail_half", "exp_trail_delay_r", "exp_skip_decisive"):
        if kw not in sig.parameters:
            raise SystemExit(f"missing kwarg {kw}")

    data_is = load_scope("is")
    data_oos = load_scope("oos")
    is_res = run_scope("is", sim, data_is)
    oos_res = run_scope("oos", sim, data_oos)

    print("\n=== EQUITY-LENS VERDICT (curve better AND net not hurt, both sides) ===", flush=True)
    verdicts = {}
    for key in CONFIGS:
        verdicts[key] = {}
        for name, _ in ARMS:
            if name == "baseline":
                continue
            d_is = is_res["configs"][key][name]["delta_vs_base"]
            d_oos = oos_res["configs"][key][name]["delta_vs_base"]
            better_is = curve_better(d_is)
            better_oos = curve_better(d_oos)
            verdicts[key][name] = {
                "d_net_is": d_is.get("d_net"),
                "d_net_oos": d_oos.get("d_net"),
                "d_net_yr_is": d_is.get("d_net_yr"),
                "d_net_yr_oos": d_oos.get("d_net_yr"),
                "d_dd_is": d_is.get("d_max_dd"),
                "d_dd_oos": d_oos.get("d_max_dd"),
                "d_ulcer_is": d_is.get("d_ulcer"),
                "d_ulcer_oos": d_oos.get("d_ulcer"),
                "curve_better_is": better_is,
                "curve_better_oos": better_oos,
                "curve_pass_both": better_is and better_oos,
            }
            v = verdicts[key][name]
            tag = (
                "CURVE PASS BOTH" if v["curve_pass_both"] else
                "CURVE OOS ONLY" if better_oos and not better_is else
                "CURVE IS ONLY" if better_is and not better_oos else
                "CURVE FAIL"
            )
            print(
                f"  {key:34} {name:<16} dNet {v['d_net_is']:+7.1f}/{v['d_net_oos']:+7.1f}  "
                f"dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f}  "
                f"dUlc {v['d_ulcer_is']:+6.2f}/{v['d_ulcer_oos']:+6.2f}  "
                f"-> {tag}",
                flush=True,
            )

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "lens": "equity-curve quality; no fixed R/year adoption threshold",
        "arms": [{"name": n, "flags": f} for n, f in ARMS],
        "years": YEARS,
        "verdicts": verdicts,
        "is": is_res,
        "oos": oos_res,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
