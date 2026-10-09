"""Register fsent_sig_multi - the sig book's filters with concurrency enabled.

Pins are computed here with the PIN CONVENTION (n = raw len(tr), net via
_net_stats, dd via _net_dd skipping open trades), which is the same chain
exp_fastcheck uses. It is called out because three harnesses got it wrong this
week and produced false mismatches with identical nets.

Run:  cd backtest/tests
      python -u exp_register_sig_multi.py          # compute pins only
"""
import json
import sys

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import get_swings, _net_dd          # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats  # noqa: E402
from src.btc.btc_engine import trade_stats              # noqa: E402

PARENT = "fsent_sig_full"


def main():
    sim = build_family_module()
    out = {}
    for era in ("is", "oos"):
        d = load_era(era)
        sw = get_swings(d, EXPERIMENTS[PARENT]["swing"])
        p = dict(EXPERIMENTS[PARENT]["params"])
        p["max_positions"] = 0
        o = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
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
    print("PARENT pins for comparison:")
    print("  ", json.dumps(EXPERIMENTS[PARENT]["pins"]))
    print()
    print("PINS TO REGISTER:")
    print("  ", json.dumps(pins))
    with open("_sig_multi_pins.json", "w", encoding="utf-8") as f:
        json.dump(pins, f, indent=2)
    print("\nwrote _sig_multi_pins.json")


if __name__ == "__main__":
    main()