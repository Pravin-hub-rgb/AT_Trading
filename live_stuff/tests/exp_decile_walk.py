"""Decile walk: champion baseline, chronological blocks of 10 trades from Jan 2023.

Asked for the R progression in 10-trade buckets, to see how the book actually
accumulates rather than as one headline number. This also answers what a single
net figure hides: whether the equity path is steady, or whether a few blocks
carry the whole curve.

Per block: n, net, cumulative net, win rate, PF, best/worst trade, and the
calendar span it covers - because "trades 300-310" means nothing without knowing
which year those fell in.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_decile_walk.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "live_stuff/tests/_decile_walk.json"
BLOCK = 10


def block_stats(rs, ds):
    n = len(rs)
    if n == 0:
        return None
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    pf = (sum(wins) / -sum(losses)) if losses else None
    return {
        "n": n, "net": round(sum(rs), 1),
        "wr": round(100.0 * len(wins) / n, 1),
        "pf": round(pf, 2) if pf else None,
        "best": round(max(rs), 1), "worst": round(min(rs), 1),
        "from": ds[0][:10], "to": ds[-1][:10],
    }


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "decile_walk", "block": BLOCK,
               "config": "champion_multi_sw10 baseline", "eras": {}}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"], **params)
        tr = out["ltf_trades"]
        rs = [net_r([t]) for t in tr]
        ds = [t.get("entry_date", "") for t in tr]
        print("=" * 100)
        print(f"  CHAMPION BASELINE · bybit {era.upper()} · "
              f"{len(rs)} trades · {ds[0][:10]} -> {ds[-1][:10]}")
        print("=" * 100, flush=True)
        print(f"  {'trades':>9} {'n':>3} {'net':>7} {'cum':>8} {'WR':>6} {'PF':>5} "
              f"{'best':>6} {'worst':>6}  span", flush=True)
        blocks = []
        cum = 0.0
        for i in range(0, len(rs), BLOCK):
            b = block_stats(rs[i:i + BLOCK], ds[i:i + BLOCK])
            cum += b["net"]
            b.update({"index": i // BLOCK,
                      "trades": f"{i+1}-{min(i+BLOCK, len(rs))}",
                      "cum": round(cum, 1)})
            blocks.append(b)
            pf = b["pf"] or 0
            print(f"  {b['trades']:>9} {b['n']:>3} {b['net']:>+7.1f} "
                  f"{b['cum']:>+8.1f} {b['wr']:>5.1f}% {pf:>5.2f} "
                  f"{b['best']:>+6.1f} {b['worst']:>+6.1f}  "
                  f"{b['from']} -> {b['to']}", flush=True)
        payload["eras"][era] = {"n": len(rs), "net": round(sum(rs), 1),
                                "first": ds[0][:10], "last": ds[-1][:10],
                                "blocks": blocks}
        neg = [b for b in blocks if b["net"] < 0]
        pos = [b for b in blocks if b["net"] > 0]
        flat = len(blocks) - len(pos) - len(neg)
        print(f"\n  SUMMARY {era.upper()}: {len(pos)} positive blocks, "
              f"{len(neg)} negative, {flat} flat")
        print(f"    total {sum(rs):+.1f}R over {len(rs)} trades = "
              f"{sum(rs)/len(rs):+.3f}R per trade")
        print(f"    best block  {max(b['net'] for b in blocks):+.1f}R")
        print(f"    worst block {min(b['net'] for b in blocks):+.1f}R")
        bn = sorted((b["net"] for b in blocks), reverse=True)
        k = max(1, len(bn) // 10)
        print(f"    best {k} of {len(bn)} blocks carry "
              f"{100.0*sum(bn[:k])/sum(bn):.1f}% of net")
        print(flush=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
