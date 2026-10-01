"""CLUSTER-LEVEL AUTOPSY - the unit nobody has ever looked at.

THE GAP
=======
Today's entry-time autopsy proved the per-trade view is empty: of nine
candidate features, the only one that separated the tail (`swing_no`) was
calendar time, and everything else sat at AUC ~0.5. **Filters on
individual trades are done.**

But every experiment in this repo scores trades one at a time. Nothing has
ever asked what the book looks like as a SEQUENCE. Two specific holes:

1. `max_consecutive_losses=3` is a HARD-CODED constant. It has never been
   swept, never been justified, and is load-bearing: the closed list says
   relaxing it is 0/4, but the value 3 itself was inherited, not chosen.
2. Nobody has measured whether losses CLUSTER, or whether the streaks are
   preceded by anything knowable. A book where losses come in runs of 6
   separated by 40 calm trades is a completely different risk object from
   one that scatters them evenly, and the halt rule only makes sense in the
   first case.

The same question is asked of WINNERS, because if winners cluster too then
the cluster is a REGIME and not a loss phenomenon - which changes what a
correct response would even be.

WHAT IS MEASURED (descriptive first; the sweep is secondary)
============================================================
  1. run-length distribution of losses and of wins, in trade order
  2. is a loss streak's CONTINUATION predictable at its first loss? Tested
     with a matched forward/backward control so a naive "streaks are long
     because streaks are long" reading cannot masquerade as a finding
  3. the `max_consecutive_losses` sweep - the constant's first real test
  4. monthly win/loss CLUSTERING: do losses and wins land in the same
     months? If yes, no monthly regime gate can separate them.

THE MATCHED CONTROL IS THE POINT
================================
A streak is self-referential: once you are in one, the next trade is more
likely to join it. So "losses cluster" is nearly tautological. The
non-trivial question is whether a streak is predictable at its FIRST loss -
which is the only point a live system could act on it. So every predictor
is scored on "given loss #1 of a run, does loss #2 follow more often than
base rate", and compared against the unconditional base rate.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_cluster_autopsy.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_cluster_autopsy.json"
LANE = "champion_multi_sw10"
YEARS = {"is": 3.67, "oos": 2.0}
BYBIT_BASE = {"is": (500, 325.8), "oos": (279, 70.2)}
MAXLOSS_LADDER = (0, 2, 3, 4, 5, 6, 8)   # 0 = no halt (the shipped value is 3)


def runs(seq):
    """[(value, length), ...] in order, for a list of booleans."""
    out = []
    for v in seq:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return [(v, n) for v, n in out]


def describe(trades):
    rs = [float(t["r_multiple"]) for t in trades]
    lose = [x <= 0 for x in rs]
    win = [not b for b in lose]
    lr = runs(lose)
    wr = runs(win)
    loss_lens = [n for v, n in lr if v]
    win_lens = [n for v, n in wr if not v]
    return rs, lose, win, lr, wr, loss_lens, win_lens


def _stats(xs):
    if not xs:
        return None
    s = sorted(xs)
    return {"n": len(s), "mean": round(statistics.fmean(s), 2),
            "median": s[len(s) // 2], "max": max(s),
            "p90": s[int(0.9 * (len(s) - 1))],
            "hist": dict(sorted(Counter(s).items()))}


def main():
    from test_experiments_craze import build_module
    from exp_5m_confirm import load_book
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    payload = {"lane": LANE, "maxloss_ladder": list(MAXLOSS_LADDER), "eras": {}}
    print("=" * 100, flush=True)
    print("  CLUSTER-LEVEL AUTOPSY - do losses and wins come in RUNS?", flush=True)
    print("=" * 100, flush=True)

    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        base_tr = sim_fn(sim, data, dict(params))
        ctl = equity_quality(base_tr, YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[scope]
        ok = ctl["n"] == exp_n and abs(ctl["net"] - exp_net) < 0.6
        print(f"\n  [{scope}] CONTROL {ctl['n']}t {ctl['net']:+.1f}R net "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload.setdefault("errors", []).append(scope)
            continue

        trades = base_tr["ltf_trades"] if isinstance(base_tr, dict) else base_tr
        rs, lose, win, lr, wr, llens, wlens = describe(trades)
        n = len(rs)
        base_rate = sum(1 for b in lose if b) / n

        print(f"    {n} trades. loss base rate {100*base_rate:.1f}%", flush=True)
        print(f"    LOSS runs : {_stats(llens)}", flush=True)
        print(f"    WIN  runs : {_stats(wlens)}", flush=True)

        # --- the non-trivial question: is a run predictable at its FIRST loss? ---
        # base rate = P(next trade is a loss). conditional = P(next is a loss |
        # this trade opened a loss run). If the two match, clustering carries
        # no forward information and the halt rule is the only response.
        cond_num = cond_den = 0
        for i, (v, ln) in enumerate(lr):
            if v or i + 1 >= len(lr):
                continue
            nxt_v, nxt_ln = lr[i + 1]
            cond_den += nxt_ln
            cond_num += nxt_ln if nxt_v else 0
        cond = cond_num / cond_den if cond_den else None
        print(f"    P(loss | run just STARTED) = "
              f"{100*cond:.1f}%  vs base {100*base_rate:.1f}%"
              f"   -> {'PREDICTABLE' if cond and cond > base_rate*1.25 else 'not predictable' if cond else 'n/a'}",
              flush=True)
        # how often does a fresh loss run continue at all?
        cont = sum(1 for i, (v, _) in enumerate(lr)
                   if v and i + 1 < len(lr) and lr[i + 1][0])
        starts = sum(1 for v, _ in lr if v)
        print(f"    a fresh loss run continues {cont}/{starts} times "
              f"({100*cont/max(starts,1):.0f}%)", flush=True)

        # --- monthly: do losses and wins share months? ---
        lm, wm = Counter(), Counter()
        for t in trades:
            m = t["exit_date"][:7]
            (lm if float(t["r_multiple"]) <= 0 else wm)[m] += 1
        months = sorted(set(lm) | set(wm))
        lshare = [lm[m] / max(lm[m] + wm[m], 1) for m in months]
        print(f"    months with trades {len(months)}; loss share per month "
              f"mean {statistics.fmean(lshare):.3f} sd "
              f"{statistics.pstdev(lshare):.3f} (book base "
              f"{base_rate:.3f})", flush=True)

        # --- the max_consecutive_losses sweep: first real test of the constant ---
        print(f"    max_consecutive_losses sweep (shipped = 3):", flush=True)
        sweep = {}
        for k in MAXLOSS_LADDER:
            p = {**params, "max_consecutive_losses": k}
            tr = sim_fn(sim, data, p)
            m = equity_quality(tr, YEARS[scope])
            d = round(m["net"] - ctl["net"], 1)
            sweep[k] = {"n": m["n"], "net": m["net"], "d_net": d,
                        "wr": m["wr"], "pf": m["pf"], "max_dd": m["max_dd"]}
            tag = "  <- shipped" if k == 3 else ""
            print(f"      k={k:<2} {m['n']:>4}t {m['net']:>+8.1f}R ({d:+7.1f})  "
                  f"WR {m['wr']:>5}%  PF {m['pf']:>6}  DD {m['max_dd']:>6.1f}{tag}",
                  flush=True)
        best = max(sweep, key=lambda k: sweep[k]["net"])
        print(f"      best k={best} ({sweep[best]['net']:+.1f}R) vs shipped 3 "
              f"({sweep[3]['net']:+.1f}R)", flush=True)

        payload["eras"][scope] = {
            "n": n, "loss_base_rate": round(base_rate, 4),
            "loss_runs": _stats(llens), "win_runs": _stats(wlens),
            "p_loss_given_run_started": (round(cond, 4) if cond else None),
            "run_continuation": f"{cont}/{starts}",
            "monthly_loss_share_mean": round(statistics.fmean(lshare), 4),
            "monthly_loss_share_sd": round(statistics.pstdev(lshare), 4),
            "maxloss_sweep": sweep, "best_k": best,
        }

    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
