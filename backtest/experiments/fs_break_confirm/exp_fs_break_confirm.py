"""
P81 - confirm the FS entry: take it only when the FS candle's own extreme breaks.

THE OWNER'S IDEA (2026-10-14)
    "when for FS, when the high of or long, when the high of FS will break, then
     we will enter. For short, when FS low will be broken, then we'll enter."

WHAT THIS IS NOT
    Not a re-run of FS-entry. FS_ENTRY.md already measured entering AT the FS
    print: viable but 36% smaller, and M2 inverts 4/4. DIRECTIONAL_FS_P80.md
    closed the directional FS trigger at P82 on a permutation test. This is a
    different question and it sits on top of the FS print:

        FS print entry : take the trade the moment the swing confirms
        FS break entry : take it only once the FS candle's own extreme breaks

    That is a CONTINUATION filter on the FS arm. It is aimed squarely at the one
    question FS_ENTRY.md left open - "the 36% of trades lost" - and at the trail
    problem it named: a late entry wants a different stop, and this gets there by
    filtering rather than by re-timing.

    Only the side exp_fs_entry_side already put on FS is moved. The other side
    still enters on its break and is untouched, so this is not a whole-book
    retiming.

MECHANISM
    For an "up" swing (a long on FS), wait for a later LTF candle whose HIGH
    exceeds the FS candle's high. For a "down" swing, a later candle whose LOW
    goes under the FS candle's low. If that never happens inside
    exp_fs_confirm_bars, the trade is not taken.

    swing_start_px is deliberately left as _collect_signals set it, so the only
    variable that moves is the entry bar, not the anchor the stop hangs from.

CAUSALITY
    Reads candles_ltf[fs_at_idx].high/low and candles_ltf[j] for j > fs_at_idx.
    fs_at_idx is at or after the swing's end bar, so the FS candle has closed
    before anything is read. The entry IS the bar on which the break occurs, so
    no field settles later than the decision bar. No swing field is read except
    this swing's own fs_at_idx, which is settled at the FS print. This is the
    same guarantee exp_fs_entry_side relies on, with one more closed bar in
    front of it.

    Contrast with the closed family: exp_require_dir_match and exp_max_swing_age
    read the swing's FINAL direction, which settles mid-swing. This does not.

IDENTITY GATE
    exp_fastcheck.py fsent_sig_full -> "shipped 325t/+114.6R vs patched-off
    325t/+114.6R -> IDENTICAL" on 2026-10-14, run immediately after the knob
    landed. The default is off and the default is byte-identical.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\..\backend\venv\Scripts\python.exe -u exp_fs_break_confirm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # backtest/experiments/<name>/ -> repo root
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
BOOKS = ["fsent_champ_long", "fsent_champ_short", "fsent_champ_long_htffs",
         "fsent_champ_long_mcloff"]
ARMS = [("base (FS print)", {}),
        ("FS break confirm", {"exp_fs_break_confirm": 1.0}),
        ("FS break confirm, 4 bars", {"exp_fs_break_confirm": 1.0,
                                      "exp_fs_confirm_bars": 4}),
        ("FS break confirm, 16 bars", {"exp_fs_break_confirm": 1.0,
                                       "exp_fs_confirm_bars": 16})]


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

    out = {"stage": "fs_break_confirm", "knob": "exp_fs_break_confirm",
           "identity_gate": "PASS (exp_fastcheck fsent_sig_full, 325t/+114.6R both sides)",
           "results": {}}
    for book in BOOKS:
        cfg = EXPERIMENTS.get(book)
        if not isinstance(cfg, dict):
            print("skip %s (not in registry)" % book)
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
                res = sim(d["c1h"], sw, d["c15"], d["sw15"],
                          fine_ltf=d["fine"], **p)
                tr = res["ltf_trades"] if isinstance(res, dict) else res
                s = stats(tr)
                row[label] = s
                print("    %-26s n=%-4d net=%+8.2fR  PF=%-5s DD=%5.2f WR=%.1f%%"
                      % (label, s["n"], s["net"],
                         s["pf"] if s["pf"] is not None else "-", s["dd"], s["win"]))
            b = row["base (FS print)"]
            for label, _ in ARMS[1:]:
                a = row[label]
                print("      vs base: %-22s n %+d   net %+7.2fR"
                      % (label, a["n"] - b["n"], a["net"] - b["net"]))
            out["results"][book][era] = row
    (HERE / "fs_break_confirm_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote %s" % (HERE / "fs_break_confirm_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())