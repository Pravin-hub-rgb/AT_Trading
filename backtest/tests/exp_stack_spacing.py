"""STACK win-spacing + what actually happens INSIDE the wait.

Two questions, one harness.

1. Redo the win-spacing / cushion study on the best candidate (STACK =
   half+delay1+skip_decisive, +110.5R OOS) rather than on baseline, so the
   cushion number reflects the config we would actually ship.

2. The follow-up the previous run did not answer: during a long wait for the
   next big win, HOW DEEP does the equity go, and are there small wins along the
   way, or is it a flat grind of losses? That matters for patience - "nine
   months of nothing" is a different experience from "nine months of -42R with
   small wins mixed in". For every gap this reports what occurred inside it:
   small wins, deepest excursion, longest losing run.

Same thresholds as the baseline run (3R+, 5R+, 10R+) so the two are comparable.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_stack_spacing.py
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
OUT = ROOT / "backtest/tests/_stack_spacing.json"
THRESHOLDS = (3.0, 5.0, 10.0)
ARMS = {
    "baseline": {},
    "STACK": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0,
              "exp_skip_decisive": 1},
}


def inside_gap(seg, segdates, thr):
    """What happened between two qualifying wins."""
    if not seg:
        return None
    small = [x for x in seg if 0 < x < thr]
    losses = [x for x in seg if x < 0]
    run = best = 0
    for x in seg:
        if x < 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
    c = worst = 0.0
    for x in seg:
        c += x
        worst = min(worst, c)
    return {"n_trades": len(seg), "small_wins": len(small),
            "small_win_R": round(sum(small), 1), "losses": len(losses),
            "net": round(sum(seg), 1), "deepest_inside": round(worst, 1),
            "longest_loss_run": best,
            "from": segdates[0][:10] if segdates else None,
            "to": segdates[-1][:10] if segdates else None}


def spacing(rs, dates, thr):
    idx = [i for i, x in enumerate(rs) if x >= thr]
    if len(idx) < 2:
        return None
    gaps = []
    for a, b in zip(idx, idx[1:]):
        seg, segd = rs[a + 1:b], dates[a + 1:b]
        c = worst = 0.0
        for x in seg:
            c += x
            worst = min(worst, c)
        d0 = datetime.strptime(dates[a][:10], "%Y-%m-%d")
        d1 = datetime.strptime(dates[b][:10], "%Y-%m-%d")
        gaps.append({"from_trade": a + 1, "to_trade": b + 1,
                     "gap_trades": len(seg), "gap_R": round(sum(seg), 1),
                     "deepest": round(worst, 1), "gap_days": (d1 - d0).days,
                     "from_date": dates[a][:10], "to_date": dates[b][:10],
                     "inside": inside_gap(seg, segd, thr)})
    gl = [g["gap_trades"] for g in gaps]
    gw = [g["deepest"] for g in gaps]
    gd = [g["gap_days"] for g in gaps]
    return {"threshold": thr, "n_wins": len(idx),
            "pct_of_book": round(100.0 * len(idx) / len(rs), 1),
            "share_of_net": round(100.0 * sum(rs[i] for i in idx) / sum(rs), 1),
            "median_gap_trades": round(statistics.median(gl), 1),
            "max_gap_trades": max(gl), "max_gap_days": max(gd),
            "cushion": round(min(gw), 1),
            "worst_gap": min(gaps, key=lambda g: g["deepest"]),
            "longest_gap": max(gaps, key=lambda g: g["gap_days"]),
            "gaps": gaps}


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "stack_spacing", "thresholds": list(THRESHOLDS),
               "books": {}}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        print("=" * 112)
        print(f"  bybit {era.upper()}")
        print("=" * 112, flush=True)
        for arm, kw in ARMS.items():
            params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params, **kw)
            tr = out["ltf_trades"]
            rs = [net_r([t]) for t in tr]
            ds = [t.get("entry_date", "") for t in tr]
            print(f"\n  --- {arm} · {len(rs)} trades · {sum(rs):+.1f}R ---",
                  flush=True)
            print(f"  {'thr':>5} {'wins':>5} {'%net':>7} {'medGap':>8} "
                  f"{'maxGap':>7} {'maxDay':>7} {'cushion':>8}  worst gap",
                  flush=True)
            for thr in THRESHOLDS:
                s = spacing(rs, ds, thr)
                if not s:
                    continue
                payload["books"][f"{era}/{arm}/{thr}"] = s
                wg = s["worst_gap"]
                ins = wg["inside"] or {}
                print(f"  {thr:>5.0f} {s['n_wins']:>5} {s['share_of_net']:>6.1f}% "
                      f"{s['median_gap_trades']:>8.1f} {s['max_gap_trades']:>7} "
                      f"{s['max_gap_days']:>7} {s['cushion']:>8.1f}  "
                      f"tr {wg['from_trade']}->{wg['to_trade']} "
                      f"({wg['gap_days']}d)", flush=True)
                if ins:
                    print(f"        inside: {ins['n_trades']} trades, "
                          f"net {ins['net']:+.1f}R, deepest "
                          f"{ins['deepest_inside']:+.1f}R, {ins['small_wins']} "
                          f"small wins (+{ins['small_win_R']}), loss run "
                          f"{ins['longest_loss_run']}", flush=True)
    print(f"\n{'='*112}\nTHE LONG WAITS, SPELLED OUT (STACK, OOS)\n{'='*112}",
          flush=True)
    for thr in (3.0, 5.0, 10.0):
        s = payload["books"].get(f"oos/STACK/{thr}")
        if not s:
            continue
        lg = s["longest_gap"]
        i = lg["inside"] or {}
        print(f"\n  {thr:.0f}R+ longest wait: {lg['gap_days']} days, "
              f"{lg['gap_trades']} trades, net {lg['gap_R']:+.1f}R, "
              f"deepest {lg['deepest']:+.1f}R")
        print(f"    {lg['from_date']} -> {lg['to_date']}")
        if i:
            print(f"    during it: {i['n_trades']} trades = {i['losses']} losses + "
                  f"{i['small_wins']} small wins worth +{i['small_win_R']}R")
            print(f"    deepest reached {i['deepest_inside']:+.1f}R · "
                  f"longest losing run {i['longest_loss_run']}")
        print("    three longest waits:")
        for g in sorted(s["gaps"], key=lambda g: -g["gap_days"])[:3]:
            gi = g["inside"] or {}
            print(f"      {g['gap_days']:>4}d  {g['from_date']} -> {g['to_date']}  "
                  f"net {g['gap_R']:+6.1f}R  deep {g['deepest']:+6.1f}R  "
                  f"{gi.get('small_wins','?')} small wins "
                  f"(+{gi.get('small_win_R','?')}R)  loss run "
                  f"{gi.get('longest_loss_run','?')}")
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

