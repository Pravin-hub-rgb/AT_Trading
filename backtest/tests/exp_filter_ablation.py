"""Filter ablation: where do the 300+ trades go?

Runs union ct=55 on IS (2023-2026) and true OOS (2021-2022),
adding one filter at a time, reporting trade count + net R at each stage.
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs, _load_fine_1m, _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as engine
from test_experiments_craze import build_module as build_craze
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]

STAGES = [
    ("0 raw (union ct=55)",              {}),
    ("1 + persist=2",                    {"exp_persist": 2}),
    ("2 + mltf",                         {"exp_persist": 2, "exp_mltf": True}),
    ("3 + swing_ratio=3",                {"exp_persist": 2, "exp_mltf": True,
                                           "exp_min_swing_ratio": 3.0}),
    ("4 + skip_weekend",                 {"exp_persist": 2, "exp_mltf": True,
                                           "exp_min_swing_ratio": 3.0,
                                           "exp_skip_weekend": 1}),
    ("5 + bias_mom=0.5 (FULL CRAZE)",    {"exp_persist": 2, "exp_mltf": True,
                                           "exp_min_swing_ratio": 3.0,
                                           "exp_skip_weekend": 1,
                                           "exp_bias_momentum_min": 0.5}),
    ("6 + dual gate (dualunion)",         {"exp_persist": 2, "exp_mltf": True,
                                           "exp_min_swing_ratio": 3.0,
                                           "exp_skip_weekend": 1,
                                           "exp_bias_momentum_min": 0.5,
                                           "exp_union_dual_only": 1}),
]


def run(sim, c1h, sw1h, c15, sw15, fine, extra):
    p = {**BASE, "mode": "union", "chop_thresh": 55.0,
         "cooldown_bars": 10, **extra}
    r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **p)
    tr = r["ltf_trades"]
    rs = [float(t["r_multiple"]) for t in tr]
    return len(rs), sum(rs)


def main():
    t0 = time.time()
    sim = build_craze()

    print("Loading IS...")
    (c15i, f15i), (c1hi, f1hi) = load_candles()
    sw15i = _compute_swings(f15i, "continuous", min_bars=MB15)
    sw1hi = _compute_swings(f1hi, "continuous", min_bars=SWING["min_bars_1h"])
    finei = _load_fine_1m(c15i[0]["ts"], c15i[-1]["ts"], symbol=INSTRUMENT)

    print("Loading OOS 2021-2022...")
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=MB15)
    sw1ho = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])

    print("\n" + "=" * 100)
    print("  FILTER ABLATION: union ct=55 — each stage adds one filter")
    print("=" * 100)
    print("  %-36s | %18s | %18s | %s" % (
        "Stage", "IS 2023-2026", "OOS 2021-2022", "trades cut (IS)"))
    print("  " + "-" * 98)

    prev_is = None
    for name, extra in STAGES:
        ni, gi = run(sim, c1hi, sw1hi, c15i, sw15i, finei, extra)
        no, go = run(sim, c1ho, sw1ho, c15o, sw15o, fineo, extra)
        cut_str = "-" if prev_is is None else "(-%d)" % (prev_is - ni)
        print("  %-36s | %4dt %+8.1fR | %4dt %+8.1fR | %s" % (
            name, ni, gi, no, go, cut_str))
        prev_is = ni

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
