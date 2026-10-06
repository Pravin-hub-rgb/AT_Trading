"""Cooldown sweep on fsent_champ_long / fsent_utcsat_long.

cooldown_bars is the only "edge off after a loss" brake besides the 3-loss
halt. This turns it off / shrinks it / grows it, to see what it carries.

Usage: python -u _cooldown_sweep.py
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

CDS = (0, 4, 8, 16, 24)


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings

    sim = build_family_module()
    results = {}
    for era in ("is", "oos"):
        data = load_era(era)
        for book in ("fsent_champ_long", "fsent_utcsat_long"):
            cfg = EXPERIMENTS[book]
            for cd in CDS:
                p = {**BP, **cfg["params"], "cooldown_bars": cd}
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
                results.setdefault(book, {})[f"cd{cd}"] = results.setdefault(book, {}).get(f"cd{cd}", {})
                results[book][f"cd{cd}"][era] = m
                print("%s %-18s cd=%2d n=%3d net=%+7.1f avgR=%+.3f PF=%.2f DD=%.1f (%.0fs)"
                      % (era, book, cd, m["n"], m["net"], m["avgR"],
                         m["pf"] or 0, m["max_dd"], time.time() - t0), flush=True)

    OUT = ROOT / "backtest/tests/_cooldown_sweep.json"
    OUT.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    lines = ["# Cooldown sweep on the fsent champ pair", ""]
    lines.append("| book | cd | IS n | IS net | OOS n | OOS net | OOS R/trd | OOS PF | OOS DD |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for book in results:
        for cd in CDS:
            e = results[book].get(f"cd{cd}", {})
            ise, ooe = e.get("is") or {}, e.get("oos") or {}
            lines.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
                book, cd, ise.get("n"),
                ("%+.1f" % ise["net"]) if ise.get("net") is not None else "-",
                ooe.get("n"),
                ("%+.1f" % ooe["net"]) if ooe.get("net") is not None else "-",
                ("%+.3f" % ooe["avgR"]) if ooe.get("avgR") is not None else "-",
                ("%.2f" % ooe["pf"]) if ooe.get("pf") else "-",
                ("%.1f" % ooe["max_dd"]) if ooe.get("max_dd") is not None else "-"))
    MD = ROOT / "backtest/tests/_cooldown_sweep.md"
    MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    print("wrote %s" % MD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
