"""exp_no_opposite: what it does, on the candidates first and then on everything.

WHY IT IS BEING RE-MEASURED
---------------------------
The only figures on record are from `_live_gates.md`, measured at engine ddd31dc
on 2026-10-08 - before the causal-stop fix and before the mark corrections that
moved every book in the registry. Everything in this repo measured on 2026-10-08
or earlier is stale, and this is no exception.

The owner wants this ON as default behaviour for every book, not just the
candidates, because a long and a short on one symbol net to roughly zero
exposure while paying fees twice and occupying margin twice. That argument does
not depend on the R at all, which is worth saying plainly: this knob is being
adopted for its risk shape, not because it makes money.

So the R question is still worth answering, but it is not what decides it.

WHAT IS MEASURED
----------------
Per book, both eras, off then on:

  trades, net R, R/trade, win rate, profit factor
  max drawdown, worst losing streak
  and HOW OFTEN IT ACTUALLY FIRES - how many trades were refused

That last one is the one that decides whether this is a filter or a formality.
A gate that never fires is not a risk control. A gate that fires twice in six
hundred trades and costs nothing is cheap insurance.

PRIORITY ORDER
--------------
107 and 110 first, because those are the two carried into the forward window
and the owner wants those answered first. Everything else follows.

Output: no_opposite.json + no_opposite.md
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

OUT = HERE / "no_opposite.json"
MD = HERE / "no_opposite.md"

PRIORITY = [
    ("fsent_champ_long_mcloff_htf15", "107"),
    ("fsent_champ_long_htf15_tskip6", "110"),
]


def profile(trades):
    tr = [t for t in trades if t.get("outcome") != "open"]
    tr.sort(key=lambda t: int(t["entry_ts"]))
    rs = [net_r([t]) for t in tr]
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    st = bst = 0
    for r in rs:
        st = st + 1 if r < 0 else 0
        bst = max(bst, st)
    n = len(tr)
    return {
        "n": n, "net": round(sum(rs), 2),
        "rpt": round(sum(rs) / n, 4) if n else 0.0,
        "wr": round(100.0 * len(w) / n, 1) if n else 0.0,
        "pf": round(sum(w) / -sum(l), 3) if l and -sum(l) else 0.0,
        "dd": round(dd, 2), "streak": bst,
    }


def run(sim, data, cfg, swing, flag):
    p = {**BP, **(cfg.get("params") or {}), "exp_no_opposite": flag}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return o["ltf_trades"] if isinstance(o, dict) else o


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()

    pinned = [k for k, v in EXPERIMENTS.items()
              if isinstance(v, dict) and isinstance(v.get("pins"), dict) and "n" in v["pins"]]
    order = [n for n, _ in PRIORITY if n in pinned] + \
            sorted(n for n in pinned if n not in dict(PRIORITY))

    res = {}
    L = ["# exp_no_opposite, re-measured on the current engine", "",
         "The previous figures were measured on 2026-10-08, before the causal-stop",
         "fix and before the mark corrections. Everything from that date or earlier",
         "in this repo is stale and this is no exception.", "",
         "This knob is NOT being adopted for its R. A long and a short on one",
         "symbol net to roughly zero exposure while paying fees twice and holding",
         "margin twice, and on a book that may hold eight positions that is a",
         "sizing bug rather than a rounding error. The numbers below answer whether",
         "it is free, not whether it is profitable.", ""]

    print("\n=== PRIORITY: the two forward candidates ===\n", flush=True)
    for name in order:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        rec = {"code": dict(PRIORITY).get(name, ""), "eras": {}}
        for era in ("is", "oos"):
            try:
                off = profile(run(sim, ERA[era], cfg, swing, 0))
                on = profile(run(sim, ERA[era], cfg, swing, 1))
            except Exception as exc:  # noqa: BLE001
                rec["eras"][era] = {"error": "%s: %s" % (type(exc).__name__, exc)}
                continue
            fired = off["n"] - on["n"]
            rec["eras"][era] = {
                "off": off, "on": on, "fired": fired,
                "fire_pct": round(100.0 * fired / off["n"], 2) if off["n"] else 0.0,
                "d_net": round(on["net"] - off["net"], 2),
                "d_dd": round(on["dd"] - off["dd"], 2),
                "d_streak": on["streak"] - off["streak"],
                "d_rpt": round(on["rpt"] - off["rpt"], 4),
            }
            e = rec["eras"][era]
            if "off" in e:
                print("%-34s %-4s off %4dt/%+8.2f dd%6.2f st%2d  |  on %4dt/%+8.2f dd%6.2f st%2d"
                      "  | fires %d (%.2f%%)  dNet %+.1f"
                      % (name[:34], era.upper(), e["off"]["n"], e["off"]["net"], e["off"]["dd"],
                         e["off"]["streak"], e["on"]["n"], e["on"]["net"], e["on"]["dd"],
                         e["on"]["streak"], e["fired"], e["fire_pct"], e["d_net"]), flush=True)
        res[name] = rec

    print("\nall %d books measured (%.0fs)" % (len(res), time.time() - t0), flush=True)

    # ---- report ----
    L += ["## The two forward candidates", "",
          "| book | era | fires | % of trades | net off | net on | d net | DD off | DD on | streak off/on | R/trade off/on |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for name in dict(PRIORITY):
        if name not in res:
            continue
        for era in ("is", "oos"):
            e = res[name]["eras"].get(era) or {}
            if "off" not in e:
                L.append("| `%s` | %s | - | - | - | - | - | - | - | - | %s |"
                         % (name, era.upper(), e.get("error", "error")))
                continue
            L.append("| `%s` | %s | %d | %.2f%% | %+.2f | %+.2f | **%+.2f** | %.2f | %.2f | %d / %d | %+.4f / %+.4f |"
                     % (name, era.upper(), e["fired"], e["fire_pct"],
                        e["off"]["net"], e["on"]["net"], e["d_net"],
                        e["off"]["dd"], e["on"]["dd"], e["off"]["streak"], e["on"]["streak"],
                        e["off"]["rpt"], e["on"]["rpt"]))
    L.append("")

    # aggregate
    agg = {"books": 0, "eras": 0, "fired_total": 0, "trades_total": 0,
           "better_net": 0, "worse_net": 0, "same_net": 0,
           "better_dd": 0, "worse_dd": 0, "sum_dnet": 0.0, "errors": 0}
    for name, rec in res.items():
        for era in ("is", "oos"):
            e = rec["eras"].get(era) or {}
            if "off" not in e:
                agg["errors"] += 1
                continue
            agg["books"] += 1
            agg["eras"] += 1
            agg["fired_total"] += e["fired"]
            agg["trades_total"] += e["off"]["n"]
            agg["sum_dnet"] += e["d_net"]
            if e["d_net"] > 0.005:
                agg["better_net"] += 1
            elif e["d_net"] < -0.005:
                agg["worse_net"] += 1
            else:
                agg["same_net"] += 1
            if e["d_dd"] < -0.005:
                agg["better_dd"] += 1
            elif e["d_dd"] > 0.005:
                agg["worse_dd"] += 1
    L += ["## Across every book", "",
          "| measure | value |", "|---|---:|",
          "| book-eras measured | %d |" % agg["books"],
          "| trades before the lock | %d |" % agg["trades_total"],
          "| trades the lock refused | %d (%.2f%%) |"
          % (agg["fired_total"], 100.0 * agg["fired_total"] / max(agg["trades_total"], 1)),
          "| net better with the lock on | %d |" % agg["better_net"],
          "| net worse | %d |" % agg["worse_net"],
          "| net unchanged | %d |" % agg["same_net"],
          "| sum of all net changes | %+.2fR |" % agg["sum_dnet"],
          "| drawdown better | %d |" % agg["better_dd"],
          "| drawdown worse | %d |" % agg["worse_dd"],
          "| errors | %d |" % agg["errors"], ""]
    L += ["## Per-book detail", "",
          "| book | era | fires | net off | net on | d net | DD off | DD on | streak off/on |",
          "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for name in sorted(res):
        for era in ("is", "oos"):
            e = res[name]["eras"].get(era) or {}
            if "off" not in e:
                L.append("| `%s` | %s | - | - | - | - | - | - | %s |" % (name, era.upper(), e.get("error", "err")))
                continue
            L.append("| `%s` | %s | %d | %+.2f | %+.2f | %+.2f | %.2f | %.2f | %d / %d |"
                     % (name, era.upper(), e["fired"], e["off"]["net"], e["on"]["net"],
                        e["d_net"], e["off"]["dd"], e["on"]["dd"],
                        e["off"]["streak"], e["on"]["streak"]))
    L.append("")
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1))
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s and %s" % (OUT.name, MD.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())