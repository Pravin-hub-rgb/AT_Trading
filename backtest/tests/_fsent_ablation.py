"""Individual knob removal on fsent_champ_long.

Each arm removes ONE parameter; the point is to see what that parameter
carries. Nothing adopted.

Usage: python -u _fsent_ablation.py
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
from exp_multi_metrics import load_era  # noqa: E402
from experiment_registry import EXPERIMENTS  # noqa: E402

BASE = EXPERIMENTS["fsent_champ_long"]["params"]

ARMS = {
    "full": {},
    "no_FS_twist": {"exp_fs_entry_side": ""},
    "no_exp_persist": {"exp_persist": 0},
    "no_chop": {"chop_thresh": 0.0},
    "no_streak3": {"max_consecutive_losses": 0},
    "no_cooldown": {"cooldown_bars": 0},
    "no_ext_3R": {"ext_stop_r": 0.0},
    "persist0+cooldown0": {"exp_persist": 0, "cooldown_bars": 0},
    "no_FS+persist0": {"exp_fs_entry_side": "", "exp_persist": 0},
    "no_FS+cooldown0": {"exp_fs_entry_side": "", "cooldown_bars": 0},
    "no_FS+persist0+cooldown0": {"exp_fs_entry_side": "", "exp_persist": 0, "cooldown_bars": 0},
}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings

    sim = build_family_module()
    results = {}
    for era in ("is", "oos"):
        data = load_era(era)
        cfg = EXPERIMENTS["fsent_champ_long"]
        for arm, extra in ARMS.items():
            p = {**BP, **cfg["params"], **extra}
            p.setdefault("exp_partial_r", 0.0)
            sw = get_swings(data, cfg.get("swing") or "sw10")
            t0 = time.time()
            out = sim(data["c1h"], sw, data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **p)
            tr = out["ltf_trades"] if isinstance(out, dict) else out
            tr = [t for t in tr if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in tr]
            ds = [t.get("entry_date", "") for t in tr]
            m = compute(rs, ds)
            results.setdefault(arm, {})[era] = m
            print("%s %-26s n=%3d net=%+7.1f avgR=%+.3f PF=%.2f DD=%.1f (%.0fs)"
                  % (era, arm, m["n"], m["net"], m["avgR"],
                     m["pf"] or 0, m["max_dd"], time.time() - t0), flush=True)

    OUT = ROOT / "backtest/tests/_fsent_ablation.json"
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# fsent_champ_long knob ablation", ""]
    lines.append("| arm | IS n | IS net | IS R/trd | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for arm, e in results.items():
        ise, ooe = e.get("is") or {}, e.get("oos") or {}
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            arm, ise.get("n"),
            ("%+.1f" % ise["net"]) if ise.get("net") is not None else "-",
            ("%+.3f" % ise["avgR"]) if ise.get("avgR") is not None else "-",
            ooe.get("n"),
            ("%+.1f" % ooe["net"]) if ooe.get("net") is not None else "-",
            ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-",
            ("%.2f" % ooe["pf"]) if ooe.get("pf") else "-",
            ("%.1f" % ooe["max_dd"]) if ooe.get("max_dd") is not None else "-"))
    MD = ROOT / "backtest/tests/_fsent_ablation.md"
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    print("wrote %s" % MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
