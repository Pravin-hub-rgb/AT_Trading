"""IS THE SHIPPED CONFIG ACTUALLY RIGHT? — forensics on the config we ship.

Asked directly after logs 109-112, and it deserves a direct answer rather than
another round of proposals. This measures the shipped champion book and asks
the only question that matters: is its positive expectancy robust, or is it a
handful of trades?

Nothing here proposes a change. It is an audit of the thing currently in
production, using the statistics the whole programme has been arguing about.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_is_it_right.py
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))
OUT = ROOT / "backtest/tests/_is_it_right.json"
BASE = {"is": (500, 325.8), "oos": (279, 70.2)}


def boot(rs, fn, n_boot=20000, seed=20260927):
    if len(rs) < 30:
        return (None, None, None)
    rng = random.Random(seed)
    d = sorted(fn([rs[rng.randrange(len(rs))] for _ in range(len(rs))])
               for _ in range(n_boot))
    pl = sum(1 for x in d if x <= 0) / n_boot
    pg = sum(1 for x in d if x >= 0) / n_boot
    return (round(fn(rs), 4), [round(d[int(0.025 * n_boot)], 4),
                               round(d[int(0.975 * n_boot)], 4)],
            round(min(1.0, 2 * min(pl, pg)), 4))


def mean(x):
    return sum(x) / len(x)


def med(x):
    return statistics.median(x)


def trimmed(x):
    s = sorted(x)
    k = int(len(s) * 0.05)
    t = s[k:len(s) - k] if len(s) - 2 * k > 0 else s
    return sum(t) / len(t)


def audit(rs):
    s = sorted(rs, reverse=True)
    net = sum(rs)
    out = {"n": len(rs), "net": round(net, 1), "avgR": round(mean(rs), 4),
           "median": round(med(rs), 4), "trimmed": round(trimmed(rs), 4),
           "stdev": round(statistics.pstdev(rs), 4),
           "boot_mean": boot(rs, mean), "boot_median": boot(rs, med),
           "boot_trimmed": boot(rs, trimmed),
           "drop_top": {}, "worst_streak": 0, "breakeven_at": None}
    for k in (1, 2, 3, 5, 10, 20):
        if k < len(rs):
            out["drop_top"][str(k)] = round(net - sum(s[:k]), 1)
    cum = 0.0
    run = 0
    for x in rs:
        if x < 0:
            run += 1
            out["worst_streak"] = max(out["worst_streak"], run)
        else:
            run = 0
        cum += x
        if out["breakeven_at"] is None and cum > 0:
            out["breakeven_at"] = len(rs) - out["n"] + rs.index(x) + 1
    return out


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    res = {}
    for era in ("is", "oos"):
        data, _ = load_book(era)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=data["fine"],
                  **{**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]})
        rs = [net_r([t]) for t in out["ltf_trades"]]
        en, ev = BASE[era]
        assert len(rs) == en and abs(sum(rs) - ev) < 0.5, f"CONTROL FAIL {era}"
        a = audit(rs)
        res[era] = a
        bm, bmed, bt = a["boot_mean"], a["boot_median"], a["boot_trimmed"]
        print(f"\n=== SHIPPED CHAMPION · bybit {era.upper()} ===")
        print(f"  n={a['n']}  net={a['net']:+.1f}R  avgR={a['avgR']:+.3f}  "
              f"median={a['median']:+.3f}  trimmed={a['trimmed']:+.3f}  "
              f"stdev={a['stdev']:.3f}")
        print(f"  worst losing streak : {a['worst_streak']} trades")
        print(f"  MEAN    {bm[0]:+.3f}  CI {bm[1]}  p={bm[2]}")
        print(f"  MEDIAN  {bmed[0]:+.3f}  CI {bmed[1]}  p={bmed[2]}")
        print(f"  TRIMMED {bt[0]:+.3f}  CI {bt[1]}  p={bt[2]}")
        print("  net if the best N trades had never been taken:")
        print("    " + "  ".join(f"top{k}={v:+.1f}" for k, v in
                                  a["drop_top"].items()))
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

