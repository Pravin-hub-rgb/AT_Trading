"""Tail-concentration audit: are these books actually robust, or lottery tickets?

Asked directly, with a set of "healthy range" figures to check against. The
numbers in `_full_metrics.json` already carry `top5_share_pct`, but that alone
cannot answer the question, because a top-5% share above 100% does not mean
"high concentration" — it means the other 95% of trades are net negative.

So this computes the full ladder, per book:

  * top-k contribution for k = 1, 3, 5, 10, 20 trades (share of net)
  * top-p% contribution for p = 5, 10, 20% of trades (share of net)
  * net remaining after removing the best k trades
  * avg win / avg loss, and the breakeven win rate
  * the same numbers on data/btc as an independent check

Reported against the ranges in the question, and the verdict is computed, not
asserted. If a book fails the "still positive after removing the top 3-5
winners" test, that is stated plainly rather than softened.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_tail_audit.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_tail_audit.json"

# The ranges to test against, as stated in the question.
HEALTHY = {
    "top5pct_net": (40.0, 70.0),
    "top10pct_net": (55.0, 80.0),
    "wr": (25.0, 40.0),
    "pf_oos": (1.40, 2.20),
    "big_winner_pct": (3.0, 8.0),
}
# Beyond these, the answer is no regardless of the other rows.
DANGER = {"top5pct_net": 80.0, "top10pct_net": 90.0, "pf_oos_low": 1.30,
          "pf_oos_high": 3.0, "wr_low": 20.0}

ARMS = {
    "baseline": {},
    "half+delay1": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0},
    "skip_decisive": {"exp_skip_decisive": 1},
    "STACK": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0,
              "exp_skip_decisive": 1},
    "delay_r_1.5": {"exp_trail_delay_r": 1.5},
}
LANES = (("champion", "champion_multi_sw10", "multi"),
         ("utcsat", "utcsat_multi_sw10", "multi"),
         ("age10", "age10_dirmatch_swingpause_single_sw10", "single"))


def audit(rs):
    n = len(rs)
    s = sorted(rs, reverse=True)
    net = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    awl = (sum(wins) / len(wins)) if wins else 0.0
    all_ = (-sum(losses) / len(losses)) if losses else 0.0
    out = {
        "n": n, "net": round(net, 1),
        "wr": round(100.0 * len(wins) / n, 1),
        "avg_win": round(awl, 3), "avg_loss": round(-all_, 3),
        "win_loss_ratio": round(awl / all_, 2) if all_ > 1e-9 else None,
        "breakeven_wr_pct": round(100.0 * all_ / (awl + all_), 1) if (awl + all_) > 1e-9 else None,
        "pf": round(sum(wins) / -sum(losses), 3) if losses else None,
        "top_k": {}, "top_p": {}, "net_minus_topk": {},
    }
    for k in (1, 3, 5, 10, 20):
        if k <= n:
            share = sum(s[:k])
            out["top_k"][str(k)] = round(100.0 * share / net, 1) if net > 0 else None
            out["net_minus_topk"][str(k)] = round(net - share, 1)
    for p in (5, 10, 20):
        k = max(1, int(n * p / 100))
        share = sum(s[:k])
        out["top_p"][f"{p}pct"] = {
            "k": k,
            "share_of_net_pct": round(100.0 * share / net, 1) if net > 0 else None,
            "net_without": round(net - share, 1)}
    return out


def verdict(a, era):
    """Computed verdict, not asserted. The decisive test is the one the question
    calls 'important': does the book stay positive after the best 3-5 winners
    are removed?"""
    v = []
    lo, hi = HEALTHY["top5pct_net"]
    t5 = a["top_p"]["5pct"]["share_of_net_pct"]
    t10 = a["top_p"]["10pct"]["share_of_net_pct"]
    wr, pf = a["wr"], a["pf"]
    if t5 is None:
        return "no net"
    if t5 > DANGER["top5pct_net"]:
        v.append(f"top5% carries {t5}% of net (danger >{DANGER['top5pct_net']}%)")
    elif not (lo <= t5 <= hi):
        v.append(f"top5%={t5}% outside healthy {lo}-{hi}")
    if t10 is not None and t10 > DANGER["top10pct_net"]:
        v.append(f"top10% carries {t10}% (danger >{DANGER['top10pct_net']}%)")
    if not (HEALTHY["wr"][0] <= wr <= HEALTHY["wr"][1]):
        v.append(f"WR {wr}% outside healthy {HEALTHY['wr']}")
    if pf is not None and era == "oos":
        if pf < DANGER["pf_oos_low"] or pf > DANGER["pf_oos_high"]:
            v.append(f"PF {pf} outside {DANGER['pf_oos_low']}-{DANGER['pf_oos_high']}")
        elif not (HEALTHY["pf_oos"][0] <= pf <= HEALTHY["pf_oos"][1]):
            v.append(f"PF {pf} outside healthy {HEALTHY['pf_oos']}")
    # the decisive robustness test
    n3 = a["net_minus_topk"].get("3")
    n5 = a["net_minus_topk"].get("5")
    if n3 is not None and n3 <= 0:
        v.append(f"ROBUSTNESS FAIL: negative ({n3}R) without the best 3")
    if n5 is not None and n5 <= 0:
        v.append(f"ROBUSTNESS FAIL: negative ({n5}R) without the best 5")
    return "OK - " + "; ".join(v) if not v else " | ".join(v)


def main():
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from run_experiment import net_r
    from experiment_registry import BP, EXPERIMENTS
    sim = build_family_module()
    payload = {"stage": "tail_audit", "healthy_ranges": HEALTHY,
               "danger": DANGER, "books": {}}
    for era in ("is", "oos"):
        print(f"\n{'='*104}\n=== bybit {era.upper()}\n{'='*104}", flush=True)
        data, _ = load_book(era)
        for lane, key, kind in LANES:
            print(f"\n--- {lane} ({kind}) ---", flush=True)
            print(f"  {'arm':<15} {'n':>4} {'net':>8} {'WR':>6} {'PF':>5} "
                  f"{'W/L':>5} {'BEwr':>6} {'top1':>7} {'top3':>7} {'top5':>7} "
                  f"{'top10':>7} {'5%':>7} {'10%':>7} {'-top3':>8} {'-top5':>8}")
            for arm, kw in ARMS.items():
                params = {**BP, **EXPERIMENTS[key]["params"]}
                out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                          fine_ltf=data["fine"], **params, **kw)
                rs = [net_r([t]) for t in out["ltf_trades"]]
                a = audit(rs)
                payload["books"][f"{era}/{lane}/{arm}"] = a
                tk, tp, nm = a["top_k"], a["top_p"], a["net_minus_topk"]

                def f(d, k, w=7):
                    x = d.get(k)
                    return f"{x:>{w}.1f}" if x is not None else f"{'--':>{w}}"
                print(f"  {arm:<15} {a['n']:>4} {a['net']:>+8.1f} {a['wr']:>5.1f}% "
                      f"{(a['pf'] or 0):>5.2f} {(a['win_loss_ratio'] or 0):>5.2f} "
                      f"{(a['breakeven_wr_pct'] or 0):>5.1f}% "
                      f"{f(tk,'1')}{f(tk,'3')}{f(tk,'5')}{f(tk,'10')} "
                      f"{f(tp['5pct'],'share_of_net_pct')}"
                      f"{f(tp['10pct'],'share_of_net_pct')} "
                      f"{f(nm,'3',8)}{f(nm,'5',8)}", flush=True)
    print(f"\n{'='*104}\nVERDICTS\n{'='*104}")
    for k, a in payload["books"].items():
        era = k.split("/")[0]
        print(f"  {k:<28} {verdict(a, era)}")
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

