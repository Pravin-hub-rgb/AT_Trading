"""Smoke test: run each new mode on full data to verify correctness."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _load_fine_1m, _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as engine

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"], symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    print("data ready (%0.0fs)" % (time.time() - t0))

    def run(mode, ct=58.0):
        b = {**BASE, "mode": mode, "chop_thresh": ct, "cooldown_bars": 10}
        t1 = time.time()
        r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
        tr = r["ltf_trades"]
        n = len(tr)
        gross = sum(float(t["r_multiple"]) for t in tr)
        dt = time.time() - t1
        is_r = sum(float(t["r_multiple"]) for t in tr if (t.get("exit_date") or "")[:4] < "2025")
        oos_r = sum(float(t["r_multiple"]) for t in tr if (t.get("exit_date") or "")[:4] >= "2025")
        print("  %-20s  %3d tr  %+7.1fR (IS:%+.1f OOS:%+.1f)  (%.0fs)" % (
            mode, n, gross, is_r, oos_r, dt))

    print("\n--- Smoke test (full data) ---")
    run("b2_vs_flip_chop")
    run("session")
    run("session_flip")
    run("entropy")
    run("entropy_inv")
    run("fd")
    run("fd_inv")

    print("\n(done %.0fs total)" % (time.time() - t0))


if __name__ == "__main__":
    main()
