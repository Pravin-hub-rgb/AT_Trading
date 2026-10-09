"""2025-H1 autopsy - six representative books, not the whole registry.

The full-registry version was aborted: 157 books x 2 eras is minutes per book and
answers the same question more slowly. The market autopsy alone already localises
the cause, and six books is enough to separate "the window" from "the family".
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

SAMPLE = [
    ("fsent_champ_long", "sw10"),
    ("fsent_champ_long_mcloff", "sw10"),
    ("fsent_champ_long_mcloff_htf15", "htf15"),
    ("fsent_champ_short", "sw10"),
    ("fsent_sig_multi", "sw10"),
    ("fsent_champ_long_htfesmcl4", "sw10"),
]


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    print("=" * 96)
    print("1. THE MARKET per half-year (1h) - and what 2025-H1 actually was")
    print("=" * 96)
    buckets = defaultdict(list)
    for c in E["is"]["c1h"]:
        t = datetime.fromtimestamp(int(c["ts"]), tz=timezone.utc)
        buckets["%d-%s" % (t.year, "H1" if t.month <= 6 else "H2")].append(c)
    mkt = []
    print("  %-9s %6s %10s %10s %9s %11s %11s"
          % ("cell", "bars", "open", "close", "ret %", "p95|move|", "med range"))
    for k in sorted(buckets):
        cs = buckets[k]
        cl = [float(c["close"]) for c in cs]
        hi = [float(c["high"]) for c in cs]
        lo = [float(c["low"]) for c in cs]
        mv = sorted(abs(cl[i] - cl[i - 1]) / cl[i - 1] for i in range(1, len(cl)))
        rg = sorted((hi[i] - lo[i]) / cl[i] * 100 for i in range(len(cl)))
        r = dict(cell=k, ret=round((cl[-1] / cl[0] - 1) * 100, 2),
                 p95=round(mv[int(.95 * (len(mv) - 1))] * 100, 3),
                 medr=round(rg[len(rg) // 2], 3))
        mkt.append(r)
        print("  %-9s %6d %10.1f %10.1f %+9.2f %10.3f%% %10.3f%%%s"
              % (k, len(cs), cl[0], cl[-1], r["ret"], r["p95"], r["medr"],
                 "  <-- THE CELL" if k == "2025-H1" else ""))
    out["market"] = mkt

    print("\n" + "=" * 96)
    print("2. SIX BOOKS across all 12 cells - net R")
    print("=" * 96)
    per = {}
    for name, swing in SAMPLE:
        agg = defaultdict(list)
        for era in ("is", "oos"):
            d = E[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **EXPERIMENTS[name]["params"])
            for t in o["ltf_trades"]:
                if t.get("outcome") != "open":
                    agg[cell(t["entry_ts"])].append(net_r([t]))
        per[name] = {c: round(sum(v), 2) for c, v in agg.items()}
        out.setdefault("books", {})[name] = per[name]

    cells = sorted(per[SAMPLE[0][0]])
    hdr = "  %-9s" % "cell"
    for n, _ in SAMPLE:
        hdr += "%14s" % n.replace("fsent_champ_long", "champ")\
            .replace("fsent_champ_short", "short")\
            .replace("fsent_sig_multi", "sigmul")\
            .replace("mcloff_htf15", "+htf15")\
            .replace("htfesmcl4", "+htffs")
    print(hdr)
    for c in cells:
        line = "  %-9s" % c
        for n, _ in SAMPLE:
            v = per[n].get(c, 0.0)
            line += "%14s" % ("%+.1f" % v + ("*" if v < 0 else " "))
        if c == "2025-H1":
            line += "   <-- every book"
        print(line)
    print("\n  (* = negative half-year)")

    n_neg = sum(1 for c in cells if any(per[n].get(c, 0) < 0 for n, _ in SAMPLE))
    print("\n  cells where AT LEAST ONE of the six is negative: %d of %d" % (n_neg, len(cells)))
    allneg = [c for c in cells if all(per[n].get(c, 0) < 0 for n, _ in SAMPLE)]
    print("  cells where ALL SIX are negative: %s" % (allneg or "NONE"))

    with open("_period_2025h1_autopsy.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print("  wrote _period_2025h1_autopsy.json")


if __name__ == "__main__":
    main()