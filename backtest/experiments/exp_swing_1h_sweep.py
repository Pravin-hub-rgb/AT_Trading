"""Re-open min_bars on the 1h swing chain. It has not been swept since 2026-09-20.

WHY THIS ONE
------------
min_bars_1h is pinned to 20 by a hard assert in run_experiment.py and the
comment beside it records why:

    min_bars_15m=50 ... mb35 -> 437t / +58.3R vs mb50 -> 351t / +238.0R
    min_bars_1h=20  ... (production=20)

So the 15m chain was measured across 35 vs 50 and found a 4x difference. The 1h
chain's 20 was recorded as production without the same comparison being visible
anywhere in the repo.

And that measurement is from 2026-09-20. It predates the mark-chain corrections
that moved every book in the registry - the same stale-chain problem already found
in 13 book descriptions, in the dropdown labels and in seven trade counts. A
constant that decides the swing series length is more load-bearing than most of
the knobs that get swept, and it is the one that has not been re-checked since
the engine moved.

This sweeps the 1h chain directly, on both eras, for the books currently being
compared. It is the largest structural knob in the family and it is read once
here rather than assumed.

Output: swing_1h_sweep.json + swing_1h_sweep.md
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

OUT = HERE / "swing_1h_sweep.json"
MD = HERE / "swing_1h_sweep.md"

# Around the production value of 20. 10 and 15 are the other two chains in
# current use, so they are included as known-live reference points.
GRID = [10, 12, 14, 16, 18, 20, 22, 25, 28, 32]
BOOKS = [
    ("fsent_champ_long_htffs", "106"),
    ("fsent_champ_long_mcloff_htf15", "107"),
]


def stat(rs):
    cum = pk = dd = 0.0
    for r in rs:
        cum += r
        pk = max(pk, cum)
        dd = max(dd, pk - cum)
    return {"n": len(rs), "net": round(sum(rs), 2), "dd": round(dd, 2)}


def main() -> int:
    t0 = time.time()
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()
    res = {}

    for name, code in BOOKS:
        base = EXPERIMENTS[name]
        params = {**BP, **(base.get("params") or {})}
        rows = []
        print("\n=== %s %s ===" % (code, name), flush=True)
        for mb in GRID:
            row = {"min_bars": mb, "eras": {}}
            for era in ("is", "oos"):
                d = ERA[era]
                # the swing chain is rebuilt at this length rather than looked
                # up, because get_swings only carries the three named chains
                sw = __import__("src.btc.btc_routes", fromlist=["_compute_swings"])._compute_swings(
                    d["f1h"], "continuous", min_bars=mb)
                sw15 = d["sw15"]
                o = sim(d["c1h"], sw, d["c15"], sw15, fine_ltf=d["fine"], **params)
                tr = [t for t in (o["ltf_trades"] if isinstance(o, dict) else o)
                      if t.get("outcome") != "open"]
                rs = [net_r([t]) for t in sorted(tr, key=lambda t: int(t["entry_ts"]))]
                row["eras"][era] = stat(rs)
            rows.append(row)
            i, o = row["eras"]["is"], row["eras"]["oos"]
            mark = "  <- production" if mb == 20 else ""
            print("  min_bars=%-3d  IS %4d/%+8.1f dd%6.2f   OOS %4d/%+8.1f dd%6.2f%s"
                  % (mb, i["n"], i["net"], i["dd"], o["n"], o["net"], o["dd"], mark), flush=True)
        res[code] = {"book": name, "rows": rows}

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1))

    L = ["# min_bars on the 1h swing chain, swept", "",
         "Pinned to 20 by a hard assert since 2026-09-20. That date predates the",
         "mark-chain corrections that moved every book in the registry, and the",
         "comment recording the 15m comparison (35 vs 50, a 4x difference) shows",
         "how load-bearing this chain length is. It had not been re-measured.", ""]
    for code, v in res.items():
        L.append("## %s `%s`" % (code, v["book"]))
        L.append("")
        L.append("| min_bars | IS trades | IS net | IS dd | OOS trades | OOS net | OOS dd |")
        L.append("|---:|---:|---:|---:|---:|---:|---:|")
        for r in v["rows"]:
            i, o = r["eras"]["is"], r["eras"]["oos"]
            mark = " **<- production**" if r["min_bars"] == 20 else ""
            L.append("| %d%s | %d | %+.1f | %.2f | %d | %+.1f | %.2f |"
                     % (r["min_bars"], mark, i["n"], i["net"], i["dd"],
                        o["n"], o["net"], o["dd"]))
        L.append("")
    io.open(MD, "w", encoding="utf-8").write("\n".join(L))
    print("\nwrote %s and %s  (%.0fs)" % (OUT.name, MD.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())