"""Verify + pin the max_consecutive_losses arms.

THE FINDING
-----------
champ_long ships max_consecutive_losses=3. That single integer is the whole
negative-cell story:

    limit 0/off   912t  +837.50R  ddIS 15.13  0 negative cells
    limit 3       839t  +772.96R  ddIS 13.42  1 negative cell  <- SHIPPED
    limit 4       872t  +817.10R  ddIS 15.06  0 negative cells

Turning the loss-run cutoff OFF gives MORE net (+64.5R), MORE trades, roughly the
same drawdown, and no negative half-year. The cutoff is not protecting the book;
it is cutting winners. A 3-loss cutoff on a book with a +0.9R median trade stops
the book right before it takes the recovery trade that follows every streak.

Also found here: chop_thresh is a DEAD KNOB in this architecture - every value
from 46 to 70 produces byte-identical output on both books.
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from exp_flip_period import instrument, SEED             # noqa: E402
from exp_period_autopsy import half, period_control, dd_of  # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats  # noqa: E402
from src.btc.btc_engine import trade_stats               # noqa: E402

ARMS = [
    ("champ_long mcl=4", "fsent_champ_long", "sw10", {"max_consecutive_losses": 4}),
    ("champ_long mcl=off", "fsent_champ_long", "sw10", {"max_consecutive_losses": 0}),
    ("htf_fs=all + mcl=4", "fsent_champ_long", "sw10",
     {"exp_htf_fs_entry": "all", "max_consecutive_losses": 4}),
    ("htf15 (proper base)", "fsent_champ_long", "htf15", {}),
]


def run(sim, era, d, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    return [t for t in o["ltf_trades"] if t.get("outcome") != "open"]


def pins_for(sim, d, book, swing, over):
    p = {**EXPERIMENTS[book]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    tr = [dict(t) for t in o["ltf_trades"]]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n = len(tr)
    net = _net_stats(trade_stats(tr), tr)["net_total_r"]
    dd = dd_of([net_r([t]) for t in tr if t.get("outcome") != "open"])
    wins = sum(1 for t in tr if t.get("outcome") != "open"
               and net_r([t]) > 0)
    return dict(n=n, net=round(net, 2), dd_net=round(dd, 2),
                win=round(100.0 * wins / n, 1) / 100.0)


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    out = {}

    for label, book, swing, over in ARMS:
        print("=" * 96)
        print("  %s" % label)
        print("=" * 96)
        tot = {}
        for era in ("is", "oos"):
            base_tr = run(sim, era, E[era], book, swing, {})
            arm_tr = run(sim, era, E[era], book, swing, over)
            res, _ = period_control(base_tr, arm_tr)
            bn = sum(net_r([t]) for t in base_tr)
            an = sum(net_r([t]) for t in arm_tr)
            print("  %-4s base %4dt /%+9.2fR   arm %4dt /%+9.2fR   dNet %+9.2fR"
                  % (era.upper(), len(base_tr), bn, len(arm_tr), an, an - bn))
            if res is None:
                print("         IDENTICAL SET")
                continue
            print("         survivors %d (%+.2fR)  NEW %d (%+.2fR)  DROPPED %d (%+.2fR)"
                  % (res["surv"], res["surv_cost"], res["new"], res["new_sum"],
                     res["drop"], res["drop_sum"]))
            print("         b=%+8.4f  t=%+6.2f  se=%.4f  MDE=%.4f  b_boot=%+8.4f  => %s"
                  % (res["b"], res["t"], res["se"], res["mde"], res["b_boot"],
                     "SIGN HOLDS" if res["all_sign"] else
                     ("UNDERPOWERED" if res["mde"] > abs(res["b"]) else "SIGN FAILS")))
            tot[era] = res
        both = all(e in tot for e in ("is", "oos"))
        signs = sum(1 for e in tot if tot[e]["b"] > 0)
        hold = both and all(tot[e]["all_sign"] for e in tot)
        powered = both and all(tot[e]["mde"] < abs(tot[e]["b"]) for e in tot)
        print("  VERDICT: b>0 in %d/2 eras | %s%s\n"
              % (signs, "SURVIVES" if hold else "does NOT survive",
                 " + POWERED" if powered else " (underpowered)"))

        pi = pins_for(sim, E["is"], book, swing, over)
        po = pins_for(sim, E["oos"], book, swing, over)
        full = {"n": pi["n"], "net": pi["net"], "dd_net": pi["dd_net"], "win": pi["win"],
                "oos_n": po["n"], "oos_net": po["net"],
                "oos_dd_net": po["dd_net"], "oos_win": po["win"]}
        # half-year cells
        per = defaultdict(list)
        for era in ("is", "oos"):
            for t in run(sim, era, E[era], book, swing, over):
                per[half(t["entry_ts"])].append(net_r([t]))
        neg = sorted(c for c in per if sum(per[c]) < 0)
        print("  pins IS  %d / %.2fR / dd %.2f / WR %.1f%%" % (pi["n"], pi["net"], pi["dd_net"], 100 * pi["win"]))
        print("  pins OOS %d / %.2fR / dd %.2f / WR %.1f%%" % (po["n"], po["net"], po["dd_net"], 100 * po["win"]))
        print("  negative half-years: %s" % (neg or "NONE"))
        print("  pins dict: %s\n" % json.dumps(full))
        out[label] = dict(pins=full, neg=neg, period=tot, survives=hold, powered=powered)

    with open("_mcl_arms.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("wrote _mcl_arms.json")


if __name__ == "__main__":
    main()