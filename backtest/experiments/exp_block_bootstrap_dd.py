"""E5-C  BLOCK BOOTSTRAP ON THE DRAWDOWN PATH - a stress estimate, not a forecast.

WHY THIS FILE EXISTS AFTER THE SHUFFLE
-------------------------------------
exp_trade_order_shuffle.py shuffles single trades. That destroys the one thing
that makes a trading book a trading book: trades arrive in RUNS. Ten losses in a
row is not ten independent events, and a construction that treats it as such
understates how bad the path can get. The owner's objection to the shuffle was
correct on its own terms - a reshuffled book never traded - and this file is the
construction that answers a question the shuffle cannot.

WHAT WAS ALREADY IN THE REPO, AND ITS THREE GAPS
------------------------------------------------
exp_null_audit.py has had a move-block bootstrap since 2026-10-10. Read before
extending it, as instructed. It works on R VALUES ONLY, so:

  1. It cannot produce a single drawdown number. No timestamps reach it, so max
     DD, days under water and recovery time are all out of reach. This file
     supplies them.
  2. nb = n // block silently drops the remainder. At n=1152, block=20 that is
     12 trades; at n=190 it is 10. It barely moves the total but it is a quiet
     truncation, and the blocks here are carried to the full length instead.
  3. Block length is fixed at 20 with no sensitivity check. Twenty trades is not
     a truth anyone can cite, so 10, 20 and 40 are all run and reported
     separately.

WHAT IS RESAMPLED, AND WHAT IS NOT
----------------------------------
Resampled: blocks of consecutive R values, drawn with replacement. Each block
keeps its internal order, so win/loss clustering survives - a 20-trade block that
was three winners then two losers is still three winners then two losers.

NOT resampled: the strategy. The engine is not re-run, the HTF windows are not
re-drawn, no signal is regenerated. **This is a stress estimate on the outcomes
the book actually produced, not a simulation of what it might produce on a
different market.** A resample can put a losing trade on a timestamp where the
HTF had said take nothing, and that is exactly the bound it gives.

The time axis is the book's real, sorted timestamps. Each resampled R is placed
on one of those dates, which is what makes days-under-water comparable across
draws and what stops this from being a fantasy calendar.

HOW TO READ THE OUTPUT
----------------------
A 95th-percentile drawdown here is NOT an expected worst case and must not be
called one. It is: **"on the historical record this book, 95% of block-resampled
arrangements of its own realised trades stayed at or below this drawdown."** It
is a stress estimate drawn from history. It does not know anything about the
future, and it inherits every assumption listed above.

Output: block_bootstrap_dd.json
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
OUT = HERE / "block_bootstrap_dd.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

DRAWS = 2000
SEED = 20261015
BLOCKS = (10, 20, 40)          # block-length sensitivity, not a chosen truth

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


# --------------------------------------------------------------------------
# Path metrics. These mirror exp_results_export.py's construction, which is
# itself checked against hand-worked answers in exp_dd_recovery_test.py.
# --------------------------------------------------------------------------
def path_metrics(rs, ts_day):
    """rs: R values. ts_day: integer day of each exit, ascending, same length.

    Returns max_dd, dd_pct_of_peak, max_recover_days, p90_recover_days,
    longest_underwater_days, end_net.
    """
    n = len(rs)
    if n == 0:
        return None
    c = np.cumsum(rs)
    run_max = np.maximum.accumulate(c)
    dd = run_max - c

    # deepest drawdown: its peak index, trough index
    i_tr = int(np.argmax(dd))
    max_dd = float(dd[i_tr])
    i_pk = int(np.argmax(c[:i_tr + 1])) if i_tr > 0 else 0
    dd_pct = 100.0 * max_dd / float(run_max[i_pk]) if run_max[i_pk] > 1e-9 else 0.0

    # every peak-to-recovery episode, same construction as the exporter:
    # one episode per underwater period, not one per dip.
    recs = []
    longest_uw = 0
    open_peak = None
    open_peak_i = None
    trough_i = None
    pk2 = -1e18
    pk2_i = None
    for i in range(n):
        if c[i] > pk2:
            if open_peak is not None:
                recs.append(int(ts_day[i] - ts_day[trough_i]))
                longest_uw = max(longest_uw, int(ts_day[i] - ts_day[open_peak_i]))
                open_peak = None
            pk2 = c[i]
            pk2_i = i
        else:
            if open_peak is None:
                open_peak = open_peak_i = pk2_i
                trough_i = i
            elif c[i] < c[trough_i]:
                trough_i = i
    if open_peak is not None:
        longest_uw = max(longest_uw, int(ts_day[n - 1] - ts_day[open_peak_i]))

    max_rec = max(recs) if recs else None
    p90 = int(np.percentile(recs, 90)) if recs else None
    return dict(max_dd=round(max_dd, 2),
                dd_pct_of_peak=round(dd_pct, 2),
                max_recover_days=max_rec,
                p90_recover_days=p90,
                longest_uw_days=longest_uw,
                end_net=round(float(c[-1]), 2))


def resample(rs, block, rng):
    """Move-block bootstrap, carried to full length.

    The nb = n // block truncation in exp_null_audit.py is not repeated: the
    final partial block is kept and the sequence is trimmed back to n at the end.
    """
    n = len(rs)
    starts = list(range(0, n, block))
    out = []
    while len(out) < n:
        s = starts[rng.integers(len(starts))]
        out.extend(rs[s:s + block])
    return np.array(out[:n], dtype=float)


def main() -> int:
    t0 = time.time()
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}
    rng = np.random.default_rng(SEED)
    print("E5-C  BLOCK BOOTSTRAP ON THE DRAWDOWN PATH")
    print("%d draws x block lengths %s, both eras" % (DRAWS, list(BLOCKS)))
    print("Outcomes are resampled. The strategy is NOT re-run.\n")

    out = {"draws": DRAWS, "seed": SEED, "blocks": list(BLOCKS), "books": {}}
    for book in SHORTLIST:
        cfg = EXPERIMENTS[book]
        rec = {}
        for era in ("is", "oos"):
            tr = trades_of(sim, eras[era], cfg)
            rs = np.array([net_r(t) for t in tr], dtype=float)
            ts = np.array([int(t["exit_ts"]) // 86400 for t in tr], dtype=np.int64)
            assert len(rs) == len(ts)
            obs = path_metrics(rs, ts)
            per_block = {}
            for b in BLOCKS:
                acc = {k: [] for k in ("max_dd", "dd_pct_of_peak", "max_recover_days",
                                       "p90_recover_days", "longest_uw_days", "end_net")}
                for _ in range(DRAWS):
                    m = path_metrics(resample(rs, b, rng), ts)
                    for k in acc:
                        acc[k].append(m[k])
                per_block[str(b)] = {
                    k: dict(p50=round(float(np.percentile([x for x in v if x is not None], 50)), 2) if any(x is not None for x in v) else None,
                             p95=round(float(np.percentile([x for x in v if x is not None], 95)), 2) if any(x is not None for x in v) else None)
                    for k, v in acc.items()}
            rec[era] = {"n": len(rs), "observed": obs, "null": per_block}
        out["books"][book] = rec
        print("  %-34s done" % book)

    # ---------------------------------------------------------------- report
    print()
    print("=" * 116)
    print("OBSERVED vs BLOCK-BOOTSTRAP PATH (out of sample)")
    print("=" * 116)
    print("p95 here is a STRESS ESTIMATE on this book's own realised trades.")
    print("It is not a forecast and not an expected worst case.")
    print()
    hdr = "  %-32s %10s %10s %10s %10s" % ("book", "DD obs", "DD p95", "rec obs", "rec p95")
    for era in ("is", "oos"):
        print("  --- %s ---" % era.upper())
        print(hdr)
        print("  " + "-" * 78)
        for book in SHORTLIST:
            r = out["books"][book][era]
            o = r["observed"]
            for b in BLOCKS:
                nn = r["null"][str(b)]
                print("  %-32s %10.2f %10.2f %10s %10s%s"
                      % (book if b == BLOCKS[0] else "", o["max_dd"],
                         nn["max_dd"]["p95"],
                         str(o["max_recover_days"]) if o["max_recover_days"] is not None else "-",
                         str(nn["max_recover_days"]["p95"]),
                         "" if b == BLOCKS[0] else "   block=%d" % b))
        print()

    print("=" * 116)
    print("BLOCK-LENGTH SENSITIVITY - does the answer move with the block size?")
    print("=" * 116)
    print("  %-32s %6s %14s %14s %14s" % ("book", "block", "DD p95", "rec p95", "UW p95"))
    print("  " + "-" * 86)
    unstable = []
    for book in SHORTLIST:
        r = out["books"][book]["oos"]
        vals = []
        for b in BLOCKS:
            nn = r["null"][str(b)]
            vals.append(nn["max_dd"]["p95"])
        if max(vals) - min(vals) > 0.25 * max(vals):
            unstable.append(book)
        for b in BLOCKS:
            nn = r["null"][str(b)]
            print("  %-32s %6d %14.2f %14s %14s"
                  % (book if b == BLOCKS[0] else "", b, nn["max_dd"]["p95"],
                     str(nn["max_recover_days"]["p95"]),
                     str(nn["longest_uw_days"]["p95"])))
    print()
    print("  Books whose p95 drawdown moves by more than 25%% across block sizes: %s"
          % (unstable or "none"))
    print("  A large swing means the block length is deciding the answer, and")
    print("  neither value should be quoted on its own.")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1, default=str))
    print()
    print("wrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())