"""EXP Creative Ideas: Test all 12 brainstorm ideas against baseline.

Tests session-based, entropy, fractal dimension modes natively in engine.
Also tests with union+mag3+wknd+bm05 filters (current champion).
"""
import sys, time, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs, _load_fine_1m, _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as engine
from test_experiments_craze import build_module as build_craze

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]


def _net(tr, g):
    rs = [float(t["r_multiple"]) for t in tr]
    c2, _ = _trade_costs(tr, g["fee_pct"], 0.0, g["entry_slip_pct"], g["exit_slip_pct"])
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return sum(rs) - c2 - f


def stats(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    py = defaultdict(float)
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        py[d[:4]] += float(t["r_multiple"])
    return {"n": len(tr), "gross": g, "rs": rs, "wr": wr, "dd": dd, "mx": mx,
            "h1": py.get("2023", 0) + py.get("2024", 0),
            "h2": py.get("2025", 0) + py.get("2026", 0),
            "py": dict(py), "pf": pf}


def split_is_oos(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    is_trades, oos_trades = [], []
    for t, r in zip(tr, rs):
        d = t.get("exit_date") or t.get("entry_date") or ""
        yr = int(d[:4]) if d[:4].isdigit() else 0
        if yr >= 2025:
            oos_trades.append(r)
        else:
            is_trades.append(r)
    is_r = sum(is_trades)
    oos_r = sum(oos_trades)
    is_n = len(is_trades)
    oos_n = len(oos_trades)
    is_wr = 100.0 * len([x for x in is_trades if x > 0]) / max(is_n, 1)
    oos_wr = 100.0 * len([x for x in oos_trades if x > 0]) / max(oos_n, 1)
    return is_r, oos_r, is_n, oos_n, is_wr, oos_wr


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    print("data ready (%0.0fs)" % (time.time() - t0))

    # ---- PART 1: Native engine modes (no CRAZE) ----
    print("\n=== PART 1: NEW IDEAS — RAW ENGINE ===")
    print("  %-22s %5s  %6s %6s  %5s %5s  %7s %7s" % (
        "Mode", "Tr", "IS_R", "OOS_R", "IS_N", "OOS_N", "IS_WR", "OOS_WR"))
    print("  " + "-" * 78)

    # Baseline: b2_vs_flip_chop
    b0 = {**BASE, "mode": "b2_vs_flip_chop", "chop_thresh": 58.0, "cooldown_bars": 10}
    r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b0)
    tr0 = r0["ltf_trades"]
    is_r0, oos_r0, is_n0, oos_n0, is_wr0, oos_wr0 = split_is_oos(tr0)
    s0 = stats(tr0)
    print("  %-22s %5d  %+6.1f %+6.1f  %5d %5d  %6.1f %6.1f" % (
        "b2_vs_flip_chop (base)", s0["n"], is_r0, oos_r0, is_n0, oos_n0, is_wr0, oos_wr0))

    # New ideas to test
    ideas = [
        ("session",          58.0, "Asia→B2, LonNY→flip"),
        ("session_flip",     58.0, "Asia→flip, LonNY→B2"),
        ("entropy",          58.0, "Low ent→B2, High→flip"),
        ("entropy_inv",      58.0, "Low ent→flip, High→B2"),
        ("fd",               58.0, "High FD→B2, Low→flip"),
        ("fd_inv",           58.0, "High FD→flip, Low→B2"),
    ]

    results = []
    for mode, ct, desc in ideas:
        try:
            b = {**BASE, "mode": mode, "chop_thresh": ct, "cooldown_bars": 10}
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"]
            s = stats(tr)
            is_r, oos_r, is_n, oos_n, is_wr, oos_wr = split_is_oos(tr)
            print("  %-22s %5d  %+6.1f %+6.1f  %5d %5d  %6.1f %6.1f" % (
                mode, s["n"], is_r, oos_r, is_n, oos_n, is_wr, oos_wr))
            results.append({"mode": mode, "desc": desc, "n": s["n"],
                          "is_r": round(is_r, 1), "oos_r": round(oos_r, 1),
                          "is_n": is_n, "oos_n": oos_n,
                          "is_wr": round(is_wr, 1), "oos_wr": round(oos_wr, 1)})
        except Exception as e:
            print("  %-22s  ERROR: %s" % (mode, e))

    # ---- PART 2: Sweep chop_thresh for best modes ----
    print("\n=== PART 2: CHOP THRESH SWEEP ===")
    print("  %-22s %-6s %5s  %6s %6s  %5s %5s" % (
        "Mode", "CT", "Tr", "IS_R", "OOS_R", "IS_N", "OOS_N"))
    print("  " + "-" * 70)

    sweep_modes = ["session", "session_flip", "entropy", "entropy_inv", "fd", "fd_inv"]
    sweep_cts = [45, 50, 55, 58, 61, 65, 70]
    best_oos = -999
    best_cfg = None

    for mode in sweep_modes:
        for ct in sweep_cts:
            try:
                b = {**BASE, "mode": mode, "chop_thresh": float(ct), "cooldown_bars": 10}
                r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
                tr = r["ltf_trades"]
                is_r, oos_r, is_n, oos_n, is_wr, oos_wr = split_is_oos(tr)
                marker = ""
                if oos_r > best_oos and is_n >= 30:
                    best_oos = oos_r
                    best_cfg = (mode, ct)
                    marker = " <-- BEST"
                if oos_r > -20 or marker:
                    print("  %-22s %-6d %5d  %+6.1f %+6.1f  %5d %5d%s" % (
                        mode, ct, is_n+oos_n, is_r, oos_r, is_n, oos_n, marker))
            except Exception:
                pass

    if best_cfg:
        print("\n  BEST: mode=%s ct=%d  OOS_R=%+.1f" % (best_cfg[0], best_cfg[1], best_oos))

    # ---- PART 3: Test with CRAZE + union filters (champion context) ----
    print("\n=== PART 3: WITH CRAZE FILTERS (mag_ratio + wknd + bm05) ===")
    print("  %-22s %5s  %6s %6s  %5s %5s  %6s %6s" % (
        "Mode", "Tr", "IS_R", "OOS_R", "IS_N", "OOS_N", "IS_WR", "OOS_WR"))
    print("  " + "-" * 78)

    OPT = dict(exp_mltf=True, exp_persist=2, chop_thresh=55.0, cooldown_bars=10)
    # union baseline
    sim_craze = build_craze()
    r_union = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine,
                        **{**BASE, **OPT, "mode": "union",
                           "mag_ratio": 1.9, "exp_wknd_skip": True,
                           "exp_bm05": True})
    tr_u = r_union["ltf_trades"]
    s_u = stats(tr_u)
    is_r_u, oos_r_u, is_n_u, oos_n_u, is_wr_u, oos_wr_u = split_is_oos(tr_u)
    print("  %-22s %5d  %+6.1f %+6.1f  %5d %5d  %6.1f %6.1f" % (
        "union+filters (king)", s_u["n"], is_r_u, oos_r_u, is_n_u, oos_n_u, is_wr_u, oos_wr_u))

    for mode in ["session", "session_flip", "entropy", "entropy_inv", "fd", "fd_inv"]:
        for ct in [50, 55, 58, 61]:
            try:
                b = {**BASE, **OPT, "mode": mode, "chop_thresh": float(ct),
                     "mag_ratio": 1.9, "exp_wknd_skip": True, "exp_bm05": True}
                r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
                tr = r["ltf_trades"]
                s = stats(tr)
                is_r, oos_r, is_n, oos_n, is_wr, oos_wr = split_is_oos(tr)
                marker = ""
                if oos_r > oos_r_u:
                    marker = " <-- BEATS KING"
                print("  %-22s %5d  %+6.1f %+6.1f  %5d %5d  %6.1f %6.1f%s" % (
                    mode+" ct=%d" % ct, s["n"], is_r, oos_r, is_n, oos_n, is_wr, oos_wr, marker))
            except Exception as e:
                print("  %-22s  ERROR: %s" % (mode+" ct=%d" % ct, e))

    out = {"raw_ideas": results, "best_raw": best_cfg}
    (ROOT / "backtest/tests/_creative_results.json").write_text(json.dumps(out, indent=1))
    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
