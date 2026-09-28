"""TRADE-COUNT EXPANSION: relax the champion's two hard trade limiters.

WHY THIS RUN EXISTS
===================
The range study (RANGE_PEAK_GRAY.md) found that the "peak position in a
narrow range" cohort is NOT a bad cohort to be removed - it is the book's
HIGHEST hit-rate cohort (WR 41-42% vs the book's 27.8-29.1%) and it carries
+107R / +127R in IS. So the productive question is not "which trades do we
drop" but the one the user actually asked:

    "cohort he trade kare, kuch toh kare... number of trades aur badhe"

i.e. KEEP every trade and ADD MORE. Every gate studied so far subtracts
trades. This run is the first one aimed at the opposite direction.

THE TWO LEVERS (the champion's own settings, not new machinery)
==============================================================
  cooldown_bars           = 8    - bars a losing trade blocks the next entry
  max_consecutive_losses  = 3    - the engine halts after N straight losses

Both are hard trade-count limiters. Relaxing either admits entries the
champion currently never sees. And critically, the mechanism finding gives a
real reason to expect this to be more than dilution: if the loss-streak halt
is firing while a 41%-win-rate cohort is being skipped, the halt is throwing
away the book's best entries.

WHY THIS IS A CLEAN TEST
========================
These are ordinary engine kwargs, so this is path-true BY CONSTRUCTION - no
source injection, no gray, no slot/cooldown bookkeeping to get wrong. The
trade sequence is whatever the real engine produces. That removes the entire
class of bug that produced the fake +10.3R in the previous study's streakOFF
arm.

PRE-REGISTERED BEFORE THE RUN (2026-09-28)
==========================================
ARMS (all reported, no best-of, nothing retuned after seeing results):
  A0  baseline                       cd=8,  mcl=3   (must reproduce ledger)
  A1  cooldown_bars        8 -> 4
  A2  cooldown_bars        8 -> 0    (full relaxation)
  A3  max_consecutive_loss 3 -> 5
  A4  max_consecutive_loss 3 -> 0    (no halt at all)
  A5  both relaxed         cd=0,     mcl=0

LANES: champion + utcsat, IS + OOS = 4 cells per arm.

THE TEST OF RECORD for a "more trades" arm is NOT just net R. A relaxed book
trivially shows more trades, and trivially shows lower avg-per-trade. So an
arm is judged on the FULL set, pre-registered:
  1. trades INCREASE (the whole point)
  2. net R INCREASE in absolute terms (not just per-trade)
  3. net per trade does NOT collapse (dilution check)
  4. maxDD does not worsen
  5. ex-best-3 and ex-best-5 remain positive (Rule 13 tail check - a book
     that only works with its biggest winner is not an improvement)
  6. the same sign in both eras, on both lanes (no era-hardcoding)
An arm that wins on (1) and (2) but breaks (5) is reported as NOT a result.

CONTROL: A0 must reproduce the reference ledgers exactly or the run aborts.

STATUS: experimental. No production change, no defaults touched.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_trade_expansion.json"
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
BYBIT_BASE = {
    "is/champion": (500, 325.8), "is/utcsat": (454, 358.9),
    "oos/champion": (279, 70.2), "oos/utcsat": (253, 60.2),
}
ARMS = (
    ("A0 baseline", {}),
    ("A1 cd=4", {"cooldown_bars": 4}),
    ("A2 cd=0", {"cooldown_bars": 0}),
    ("A3 mcl=5", {"max_consecutive_losses": 5}),
    ("A4 mcl=0", {"max_consecutive_losses": 0}),
    ("A5 cd=0,mcl=0", {"cooldown_bars": 0, "max_consecutive_losses": 0}),
)

def metrics(trades, years):
    """Full metric set on NET R (costs + funding), the repo's convention."""
    from run_experiment import net_r
    rs = [net_r([t]) for t in trades]
    n = len(rs)
    if not n:
        return {"n": 0}
    wins = [x for x in rs if x > 0]
    gp = sum(wins)
    gl = -sum(x for x in rs if x < 0)
    eq = peak = dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    net = sum(rs)
    top3 = sum(sorted(rs, reverse=True)[:3])
    top5 = sum(sorted(rs, reverse=True)[:5])
    k = max(1, n // 10)
    return {
        "n": n, "net": round(net, 1),
        "net_per_trade": round(net / n, 3),
        "wr_pct": round(100.0 * len(wins) / n, 1),
        "pf": round(gp / gl, 2) if gl > 0 else None,
        "median": round(statistics.median(rs), 3),
        "trimmed": round(statistics.mean(sorted(rs)[k:n - k] or rs), 3),
        "max_dd": round(dd, 1),
        "net_per_year": round(net / years, 1) if years else None,
        "ex_best3_net": round(net - top3, 1),
        "ex_best5_net": round(net - top5, 1),
        "top5_share_pct": round(100.0 * top5 / net, 1) if net else None,
    }


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  TRADE-COUNT EXPANSION - relax the champion's hard trade limiters",
          flush=True)
    print("=" * 104, flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_tf_family import build_family_module
    from exp_5m_confirm import load_book
    from experiment_registry import BP, EXPERIMENTS

    sim = build_family_module()
    payload = {"stage": "trade_expansion", "arms": {}, "errors": []}
    books = {}
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        for name, key in LANES:
            books[(scope, name)] = (data, {**BP,
                                          **EXPERIMENTS[key]["params"]})

    # CONTROL: A0 must reproduce the reference ledgers exactly.
    for (scope, name), (data, params) in books.items():
        m = metrics(sim_fn(sim, data, params), YEARS[scope])
        exp_n, exp_net = BYBIT_BASE[f"{scope}/{name}"]
        ok = m["n"] == exp_n and abs(m["net"] - exp_net) < 0.6
        print(f"  CTRL {scope}/{name}: {m['n']}t {m['net']:+.1f}R "
              f"(expect {exp_n}t {exp_net:+.1f}) "
              f"{'OK' if ok else 'MISMATCH'}", flush=True)
        if not ok:
            payload["errors"].append(f"ctrl {scope}/{name}")
    if payload["errors"]:
        print("\nABORT: controls did not reproduce.", flush=True)
        OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return

    base = {}
    for arm, override in ARMS:
        print(f"\n  {arm}", flush=True)
        cells = {}
        for (scope, name), (data, params) in books.items():
            p = {**params, **override}
            trades = sim_fn(sim, data, p)
            m = metrics(trades, YEARS[scope])
            if arm.startswith("A0"):
                base[f"{scope}/{name}"] = m
            b = base[f"{scope}/{name}"]
            k = f"{scope}/{name}"
            cells[k] = m
            d_n = m["n"] - b["n"]
            d_net = round(m["net"] - b["net"], 1)
            d_dd = round(b["max_dd"] - m["max_dd"], 1)
            print(f"    {k:<16} trades {b['n']:>3} -> {m['n']:>3} "
                  f"({d_n:+4d})   net {b['net']:+7.1f} -> {m['net']:+7.1f} "
                  f"({d_net:+7.1f})", flush=True)
            print(f"    {'':<16} per-trade {b['net_per_trade']:>+6.3f} -> "
                  f"{m['net_per_trade']:>+6.3f}   WR {b['wr_pct']:>5.1f}% -> "
                  f"{m['wr_pct']:>5.1f}%   PF {b['pf']} -> {m['pf']}   "
                  f"maxDD {b['max_dd']:>5.1f} -> {m['max_dd']:>5.1f} "
                  f"({d_dd:+.1f})", flush=True)
            print(f"    {'':<16} ex-best3 {b['ex_best3_net']:+7.1f} -> "
                  f"{m['ex_best3_net']:+7.1f}   ex-best5 "
                  f"{b['ex_best5_net']:+7.1f} -> {m['ex_best5_net']:+7.1f}   "
                  f"trim {b['trimmed']:>+6.2f} -> {m['trimmed']:>+6.2f}",
                  flush=True)
        payload["arms"][arm] = cells
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()

