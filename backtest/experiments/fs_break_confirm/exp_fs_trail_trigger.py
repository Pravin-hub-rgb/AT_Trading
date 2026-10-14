"""
P82 - the FS-extreme level as a STOP TRIGGER, not an entry delay.

The first two arms of this idea are closed in CLOSED_DO_NOT_REPEAT.md:
`exp_fs_break_confirm` 1.0 (every FS entry waits for the break) and 2.0 (only
when the FS candle's colour opposes). Both lose on net R - IS negative in 5 of 5
books at every window - because paying for confirmation with a later entry gives
up 13-17% of the book.

What survived that measurement was not the entry. It was that the FS-extreme
level is a good DISCRIMINATOR: at 16 bars, pf rose and maxDD fell in BOTH eras in
every cell. That was recorded as an open lead rather than closed:

    "a trail trigger on the FS entry rather than an entry delay, and a
     per-trade risk change on the trades it would have dropped"

This is the first of those two. Entry stays ON the FS print. Nothing is dropped,
so no size is lost. The stop simply tightens once the FS candle's own extreme
breaks - on the trades whose FS actually confirmed.

    1.0 = ratchet the stop to breakeven
    2.0 = ratchet it to the FS candle's opposite extreme
          (long -> the FS candle's low, short -> its high)

WHAT IS AND IS NOT MOVED
    Entry price, risk, sl0 and the 3R target are all fixed at the entry and are
    NOT recomputed. Only the live stop moves, and only in the tightening
    direction, and only to a level on the losing side of the price running on
    that bar - so it cannot arm a stop the same bar immediately takes out.

CAUSALITY
    The ratchet is applied inside the bar loops, at bar j (or 1m timestamp ts) at
    or after the trigger bar, reading only candles up to that bar. The trigger
    condition - did the FS candle's extreme break - is settled at the trigger bar
    itself. Nothing here settles later than the bar it is applied on, and no
    swing field is read except this swing's own fs_at_idx.
    Contrast exp_require_dir_match / exp_max_swing_age, which read the swing's
    FINAL direction and settle mid-swing. Not this family.

IDENTITY GATE
    exp_fastcheck.py fsent_champ_long -> shipped 325t/+114.6R vs patched-off
    325t/+114.6R IDENTICAL; IS 497/+466.92, OOS 281/+215.32, every pinned field
    reproduced. Default is off and the default is byte-identical.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\..\..\backend\venv\Scripts\python.exe -u exp_fs_trail_trigger.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
BOOKS = ["fsent_champ_long", "fsent_champ_short", "fsent_champ_long_htf15",
         "fsent_champ_long_htffs", "fsent_champ_long_mcloff"]
ARMS = [("base (FS print)", {}),
        ("stop->breakeven, 8b", {"exp_fs_trail_trigger": 1.0}),
        ("stop->breakeven, 16b", {"exp_fs_trail_trigger": 1.0,
                                  "exp_fs_confirm_bars": 16}),
        ("stop->FS extreme, 8b", {"exp_fs_trail_trigger": 2.0}),
        ("stop->FS extreme, 16b", {"exp_fs_trail_trigger": 2.0,
                                   "exp_fs_confirm_bars": 16}),
        ("stop->FS extreme, 32b", {"exp_fs_trail_trigger": 2.0,
                                   "exp_fs_confirm_bars": 32})]


def load_era(era: str) -> dict:
    if era == "is":
        from run_experiment import get_data
        return get_data()
    from test_4_new_concepts import load_unseen, load_fine_1m as load_fine
    from engine.v18_params import SWING
    from src.btc.btc_routes import _compute_swings
    (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(f1h, "continuous", min_bars=10),
            "sw20": _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"]),
            "htf15": _compute_swings(f1h, "continuous", min_bars=15),
            "fine": load_fine(c15[0]["ts"], c15[-1]["ts"])}


def stats(trades: list[dict]) -> dict:
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    rs = [float(t["r_multiple"]) for t in closed if t.get("r_multiple") is not None]
    n = len(rs)
    net = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    eq = peak = dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "pf": round(pf, 2) if pf is not None else None,
            "win": round(len(wins) / n * 100, 1) if n else 0.0}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_swings
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    data = {e: load_era(e) for e in ("is", "oos")}

    out = {"stage": "fs_trail_trigger", "knob": "exp_fs_trail_trigger",
           "identity_gate": "PASS (fsent_champ_long 497/+466.92 IS, 281/+215.32 OOS)",
           "results": {}}
    for book in BOOKS:
        cfg = EXPERIMENTS.get(book)
        if not isinstance(cfg, dict):
            continue
        print("\n=== %s ===" % book)
        out["results"][book] = {}
        for era in ("is", "oos"):
            d = data[era]
            base = {**BP, **cfg["params"]}
            base.setdefault("exp_partial_r", 0.0)
            sw = get_swings(d, cfg.get("swing") or "sw10")
            row = {}
            print("  --- %s ---" % era.upper())
            for label, extra in ARMS:
                p = {**base, **extra}
                res = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
                tr = res["ltf_trades"] if isinstance(res, dict) else res
                s = stats(tr)
                row[label] = s
                print("    %-24s n=%-4d net=%+8.2fR  PF=%-5s DD=%5.2f WR=%.1f%%"
                      % (label, s["n"], s["net"],
                         s["pf"] if s["pf"] is not None else "-", s["dd"], s["win"]))
            b = row["base (FS print)"]
            print("      -- vs base --")
            for label, _ in ARMS[1:]:
                a = row[label]
                print("      %-24s n %+d   net %+7.2fR" % (label, a["n"] - b["n"],
                                                          a["net"] - b["net"]))
            out["results"][book][era] = row
    (HERE / "fs_trail_trigger_results.json").write_text(json.dumps(out, indent=2),
                                                       encoding="utf-8")
    print("\nwrote %s" % (HERE / "fs_trail_trigger_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())