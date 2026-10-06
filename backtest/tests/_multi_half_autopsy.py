"""Cohort autopsy: base vs trail_half on fsent_champ_long / fsent_utcsat_long.

trail_half should only move the ratchet: entries must be the same set, exits
shift. If so, the cohort story is simply "same trades, different exits" -
exit-ledger fingerprint + winner-gap check makes that visible.

Usage: python -u _multi_half_autopsy.py
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


def key(t):
    return (t.get("entry_date") or t.get("entry_dt") or t.get("ts_entry_str"),
            t.get("dir") or t.get("side"))


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings

    sim = build_family_module()
    out_all = {}
    for era in ("is", "oos"):
        data = load_era(era)
        for book in ("fsent_champ_long", "fsent_utcsat_long"):
            cfg = EXPERIMENTS[book]
            sw = get_swings(data, cfg.get("swing") or "sw10")
            legs = {}
            for arm, extra in (("base", {}), ("trail_half", {"exp_trail_half": 1})):
                p = {**BP, **cfg["params"], **extra}
                p.setdefault("exp_partial_r", 0.0)
                out = sim(data["c1h"], sw, data["c15"], data["sw15"],
                          fine_ltf=data["fine"], **p)
                tr = out["ltf_trades"] if isinstance(out, dict) else out
                tr = [t for t in tr if t.get("outcome") != "open"]
                legs[arm] = tr
                print("%s %s %s n=%d" % (era, book, arm, len(tr)), flush=True)
            btr, htr = legs["base"], legs["trail_half"]
            bkeys = {key(t): t for t in btr}
            hkeys = {key(t): t for t in htr}
            shared = set(bkeys) & set(hkeys)
            removed = set(bkeys) - set(hkeys)
            added = set(hkeys) - set(bkeys)
            same_exit = sum(1 for k in shared
                            if (abs(float(bkeys[k].get("r_multiple", 0))
                                    - float(hkeys[k].get("r_multiple", 0))) < 1e-9))
            exit_moved = []
            for k in shared:
                b, h = bkeys[k], hkeys[k]
                exit_moved.append((float(b.get("r_multiple", 0)),
                                   float(h.get("r_multiple", 0))))
            improved = sum(1 for b, h in exit_moved if h > b + 1e-9)
            degraded = sum(1 for b, h in exit_moved if h < b - 1e-9)
            same = sum(1 for b, h in exit_moved if abs(h - b) < 1e-9)
            gross_base = sum(b for b, _ in exit_moved)
            gross_half = sum(h for _, h in exit_moved)
            med_dr = sorted(h - b for b, h in exit_moved)
            med = med_dr[len(med_dr) // 2] if med_dr else 0.0

            def winner_gap(tr, thresh=3.0):
                rs = [float(t.get("r_multiple", 0)) for t in tr]
                idx = [i for i, r in enumerate(rs) if r >= thresh]
                g = [b - a for a, b in zip(idx, idx[1:])]
                return (len(g), g[len(g) // 2] if g else None)

            gb = winner_gap(btr)
            gh = winner_gap(htr)
            print("", "%s %s: shared=%d removed=%d added=%d same_exit=%d moved_exit=%d (improved=%d degraded=%d) deltaR=%+.1f medDelta=%+.2f gap3R base~%s~%s half~%s~%s"
                  % (era, book, len(shared), len(removed), len(added),
                     same_exit, len(exit_moved) - same_exit, improved, degraded,
                     gross_half - gross_base, med, gb[0], gb[1], gh[0], gh[1]), flush=True)
            # also net per-trade
            bnet = sum(net_r([t]) for t in btr)
            hnet = sum(net_r([t]) for t in htr)
            print("    net base=%+.1f half=%+.1f ; removed-trade count %d [their r sum n=%d]"
                  % (bnet, hnet, len(removed), len(removed)), flush=True)
            out_all.setdefault(era, {})[book] = {
                "shared": len(shared), "removed": len(removed), "added": len(added),
                "same_exit": same_exit, "improved": improved, "degraded": degraded,
                "delta_gross": round(gross_half - gross_base, 1),
                "net_base": round(bnet, 1), "net_half": round(hnet, 1),
                "gap3R_base": gb, "gap3R_half": gh,
            }

    OUT = ROOT / "backtest/tests/_multi_half_autopsy.json"
    OUT.write_text(json.dumps(out_all, indent=2, default=str) + "\n", encoding="utf-8")
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
