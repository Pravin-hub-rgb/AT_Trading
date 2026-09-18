"""CRAZE sweep #1: halt (max_consecutive_losses) + mb_1h — shipped engine only.

Both knobs are engine params, so this runs the COMMITTED engine unchanged
(zero look-ahead risk). Anchor: halt=3 / mb_1h=20 -> 340t / +225.3R coarse.
Rule: a knob change must beat the anchor on BOTH halves (2023-24 / 2025-26)
and not worsen max-DD materially.
"""
import sys, time
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))       # live_stuff
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt

_p = dict(get_v18_params(INSTRUMENT)); _p.update(V18_ENGINE)
BASE = {k: _p[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _p}
MB15 = SWING["min_bars_15m"]


def stats(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    py = defaultdict(float)
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        py[d[:4]] += float(t["r_multiple"])
    h1 = py.get("2023", 0.0) + py.get("2024", 0.0)
    h2 = py.get("2025", 0.0) + py.get("2026", 0.0)
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1)
    return {"n": len(tr), "gross": g, "wr": wr, "dd": dd, "mx": mx,
            "h1": h1, "h2": h2, "py": dict(py)}


def run(c1h, sw1h, c15, sw15, over):
    kw = dict(BASE); kw.update(over)
    r = simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15, fine_ltf=[], **kw)
    tr = r["ltf_trades"] if isinstance(r, dict) else r
    return stats(tr)


def show(tag, s):
    print("  %-18s %4dt %+8.1fR  WR %4.1f%%  DD %5.1f  streak %2d  H1 %+7.1f H2 %+7.1f  %s"
          % (tag, s["n"], s["gross"], s["wr"], s["dd"], s["mx"], s["h1"], s["h2"],
             {k: round(v, 1) for k, v in sorted(s["py"].items())}))


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    chains = {}
    for mb in (14, 20, 28):
        chains[mb] = _compute_swings(f1h, "continuous", min_bars=mb)
        print("mb_1h=%d: %d swings" % (mb, len(chains[mb])))
    print("(%0.0fs)\n" % (time.time() - t0))

    print("=== ANCHOR (must be 340t / +225.3R) ===")
    show("halt=3 mb1h=20", run(c1h, chains[20], c15, sw15, {}))

    print("\n=== HALT SWEEP (mb_1h=20) ===")
    for h in (1, 2, 3, 4, 5, 6, 8):
        show("halt=%d" % h, run(c1h, chains[20], c15, sw15,
                                {"max_consecutive_losses": h}))

    print("\n=== MB_1H SWEEP (halt=3) ===")
    for mb in (14, 20, 28):
        show("mb_1h=%d" % mb, run(c1h, chains[mb], c15, sw15, {}))

    print("\n(sweep done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
