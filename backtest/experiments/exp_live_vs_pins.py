"""Does the LIVE engine reproduce the registry pins for the multi books?

THE QUESTION THIS ANSWERS
-------------------------
Six books were quietly serving a different book on the live backend. Their
registry params carry exp_mltf=True; the live engine has no exp_mltf parameter
at all, so their dispatch branches cannot pass it and were running without it.
Two other books crashed loudly instead, because their branches did pass it.

exp_mltf is injected into the engine by a source patch in
test_experiments_craze.py, and it only does anything on the loss-window hard
close path - a path that also does not exist in unified.py. No book in the
shortlist sets any exp_window_loss_kill_* parameter, so the knob has nothing to
modify and should be inert for every one of them.

"Should be inert" is a prediction. This measures it: run the LIVE engine on the
IS dataset through the same call the backend makes, and compare against the pin.

    match      the live engine reproduces the pin. The book on the page is the
               book that was measured, and the crash was cosmetic.
    differs    the live engine is running a different book from the one every
               number in this repository was measured against.

Output: live_vs_pins.md
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import EXPERIMENTS  # noqa: E402
from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt as live  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402

MD = HERE / "live_vs_pins.md"

# exactly the calls the dispatch branches make
CALLS = {
    "fsent_champ_long": dict(
        mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
        sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
        max_consecutive_losses=3, max_positions=0, ext_stop_r=3.0,
        exp_partial_r=0.0, exp_persist=7, pivot_rule="leg",
        exp_fs_entry_side="long"),
    "fsent_champ_long_htffs": dict(
        mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
        sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
        max_consecutive_losses=3, max_positions=0, ext_stop_r=3.0,
        exp_partial_r=0.0, exp_persist=7, pivot_rule="leg",
        exp_fs_entry_side="long", exp_htf_fs_entry="flip"),
    "fsent_champ_long_htfesmcl4": dict(
        mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
        sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
        max_consecutive_losses=4, max_positions=0, ext_stop_r=3.0,
        exp_partial_r=0.0, exp_persist=7, pivot_rule="leg",
        exp_fs_entry_side="long", exp_htf_fs_entry="all"),
    "fsent_champ_long_mcloff_htf15": dict(
        mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
        sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
        max_consecutive_losses=0, max_positions=0, ext_stop_r=3.0,
        exp_partial_r=0.0, exp_persist=7, pivot_rule="leg",
        exp_fs_entry_side="long"),
    "fsent_champ_long_htf15_htffs": dict(
        mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
        sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
        max_consecutive_losses=3, max_positions=0, ext_stop_r=3.0,
        exp_partial_r=0.0, exp_persist=7, pivot_rule="leg",
        exp_fs_entry_side="long", exp_htf_fs_entry="flip"),
    "fsent_champ_long_htf15_tskip6": dict(
        mode="atr_high", atr_high_thresh=0.65, atr_low_thresh=0.35,
        sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
        max_consecutive_losses=3, max_positions=0, ext_stop_r=3.0,
        exp_partial_r=0.0, exp_persist=7, pivot_rule="leg",
        exp_fs_entry_side="long", exp_trail_skip_n=6),
}


def main() -> int:
    data = get_data()
    L = ["# Live engine vs registry pins", "",
         "The live engine has 46 parameters. The backtest harness has 151. Nothing",
         "the harness supports is missing from live except the reverse, so a book",
         "using a harness-only knob cannot be reproduced on the live backend at",
         "all.", "",
         "Six books carry exp_mltf=True in the registry and their branches omit it;",
         "two passed it and crashed. exp_mltf only acts on the loss-window hard",
         "close path, which does not exist in unified.py either, and no book in",
         "the shortlist sets an exp_window_loss_kill_* parameter. So it should be",
         "inert. Measured rather than assumed:", "",
         "| book | pin n | pin net | live n | live net | reproduces the pin? |",
         "|---|---:|---:|---:|---:|---|"]
    ok = bad = 0
    for name, params in CALLS.items():
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        o = live(candles_htf=data["c1h"], swings_htf=get_swings(data, swing),
                 candles_ltf=data["c15"], swings_ltf=data["sw15"],
                 fine_ltf=data["fine"], **params)
        tr = [t for t in o.get("ltf_trades", []) if t.get("outcome") != "open"]
        rs = [net_r([t]) for t in sorted(tr, key=lambda t: int(t["entry_ts"]))]
        pn, pnet = cfg["pins"]["n"], cfg["pins"]["net"]
        match = len(rs) == pn and abs(sum(rs) - pnet) < 0.05
        ok += match
        bad += (not match)
        L.append("| `%s` | %d | %+.2f | %d | %+.2f | %s |"
                 % (name, pn, pnet, len(rs), sum(rs), "yes" if match else "** NO **"))
        print("%-34s pin %4d/%+8.2f   live %4d/%+8.2f   %s"
              % (name, pn, pnet, len(rs), sum(rs), "MATCH" if match else "DIFFERS"), flush=True)
    L.append("")
    L.append("**%d of %d books reproduce their pin on the live engine.**"
             % (ok, ok + bad))
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s" % MD.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())