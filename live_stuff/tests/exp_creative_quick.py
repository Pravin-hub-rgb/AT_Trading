"""Quick test of 3 new creative idea modes."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs, _load_fine_1m, _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as engine

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]


def stats(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1)
    py = {}
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        yr = d[:4]
        py[yr] = py.get(yr, 0) + float(t["r_multiple"])
    is_r = sum(v for k, v in py.items() if k < "2025")
    oos_r = sum(v for k, v in py.items() if k >= "2025")
    is_n = sum(1 for t in tr if (t.get("exit_date") or "")[:4] < "2025")
    oos_n = sum(1 for t in tr if (t.get("exit_date") or "")[:4] >= "2025")
    return {"n": len(tr), "gross": g, "wr": wr, "dd": dd, "mx": mx,
            "is_r": is_r, "oos_r": oos_r, "is_n": is_n, "oos_n": oos_n,
            "py": py}


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    print("data ready (%0.0fs)" % (time.time() - t0))

    hdr = "  %-24s %4s  %+6s %+6s  %4s %4s  %5s  %s" % (
        "Mode", "Tr", "IS_R", "OOS_R", "IS", "OOS", "WR", "PY")
    print("\n" + hdr)
    print("  " + "-" * 80)

    def run(mode, ct=58.0, cb=10, **kw):
        try:
            b = {**BASE, "mode": mode, "chop_thresh": ct, "cooldown_bars": cb, **kw}
            t1 = time.time()
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"]
            s = stats(tr)
            dt = time.time() - t1
            py_str = " ".join("%s:%+.0f" % (k, v) for k, v in sorted(s["py"].items()))
            print("  %-24s %4d  %+6.1f %+6.1f  %4d %4d  %4.0f%%  %s  (%.0fs)" % (
                mode, s["n"], s["is_r"], s["oos_r"], s["is_n"], s["oos_n"],
                s["wr"], py_str, dt))
            return s
        except Exception as e:
            print("  %-24s  ERROR: %s" % (mode, e))
            return None

    # Baseline
    run("b2_vs_flip_chop", ct=58.0, cb=10)

    # New ideas
    print("\n--- NEW IDEAS ---")
    run("session")
    run("session_flip")
    run("entropy")
    run("entropy_inv")
    run("fd")
    run("fd_inv")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
