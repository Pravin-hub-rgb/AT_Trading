"""ENTRY-BREAK COMPARISON ON THE FIXED ENGINE.

WHAT THIS IS FOR
----------------
The entry-break presets in btc_routes.py - decisive / flip / b2 and the
fs_long / fs_short / fs_both family - were last touched on 2026-09-07
(7ec23b4). That is BEFORE the B1 arming fix (2026-10-11, 77711a6), before V13
(2026-10-12, 88ecd00), and before the volatile-B1 and same-bar duplicate-pivot
work (2026-10-13). Every number those presets produced was measured while B1,
B2 and FLIP were landing on the wrong bars, so the RANKING BETWEEN THE ENTRY
BREAKS was never a ranking of anything real. The books were re-pinned, but the
entry-break question itself was never re-asked.

HOW THE KNOB WORKS
------------------
unified.py already runs all three HTF entry breaks every call and picks
between them by exp_htf_fs_entry (unified.py:629-636):

    _fb_flip     = "fs_both" if "flip"     in move else "flip"
    _fb_dec      = "fs_both" if "decisive" in move else "decisive"
    _fb_b2       = "fs_both" if "b2"       in move else "b2"

    move = {"flip": {"fs_both"}, "decisive": {"fs_both"}, "b2": {"fs_both"},
            "all": {"flip","decisive","b2"}}.get(hfs, set())

So setting exp_htf_fs_entry="flip" | "decisive" | "b2" moves that ONE entry
onto the FS print and leaves the other two on their break. That is the axis.
The LTF plane is held fixed at its normal break entry throughout, so nothing
else varies.

WHAT IS MEASURED
----------------
Same risk model as the shipping champion on both planes, both eras:
ATR-high regime gate, 58 chop, 8-bar cooldown, 3-loss streak halt, no ext stop,
leg pivot rule, exit window end, and costs applied (55bp fee/side, 2pt slippage,
5bp entry / 10bp exit). Reads nothing from the registry pins.

Writes _entry_break_study.json.
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

MODES = [
    # (label, extra params)
    # exp_htf_fs_entry moves ONE HTF entry break onto the FS print and leaves
    # the other two on their break (unified.py:629-636), so the first three are
    # a clean one-axis comparison of which break opens the window.
    ("decisive (B2 or FLIP)", {"exp_htf_fs_entry": "decisive"}),
    ("b2 only", {"exp_htf_fs_entry": "b2"}),
    ("flip only", {"exp_htf_fs_entry": "flip"}),
    ("htf_fs = all three", {"exp_htf_fs_entry": "all"}),
    # The fourth arm the owner actually asked about: enter on the LTF FS print.
    # exp_fs_entry_side="long" is what fsent_champ_long ships with, so this arm
    # IS the shipping book and the others are its controls.
    ("FS print (long)", {"exp_fs_entry_side": "long"}),
    ("FS print (both)", {"exp_fs_entry_side": "both"}),
]

# The shipping champion's risk model. This is fsent_champ_long's params with
# exp_htf_fs_entry added as the single variable under test.
# NOTE exp_mltf is NOT a parameter of this engine - the concurrent-position
# knob is max_positions. An earlier draft passed exp_mltf=True and the call
# raised TypeError on the keyword, so nothing ran.
BASE = dict(
    exp_partial_r=0.0, exp_persist=7,
    mode="atr_high", atr_high_thresh=0.65, chop_thresh=58.0,
    cooldown_bars=8, max_consecutive_losses=3, ext_stop_r=0.0,
    pivot_rule="leg", window_end="exit",
)


def summarise(tr):
    tr = [t for t in tr if t.get("outcome") != "open"]
    if not tr:
        return None
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    rs = [net_r([t]) for t in tr]
    # compute(rs, dates) zips them for the monthly/annual rollups, so dates has
    # to be the same length. The engine stamps exit time on the trade dict.
    dates = [t.get("exit_date") or t.get("date") or t.get("entry_date")
             for t in tr]
    if any(d is None for d in dates):
        dates = [""] * len(tr)
    m = compute(rs, dates)
    tot = sum(rs)
    return {
        "n": len(tr), "net": round(tot, 2),
        "avgR": round(tot / len(tr), 3),
        "pf": m.get("pf"), "wr": m.get("wr"), "max_dd": m.get("max_dd"),
        "ulcer": m.get("ulcer"), "max_streak": m.get("max_streak"),
        "top5_share_pct": m.get("top5_share_pct"),
    }


def main() -> int:
    from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt
    t0 = time.time()
    print("loading eras ...", flush=True)
    data = {"is": load_era("is"), "oos": load_era("oos")}
    print("loaded (%.0fs)" % (time.time() - t0), flush=True)

    out = {}
    for era in ("is", "oos"):
        d = data[era]
        # What does the HTF chain actually offer? decisive == b2 in the result
        # table is either "no FLIP ever opens a 1h window" or a wiring fault, and
        # the two are told apart by counting the marks rather than by trusting
        # the equal totals.
        for name in ("sw10", "sw15"):
            kinds = {}
            for s in d[name]:
                for b in s.get("breaks", []):
                    kinds[b.get("kind")] = kinds.get(b.get("kind"), 0) + 1
            print("  marks on %-5s %-4s : %s" % (name, era, dict(sorted(kinds.items()))),
                  flush=True)

        for label, extra in MODES:
            key = "%s | %s" % (era, label)
            tr = simulate_htf_ltf_streak_halt(
                d["c1h"], d["sw10"], d["c15"], d["sw15"],
                fine_ltf=d["fine"],
                **dict(BASE, **extra),
            )
            # the engine returns a dict of series, not a trade list. The books
            # are measured on the LTF plane (repin.measure does the same), so
            # that is the leg the entry knob feeds through into.
            s = summarise(tr["ltf_trades"])
            if s is None:
                print("  %-34s no trades" % key, flush=True)
                continue
            out[key] = s
            print("  %-34s n=%-5d net=%9.2f avgR=%6.3f PF=%5s DD=%6s WR=%s"
                  % (key, s["n"], s["net"], s["avgR"], s["pf"],
                     s["max_dd"], s["wr"]), flush=True)

    Path(__file__).with_name("_entry_break_study.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print()
    print("=" * 80)
    print("%-34s %7s %10s %7s %6s %8s %7s" %
          ("era | entry", "n", "net", "avgR", "PF", "maxDD", "WR%"))
    print("-" * 80)
    for era in ("is", "oos"):
        for label, _ in MODES:
            s = out.get("%s | %s" % (era, label))
            if not s:
                continue
            print("%-34s %7d %10.2f %7.3f %6s %8s %7s"
                  % (era + " | " + label, s["n"], s["net"], s["avgR"],
                     s["pf"], s["max_dd"], s["wr"]))
    print()
    print("wrote _entry_break_study.json  (%d cells, %.0fs)" % (len(out), time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())