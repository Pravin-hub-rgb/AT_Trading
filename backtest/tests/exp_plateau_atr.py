"""PARAMETER PLATEAU - tier 4 of docs/learn/finding optimal book.md, on the fixed engine.

WHAT THIS IS FOR
----------------
The framework's tier 4 was explicitly not faked by exp_optimalbook_study.py
("tier 4 is a separate harness per axis and is NOT faked here"). This is that
harness for the one axis the registry itself flags as suspicious.

fsent_champ_long_mode_atr_low's own registry desc records the worry:

  "Its own threshold swept 0.20-0.60 and the OOS gain peaks sharply at 0.35
   (+41.1R) and is NEGATIVE everywhere else - one point, not a region, which
   is exactly the grid-peak failure P69 warns about."

That sweep predates the B1 fix (2026-10-11) and every mark fix after it, so it
was a sweep of a chain whose B2, FLIP and FS marks were on the wrong bars. A
threshold that peaks on one point may peak there only because the marks moved.

THE TEST THE DOC ASKS FOR
-------------------------
  a plateau:  0.20 0.25 0.30 0.35 0.40 0.45 0.50 0.55 0.60
               all positive, flat, in BOTH eras          -> keep
  a spike:    one point positive, everything else negative -> do not keep

Both eras, and the same grid on the shipping atr_high book as the control, so a
plateau in one mode and a spike in the other is distinguishable from an
artefact of the mode.

Writes _plateau_atr_low.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from exp_signal_metrics import load_era                      # noqa: E402
import exp_repin_stale as repin                               # noqa: E402
from run_experiment import net_r                              # noqa: E402
from exp_full_metrics import compute                          # noqa: E402

GRID = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

BASE = dict(
    exp_partial_r=0.0, exp_persist=7,
    chop_thresh=58.0, cooldown_bars=8, max_consecutive_losses=3,
    ext_stop_r=0.0, pivot_rule="leg", window_end="exit",
)

MODES = [("atr_low", "fsent_champ_long_mode_atr_low", "long"),
         ("atr_high", "fsent_champ_long", "long")]


def summarise(tr):
    tr = [t for t in tr if t.get("outcome") != "open"]
    if not tr:
        return None
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    rs = [net_r([t]) for t in tr]
    dates = [t.get("exit_date") or t.get("date") or "" for t in tr]
    m = compute(rs, dates)
    tot = sum(rs)
    return {"n": len(tr), "net": round(tot, 2),
            "avgR": round(tot / len(tr), 3), "pf": m.get("pf"),
            "wr": m.get("wr"), "max_dd": m.get("max_dd")}


def main() -> int:
    from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt
    t0 = time.time()
    print("loading eras ...", flush=True)
    data = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)\n" % (time.time() - t0), flush=True)

    out = {}
    for mode, book, entry in MODES:
        print("=" * 76)
        print("%s  (%s, exp_fs_entry_side=%s)" % (mode, book, entry))
        print("=" * 76)
        print("  %-6s | %-28s | %-28s" % ("thr", "IS", "OOS"))
        print("  %-6s | %6s %8s %5s %6s | %6s %8s %5s %6s"
              % ("", "n", "net", "PF", "DD", "n", "net", "PF", "DD"))
        print("  " + "-" * 72)
        rows = []
        for thr in GRID:
            row = {"thr": thr}
            for era in ("is", "oos"):
                d = data[era]
                tr = simulate_htf_ltf_streak_halt(
                    d["c1h"], d["sw10"], d["c15"], d["sw15"],
                    fine_ltf=d["fine"],
                    **dict(BASE, mode=mode, atr_low_thresh=thr,
                           atr_high_thresh=thr, exp_fs_entry_side=entry))
                s = summarise(tr["ltf_trades"])
                row[era] = s
            out.setdefault(mode, {})[str(thr)] = row
            f = lambda s: ("%6d %8.2f %5s %6s" % (s["n"], s["net"], s["pf"], s["max_dd"])
                           if s else "%6s %8s %5s %6s" % ("-", "-", "-", "-"))
            print("  %-6.2f | %s | %s" % (thr, f(row["is"]), f(row["oos"])))
            rows.append(row)
        for era in ("is", "oos"):
            vals = [r[era]["net"] for r in rows if r[era]]
            pos = [v for v in vals if v > 0]
            print()
            print("  %s : %d of %d points positive   range %.1f .. %.1f"
                  % (era, len(pos), len(vals), min(vals), max(vals)))
            if pos:
                print("       plateau? %s"
                      % ("yes - a region, not a spike"
                         if len(pos) >= 4 else
                         "NO - fewer than 4 of 9 points positive, this is a spike"))
        print()

    Path(__file__).with_name("_plateau_atr_low.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("wrote _plateau_atr_low.json  (%.0fs)" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())