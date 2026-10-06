"""Joint ablation: strip the chaff from fsent_champ_long in one go.

Arms: remove chop_thresh, exp_persist=0, no 3-loss halt, no ext_stop_r, and
the full stripped book. CD 4 vs 8 stays in for comparison, because it was the
suspect before.

Usage: python -u _strip.py
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

BOOK = "fsent_champ_long"

CHOP_OFF = {"chop_thresh": 0.0}
PERSIST_OFF = {"exp_persist": 0}
STREAK_OFF = {"max_consecutive_losses": 0}
EXT_OFF = {"ext_stop_r": 0.0}

ARMS = {
    "full": {},
    "cheap_cd0": {"chop_thresh": 0.0, "exp_persist": 0,
                  "max_consecutive_losses": 0, "ext_stop_r": 0.0,
                  "cooldown_bars": 0},
    "all_brakes_off": {**CHOP_OFF, **PERSIST_OFF, **STREAK_OFF, **EXT_OFF},
    "all_off+no_cooldown": {**CHOP_OFF, **PERSIST_OFF, **STREAK_OFF, **EXT_OFF,
                             "cooldown_bars": 0},
    "all_off+cd4": {**CHOP_OFF, **PERSIST_OFF, **STREAK_OFF, **EXT_OFF,
                     "cooldown_bars": 4},
    "no_halt_only": dict(STREAK_OFF),
    "persist_chop_off_only": {**CHOP_OFF, **PERSIST_OFF},
    "persist_chop_ext_off": {**CHOP_OFF, **PERSIST_OFF, **EXT_OFF},
}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings

    sim = build_family_module()
    results = {}
    for era in ("is", "oos"):
        data = load_era(era)
        cfg = EXPERIMENTS[BOOK]
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
            print("%s %-26s n=%3d net=%+7.1f avgR=%+.3f PF=%.2f DD=%.1f strk=%s top5=%s (%.0fs)"
                  % (era, arm, m["n"], m["net"], m["avgR"], m["pf"] or 0,
                     m["max_dd"], m.get("max_streak"), m.get("top5_share_pct"),
                     time.time() - t0), flush=True)

    OUT = ROOT / "backtest/tests/_strip.json"
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# fsent_champ_long stripped-down ablation", ""]
    lines.append("| arm | IS n | IS net | IS R/trd | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD | OOS strk |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for arm, e in results.items():
        ise, ooe = e.get("is") or {}, e.get("oos") or {}
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            arm, ise.get("n"),
            ("%+.1f" % ise["net"]) if ise.get("net") is not None else "-",
            ("%+.3f" % ise["avgR"]) if ise.get("avgR") is not None else "-",
            ooe.get("n"),
            ("%+.1f" % ooe["net"]) if ooe.get("net") is not None else "-",
            ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-",
            ("%.2f" % ooe["pf"]) if ooe.get("pf") else "-",
            ("%.1f" % ooe["max_dd"]) if ooe.get("max_dd") is not None else "-",
            ooe.get("max_streak")))
    MD = ROOT / "backtest/tests/_strip.md"
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    print("wrote %s" % MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
