"""FULL METRICS for every MULTI book (max_positions != 1), from the engine.

Mirror of exp_signal_metrics.py. That harness deliberately refused to mix the
planes: a 500-trade multi run at the top of a "best signal" list answers
neither question, because total R on parallel slots is bought with concurrency
and not with the quality of any one trade. So the multi plane gets its own run
and its own file, and nothing is ranked across the seam.

Why the metrics and not just the pins: experiment_registry stores four fields
per era (n, net, dd_net, win). Average R per trade, profit factor, payoff,
median, std and the streak counts are in the engine but not in the pins, and
the two rankings that matter - total net R and R per trade - disagree on
purpose. On this plane the disagreement should be large, because a book here
can earn its total by running more slots at once.

The books quarantined for look-ahead are skipped and reported as skipped rather
than run, so a filtered list can never quietly include one. The knobs
(exp_require_dir_match, exp_max_swing_age, exp_union_dual_only,
exp_max_running_mag) read a field that is not settled at the entry bar; the
same quarantine list is used by both planes so the two stay comparable.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_multi_metrics.py [n_limit]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_multi_metrics.json"
DB = ROOT / "backtest/tests/results.db"

# Reuse the harness's own metric definitions rather than restating them, so the
# numbers here mean what the rest of the repo means by them.
from exp_full_metrics import compute  # noqa: E402
from exp_signal_metrics import (GRAVEYARD_KNOBS, load_era,  # noqa: E402
                                quarantine_reason)


def multi_books() -> tuple[list[str], dict]:
    """Every multi-plane book the registry knows, plus the quarantined ones."""
    from experiment_registry import EXPERIMENTS
    import results_db as rdb

    conn = rdb.connect(DB)
    names = [r["name"] for r in conn.execute(
        "SELECT name FROM books WHERE plane='multi' ORDER BY name")]
    conn.close()

    clean, skipped = [], {}
    for n in names:
        cfg = EXPERIMENTS.get(n)
        if not isinstance(cfg, dict):
            continue
        bad = quarantine_reason(cfg.get("params") or {})
        if bad:
            skipped[n] = bad.split(",")
            continue
        clean.append(n)
    return clean, skipped


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    t0 = time.time()

    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from experiment_registry import EXPERIMENTS

    books, skipped = multi_books()
    if limit:
        books = books[:limit]
    print("multi books: %d to run, %d skipped as quarantined"
          % (len(books), len(skipped)), flush=True)
    print("graveyard knobs: %s" % ", ".join(GRAVEYARD_KNOBS), flush=True)
    for n, why in sorted(skipped.items()):
        print("  SKIP %-38s %s" % (n, ",".join(why)), flush=True)
    if not books:
        print("nothing to run")
        return 1

    sim = build_family_module()
    payload = {"stage": "multi_metrics",
               "note": "computed from the engine; nothing transcribed by hand",
               "plane": "multi (max_positions != 1)",
               "skipped_quarantined": {k: v for k, v in sorted(skipped.items())},
               "configs": {}}

    for era in ("is", "oos"):
        print("\n=== bybit %s ===" % era.upper(), flush=True)
        data = load_era(era)
        got = 0
        for i, key in enumerate(books, 1):
            cfg = EXPERIMENTS[key]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            # The swing length lives on the registry ENTRY as `swing`, not in
            # params: passing data["sw10"] unconditionally runs every sw20 book
            # as sw10. Same trap as the signal harness, same fix.
            sw = get_swings(data, cfg.get("swing") or "sw10")
            try:
                out = sim(data["c1h"], sw, data["c15"], data["sw15"],
                          fine_ltf=data["fine"], **p)
            except Exception as e:                       # noqa: BLE001
                print("  [%d/%d] %-38s ERROR %s" % (i, len(books), key, e),
                      flush=True)
                payload["configs"].setdefault(era, {})[key] = {"error": str(e)}
                continue
            tr = out["ltf_trades"] if isinstance(out, dict) else out
            rs = [net_r([t]) for t in tr]
            ds = [t.get("entry_date", "") for t in tr]
            m = compute(rs, ds)
            # Compare against the pin instead of trusting the run. A mismatch is
            # printed, not swallowed: the whole point is that nothing is hidden.
            pin = (cfg.get("pins") or {}).get("net") if era == "is" else \
                (cfg.get("pins") or {}).get("oos_net")
            m["pin_net"] = pin
            m["vs_pin"] = round(m["net"] - pin, 1) if (m.get("n") and pin is not None) else None
            payload["configs"].setdefault(era, {})[key] = m
            if m.get("n"):
                got += 1
                flag = "" if (m["vs_pin"] is None or abs(m["vs_pin"]) < 0.5) \
                    else "  <<PIN %s" % m["vs_pin"]
                print("  [%d/%d] %-38s n=%3d net=%+7.1f WR=%4.1f%% avgR=%+6.3f "
                      "med=%+5.2f PF=%4.2f DD=%5.1f cal=%6.2f strk=%2d top5=%s%%%s"
                      % (i, len(books), key, m["n"], m["net"], m["wr"], m["avgR"],
                         m["median"], m["pf"] or 0, m["max_dd"],
                         m["calmar"] or 0, m["max_streak"],
                         m["top5_share_pct"], flag), flush=True)
            else:
                print("  [%d/%d] %-38s no trades" % (i, len(books), key),
                      flush=True)
        print("  ran %d/%d with trades (%s)" % (got, len(books), era), flush=True)

    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print("\nwrote %s  (%.0fs)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
