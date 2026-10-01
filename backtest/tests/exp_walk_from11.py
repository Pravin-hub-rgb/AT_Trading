"""Decile walk from trade 11, cumulative measured from ZERO, with dates.

Follow-up to the start-sensitivity result: dropping the first 10 trades costs
+30.6R and the book still returns +295.2R. This shows that walk explicitly, from
zero, so the realistic waiting time is visible rather than implied.

For every 10-trade block, from trade 11 onward:

  net, cumulative-from-zero, win rate, PF, best trade, calendar span
  and the two columns that answer "how long do I wait":
    - how many blocks since the last cumulative high (the underwater run)
    - whether this block is a new equity high or a recovery

The `underwater` column is the one to read for patience: it counts consecutive
blocks spent below the previous cumulative peak, so a reader can see exactly
how long a flat-to-drawing-down stretch lasts in calendar terms, not just in R.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_walk_from11.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "backtest/tests/_walk_from11.json"
BLOCK = 10
START = 10          # skip the first 10 trades


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "walk_from_11", "block": BLOCK, "skip_first": START,
               "config": "champion_multi_sw10 baseline", "eras": {}}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        tr = out["ltf_trades"][START:]
        ds = [t.get("entry_date", "") for t in tr]
        rs = [net_r([t]) for t in tr]
        print("=" * 118)
        print(f"  CHAMPION BASELINE · {era.upper()} · first {START} trades REMOVED")
        print(f"  {len(rs)} trades remain · {ds[0][:10]} -> {ds[-1][:10]} · "
              f"from zero")
        print("=" * 118, flush=True)
        print(f"  {'trades':>9} {'net':>7} {'cum':>8} {'WR':>6} {'PF':>5} "
              f"{'best':>6} {'underwater':>10}  span", flush=True)
        cum = 0.0
        peak = 0.0
        uw = 0
        blocks = []
        for i in range(0, len(rs), BLOCK):
            seg = rs[i:i + BLOCK]
            segd = ds[i:i + BLOCK]
            net = sum(seg)
            cum += net
            wins = [x for x in seg if x > 0]
            losses = [x for x in seg if x < 0]
            pf = (sum(wins) / -sum(losses)) if losses else None
            if cum > peak:
                peak = cum
                uw = 0
                tag = ""
            else:
                uw += 1
                tag = f"{uw}b below peak"
            row = {"trades": f"{i+START+1}-{min(i+START+BLOCK, len(rs)+START)}",
                   "net": round(net, 1), "cum": round(cum, 1),
                   "wr": round(100.0 * len(wins) / len(seg), 1),
                   "pf": round(pf, 2) if pf else None,
                   "best": round(max(seg), 1),
                   "underwater_blocks": uw,
                   "from": segd[0][:10], "to": segd[-1][:10]}
            blocks.append(row)
            print(f"  {row['trades']:>9} {net:>+7.1f} {cum:>+8.1f} "
                  f"{row['wr']:>5.1f}% {(pf or 0):>5.2f} {row['best']:>+6.1f} "
                  f"{tag:>10}  {segd[0][:10]} -> {segd[-1][:10]}", flush=True)
        payload["eras"][era] = {"n": len(rs), "net": round(sum(rs), 1),
                                "first": ds[0][:10], "last": ds[-1][:10],
                                "blocks": blocks}
        deepest = min(blocks, key=lambda b: b["cum"])
        maxuw = max(b["underwater_blocks"] for b in blocks)
        worst_streak = [b for b in blocks if b["underwater_blocks"] == maxuw]
        print(f"\n  {era.upper()} from zero: {sum(rs):+.1f}R over {len(rs)} trades "
              f"= {sum(rs)/len(rs):+.3f}R/trade")
        print(f"    deepest point   {deepest['cum']:+.1f}R at block "
              f"{deepest['trades']} ({deepest['from']} -> {deepest['to']})")
        print(f"    longest wait below a prior peak: {maxuw} blocks"
              + (f"  ({worst_streak[0]['from']} -> {worst_streak[-1]['to']})"
                 if worst_streak else ""), flush=True)
        pos = sum(1 for b in blocks if b["net"] > 0)
        print(f"    {pos} positive blocks, {len(blocks)-pos} negative", flush=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
