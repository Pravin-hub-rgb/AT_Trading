"""Full metrics for the two mode-census books registered on 2026-10-14.

    fsent_champ_short_session      (session routing)
    fsent_champ_long_htf15_union   (union routing)

Each is printed against the shipped book it was derived from, on the same eras,
so the comparison is like-for-like rather than absolute-only.

Every field comes from exp_equity_quality.equity_quality, the same lens
exp_equity_lens.py uses. Years are 3.67 for IS and 2.0 for OOS, taken from that
harness - calmar and recovery are annualised/relative and are meaningless
without them, so they are not recomputed here.

Output: mode_census_full_metrics.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "mode_census_full_metrics.json"

import exp_repin_stale as repin                                  # noqa: E402
import test_experiments_craze as craze                           # noqa: E402
from exp_equity_quality import equity_quality                    # noqa: E402
from exp_signal_metrics import load_era                          # noqa: E402
from registry import EXPERIMENTS                                # noqa: E402

YEARS = {"is": 3.67, "oos": 2.0}

# (new book, the shipped book it was measured against)
PAIRS = [
    ("fsent_champ_short_session", "fsent_champ_short"),
    ("fsent_champ_long_htf15_union", "fsent_champ_long_htf15"),
]

ORDER = [
    ("n", "trades", 0),
    ("wr", "win rate %", 1),
    ("net", "net total R", 0),
    ("avg_r", "avg R / trade", 2),
    ("pf", "profit factor", 2),
    ("expectancy_win", "avg R on winners", 2),
    ("expectancy_loss", "avg R on losers", 2),
    ("net_closed", "net, closed only", 2),
    ("max_dd", "max drawdown R", 2),
    ("max_dd_pct", "max DD % of net", 1),
    ("max_dd_dur", "max DD length (trades)", 0),
    ("recovery", "recovery (net/maxDD)", 2),
    ("calmar", "calmar (annualised)", 2),
    ("sortino", "sortino", 2),
    ("ulcer", "ulcer", 2),
    ("uw_pct", "% trades underwater", 1),
    ("max_uw", "longest underwater run", 0),
    ("max_streak", "longest loss streak", 0),
    ("pos_month_pct", "% positive months", 1),
    ("worst_month", "worst month R", 2),
    ("best_month", "best month R", 2),
    ("pos_year_pct", "% positive years", 1),
    ("worst_year", "worst year R", 2),
    ("months_n", "months traded", 0),
]

_DONE = 0
_TOTAL = len(PAIRS) * 2 * 2 * 2      # pairs x books x eras x (warm + measure)
_T0 = time.time()


def progress(label):
    global _DONE
    _DONE += 1
    pct = 100.0 * _DONE / _TOTAL
    el = time.time() - _T0
    eta = (el / _DONE) * (_TOTAL - _DONE) if _DONE else 0.0
    bar = "#" * int(pct / 2.5)
    msg = "[%3d%%] %-40s %6.1fs elapsed, ~%5.0fs left" % (pct, bar, el, eta)
    sys.stdout.write("\r  %s   %s" % (msg, label))
    sys.stdout.flush()


def trades_of(sim, data, cfg):
    """An exact replica of exp_repin_stale.measure's trade pipeline.

    Three things had to match or the lens reports a different book than the
    one the pins describe:
      - the swing key comes from cfg["swing"], not a hardcoded sw10. The htf15
        books were being measured on the sw10 chain here, which changed the
        trade list (union 451 -> 431).
      - BP is repin.re_.BP, i.e. run_experiment.BP - the same defaults dict
        exp_repin_stale.measure() merges the book params over.
      - _trade_costs is applied before any statistic is taken. Without it the
        lens reported 196R where the pin says 321.38R.
    """
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"], fine_ltf=fine,
             **{**dict(repin.re_.BP), **cfg["params"]})["ltf_trades"]
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return tr


def net_r(t):
    from exp_equity_quality import net_r as _nr
    return _nr([t])


def enrich(q, trades, years):
    n = q.get("n") or 0
    if not n:
        return q
    nets = [net_r(t) for t in trades]
    wins = [x for x in nets if x > 0]
    loss = [x for x in nets if x <= 0]
    q = dict(q)
    q["avg_r"] = round(q["net"] / n, 4)
    q["expectancy_win"] = round(sum(wins) / len(wins), 4) if wins else 0.0
    q["expectancy_loss"] = round(sum(loss) / len(loss), 4) if loss else 0.0
    q["max_dd_pct"] = round(100.0 * q["max_dd"] / q["net"], 2) if q["net"] else 0.0
    q["gross_win"] = round(sum(wins), 2)
    q["gross_loss"] = round(sum(loss), 2)
    q["open_trades"] = sum(1 for t in trades if t.get("outcome") == "open")
    # equity_quality's net_r and btc_routes' _net_stats disagree on an OPEN
    # trade - fsent_champ_short_session measures 589.14R here and pins at
    # 589.36R, the gap being the one still-open IS position. The pinned number
    # is the _net_stats one and is what every other harness compares against, so
    # both are reported rather than quietly reconciling to either.
    closed = [x for x, t in zip(nets, trades) if t.get("outcome") != "open"]
    q["n_closed"] = len(closed)
    q["net_closed"] = round(sum(closed), 4)
    q["years"] = years
    return q


def line(field, label, dp, a, b):
    def f(v):
        if v is None:
            return "n/a"
        if dp == 0:
            return "%d" % v
        return ("%%.%df" % dp) % v
    d = ""
    if a is not None and b is not None and dp == 0:
        d = "  (%+d)" % (a - b)
    elif a is not None and b is not None:
        d = "  (%+.2f)" % (a - b)
    return "  %-24s %16s %16s%s" % (label, f(a), f(b), d)


def main() -> int:
    print("FULL METRICS - the two mode-census books vs the shipped books they came from")
    print("lens: exp_equity_quality.equity_quality, years IS %.2f / OOS %.2f"
          % (YEARS["is"], YEARS["oos"]))
    print()
    t0 = time.time()
    sim = craze.build_module()
    eras = {e: load_era(e) for e in ("is", "oos")}
    print("loaded (%.0fs)" % (time.time() - t0))
    print()

    out = {}
    for new, old in PAIRS:
        out[new] = {"baseline": old, "eras": {}}
        for era in ("is", "oos"):
            row = {}
            for book in (old, new):
                cfg = EXPERIMENTS[book]
                tr = trades_of(sim, eras[era], cfg)
                progress("%s | %s | %s" % (new, book, era))
                q = enrich(equity_quality(tr, YEARS[era]), tr, YEARS[era])
                pin = cfg.get("pins") or {}
                want = pin.get("n") if era == "is" else pin.get("oos_n")
                wnet = pin.get("net") if era == "is" else pin.get("oos_net")
                q["pin_ok"] = (q["n"] == want) and (abs(q["net"] - wnet) < 0.01)
                row[book] = q
            out[new]["eras"][era] = row

            print("=" * 82)
            print("%s   [%s]" % (new, era.upper()))
            print("  baseline: %s" % old)
            print("=" * 82)
            a, b = row[old], row[new]
            for f, lab, dp in ORDER:
                print(line(f, lab, dp, b.get(f), a.get(f)))
            print("  %-24s %16s %16s" % ("", "NEW", "BASELINE"))
            print("  pins match: new=%s baseline=%s"
                  % (b.get("pin_ok"), a.get("pin_ok")))
            print()

    RESULTS.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s  (%.0fs)" % (RESULTS.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
