"""Champion truncation probe: champion_multi_sw10 (sw10, persist7, mltf) causal check."""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, EXPERIMENTS, fund
from src.btc.btc_routes import _trade_costs, _compute_swings, _load_fine_1m
from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import get_v18_params as gvp
from src.walker import FlowCandle

G = gvp(INSTRUMENT)
DAY = 86400


def main():
    data = get_data()
    sim = __import__("test_experiments_craze").build_module()
    params = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    (c15_all, f15_all), (c1h_all, f1h_all) = load_candles()
    full = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"], fine_ltf=data["fine"], **params)["ltf_trades"]
    c2, _ = _trade_costs(full, G["fee_pct"], 0.0, G["entry_slip_pct"], G["exit_slip_pct"])
    net = sum(float(t["r_multiple"]) for t in full) - c2 - fund(full)
    print("champion full: n=%d NET=%+.1f" % (len(full), net))

    def sig(t):
        return (int(t["entry_ts"]), t["dir"], float(t["entry_price"]), round(float(t["sl"]), 2))

    for days_back, tag in [(460, "T1~2025-06"), (170, "T2~2026-03")]:
        T = c1h_all[-1]["ts"] - days_back * DAY
        T -= T % 900
        guard = 3 * DAY
        c15t = [c for c in c15_all if c["ts"] <= T]
        c1ht = [c for c in c1h_all if c["ts"] <= T]
        f15t = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in c15t]
        f1ht = [FlowCandle(date=c["date"], open=c["open"], high=c["high"], low=c["low"], close=c["close"]) for c in c1ht]
        sw15t = _compute_swings(f15t, "continuous", min_bars=50)
        sw10t = _compute_swings(f1ht, "continuous", min_bars=10)
        finet = _load_fine_1m(c1h_all[0]["ts"], T, symbol=INSTRUMENT)
        trunc = sim(c1ht, sw10t, c15t, sw15t, fine_ltf=finet, **params)["ltf_trades"]
        pre = [t for t in full if int(t["entry_ts"]) < T - guard]
        kt = {sig(t): t for t in trunc}
        miss = [t for t in pre if sig(t) not in kt]
        rbad = sum(1 for t in pre if sig(t) in kt and int(t["exit_ts"]) < T - guard
                   and abs(float(t["r_multiple"]) - float(kt[sig(t)]["r_multiple"])) > 1e-6)
        print("[TRUNC %s] past=%d trunc=%d missing=%d R-mismatch=%d -> %s" %
              (tag, len(pre), len(trunc), len(miss), rbad,
               "CLEAN" if not miss and not rbad else "PROBLEM"))
        for t in miss[:3]:
            print("   LOST: %s %s R=%+.2f" % (t["entry_date"][:16], t["dir"], float(t["r_multiple"])))


if __name__ == "__main__":
    main()
