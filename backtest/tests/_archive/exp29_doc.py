"""Exp 29 doc builder -- reads _exp29_results.json, writes the comparison doc."""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
results = json.loads((ROOT / "backtest/tests/_exp29_results.json").read_text())
results.sort(key=lambda m: -m["net"])

L = []
L.append("# All Combined Experiment Trade Metrics (v31)\n")
L.append("**Every viable config from BOTH lanes, run on the SHIPPED engine "
         "(identity-gated), production params (chop=58, cd=10, halt=3, "
         "sl_buf=0.01, ext_stop=1.5, mode b2_vs_flip_chop), FINE 1m fills, "
         "2023-01 -> 2026-09 (3.7y). COST MODEL (v2, both-lane-agreed): "
         "NET = Gross - (fee+entry slip+exit slip) - FUNDING "
         "(0.01%%/8h on notional, hold-time weighted, leverage-adjusted; "
         "notional/risk = entry/SL-distance). CONVENTION: WR, AvgWin/Loss, "
         "Payoff, PF, MaxDD, per-year on RAW trade R (gross); NET its own "
         "column. Matches the other lane's corrected harness to the decimal "
         "on all halt6/anchor variants. Generated %s. Source: "
         "tests/exp29_final_metrics.py.\n" % time.strftime("%Y-%m-%d"))

L.append("## Main table (sorted by NET)\n")
hdr = ("| Config | Trades | Tr/yr | Gross R | Fees | Funding | **NET R** | NET/trd |"
       " WR%% | AvgWin | AvgLoss | Payoff | PF | MaxDD | DD dur (trd/days) |"
       " MaxConsecL | AvgHold(h) |")
L.append(hdr)
L.append("|" + "---|" * 17)
for m in results:
    L.append("| %s | %d | %.0f | %+.1f | %.1f | %.1f | **%+.1f** | %+.3f | %.1f | %+.2f | %+.2f | %.2f | %.2f | %.1f | %d / %.0f | %d | %.1f |"
             % (m["tag"], m["n"], m["tpy"], m["gross"], m["cost"], m["fund"],
                m["net"], m["npt"], m["wr"], m["aw"], m["al"], m["payo"], m["pf"],
                m["dd"], m["ddt"], m["ddd"], m["mc"], m["hold_h"]))

L.append("\n## Per-year R + halves (strict both-halves rule, raw R)\n")
L.append("| Config | 2023 | 2024 | 2025 | 2026 (9mo) | H1 | H2 | both>0? |")
L.append("|" + "---|" * 8)
for m in results:
    py = m["py"]
    both = "PASS" if (m["h1"] > 0 and m["h2"] > 0) else "FAIL"
    L.append("| %s | %+.1f | %+.1f | %+.1f | %+.1f | %+.1f | %+.1f | %s |"
             % (m["tag"], py.get("2023", 0.0), py.get("2024", 0.0),
                py.get("2025", 0.0), py.get("2026", 0.0), m["h1"], m["h2"], both))

L.append("\n## Notes & caveats\n")
L.append("- All configs share the same engine, data, and cost model; differences are config only.")
L.append("- multi-LTF configs (mltf, S9, their-OPTIMAL, OPTIMAL+halt6) can hold concurrent positions (max 5 observed; 80-88% of time <=1) -- needs concurrency design before live.")
L.append("- cd0 configs (their-OPTIMAL, OPTIMAL+halt6, B3-OPT cd0) remove the loss cooldown -- cd=0 latency/re-entry behavior needs live validation (their lane's own caveat).")
L.append("- B3-OPT cd10 and B3-OPT+halt6 cd10 are fully production-parameter single-position configs (no concurrency, no cd0).")
L.append("- their-OPTIMAL fine gross (+456.2R) vs coarse (+429.8R): fine fills HELP this engine (Exp 28 Q3 reconciliation, 515/515 matched).")
L.append("- halt4 cliff on OPTIMAL (Exp 28 Q5): single-halt sensitivity exists; halt=3 is the shipped default.")
L.append("- NOT yet done: true re-optimizing walk-forward (fixed-config 3-cut stability passed for OPTIMAL/B3-OPT); cd=0 live latency validation; concurrency-cap variants (cap 2/3).")
L.append("- Decisions DEFERRED until experiment list exhausted (user process).")

out = ROOT / "backtest/docs/all combined experiment trade metric.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
print("doc written: %s (%d lines)" % (out, len(L)))
