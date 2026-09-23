"""EVERY METRIC for EVERY config — clean per-config blocks."""
import sys, time, math
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
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


def F(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    n = len(rs)
    if n == 0: return None
    gross = sum(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    nw = len(wins); nl = len(losses)
    wr = 100.0 * nw / n
    aw = sum(wins) / max(nw, 1)
    al = sum(losses) / max(nl, 1)
    awal = aw / max(abs(al), 1e-9)
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    exp = gross / n
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    mcl = mx
    mcw = 0; cw = 0
    for x in rs:
        if x > 0: cw += 1; mcw = max(mcw, cw)
        else: cw = 0
    mean_r = gross / n
    var_r = sum((x - mean_r) ** 2 for x in rs) / max(n - 1, 1)
    std_r = math.sqrt(var_r) if var_r > 0 else 1e-9
    sharpe = mean_r / std_r * math.sqrt(n)
    g_costs, _ = _trade_costs(tr, _P["fee_pct"], 0.0, _P["entry_slip_pct"], _P["exit_slip_pct"])
    funding = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            funding += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    costs = g_costs + funding
    net = gross - costs
    bars = [int(t.get("bars_held") or 0) for t in tr]
    avg_bars = sum(bars) / max(len(bars), 1)
    py = defaultdict(float); py_n = defaultdict(int)
    for t, r in zip(tr, rs):
        yr = (t.get("exit_date") or "")[:4]; py[yr] += r; py_n[yr] += 1
    is_r = sum(v for k, v in py.items() if k < "2025")
    oos_r = sum(v for k, v in py.items() if k >= "2025")
    is_n = sum(v for k, v in py_n.items() if k < "2025")
    oos_n = sum(v for k, v in py_n.items() if k >= "2025")
    ratio = is_r / max(oos_r, 0.01)
    sorted_rs = sorted(rs)
    median = sorted_rs[n // 2]
    neg_yrs = sum(1 for v in py.values() if v < 0)
    # avg win streak, avg loss streak
    win_streaks = []; lose_streaks = []; cs = 0; ls = 0
    for x in rs:
        if x > 0:
            cs += 1; ls = 0
            if cs == 1 and ls == 0: pass
        else:
            if cs > 0: win_streaks.append(cs)
            cs = 0; ls += 1
    if cs > 0: win_streaks.append(cs)
    if ls > 0: lose_streaks.append(ls)
    avg_win_streak = sum(win_streaks) / max(len(win_streaks), 1)
    avg_lose_streak = sum(lose_streaks) / max(len(lose_streaks), 1)
    return {
        "n": n, "gross": gross, "net": net, "costs": costs,
        "nw": nw, "nl": nl,
        "wr": wr, "aw": aw, "al": al, "awal": awal,
        "pf": pf, "exp": exp,
        "dd": dd, "mcl": mcl, "mcw": mcw,
        "sharpe": sharpe, "median": median,
        "avg_bars": avg_bars,
        "is_r": is_r, "oos_r": oos_r, "is_n": is_n, "oos_n": oos_n,
        "ratio": ratio, "neg_yrs": neg_yrs,
        "py": dict(py), "py_n": dict(py_n),
        "avg_win_streak": avg_win_streak, "avg_lose_streak": avg_lose_streak,
    }


def pr_block(label, s, tag=""):
    if not s: return
    py = s["py"]; py_n = s["py_n"]
    ov = "ANTI-OVERFIT" if s["ratio"] < 1.0 else "PASS" if s["ratio"] < 2.0 else "CAUTION" if s["ratio"] < 3.0 else "OVERFIT"
    print()
    print("  %s%s" % (label, tag))
    print("  " + "-" * 70)
    print("    Trades:          %d" % s["n"])
    print("    Winners:         %d  (%.1f%%)" % (s["nw"], s["wr"]))
    print("    Losers:          %d  (%.1f%%)" % (s["nl"], 100.0 - s["wr"]))
    print()
    print("    Gross R:         %+8.1f" % s["gross"])
    print("    Costs:           %8.1f" % s["costs"])
    print("    Net R:           %+8.1f" % s["net"])
    print()
    print("    Avg Win:         %+8.3f R" % s["aw"])
    print("    Avg Loss:        %8.3f R" % s["al"])
    print("    Win/Loss Ratio:  %8.2f" % s["awal"])
    print("    Expectancy:      %+8.3f R per trade" % s["exp"])
    print("    Profit Factor:   %8.2f" % s["pf"])
    print()
    print("    Max Drawdown:    %8.1f R" % s["dd"])
    print("    Max Consec Loss: %8d" % s["mcl"])
    print("    Max Consec Win:  %8d" % s["mcw"])
    print("    Avg Win Streak:  %8.1f" % s["avg_win_streak"])
    print("    Avg Lose Streak: %8.1f" % s["avg_lose_streak"])
    print()
    print("    Sharpe Ratio:    %8.2f" % s["sharpe"])
    print("    Median R:        %+8.3f" % s["median"])
    print("    Avg Bars Held:   %8.1f" % s["avg_bars"])
    print()
    print("    IS:   %+8.1f R  (%d trades)" % (s["is_r"], s["is_n"]))
    print("    OOS:  %+8.1f R  (%d trades)" % (s["oos_r"], s["oos_n"]))
    print("    Ratio: %6.2f   %s" % (s["ratio"], ov))
    print()
    print("    Year-by-Year:")
    for yr in ["2023", "2024", "2025", "2026"]:
        tag2 = "IS" if yr < "2025" else "OOS"
        yn = py_n.get(yr, 0)
        yr_wr = 100.0 * sum(1 for r in [py[yr]] if r > 0) / max(yn, 1) if yn > 0 else 0
        print("      %s (%s): %+7.1f R  %3d trades" % (yr, tag2, py.get(yr, 0), yn))
    print()


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"], symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    sim_craze = build_craze()
    print("data ready (%.0fs)" % (time.time() - t0))

    def run_raw(mode, ct=58, cb=10):
        b = {**BASE, "mode": mode, "chop_thresh": float(ct), "cooldown_bars": cb}
        return F(sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)["ltf_trades"])

    def run_filt(mode, ct=58):
        OPT = dict(exp_mltf=True, exp_persist=2, cooldown_bars=10,
                   exp_min_swing_ratio=3.0, exp_skip_weekend=1, exp_bias_momentum_min=0.5)
        b = {**BASE, **OPT, "mode": mode, "chop_thresh": float(ct)}
        return F(sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)["ltf_trades"])

    # ====================================================================
    # RAW
    # ====================================================================
    print("\n" + "#" * 80)
    print("#  RAW ENGINE — ALL CONFIGS")
    print("#" * 80)

    configs_raw = [
        ("b2_vs_flip_chop ct=58 cb=10",     "b2_vs_flip_chop", 58, 10, "PRODUCTION BASELINE"),
        ("b2_vs_flip_chop ct=65 cb=0",      "b2_vs_flip_chop", 65, 0, "BEST OOS RAW"),
        ("entropy ct=50",                   "entropy", 50, 10, "ENTROPY LOW CT — BEST NET R"),
        ("entropy ct=55",                   "entropy", 55, 10, ""),
        ("entropy ct=58",                   "entropy", 58, 10, ""),
        ("entropy ct=61",                   "entropy", 61, 10, "ENTROPY BEST OOS RATIO"),
        ("entropy ct=65",                   "entropy", 65, 10, ""),
        ("fd ct=50",                        "fd", 50, 10, ""),
        ("fd ct=55",                        "fd", 55, 10, ""),
        ("fd ct=58",                        "fd", 58, 10, "FD DEFAULT"),
        ("fd ct=65",                        "fd", 65, 10, ""),
        ("fd ct=70",                        "fd", 70, 10, "FD BEST OOS"),
        ("session ct=58",                   "session", 58, 10, "SESSION — CT INSENSITIVE"),
        ("entropy_inv ct=58",               "entropy_inv", 58, 10, "INVERTED — DO NOT USE"),
        ("fd_inv ct=58",                    "fd_inv", 58, 10, "INVERTED — DO NOT USE"),
        ("session_flip ct=58",              "session_flip", 58, 10, "INVERTED — DO NOT USE"),
    ]

    results_raw = []
    for label, mode, ct, cb, note in configs_raw:
        s = run_raw(mode, ct, cb)
        if s:
            pr_block(label, s, "  *** %s ***" % note if note else "")
            results_raw.append((label, s))

    # ====================================================================
    # FILTERED
    # ====================================================================
    print("\n" + "#" * 80)
    print("#  CRAZE FILTERED (min_swing=3.0, wknd_skip, bm05)")
    print("#" * 80)

    configs_filt = [
        ("union ct=55 +filt",               "union", 55, "PREVIOUS KING"),
        ("b2_vs_flip ct=58 +filt",          "b2_vs_flip_chop", 58, "BASELINE FILTERED"),
        ("entropy ct=50 +filt",             "entropy", 50, ""),
        ("entropy ct=55 +filt",             "entropy", 55, ""),
        ("entropy ct=58 +filt",             "entropy", 58, ""),
        ("entropy ct=61 +filt",             "entropy", 61, "NEW KING"),
        ("entropy ct=65 +filt",             "entropy", 65, ""),
        ("entropy ct=70 +filt",             "entropy", 70, ""),
        ("fd ct=50 +filt",                  "fd", 50, "BEST FD FILTERED"),
        ("fd ct=55 +filt",                  "fd", 55, ""),
        ("fd ct=58 +filt",                  "fd", 58, ""),
        ("session ct=58 +filt",             "session", 58, ""),
    ]

    results_filt = []
    for label, mode, ct, note in configs_filt:
        s = run_filt(mode, ct)
        if s:
            pr_block(label, s, "  *** %s ***" % note if note else "")
            results_filt.append((label, s))

    # ====================================================================
    # SUMMARY TABLE
    # ====================================================================
    print("\n" + "#" * 80)
    print("#  SUMMARY TABLE — SORTED BY OOS")
    print("#" * 80)
    print()
    print("  %-28s %4s  %7s %7s %5s  %5s %5s  %5s %6s %5s  %5s %5s  %5s  %s" % (
        "Config", "Tr", "Gross", "Net", "Costs",
        "IS", "OOS", "Ratio", "WR", "PF",
        "AvgW", "AvgL", "DD", "Verdict"))
    print("  " + "-" * 140)

    all_results = [(l, s, "RAW") for l, s in results_raw] + [(l, s, "FILT") for l, s in results_filt]
    all_sorted = sorted(all_results, key=lambda x: x[1]["oos_r"], reverse=True)

    for label, s, typ in all_sorted:
        ov = "ANTI" if s["ratio"] < 1.0 else "PASS" if s["ratio"] < 2.0 else "WARN" if s["ratio"] < 3.0 else "FIT"
        print("  %-28s %4d  %+7.1f %+7.1f %5.1f  %+5.1f %+5.1f  %5.2f %5.1f%% %5.2f  %+5.3f %+.3f  %5.1f  %s %s" % (
            label, s["n"], s["gross"], s["net"], s["costs"],
            s["is_r"], s["oos_r"], s["ratio"], s["wr"], s["pf"],
            s["aw"], s["al"], s["dd"], ov, typ))

    print("  " + "-" * 140)

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
