"""Streak-halt size sweep x persist x ext-stop, on fsent_champ_long.

The strip found that the 3-loss halt hurts the book. Now check what the
alternative halt heights do (0=off, 1, 2, 3, 5) together with
exp_persist and ext_stop_r being on/off, to cover the combination we had
not tested. chop_thresh is held fixed: a single-arm removal gave a
byte-identical result, so it does not interact with anything.

Usage: python -u _halt_sweep.py
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

PERS = (7, 0)
EXT = (3.0, 0.0)
HALT = (0, 1, 2, 3, 5)


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings

    sim = build_family_module()
    cfg = EXPERIMENTS["fsent_champ_long"]
    results = {}
    arms = [(p_, e_, h_) for p_ in PERS for e_ in EXT for h_ in HALT]
    for era in ("is", "oos"):
        data = load_era(era)
        for pers, ext, halt in arms:
            extra = {"exp_persist": pers, "ext_stop_r": ext,
                     "max_consecutive_losses": halt}
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
            results.setdefault(f"p{pers}_e{ext}_h{halt}", {})[era] = m
            print("%s persist=%d ext=%.1f halt=%d  n=%3d net=%+7.1f avgR=%+.3f PF=%.2f DD=%.1f (%.0fs)"
                  % (era, pers, ext, halt, m["n"], m["net"], m["avgR"],
                     m["pf"] or 0, m["max_dd"], time.time() - t0), flush=True)

    OUT = ROOT / "backtest/tests/_halt_sweep.json"
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# fsent_champ_long: halt height x persist x ext-stop", ""]
    lines.append("| persist | ext | halt | IS n | IS net | IS R/trd | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD | OOS avgR |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for pers, ext, halt in arms:
        e = results.get(f"p{pers}_e{ext}_h{halt}", {})
        ise, ooe = e.get("is") or {}, e.get("oos") or {}
        lines.append("| %d | %.1f | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            pers, ext, halt, ise.get("n"),
            ("%+.1f" % ise["net"]) if ise.get("net") is not None else "-",
            ("%+.3f" % ise["avgR"]) if ise.get("avgR") is not None else "-",
            ooe.get("n"),
            ("%+.1f" % ooe["net"]) if ooe.get("net") is not None else "-",
            ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-",
            ("%.2f" % ooe["pf"]) if ooe.get("pf") else "-",
            ("%.1f" % ooe["max_dd"]) if ooe.get("max_dd") is not None else "-",
            ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-"))
    MD = ROOT / "backtest/tests/_halt_sweep.md"
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    print("wrote %s" % MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
