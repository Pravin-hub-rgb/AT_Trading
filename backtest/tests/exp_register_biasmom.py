import json
import sys

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import get_swings, _net_dd          # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats  # noqa: E402
from src.btc.btc_engine import trade_stats              # noqa: E402

PARENT = "fsent_champ_long"
ARMS = {
    "fsent_champ_long_biasmom05": ("sw10", 0.5),
    "fsent_champ_long_htf15_biasmom05": ("htf15", 0.5),
}


def pins_for(swing, biasmom):
    sim = build_family_module()
    out = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, swing)
        p = {**EXPERIMENTS[PARENT]["params"], "exp_bias_momentum_min": biasmom}
        o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
        tr = o["ltf_trades"]
        _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
        n = len(tr)
        net = _net_stats(trade_stats(tr), tr)["net_total_r"]
        dd = _net_dd(tr)
        wins = sum(1 for t in tr
                   if float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)) > 0)
        print("  %-4s n=%3d  net=%+8.2f  dd=%6.2f  WR=%.1f%%"
              % (era.upper(), n, round(net, 2), round(dd, 2), 100.0 * wins / n))
        out[era] = {"n": n, "net": round(net, 2), "dd": round(dd, 2),
                    "win": round(100.0 * wins / n, 1) / 100.0}
    return {"n": out["is"]["n"], "net": out["is"]["net"], "dd_net": out["is"]["dd"],
            "win": out["is"]["win"], "oos_n": out["oos"]["n"],
            "oos_net": out["oos"]["net"], "oos_dd_net": out["oos"]["dd"],
            "oos_win": out["oos"]["win"]}


def main():
    all_pins = {}
    for name, (swing, bm) in ARMS.items():
        print("=== %s   (swing=%s, exp_bias_momentum_min=%s) ===" % (name, swing, bm))
        all_pins[name] = {"swing": swing, "bias_momentum_min": bm,
                          "pins": pins_for(swing, bm)}
        print()
    print("PARENT pins:")
    print("  ", json.dumps(EXPERIMENTS[PARENT]["pins"]))
    print()
    for k, v in all_pins.items():
        print("%s -> swing=%s  params add exp_bias_momentum_min=%s"
              % (k, v["swing"], v["bias_momentum_min"]))
        print("   pins: %s" % json.dumps(v["pins"]))
    with open("_biasmom_pins.json", "w", encoding="utf-8") as f:
        json.dump(all_pins, f, indent=2)
    print("\nwrote _biasmom_pins.json")


if __name__ == "__main__":
    main()