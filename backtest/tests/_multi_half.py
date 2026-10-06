"""FS trailing-half probe on the multi champion pair.

fsent_champ_long / fsent_utcsat_long are the scorecard leaders. Question: does
the same trail_half / trail_half+delay / decay lens, measured earlier on the
signal-plane champion, lift them too?

Usage: python -u _multi_half.py
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

ARMS = {
    "base": {},
    "trail_half": {"exp_trail_half": 1},
    "half+delay1": {"exp_trail_half": 1, "exp_trail_delay_r": 1.0},
    "decay_crossed": {"exp_decay_mode": 4, "exp_decay_thr": 0.75, "exp_decay_legs": 4},
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
        for base in ("fsent_champ_long", "fsent_utcsat_long"):
            cfg = EXPERIMENTS[base]
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
                results.setdefault(base, {}).setdefault(arm, {})[era] = m
                print("%s %-18s %-13s n=%3d net=%+7.1f avgR=%+.3f PF=%.2f DD=%.1f (%.0fs)"
                      % (era, base, arm, m["n"], m["net"], m["avgR"],
                         m["pf"] or 0, m["max_dd"], time.time() - t0), flush=True)

    OUT = ROOT / "backtest/tests/_multi_half.json"
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# FS trailing-half probe on fsent_champ_long / fsent_utcsat_long", ""]
    lines.append("| book | arm | IS n | IS net | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for base in results:
        for arm, e in results[base].items():
            ise, ooe = e.get("is") or {}, e.get("oos") or {}
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                base, arm, ise.get("n"),
                ("%+.1f" % ise["net"]) if ise.get("net") is not None else "-",
                ooe.get("n"),
                ("%+.1f" % ooe["net"]) if ooe.get("net") is not None else "-",
                ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-",
                ("%.2f" % ooe["pf"]) if ooe.get("pf") else "-",
                ("%.1f" % ooe["max_dd"]) if ooe.get("max_dd") is not None else "-"))
    MD = ROOT / "backtest/tests/_multi_half.md"
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    print("wrote %s" % MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
