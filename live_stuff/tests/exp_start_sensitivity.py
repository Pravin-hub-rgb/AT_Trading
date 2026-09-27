"""Start-date sensitivity: what would you have seen if you started later?

The observation that the first 10 trades of the champion IS book gave +30.6R of
cushion is exactly right, and it is the kind of thing that quietly flatters a
backtest. The honest question is not "what did the book do" but "what would the
book have looked like to someone who started on any other day".

This computes, for every 10-trade offset:

  * final cumulative R measured from that start (not from trade 1)
  * the worst point along the way (max drawdown experienced from that start)
  * the worst streak of consecutive losing blocks
  * how many trades it took to get back to breakeven
  * whether the start date matters more than the config

It also does the same for the OOS book, where the walk shows a 120-trade stretch
underwater - which should show up here as a large fraction of bad starts.

No new experiment, no new predicate. This is a property of the existing ledger.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_start_sensitivity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "live_stuff/tests/_start_sensitivity.json"
STEP = 10


def from_start(rs, ds, i):
    """Everything a trader starting at trade i (0-indexed) would experience."""
    sub = rs[i:]
    cum = 0.0
    worst = 0.0
    worst_at = None
    peak = 0.0
    peak_i = 0
    dd = 0.0
    dd_worst = 0.0
    be_at = None
    for j, x in enumerate(sub):
        cum += x
        if be_at is None and cum > 0:
            be_at = j + 1
        if cum > peak:
            peak = cum
            peak_i = j
        d = peak - cum
        if d > dd:
            dd = d
            dd_worst = j - peak_i
        if cum < worst:
            worst = cum
            worst_at = j
    # worst run of consecutive losing blocks of 10
    blocks = [sum(sub[k:k + STEP]) for k in range(0, len(sub), STEP)]
    run = best_run = 0
    for b in blocks:
        if b < 0:
            run += 1
            best_run = max(best_run, run)
        else:
            run = 0
    return {
        "start_trade": i + 1,
        "start_date": ds[i][:10],
        "n": len(sub),
        "final": round(cum, 1),
        "worst_point": round(worst, 1),
        "worst_date": ds[worst_at][:10] if worst_at is not None else None,
        "max_dd": round(dd, 1),
        "max_dd_dur": dd_worst,
        "breakeven_after": be_at,
        "worst_losing_block_run": best_run,
    }


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "start_sensitivity", "step": STEP, "eras": {}}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        tr = out["ltf_trades"]
        rs = [net_r([t]) for t in tr]
        ds = [t.get("entry_date", "") for t in tr]
        print("=" * 106)
        print(f"  CHAMPION BASELINE · {era.upper()} · {len(rs)} trades · "
              f"full book {sum(rs):+.1f}R")
        print("=" * 106, flush=True)
        print(f"  {'start':>6} {'date':>11} {'n':>4} {'final':>8} {'worst':>8} "
              f"{'worst date':>11} {'maxDD':>7} {'DDdur':>6} {'BE@':>5} "
              f"{'loseRun':>8}", flush=True)
        rows = []
        for i in range(0, len(rs), STEP):
            r = from_start(rs, ds, i)
            r["era"] = era
            rows.append(r)
            print(f"  {r['start_trade']:>6} {r['start_date']:>11} {r['n']:>4} "
                  f"{r['final']:>+8.1f} {r['worst_point']:>+8.1f} "
                  f"{(r['worst_date'] or '-'):>11} {r['max_dd']:>7.1f} "
                  f"{r['max_dd_dur']:>6} {str(r['breakeven_after'] or '-'):>5} "
                  f"{r['worst_losing_block_run']:>8}", flush=True)
        payload["eras"][era] = rows
        neg = [r for r in rows if r["final"] < 0]
        print(f"\n  {era.upper()}: {len(rows)} possible start points · "
              f"**{len(neg)} end NEGATIVE** ({100.0*len(neg)/len(rows):.0f}%)")
        if rows:
            print(f"    best start  +{max(r['final'] for r in rows):.1f}R "
                  f"(from trade {max(rows, key=lambda r: r['final'])['start_trade']}, "
                  f"{max(rows, key=lambda r: r['final'])['start_date']})")
            print(f"    worst start {min(r['final'] for r in rows):+.1f}R "
                  f"(from trade {min(rows, key=lambda r: r['final'])['start_trade']}, "
                  f"{min(rows, key=lambda r: r['final'])['start_date']})")
            print(f"    median start {sorted(r['final'] for r in rows)[len(rows)//2]:+.1f}R")
            print(f"    worst maxDD experienced from any start: "
                  f"{max(r['max_dd'] for r in rows):.1f}R")
            print(f"    longest losing block run from any start: "
                  f"{max(r['worst_losing_block_run'] for r in rows)} blocks")
        print(flush=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
