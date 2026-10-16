"""E5-A  TRADE-ORDER SHUFFLE - is the drawdown number an artefact of ordering?

WHAT THIS IS NOT
----------------
**This is not a profitability test. It cannot tell you whether the strategy
works, and nothing here should be read as saying so.**

It shuffles trades that never happened in that order. It therefore answers one
narrow question and no other: **is the drawdown number in the table a property of
the book, or a property of the one order its trades happened to arrive in?**

THE OBJECTION, WHICH IS CORRECT
-------------------------------
> "The market will not shuffle. We take trades in specific HTF windows. If the
>  HTF says long is right, we only take long. Does shuffle go against the
>  premise of the whole strategy?"

Yes, and that is exactly why this cannot be used to judge the strategy. A
shuffled arrangement puts the outcome of trade 57 on the timestamp of trade 1.
No 1h window ever produced that. The reshuffle is not a possible history.

What survives that objection:

    The set of trades is fixed, and so is their total. Net R, win rate and profit
    factor are unchanged by construction - and net R is asserted unchanged on
    every book, because if it moved the whole comparison would be meaningless.

    Only the PATH moves. Max drawdown, days under water, recovery time, longest
    losing run and every rolling-window percentage are functions of order. If
    the observed order sits at the lucky end of that distribution, those numbers
    are flattering the book.

Worked example. 100 trades, 70 winners of +3R and 30 losers of -1R:

    total is +180R in every arrangement, always.

    losers first:  equity 0 -> -30R -> +180R    max drawdown 30R, long recovery
    mixed:        equity wanders around 0        max drawdown 4R, short recovery

Same trades, same money, drawdown differing by nearly 8x. Which one the book
actually experienced is what this test asks about.

Note that shuffling does NOT change how many winners there are. It cannot turn 70
winners into 40 - the outcomes are the outcomes. Only their order moves.

LIMITS, STATED WHERE THEY WILL BE READ
--------------------------------------
  - Not a strategy test. A shuffled book never traded.
  - Serial dependence is destroyed, so this is a LOWER BOUND on sequence risk,
    not the whole of it. A block bootstrap (exp_block_bootstrap_dd.py) keeps
    runs intact and is the construction to use for a stress estimate.
  - Times are kept, trades are not. A shuffled outcome lands on a real
    timestamp, which is what makes the day counts comparable but is also why the
    result is a bound and not a scenario.

Output: trade_order_shuffle.json
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
OUT = HERE / "trade_order_shuffle.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

DRAWS = 2000
SHORTLIST = [
    "fsent_sig_sw20_short", "fsent_sig_wk_pause_short", "fsent_sig_trail_delay1",
    "fsent_sig_full", "fsent_sig_fs_mom",
    "fsent_champ_long_htf15_htffs", "fsent_champ_long_htfesmcl4",
    "fsent_champ_long_htf15_tskip6", "fsent_champ_long_htffs",
    "fsent_champ_long_mcloff_htf15",
]


def net_r(t):
    from exp_equity_quality import net_r as _nr
    return float(_nr([t]))


def trades_of(sim, data, cfg):
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=data["fine"],
             **{**dict(repin.re_.BP), **cfg["params"]})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return [t for t in tr if t.get("outcome") != "open"]


def max_dd_of(rs):
    c = np.cumsum(rs)
    return float(np.max(np.maximum.accumulate(c) - c))


def longest_loss_run(rs):
    best = cur = 0
    for x in rs:
        cur = 0 if x > 0 else cur + 1
        if cur > best:
            best = cur
    return best


def roll_prof(rs, w):
    if len(rs) < w:
        return None
    c = np.convolve(rs, np.ones(w), mode="valid")
    return 100.0 * float((c > 0).sum()) / len(c)


def drawdown_days(rs, ts):
    """Deepest drawdown peak-to-trough, in calendar days, on this order."""
    c = np.cumsum(rs)
    run_max = np.maximum.accumulate(c)
    dd = run_max - c
    i = int(np.argmax(dd))
    if dd[i] <= 0:
        return 0.0
    j = int(np.argmax(c[:i + 1]))
    return (int(ts[i]) - int(ts[j])) / 86400.0


def pct_rank(value, null):
    """Where the observed value sits inside the shuffled distribution.
    0 = smallest ever, 100 = larger than all of them."""
    if not len(null):
        return None
    return 100.0 * float((np.asarray(null) <= value).sum()) / len(null)


def main() -> int:
    t0 = time.time()
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}
    rng = np.random.default_rng(20261015)
    print("E5-A  TRADE-ORDER SHUFFLE - %d shuffles per book, both eras" % DRAWS)
    print("net R must not move. asserting it on every book.\n")

    out = {"draws": DRAWS, "seed": 20261015, "books": {}}
    for book in SHORTLIST:
        cfg = EXPERIMENTS[book]
        rec = {}
        for era in ("is", "oos"):
            tr = trades_of(sim, eras[era], cfg)
            rs = np.array([net_r(t) for t in tr], dtype=float)
            ts = np.array([int(t["exit_ts"]) for t in tr], dtype=np.int64)
            obs_net = float(rs.sum())
            obs = {
                "net": round(obs_net, 2),
                "max_dd": round(max_dd_of(rs), 2),
                "dd_days": round(drawdown_days(rs, ts), 1),
                "loss_run": longest_loss_run(rs),
                "roll50_pct": roll_prof(rs, 50),
            }
            null = {"net": [], "max_dd": [], "dd_days": [], "loss_run": [], "roll50_pct": []}
            for _ in range(DRAWS):
                p = rng.permutation(rs)
                null["net"].append(float(p.sum()))
                null["max_dd"].append(max_dd_of(p))
                null["dd_days"].append(drawdown_days(p, ts))
                null["loss_run"].append(longest_loss_run(p))
                null["roll50_pct"].append(roll_prof(p, 50))
            # THE CONTROL
            net_moved = abs(float(np.max(np.abs(np.array(null["net"]) - obs_net)))) > 0.01
            rec[era] = {
                "observed": obs,
                "pct_rank": {k: pct_rank(obs[k], np.array(v, dtype=float))
                             for k, v in null.items() if k != "net"},
                "null_median": {k: float(np.median(v)) for k, v in null.items()},
                "null_p95_worse": {k: float(np.percentile(v, 95)) for k, v in null.items()},
                "net_invariance_ok": not net_moved,
            }
        out["books"][book] = rec
        print("  %-34s done" % book)

    # ---------------- report --------------------------------------------
    print()
    print("=" * 118)
    print("WHERE DOES EACH BOOK'S REAL SEQUENCE SIT AMONG SHUFFLED ARRANGEMENTS?")
    print("=" * 118)
    print("A LOW rank means the real order was LUCKY - better than most orderings.")
    print("A HIGH rank means the real order was UNUSUAL/BAD - most shuffles did better.")
    print()
    for era in ("is", "oos"):
        print("  %s" % era.upper())
        print("  %-34s %10s %10s %10s %10s %8s"
              % ("book", "DD rank", "DDdays", "lossrun", "roll50", "net ok"))
        print("  " + "-" * 86)
        for book in SHORTLIST:
            r = out["books"][book][era]
            pr = r["pct_rank"]
            f = lambda k: ("%.0f%%" % pr[k]) if pr.get(k) is not None else "n/a"
            print("  %-34s %10s %10s %10s %10s %8s"
                  % (book, f("max_dd"), f("dd_days"), f("loss_run"),
                     f("roll50_pct"), "yes" if r["net_invariance_ok"] else "*** NO ***"))
        print()

    print("=" * 118)
    print("READING IT")
    print("=" * 118)
    bad_net = [b for b in SHORTLIST
               if not (out["books"][b]["is"]["net_invariance_ok"]
                       and out["books"][b]["oos"]["net_invariance_ok"])]
    print("Books where net R moved under shuffling (must be zero): %s" % (bad_net or "none - shuffle is clean"))
    oos_low = [(b, out["books"][b]["oos"]["pct_rank"]["max_dd"])
               for b in SHORTLIST
               if out["books"][b]["oos"]["pct_rank"].get("max_dd") is not None]
    lucky = [x for x in oos_low if x[1] < 25]
    unlucky = [x for x in oos_low if x[1] > 75]
    print()
    print("Books whose out-of-sample drawdown sits in the LUCKY quarter (<25th pct): %s"
          % ([b for b, _ in lucky] or "none"))
    print("Books whose out-of-sample drawdown sits in the UNUSUAL quarter (>75th pct): %s"
          % ([b for b, _ in unlucky] or "none"))
    print()
    print("A low DD rank means the sequence was lucky and the true sequence risk is")
    print("worse than the table shows. A high rank means the opposite - the drawdown")
    print("is worse than most orderings of the same trades, so the book is carrying")
    print("its pain rather than dodging it.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1, default=float))
    print()
    print("wrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())