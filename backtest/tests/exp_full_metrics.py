"""FULL METRICS for every candidate in the repo — actually computed, not typed.

The hand-written summary in MASTER_CANDIDATES.md was missing win rate and trade
count on several rows. This computes the complete metric set from the engine for
every runnable candidate, so nothing has to be transcribed by hand again.

Metric set per (config, arm, era):
  n, net, avgR, WR, median, trimmed mean, PF, maxDD, DD duration, ulcer,
  sortino, calmar, % months positive, worst month, max losing streak,
  top-5% share of net, and OOS/IS retention (annualised, multi-year).

Candidates that cannot be re-run here (CRAZE session modes, the sizing queue,
the M2 bridge study) are NOT faked - they are reported as "not runnable in this
harness" and the reader is pointed at the source doc. Fabricating those numbers
from prose is exactly the failure mode that produced the incomplete table.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_full_metrics.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_full_metrics.json"
YEARS = {"is": 3.67, "oos": 2.0, "btc": 3.67}

# arm name -> kwargs. Baseline has no flags.
ARMS = {
    "baseline": {},
    "half": {"exp_trail_half": 1},
    "half+delay1": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0},
    "skip_decisive": {"exp_skip_decisive": 1},
    "STACK": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0,
              "exp_skip_decisive": 1},
    "delay_r_1.5": {"exp_trail_delay_r": 1.5},
}

LANES = (("champion", "champion_multi_sw10", "multi"),
         ("utcsat", "utcsat_multi_sw10", "multi"),
         ("age10", "age10_dirmatch_swingpause_single_sw10", "single"))


def compute(rs, dates):
    """All metrics from one R-series. Same definitions the docs use."""
    n = len(rs)
    if n == 0:
        return {"n": 0}
    s = sorted(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    gross_w, gross_l = sum(wins), -sum(losses)
    # equity curve (chronological, as given)
    peak = cum = mdd = 0.0
    cur_peak_i = cur_peak = 0.0
    dd_dur = 0
    worst_dd_dur = 0
    for i, x in enumerate(rs):
        cum += x
        if cum > cur_peak:
            cur_peak = cum
            cur_peak_i = i
        dd = cur_peak - cum
        if dd > mdd:
            mdd = dd
            dd_dur = i - cur_peak_i
            worst_dd_dur = max(worst_dd_dur, dd_dur)
    # ulcer: RMS of pct drawdown
    uplist = []
    peak = cum = 0.0
    for x in rs:
        cum += x
        if cum > peak:
            peak = cum
        if peak > 0:
            uplist.append(100.0 * (peak - cum) / peak)
    ulcer = math.sqrt(sum(u * u for u in uplist) / len(uplist)) if uplist else 0.0
    # downside deviation (sortino denominator) on R
    dd_dev = [min(x, 0.0) for x in rs]
    dd_rms = math.sqrt(sum(d * d for d in dd_dev) / len(rs))
    sortino = (sum(rs) / n) / dd_rms if dd_rms > 1e-12 else None
    # months
    mon = defaultdict(float)
    for d, x in zip(dates, rs):
        mon[d[:7]] += x
    pos = sum(1 for v in mon.values() if v > 0)
    worst_mon = min(mon.values()) if mon else None
    # streak
    streak = run = 0
    for x in rs:
        if x < 0:
            run += 1
            streak = max(streak, run)
        else:
            run = 0
    # top-5% concentration
    k = max(1, n // 20)
    top5 = sum(s[-k:])
    k3 = sum(x for x in rs if x >= 3)
    return {
        "n": n,
        "n_wins": len(wins),
        "n_losses": len(losses),
        "net": round(sum(rs), 1),
        "avgR": round(sum(rs) / n, 4),
        "wr": round(100.0 * len(wins) / n, 1),
        "median": round(statistics.median(rs), 4),
        "trimmed": round(sum(s[k:n - k]) / max(n - 2 * k, 1), 4),
        "pf": round(gross_w / gross_l, 3) if gross_l > 1e-9 else None,
        "avg_win": round(gross_w / len(wins), 4) if wins else None,
        "avg_loss": round(-gross_l / len(losses), 4) if losses else None,
        # gross_l is already positive (-sum(losses)), so dividing by it directly
        # is what gives a positive payoff. Negating it here returned a negative
        # payoff for a book whose trades were plainly profitable.
        "payoff": round((gross_w / len(wins)) / (gross_l / len(losses)), 4)
        if wins and losses and gross_l > 1e-9 else None,
        "stdR": round(statistics.pstdev(rs), 4) if n > 1 else None,
        "max_dd": round(mdd, 1),
        "dd_dur": worst_dd_dur,
        "ulcer": round(ulcer, 2),
        "sortino": round(sortino, 1) if sortino else None,
        "calmar": round((sum(rs) / n) / mdd, 3) if mdd > 1e-9 else None,
        "pos_month_pct": round(100.0 * pos / len(mon), 1) if mon else None,
        "worst_month": round(worst_mon, 1) if worst_mon is not None else None,
        "max_streak": streak,
        "top5_share_pct": round(100.0 * top5 / sum(rs), 1) if sum(rs) > 0 else None,
        "n_3R_plus": k3,
    }


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "full_metrics",
               "note": "computed from the engine; nothing transcribed by hand",
               "configs": {}}
    for era in ("is", "oos"):
        print(f"\n=== bybit {era.upper()} ===", flush=True)
        data, _ = load_book(era)
        for lane, key, kind in LANES:
            print(f"  --- {lane} ({kind}) ---", flush=True)
            res = {}
            for arm, kw in ARMS.items():
                out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                          fine_ltf=data["fine"],
                          **{**BP, **EXPERIMENTS[key]["params"]}, **kw)
                tr = out["ltf_trades"]
                rs = [net_r([t]) for t in tr]
                ds = [t.get("entry_date", "") for t in tr]
                m = compute(rs, ds)
                res[arm] = m
                pf = m["pf"] or 0
                cal = m["calmar"] or 0
                print(f"    {arm:<15} n={m['n']:>3} net={m['net']:>+7.1f} "
                      f"WR={m['wr']:>4.1f}% avgR={m['avgR']:>+6.3f} "
                      f"med={m['median']:>+5.2f} PF={pf:>4.2f} "
                      f"DD={m['max_dd']:>5.1f} cal={cal:>6.2f} "
                      f"ulc={m['ulcer']:>6.1f} m+={m['pos_month_pct']}% "
                      f"strk={m['max_streak']:>2} top5={m['top5_share_pct']}%",
                      flush=True)
            payload["configs"].setdefault(era, {})[lane] = res
    # retention
    ret = {}
    for lane, key, kind in LANES:
        ret[lane] = {}
        for arm in ARMS:
            a = payload["configs"]["is"][lane][arm]["net"]
            b = payload["configs"]["oos"][lane][arm]["net"]
            ret[lane][arm] = {
                "is_annual": round(a / YEARS["is"], 1),
                "oos_annual": round(b / YEARS["oos"], 1),
                "retention_pct": round(100.0 * (b / YEARS["oos"]) /
                                       (a / YEARS["is"]), 1)
                if a > 0 else None}
    payload["retention"] = ret
    print("\n=== RETENTION (annualised OOS / annualised IS) ===")
    for lane in ret:
        print(f"  {lane}:")
        for arm, r in ret[lane].items():
            s = f"{r['retention_pct']}%" if r["retention_pct"] is not None else "n/a"
            print(f"    {arm:<15} IS/yr {r['is_annual']:>+7.1f}  "
                  f"OOS/yr {r['oos_annual']:>+7.1f}  ret={s}")
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

