"""ARE THE BIG WINS SPREAD EVENLY? And what cushion does that imply?

The patience question, measured. The previous walk showed *that* long underwater
stretches happen; it did not show whether the big wins arrive on a schedule or in
clumps. Those are different questions and they lead to different sizing answers:

  - evenly spaced winners  -> a book you can size to a known drawdown
  - clumped winners       -> a book where the gap is unbounded and the only
                             defence is a small enough lot

Thresholds are NOT chosen here. They are the book's own definitions, already in
use across the repo: 3R+ and 5R+ (LOSS_AUTOPSY / EQUITY_CURVE_STUDY) and 10R+
("monsters", 17 trades in champion IS per LOSS_AUTOPSY).

For each threshold this reports the spacing of qualifying trades, and the one
number that actually answers "how much cushion do I need":

  the largest R decline that occurred BETWEEN two consecutive qualifying wins
  - i.e. what the equity had to absorb, and for how long, before the next one
  arrived. That is the true cushion requirement, not the max drawdown of the
  whole book, because the max drawdown may already be partly filled.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_win_spacing.py
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "backtest/tests/_win_spacing.json"
# The repo's own thresholds. 3R+ and 5R+ from LOSS_AUTOPSY / EQUITY_CURVE_STUDY,
# 10R+ is the "monster" definition used throughout.
THRESHOLDS = (3.0, 5.0, 10.0)


def spacing(rs, dates, thr):
    """Gaps between consecutive trades at or above `thr`, and what the equity
    had to absorb across each gap."""
    idx = [i for i, x in enumerate(rs) if x >= thr]
    if len(idx) < 2:
        return None
    gaps = []
    for a, b in zip(idx, idx[1:]):
        seg = rs[a + 1:b]          # everything strictly between the two wins
        decline = sum(seg)
        worst = 0.0
        c = 0.0
        for x in seg:
            c += x
            worst = min(worst, c)
        d0 = datetime.strptime(dates[a][:10], "%Y-%m-%d")
        d1 = datetime.strptime(dates[b][:10], "%Y-%m-%d")
        gaps.append({
            "from_trade": a + 1, "to_trade": b + 1,
            "gap_trades": b - a - 1,
            "gap_R": round(decline, 1),
            "worst_within_gap": round(worst, 1),
            "gap_days": (d1 - d0).days,
            "from_date": dates[a][:10], "to_date": dates[b][:10],
        })
    gl = [g["gap_trades"] for g in gaps]
    gr = [g["gap_R"] for g in gaps]
    gw = [g["worst_within_gap"] for g in gaps]
    gd = [g["gap_days"] for g in gaps]
    worst_gap = min(gaps, key=lambda g: g["worst_within_gap"])
    return {
        "threshold": thr,
        "n_wins": len(idx),
        "pct_of_book": round(100.0 * len(idx) / len(rs), 1),
        "share_of_net": round(100.0 * sum(rs[i] for i in idx) / sum(rs), 1),
        "mean_gap_trades": round(statistics.mean(gl), 1),
        "median_gap_trades": round(statistics.median(gl), 1),
        "max_gap_trades": max(gl),
        "max_gap_days": max(gd),
        "median_gap_days": round(statistics.median(gd), 1),
        "mean_gap_R": round(statistics.mean(gr), 1),
        "worst_gap_R": min(gr),
        "worst_within_gap": round(min(gw), 1),
        "worst_gap": worst_gap,
        "gaps": gaps,
    }


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "win_spacing", "thresholds": list(THRESHOLDS),
               "note": "thresholds are the repo's own, not chosen for effect",
               "eras": {}}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        tr = out["ltf_trades"]
        rs = [net_r([t]) for t in tr]
        ds = [t.get("entry_date", "") for t in tr]
        print("=" * 100)
        print(f"  CHAMPION BASELINE · {era.upper()} · {len(rs)} trades · "
              f"{sum(rs):+.1f}R")
        print("=" * 100, flush=True)
        print(f"  {'thr':>5} {'wins':>5} {'%book':>7} {'%net':>7} "
              f"{'medGap':>8} {'maxGap':>7} {'maxDays':>8} "
              f"{'worstR':>7} {'cushion':>8}  worst gap", flush=True)
        res = {}
        for thr in THRESHOLDS:
            s = spacing(rs, ds, thr)
            if not s:
                print(f"  {thr:>5.0f}  fewer than 2 qualifying trades", flush=True)
                continue
            res[str(thr)] = s
            wg = s["worst_gap"]
            print(f"  {thr:>5.0f} {s['n_wins']:>5} {s['pct_of_book']:>6.1f}% "
                  f"{s['share_of_net']:>6.1f}% {s['median_gap_trades']:>8.1f} "
                  f"{s['max_gap_trades']:>7} {s['max_gap_days']:>7} "
                  f"{s['worst_gap_R']:>7.1f} {s['worst_within_gap']:>8.1f}  "
                  f"trades {wg['from_trade']}->{wg['to_trade']} "
                  f"({wg['gap_days']}d, {wg['from_date']}->{wg['to_date']})",
                  flush=True)
        payload["eras"][era] = res
        print(flush=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
