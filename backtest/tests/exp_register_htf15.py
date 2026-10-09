import json
import sys

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import get_swings, _net_dd          # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from src.btc.btc_routes import (_compute_swings, _trade_costs, _net_stats)  # noqa: E402
from src.btc.btc_engine import trade_stats              # noqa: E402

PARENT = "fsent_champ_long"
HTF_MB = 15


def main():
    sim = build_family_module()
    out = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = _compute_swings(d["f1h"], "continuous", min_bars=HTF_MB)
        o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"],
                **{**EXPERIMENTS[PARENT]["params"]})
        tr = o["ltf_trades"]
        _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
        n = len(tr)
        net = _net_stats(trade_stats(tr), tr)["net_total_r"]
        dd = _net_dd(tr)
        wins = sum(1 for t in tr
                   if float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)) > 0)
        wr = round(100.0 * wins / n, 1)
        print("  %-4s n=%3d  net=%+8.2f  dd=%6.2f  WR=%.1f%%"
              % (era.upper(), n, round(net, 2), round(dd, 2), wr))
        out[era] = {"n": n, "net": round(net, 2), "dd": round(dd, 2), "win": wr / 100.0}

    pins = {
        "n": out["is"]["n"], "net": out["is"]["net"], "dd_net": out["is"]["dd"],
        "win": out["is"]["win"],
        "oos_n": out["oos"]["n"], "oos_net": out["oos"]["net"],
        "oos_dd_net": out["oos"]["dd"], "oos_win": out["oos"]["win"],
    }
    print()
    print("PARENT (htf min_bars=10) pins:")
    print("  ", json.dumps(EXPERIMENTS[PARENT]["pins"]))
    print()
    print("PINS TO REGISTER for fsent_champ_long_htf15:")
    print("  ", json.dumps(pins))
    with open("_htf15_pins.json", "w", encoding="utf-8") as f:
        json.dump(pins, f, indent=2)
    print("\nwrote _htf15_pins.json")
    print("\nNOTE: the HTF swing series is NOT a registry param - it is the `swing`")
    print("field, which selects which precomputed series the harness feeds the engine")
    print("in slot 2. A new HTF length therefore needs a NEW swing series registered")
    print("in run_experiment.get_data, not just a params edit. See the doc.")


if __name__ == "__main__":
    main()