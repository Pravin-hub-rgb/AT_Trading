"""Is the tail concentration a property of the STRATEGY or of the ERA?

The bybit audit shows every OOS book going negative once the best 5 winners are
removed. Before that is called fragility, it has to survive an independent
dataset where nothing was tuned. `data/btc` is that test.

A trend book being tail-dependent is normal and expected — every one of them is.
A book being FRAGILE is a different thing, and the two look identical on a
single sample. The only way to tell them apart without live data is to ask
whether the same shape appears on a second, independent market history.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_tail_replication.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "live_stuff/tests/_tail_replication.json"

from exp_tail_audit import ARMS, LANES, audit, verdict   # reuse, no duplicate logic


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    data, _ = load_book("btc")
    payload = {"stage": "tail_replication", "dataset": "data/btc (independent)",
               "books": {}}
    print("=" * 104)
    print("  TAIL CONCENTRATION ON AN INDEPENDENT DATASET (data/btc)")
    print("=" * 104, flush=True)
    for lane, key, kind in LANES:
        print(f"\n--- {lane} ({kind}) ---", flush=True)
        print(f"  {'arm':<15} {'n':>4} {'net':>8} {'WR':>6} {'PF':>5} "
              f"{'5%':>7} {'10%':>7} {'-top3':>8} {'-top5':>8}")
        for arm, kw in ARMS.items():
            params = {**BP, **EXPERIMENTS[key]["params"]}
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params, **kw)
            rs = [net_r([t]) for t in out["ltf_trades"]]
            a = audit(rs)
            payload["books"][f"btc/{lane}/{arm}"] = a
            nm, tp = a["net_minus_topk"], a["top_p"]
            g = lambda k: ("%+8.1f" % nm[k]) if k in nm else "       --"
            s5 = tp["5pct"]["share_of_net_pct"]
            s10 = tp["10pct"]["share_of_net_pct"]
            print(f"  {arm:<15} {a['n']:>4} {a['net']:>+8.1f} {a['wr']:>5.1f}% "
                  f"{(a['pf'] or 0):>5.2f} {s5:>6.1f}% {s10:>6.1f}% "
                  f"{g('3')}{g('5')}", flush=True)
    print(f"\n{'='*104}\nVERDICTS (btc)\n{'='*104}")
    for k, a in payload["books"].items():
        print(f"  {k:<28} {verdict(a, 'oos')}")
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
