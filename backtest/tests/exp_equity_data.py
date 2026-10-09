"""Bar equity curve - data export for the support chart.

Emits _equity_data.json: per-book trade series, half-year aggregates, cumulative
equity and drawdown, so the HTML viewer has everything and re-running the engine
is not needed to redraw it.

The chart exists to make ONE thing visible: the shipping book's only negative
half-year is a -0.69R dip on 60 trades, and the candidates remove it without
removing the book. A table of pins does not show that; a curve does.
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

BOOKS = [
    ("fsent_champ_long", "sw10", {},
     "fsent_champ_long", "SHIPPING - max_consecutive_losses=3"),
    ("fsent_champ_long_mcloff", "sw10", {"max_consecutive_losses": 0},
     "fsent_champ_long", "mcloff - loss-run cutoff OFF  [best EVIDENCE]"),
    ("fsent_champ_long_mcloff_htf15", "htf15", {"max_consecutive_losses": 0},
     "fsent_champ_long", "mcloff + htf15 swing  [best RETURN]"),
]


def half_label(epoch):
    d = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def collect(sim, E, parent, swing, over):
    pts = []
    for era in ("is", "oos"):
        d = E[era]
        p = {**EXPERIMENTS[parent]["params"], **over}
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        for t in sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                        key=lambda t: int(t["entry_ts"])):
            pts.append((int(t["entry_ts"]), net_r([t])))
    pts.sort(key=lambda z: z[0])
    cum = 0.0
    pk = 0.0
    mdd = 0.0
    series = []
    per = defaultdict(list)
    for ts, r in pts:
        cum += r
        pk = max(pk, cum)
        dd = pk - cum
        mdd = max(mdd, dd)
        series.append(dict(ts=ts, r=round(r, 4), cum=round(cum, 3), dd=round(dd, 3)))
        per[half_label(ts)].append(r)
    halfs = [dict(cell=c, n=len(v), net=round(sum(v), 2),
                  trades=[round(x, 3) for x in v]) for c, v in sorted(per.items())]
    neg = [h["cell"] for h in halfs if h["net"] < 0]
    return dict(series=series, halfs=halfs, total=round(cum, 2), max_dd=round(mdd, 2),
                n=len(pts), neg_cells=neg, start=pts[0][0], end=pts[-1][0])


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {"books": [], "split": None}

    # the 2026-09-13 cut between the two eras, drawn as a marker on the curve
    cut = None
    for era in ("is", "oos"):
        d = E[era]
        cut = cut or None

    for name, swing, over, parent, label in BOOKS:
        rec = collect(sim, E, parent, swing, over)
        rec["key"] = name
        rec["label"] = label
        out["books"].append(rec)
        print("%-32s n=%4d  total=%+9.2fR  maxDD=%5.2fR  neg=%s"
              % (name, rec["n"], rec["total"], rec["max_dd"], rec["neg_cells"] or "NONE"))

    # the era boundary timestamp, for the marker
    d_is = E["is"]
    o = sim(d_is["c1h"], get_swings(d_is, "sw10"), d_is["c15"], d_is["sw15"],
            fine_ltf=d_is["fine"], **EXPERIMENTS["fsent_champ_long"]["params"])
    ts = [int(t["entry_ts"]) for t in o["ltf_trades"]]
    out["split"] = max(ts) if ts else None
    print("\nIS/OOS boundary ts:", out["split"])

    with open("_equity_data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote _equity_data.json")
    for b in out["books"]:
        print("\n%s" % b["label"])
        for h in b["halfs"]:
            flag = "  <-- NEGATIVE" if h["net"] < 0 else ""
            print("   %-9s n=%4d  %+8.2fR%s" % (h["cell"], h["n"], h["net"], flag))


if __name__ == "__main__":
    main()