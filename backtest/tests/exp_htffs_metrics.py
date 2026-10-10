"""Full metrics for every book in the HTF-FS comparison, both eras.

The grid printed n, net, drawdown and a p-value. That is not enough to judge
anything and it is not what the owner has been reading on /results, which shows
win rate, ulcer and recovery. This prints the same shape of numbers for the new
arms so they can be placed next to the books already on that page.

Every field here is defined in HTF_METRICS_EXPLAINED.md, which exists because
four new terms arrived in one answer and none of them were explained.
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")

from progress import Announce, Bar                  # noqa: E402
from exp_tf_family import build_family_module      # noqa: E402
from run_experiment import net_r, get_swings        # noqa: E402
from exp_signal_metrics import load_era             # noqa: E402
from experiment_registry import EXPERIMENTS         # noqa: E402

BOOKS = [
    ("fsent_champ_long", "sw10", "SHIPPING"),
    ("fsent_champ_long_mcloff", "sw10", ""),
    ("fsent_champ_long_htffs", "sw10", "NEW - flip bucket on FS"),
    ("fsent_champ_long_htf15_htffs", "htf15", "NEW - flip FS, htf15 swing"),
    ("fsent_sig_multi_htffs", "sw10", "NEW - sig_multi, flip FS"),
    ("fsent_champ_long_htfesmcl4", "sw10", "earlier htf_fs=all arm"),
    ("fsent_champ_long_htf15", "htf15", ""),
]


def half(d):
    return d[:4] + "H" + ("1" if int(d[5:7]) <= 6 else "2")


def metrics(rs):
    """Everything the owner reads on /results, plus the two they do not."""
    if not rs:
        return None
    n = len(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gw = sum(wins)
    gl = -sum(losses)
    cum = pk = mdd = 0.0
    under = longest = cur = 0
    streak = worst_streak = cur_streak = 0
    ulc = []
    for r in rs:
        cum += r
        pk = max(pk, cum)
        dd = pk - cum
        mdd = max(mdd, dd)
        ulc.append(dd)
        if cum < pk:
            under += 1
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
        if r <= 0:
            cur_streak += 1
            worst_streak = max(worst_streak, cur_streak)
        else:
            cur_streak = 0
    avg_ulc = sum(ulc) / len(ulc)
    return {
        "n": n,
        "net": round(sum(rs), 2),
        "win_pct": round(100.0 * len(wins) / n, 1),
        "avg_win": round(gw / len(wins), 3) if wins else 0.0,
        "avg_loss": round(-gl / len(losses), 3) if losses else 0.0,
        "pf": round(gw / gl, 3) if gl > 0 else float("inf"),
        "expectancy": round(sum(rs) / n, 4),
        "max_dd": round(mdd, 2),
        "dd_pct_of_net": round(100.0 * mdd / sum(rs), 1) if sum(rs) > 0 else 0.0,
        "ulcer": round(avg_ulc, 2),
        "uw_pct": round(100.0 * under / n, 1),
        "longest_uw": longest,
        "worst_loss_streak": worst_streak,
    }


def main():
    Announce("building engine, loading eras, measuring full metrics",
             "~5 min for seven books across both eras")
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    nulls = json.load(open("_null_audit.json", encoding="utf-8"))
    pmap = {}
    for r in nulls["rows"]:
        pmap.setdefault(r["book"], {})[r["era"]] = r

    bar = Bar(len(BOOKS), "full metrics")
    out = {}

    for key, swing, note in BOOKS:
        params = dict(EXPERIMENTS[key]["params"])
        rec = {}
        for era in ("is", "oos"):
            d = E[era]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **params)
            allt = o["ltf_trades"]
            closed = [t for t in allt if t.get("outcome") != "open"]
            rs = [net_r([t]) for t in closed]
            m = metrics(rs)
            m["n_open"] = len(allt) - len(closed)
            ph = defaultdict(list)
            for t, r in zip(closed, rs):
                ph[half(t["entry_date"])].append(r)
            m["neg_cells"] = sorted(c for c, v in ph.items() if sum(v) < 0)
            m["n_neg"] = len(m["neg_cells"])
            rec[era] = m
        pk = pmap.get(key, {})
        rec["p_is"] = pk.get("is", {}).get("p")
        rec["p_oos"] = pk.get("oos", {}).get("p")
        rec["note"] = note
        rec["swing"] = swing
        out[key] = rec
        bar.update(key)

    def f(v, w=7, d=2):
        return ("%*.*f" % (w, d, v)) if isinstance(v, (int, float)) else "%*s" % (w, "-")

    for era, title in (("is", "IN SAMPLE"), ("oos", "OUT OF SAMPLE (reused 2021-22, NOT a holdout)")):
        print()
        print("=" * 132)
        print(title)
        print("=" * 132)
        print("  %-28s %5s %8s %6s %7s %7s %6s %8s %7s %6s %6s"
              % ("book", "n", "net", "win%", "avgW", "avgL", "PF", "expect",
                 "maxDD", "ulcer", "neg"))
        print("  " + "-" * 128)
        for key, _s, note in BOOKS:
            m = out[key][era]
            print("  %-28s %5d %8s %6s %7s %7s %6s %8s %7s %6s %6d"
                  % (key[:28], m["n"], f(m["net"], 8), f(m["win_pct"], 6, 1),
                     f(m["avg_win"], 7, 3), f(m["avg_loss"], 7, 3),
                     f(m["pf"], 6), f(m["expectancy"], 8, 3),
                     f(m["max_dd"], 7), f(m["ulcer"], 6),
                     m["n_neg"]))

    print()
    print("=" * 132)
    print("THE OWNER'S THREE GATES, side by side")
    print("=" * 132)
    print("  %-28s %8s %8s %11s %9s %s"
          % ("book", "dd IS", "dd OOS", "neg cells", "worstLS", "p IS / p OOS"))
    print("  " + "-" * 124)
    for key, _s, note in BOOKS:
        a, b = out[key]["is"], out[key]["oos"]
        dd_ok = max(a["max_dd"], b["max_dd"]) <= 29.0
        print("  %-28s %8.2f %8.2f %5d + %-3d %9d   %s"
              % (key[:28], a["max_dd"], b["max_dd"], a["n_neg"], b["n_neg"],
                 max(a["worst_loss_streak"], b["worst_loss_streak"]),
                 ("%.4f / %.4f" % (out[key]["p_is"], out[key]["p_oos"]))
                 if out[key]["p_is"] is not None else "not tested"))
        print("  %-28s   drawdown %-22s  negative half-years: IS %d, OOS %d"
              % ("", "WITHIN 29R budget" if dd_ok else "*** OVER the 29R ceiling ***",
                 a["n_neg"], b["n_neg"]))

    json.dump(out, open("_htffs_metrics.json", "w", encoding="utf-8"), indent=1)
    print("\n  wrote _htffs_metrics.json")
    bar.close("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())