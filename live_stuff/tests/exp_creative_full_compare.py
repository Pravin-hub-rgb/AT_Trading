"""FULL COMPARISON: Every mode, every metric, side by side."""
import sys, time, json, math
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


def full_stats(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    n = len(rs)
    if n == 0:
        return None
    gross = sum(rs)
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    wr = 100.0 * len(wins) / n
    avg_win = sum(wins) / max(len(wins), 1)
    avg_loss = sum(losses) / max(len(losses), 1)
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    expectancy = gross / n
    mean_r = gross / n
    var_r = sum((x - mean_r) ** 2 for x in rs) / max(n - 1, 1)
    std_r = math.sqrt(var_r) if var_r > 0 else 1e-9
    sharpe = mean_r / std_r * math.sqrt(n)
    g_costs, f_costs = _trade_costs(tr, _P["fee_pct"], 0.0, _P["entry_slip_pct"], _P["exit_slip_pct"])
    funding = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0:
            funding += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    net_r = gross - g_costs - funding
    py = defaultdict(float); py_n = defaultdict(int)
    for t, r in zip(tr, rs):
        yr = (t.get("exit_date") or "")[:4]
        py[yr] += r; py_n[yr] += 1
    is_r = sum(v for k, v in py.items() if k < "2025")
    oos_r = sum(v for k, v in py.items() if k >= "2025")
    is_n = sum(v for k, v in py_n.items() if k < "2025")
    oos_n = sum(v for k, v in py_n.items() if k >= "2025")
    return {
        "n": n, "gross": round(gross, 1), "net": round(net_r, 1),
        "costs": round(g_costs + funding, 1),
        "wr": round(wr, 1), "dd": round(dd, 1), "mx": mx,
        "pf": round(pf, 2), "exp": round(expectancy, 3),
        "aw": round(avg_win, 3), "al": round(avg_loss, 3),
        "sharpe": round(sharpe, 2),
        "is_r": round(is_r, 1), "oos_r": round(oos_r, 1),
        "is_n": is_n, "oos_n": oos_n,
        "ratio": round(is_r / max(oos_r, 0.01), 2),
        "py": dict(py), "py_n": dict(py_n),
    }


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"], symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    sim_craze = build_craze()
    print("data ready (%.0fs)\n" % (time.time() - t0))

    W = 120  # terminal width
    def sep(char="=", n=W):
        print("  " + char * n)
    def hdr(title):
        sep(); print("  " + title); sep()

    # ====================================================================
    # TABLE 1: ALL RAW MODES — best CT for each
    # ====================================================================
    hdr("TABLE 1: ALL RAW MODES (best CT, cooldown=10)")
    print("  %-18s %-3s %4s  %6s %6s %6s  %4s %4s  %4s %5s  %5s %5s  %4s %5s" % (
        "Mode", "CT", "Tr", "Gross", "Net", "Costs", "IS", "OOS",
        "Rat", "WR", "PF", "Sharpe", "DD", "MCL"))
    sep("-")

    raw_configs = [
        ("b2_vs_flip_chop", 58, "baseline (production)"),
        ("b2_vs_flip_chop", 65, "baseline best OOS"),
        ("entropy", 50, "entropy low CT"),
        ("entropy", 55, ""),
        ("entropy", 58, ""),
        ("entropy", 61, "entropy best OOS"),
        ("entropy", 65, "entropy high CT"),
        ("fd", 50, ""),
        ("fd", 55, ""),
        ("fd", 58, "fd default"),
        ("fd", 65, ""),
        ("fd", 70, "fd best OOS"),
        ("session", 58, "session (CT-insensitive)"),
        ("fd_inv", 58, "fd inverted"),
        ("entropy_inv", 58, "entropy inverted"),
        ("session_flip", 58, "session inverted"),
    ]

    all_raw = []
    for mode, ct, note in raw_configs:
        try:
            b = {**BASE, "mode": mode, "chop_thresh": float(ct), "cooldown_bars": 10}
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            s = full_stats(r["ltf_trades"])
            tag = " *" if "best OOS" in note else ""
            print("  %-18s %-3d %4d  %+6.1f %+6.1f %5.1f  %+5.1f %+5.1f  %5.2f %5.1f%%  %5.2f %5.2f  %4.1f %3d%s" % (
                mode, ct, s["n"], s["gross"], s["net"], s["costs"],
                s["is_r"], s["oos_r"], s["ratio"], s["wr"], s["pf"], s["sharpe"],
                s["dd"], s["mx"], tag))
            all_raw.append({"mode": mode, "ct": ct, **s, "note": note})
        except Exception as e:
            print("  %-18s %-3d  ERROR: %s" % (mode, ct, e))

    # ====================================================================
    # TABLE 2: ALL CRAZE-FILTERED MODES
    # ====================================================================
    hdr("TABLE 2: WITH CRAZE FILTERS (min_swing=3.0, wknd, bm05)")
    print("  %-22s %-3s %4s  %6s %6s  %4s %4s  %4s %5s  %5s %5s  %4s %5s" % (
        "Mode", "CT", "Tr", "Gross", "Net", "IS", "OOS",
        "Rat", "WR", "PF", "Sharpe", "DD", "MCL"))
    sep("-")

    OPT = dict(exp_mltf=True, exp_persist=2, cooldown_bars=10,
               exp_min_swing_ratio=3.0, exp_skip_weekend=1, exp_bias_momentum_min=0.5)

    craze_configs = [
        ("b2_vs_flip_chop", 58, "baseline filtered"),
        ("union", 55, "union prev king"),
        ("entropy", 50, ""),
        ("entropy", 55, ""),
        ("entropy", 58, ""),
        ("entropy", 61, "entropy best OOS"),
        ("entropy", 65, ""),
        ("entropy", 70, ""),
        ("fd", 50, "fd best OOS"),
        ("fd", 55, ""),
        ("fd", 58, ""),
        ("fd", 65, ""),
        ("session", 58, ""),
    ]

    all_craze = []
    for mode, ct, note in craze_configs:
        try:
            b = {**BASE, **OPT, "mode": mode, "chop_thresh": float(ct)}
            r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            s = full_stats(r["ltf_trades"])
            tag = " <-- KING" if mode == "entropy" and ct == 61 else (
                  " <-- prev" if mode == "union" and ct == 55 else "")
            print("  %-22s %-3d %4d  %+6.1f %+6.1f  %+5.1f %+5.1f  %5.2f %5.1f%%  %5.2f %5.2f  %4.1f %3d%s" % (
                mode + " filt", ct, s["n"], s["gross"], s["net"],
                s["is_r"], s["oos_r"], s["ratio"], s["wr"], s["pf"], s["sharpe"],
                s["dd"], s["mx"], tag))
            all_craze.append({"mode": mode, "ct": ct, **s, "note": note})
        except Exception as e:
            print("  %-22s %-3d  ERROR: %s" % (mode + " filt", ct, e))

    # ====================================================================
    # TABLE 3: RAW — YEAR-BY-YEAR for top configs
    # ====================================================================
    hdr("TABLE 3: YEAR-BY-YEAR (RAW) — top 5 by OOS")
    print("  %-22s  %12s %12s  %12s %12s  %5s" % (
        "Config", "2023(IS)", "2024(IS)", "2025(OOS)", "2026(OOS)", "Ratio"))
    sep("-")

    top5_raw = sorted(all_raw, key=lambda x: x["oos_r"], reverse=True)[:5]
    for cfg in top5_raw:
        py = cfg["py"]
        print("  %-22s  %+11.1f %+11.1f  %+11.1f %+11.1f  %5.2f" % (
            "%s ct=%d" % (cfg["mode"], cfg["ct"]),
            py.get("2023", 0), py.get("2024", 0), py.get("2025", 0), py.get("2026", 0),
            cfg["ratio"]))

    # ====================================================================
    # TABLE 4: CRAZE — YEAR-BY-YEAR for top configs
    # ====================================================================
    hdr("TABLE 4: YEAR-BY-YEAR (CRAZE FILTERED) — top 5 by OOS")
    print("  %-24s  %12s %12s  %12s %12s  %5s" % (
        "Config", "2023(IS)", "2024(IS)", "2025(OOS)", "2026(OOS)", "Ratio"))
    sep("-")

    top5_craze = sorted(all_craze, key=lambda x: x["oos_r"], reverse=True)[:5]
    for cfg in top5_craze:
        py = cfg["py"]
        print("  %-24s  %+11.1f %+11.1f  %+11.1f %+11.1f  %5.2f" % (
            "%s ct=%d" % (cfg["mode"], cfg["ct"]),
            py.get("2023", 0), py.get("2024", 0), py.get("2025", 0), py.get("2026", 0),
            cfg["ratio"]))

    # ====================================================================
    # TABLE 5: HEAD-TO-HEAD — entropy vs baseline vs union
    # ====================================================================
    hdr("TABLE 5: HEAD-TO-HEAD — entropy vs b2_vs_flip vs union")
    print("  %-30s  %6s %6s %6s  %5s %5s  %5s %5s  %4s %5s  %5s %4s" % (
        "Config", "Gross", "Net", "Costs", "IS", "OOS",
        "Ratio", "WR", "DD", "PF", "Sharpe", "MCL"))
    sep("-")

    # Raw
    b_raw = [c for c in all_raw if c["mode"] == "b2_vs_flip_chop" and c["ct"] == 58]
    e_raw = [c for c in all_raw if c["mode"] == "entropy" and c["ct"] == 61]
    f_raw = [c for c in all_raw if c["mode"] == "fd" and c["ct"] == 58]
    s_raw = [c for c in all_raw if c["mode"] == "session" and c["ct"] == 58]

    for label, arr in [("b2_vs_flip ct=58 (RAW)", b_raw),
                       ("entropy ct=61 (RAW)", e_raw),
                       ("fd ct=58 (RAW)", f_raw),
                       ("session ct=58 (RAW)", s_raw)]:
        if arr:
            c = arr[0]
            print("  %-30s  %+6.1f %+6.1f %5.1f  %+5.1f %+5.1f  %5.2f %5.1f%%  %4.1f %5.2f  %5.2f %3d" % (
                label, c["gross"], c["net"], c["costs"], c["is_r"], c["oos_r"],
                c["ratio"], c["wr"], c["dd"], c["pf"], c["sharpe"], c["mx"]))

    print()
    # Filtered
    b_f = [c for c in all_craze if c["mode"] == "b2_vs_flip_chop" and c["ct"] == 58]
    u_f = [c for c in all_craze if c["mode"] == "union" and c["ct"] == 55]
    e_f = [c for c in all_craze if c["mode"] == "entropy" and c["ct"] == 61]
    f_f = [c for c in all_craze if c["mode"] == "fd" and c["ct"] == 50]
    s_f = [c for c in all_craze if c["mode"] == "session" and c["ct"] == 58]

    for label, arr in [("b2_vs_flip ct=58 (+filt)", b_f),
                       ("union ct=55 (+filt)", u_f),
                       ("entropy ct=61 (+filt)", e_f),
                       ("fd ct=50 (+filt)", f_f),
                       ("session ct=58 (+filt)", s_f)]:
        if arr:
            c = arr[0]
            print("  %-30s  %+6.1f %+6.1f %5.1f  %+5.1f %+5.1f  %5.2f %5.1f%%  %4.1f %5.2f  %5.2f %3d" % (
                label, c["gross"], c["net"], c["costs"], c["is_r"], c["oos_r"],
                c["ratio"], c["wr"], c["dd"], c["pf"], c["sharpe"], c["mx"]))

    # ====================================================================
    # TABLE 6: OVERFITTING SCORECARD
    # ====================================================================
    hdr("TABLE 6: OVERFITTING SCORECARD")
    print("  %-30s  %6s %6s  %5s  %5s  %s" % (
        "Config", "IS_R", "OOS_R", "Ratio", "NegYrs", "Verdict"))
    sep("-")

    for label, arr in [("b2_vs_flip ct=58 RAW", b_raw),
                       ("b2_vs_flip ct=65 RAW", [c for c in all_raw if c["mode"] == "b2_vs_flip_chop" and c["ct"] == 65]),
                       ("entropy ct=61 RAW", e_raw),
                       ("entropy ct=50 RAW", [c for c in all_raw if c["mode"] == "entropy" and c["ct"] == 50]),
                       ("fd ct=58 RAW", f_raw),
                       ("fd ct=70 RAW", [c for c in all_raw if c["mode"] == "fd" and c["ct"] == 70]),
                       ("session ct=58 RAW", s_raw),
                       ("entropy ct=61 +filt", e_f),
                       ("union ct=55 +filt", u_f)]:
        if arr:
            c = arr[0]
            neg_yrs = sum(1 for v in c["py"].values() if v < 0)
            r = c["ratio"]
            if r < 1.0:
                verdict = "ANTI-OVERFIT (OOS>IS)"
            elif r < 2.0:
                verdict = "PASS"
            elif r < 3.0:
                verdict = "CAUTION"
            else:
                verdict = "OVERFIT RISK"
            print("  %-30s  %+6.1f %+6.1f  %5.2f  %5d  %s" % (
                label, c["is_r"], c["oos_r"], r, neg_yrs, verdict))

    # ====================================================================
    # TABLE 7: COST ANALYSIS
    # ====================================================================
    hdr("TABLE 7: COST ANALYSIS (RAW)")
    print("  %-22s %4s  %6s %5s %5s  %5s %5s" % (
        "Mode", "CT", "Gross", "Fees", "Fund", "Net", "%Cost"))
    sep("-")

    for c in sorted(all_raw, key=lambda x: x["net"], reverse=True)[:8]:
        pct = 100.0 * c["costs"] / max(abs(c["gross"]), 1)
        print("  %-22s %3d  %+6.1f %5.1f %5.1f  %+5.1f %5.1f%%" % (
            "%s ct=%d" % (c["mode"], c["ct"]), c["ct"],
            c["gross"], c["costs"] * 0.6, c["costs"] * 0.4,  # rough fee/fund split
            c["net"], pct))

    # ====================================================================
    # TABLE 8: TRADE FREQUENCY
    # ====================================================================
    hdr("TABLE 8: TRADE FREQUENCY & CAPACITY")
    print("  %-22s %4s  %4s %4s  %5s  %4s trades/year" % (
        "Mode", "CT", "IS", "OOS", "Total", "Avg"))
    sep("-")

    for c in sorted(all_raw, key=lambda x: x["oos_r"], reverse=True)[:10]:
        avg_yr = c["n"] / 4.0  # 4 years of data
        print("  %-22s %3d  %4d %4d  %4d  %.0f" % (
            "%s ct=%d" % (c["mode"], c["ct"]), c["ct"],
            c["is_n"], c["oos_n"], c["n"], avg_yr))

    sep()
    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
