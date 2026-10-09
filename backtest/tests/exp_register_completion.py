import json
import sys

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from exp_period_autopsy import dd_of                    # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats  # noqa: E402
from src.btc.btc_engine import trade_stats              # noqa: E402

ARMS = {
    "fsent_champ_long_mcloff_htf15": ("htf15", {"max_consecutive_losses": 0}),
    "fsent_champ_long_mcl4_htf15": ("htf15", {"max_consecutive_losses": 4}),
    "fsent_champ_long_cap21": ("sw10", {"exp_cap_days": 21}),
}


def pins(sim, d, swing, over):
    p = {**EXPERIMENTS["fsent_champ_long"]["params"], **over}
    o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
    tr = [dict(t) for t in o["ltf_trades"]]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n = len(tr)
    net = _net_stats(trade_stats(tr), tr)["net_total_r"]
    done = [t for t in tr if t.get("outcome") != "open"]
    dd = dd_of([net_r([t]) for t in done])
    wins = sum(1 for t in done if net_r([t]) > 0)
    return dict(n=n, net=round(net, 2), dd_net=round(dd, 2),
                win=round(100.0 * wins / n, 1) / 100.0)


def main():
    sim = build_family_module()
    out = {}
    for name, (swing, over) in ARMS.items():
        pi = pins(sim, load_era("is"), swing, over)
        po = pins(sim, load_era("oos"), swing, over)
        full = {"n": pi["n"], "net": pi["net"], "dd_net": pi["dd_net"], "win": pi["win"],
                "oos_n": po["n"], "oos_net": po["net"],
                "oos_dd_net": po["dd_net"], "oos_win": po["win"]}
        print("%s  swing=%s  over=%s" % (name, swing, over))
        print("   IS  %d / %.2fR / dd %.2f / WR %.1f%%" % (pi["n"], pi["net"], pi["dd_net"], 100 * pi["win"]))
        print("   OOS %d / %.2fR / dd %.2f / WR %.1f%%" % (po["n"], po["net"], po["dd_net"], 100 * po["win"]))
        print("   pins: %s" % json.dumps(full))
        out[name] = dict(swing=swing, over=over, pins=full)
        print()
    with open("_completion_pins.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote _completion_pins.json")


if __name__ == "__main__":
    main()