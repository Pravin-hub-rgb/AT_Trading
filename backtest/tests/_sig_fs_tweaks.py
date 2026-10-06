"""Tweak hunt on the FS signal ladder: can trail_half and the decay gate lift
fsent_sig_full (short) and its both-side mirror?

Base A: fsent_sig_full params with exp_fs_entry_side="short" (the champion).
Base B: same stack but exp_fs_entry_side="both" (the weaker both-side
candidate). Arms add trail_half / trail_delay_r / decay gate modes from
unified.py P36. No registry writes; reads both eras.

Usage:  python -u _sig_fs_tweaks.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

from exp_full_metrics import compute  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

FULL = {
    "max_positions": 1,
    "mode": "atr_high",
    "atr_high_thresh": 0.65,
    "atr_low_thresh": 0.35,
    "sl_buf_atr": 0.01,
    "chop_thresh": 58.0,
    "cooldown_bars": 8,
    "max_consecutive_losses": 3,
    "ext_stop_r": 3.0,
    "exp_bias_momentum_min": 0.8,
    "exp_partial_r": 0.0,
    "exp_trail_skip_n": 2,
    "exp_fs_small_swing": 6.0,
    "exp_skip_weekend": 1,
    "window_end": "exit",
}

ARMS = {
    "base": {},
    "trail_half": {"exp_trail_half": 1},
    "trail_half+delay1": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0},
    "decay_own_side": {"exp_decay_mode": 3, "exp_decay_thr": 0.75, "exp_decay_legs": 4},
    "decay_crossed": {"exp_decay_mode": 4, "exp_decay_thr": 0.75, "exp_decay_legs": 4},
    "decay_buying_block": {"exp_decay_mode": 1, "exp_decay_thr": 0.75, "exp_decay_legs": 4},
    "half+own_side": {"exp_trail_half": 1, "exp_decay_mode": 3,
                      "exp_decay_thr": 0.75, "exp_decay_legs": 4},
    "half+crossed": {"exp_trail_half": 1, "exp_decay_mode": 4,
                     "exp_decay_thr": 0.75, "exp_decay_legs": 4},
}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings

    sim = build_family_module()
    results = {}
    for era in ("is", "oos"):
        data = load_era(era)
        for base_name, side in (("short_full", "short"), ("both_full", "both")):
            for arm, extra in ARMS.items():
                p = {**BP, **FULL, "exp_fs_entry_side": side, **extra}
                p.setdefault("exp_partial_r", 0.0)
                sw = get_swings(data, "sw10")
                t0 = time.time()
                try:
                    out = sim(data["c1h"], sw, data["c15"], data["sw15"],
                              fine_ltf=data["fine"], **p)
                except Exception as e:
                    print("ERR %s %s %s: %s" % (era, base_name, arm, e), flush=True)
                    continue
                tr = out["ltf_trades"] if isinstance(out, dict) else out
                tr = [t for t in tr if t.get("outcome") != "open"]
                rs = [net_r([t]) for t in tr]
                ds = [t.get("entry_date", "") for t in tr]
                m = compute(rs, ds)
                results.setdefault(base_name, {}).setdefault(arm, {})[era] = m
                print("%s %-12s %-18s n=%3d net=%+7.1f avgR=%+.3f PF=%.2f DD=%.1f (%.0fs)"
                      % (era, base_name, arm, m["n"], m["net"], m["avgR"],
                         m["pf"] or 0, m["max_dd"], time.time() - t0), flush=True)

    OUT = ROOT / "backtest/tests/_sig_fs_tweaks.json"
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)

    lines = ["# FS signal tweaks: trail_half x decay x side", ""]
    lines.append("| base | arm | IS n | IS net | IS R/trd | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for base in results:
        for arm, e in results[base].items():
            ise = e.get("is") or {}
            ooe = e.get("oos") or {}
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                base, arm,
                ise.get("n"), ("%+.1f" % ise["net"]) if ise.get("net") is not None else "-",
                ("%+.3f" % ise["avgR"]) if ise.get("avgR") is not None else "-",
                ooe.get("n"), ("%+.1f" % ooe["net"]) if ooe.get("net") is not None else "-",
                ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-",
                ("%.2f" % ooe["pf"]) if ooe.get("pf") else "-",
                ("%.1f" % ooe["max_dd"]) if ooe.get("max_dd") is not None else "-"))
    MD = ROOT / "backtest/tests/_sig_fs_tweaks.md"
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
