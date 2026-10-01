"""Dual-qualification validation on SEPARATE 2021-2022 OOS data.

The other bot tested dualunion on the same 2023-2026 (IS/OOS split at 2025).
We have SEPARATE 2021-2022 data in data/unseen/bybit/. This runs dualunion,
union, and entropy ct=61 on both datasets and compares.
"""
import sys, time, math
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
from test_4_new_concepts import load_unseen, load_fine_1m as load_fine_unseen

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]
OPT = dict(exp_mltf=True, exp_persist=2, cooldown_bars=10,
           exp_min_swing_ratio=3.0, exp_skip_weekend=1, exp_bias_momentum_min=0.5)


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
    py = defaultdict(float); py_n = defaultdict(int)
    for t, r in zip(tr, rs):
        yr = (t.get("exit_date") or "")[:4]; py[yr] += r; py_n[yr] += 1
    return {
        "n": n, "gross": gross, "net": net, "costs": costs,
        "nw": nw, "nl": nl, "wr": wr, "aw": aw, "al": al, "awal": awal,
        "pf": pf, "exp": exp, "dd": dd, "mcl": mcl,
        "sharpe": sharpe, "py": dict(py), "py_n": dict(py_n),
    }


def pr(label, s, years=None):
    if not s:
        print("  %-30s  NO TRADES" % label)
        return
    yrs = years or ["2021", "2022", "2023", "2024", "2025", "2026"]
    py_str = "  ".join("%s:%+.1f" % (y, s["py"].get(y, 0)) for y in yrs if y in s["py"])
    print("  %-30s %4d  %+7.1f %+7.1f %5.1f  %5.1f%% %+.3f %+.3f  %4.2f %5.2f  %5.2f  %2d  %s" % (
        label, s["n"], s["gross"], s["net"], s["costs"],
        s["wr"], s["aw"], s["al"], s["awal"], s["pf"], s["sharpe"],
        s["mcl"], py_str))


def hdr(title):
    print("\n" + "=" * 140)
    print("  " + title)
    print("=" * 140)
    print("  %-30s %4s  %7s %7s %5s  %5s %6s %6s  %4s %5s  %5s  %2s  %s" % (
        "Config", "Tr", "Gross", "Net", "Costs",
        "WR", "AvgW", "AvgL", "W/L", "PF", "Sharpe", "CL", "Yearly R"))
    print("  " + "-" * 138)


def main():
    t0 = time.time()
    sim_craze = build_craze()
    sim = engine.simulate_htf_ltf_streak_halt

    # ====================================================================
    # LOAD IS DATA (2023-2026)
    # ====================================================================
    print("Loading IS (2023-2026)...")
    (c15i, f15i), (c1hi, f1hi) = load_candles()
    sw15i = _compute_swings(f15i, "continuous", min_bars=MB15)
    sw1hi = _compute_swings(f1hi, "continuous", min_bars=SWING["min_bars_1h"])
    finei = _load_fine_1m(c15i[0]["ts"], c15i[-1]["ts"], symbol=INSTRUMENT)
    print("  IS: %d 15m, %d 1h bars  %s -> %s" % (
        len(c15i), len(c1hi), c15i[0]["date"], c15i[-1]["date"]))

    # ====================================================================
    # LOAD OOS DATA (2021-2022)
    # ====================================================================
    print("Loading OOS (2021-2022)...")
    (c15o, f15o), (c1ho, f1ho) = load_unseen("15m"), load_unseen("1h")
    sw15o = _compute_swings(f15o, "continuous", min_bars=MB15)
    sw1ho = _compute_swings(f1ho, "continuous", min_bars=SWING["min_bars_1h"])
    fineo = load_fine_unseen(c15o[0]["ts"], c15o[-1]["ts"])
    print("  OOS: %d 15m, %d 1h bars  %s -> %s" % (
        len(c15o), len(c1ho), c15o[0]["date"], c15o[-1]["date"]))

    # ====================================================================
    # CONFIGS TO TEST
    # ====================================================================
    configs = [
        # (label, mode, ct, use_dual, use_filt)
        ("union ct=55",               "union", 55, False, True),
        ("dualunion ct=55",           "union", 55, True,  True),
        ("dualunion ct=58",           "union", 58, True,  True),
        ("dualunion ct=61",           "union", 61, True,  True),
        ("entropy ct=61",             "entropy", 61, False, True),
        ("entropy ct=55",             "entropy", 55, False, True),
        ("fd ct=50",                  "fd", 50, False, True),
        ("b2_vs_flip ct=58",          "b2_vs_flip_chop", 58, False, True),
        # Raw versions (no filters) for reference
        ("union ct=55 RAW",           "union", 55, False, False),
        ("dualunion ct=55 RAW",       "union", 55, True,  False),
        ("entropy ct=61 RAW",         "entropy", 61, False, False),
        ("b2_vs_flip ct=58 RAW",      "b2_vs_flip_chop", 58, False, False),
        ("b2_vs_flip ct=65 RAW",      "b2_vs_flip_chop", 65, False, False),
    ]

    # ====================================================================
    # RUN ALL CONFIGS ON BOTH DATASETS
    # ====================================================================
    results_is = []
    results_oos = []

    for label, mode, ct, use_dual, use_filt in configs:
        try:
            if use_filt:
                params = {**BASE, **OPT, "mode": mode, "chop_thresh": float(ct)}
            else:
                params = {**BASE, "mode": mode, "chop_thresh": float(ct), "cooldown_bars": 10}
            if use_dual:
                params["exp_union_dual_only"] = 1

            # IS run
            r_is = sim_craze(c1hi, sw1hi, c15i, sw15i, fine_ltf=finei, **params)
            s_is = F(r_is["ltf_trades"])
            # OOS run
            r_oos = sim_craze(c1ho, sw1ho, c15o, sw15o, fine_ltf=fineo, **params)
            s_oos = F(r_oos["ltf_trades"])

            results_is.append((label, s_is))
            results_oos.append((label, s_oos))
        except Exception as e:
            print("  %-30s  ERROR: %s" % (label, e))

    # ====================================================================
    # PRINT IS RESULTS
    # ====================================================================
    hdr("IS DATA: 2023-2026 (data/bybit/)  — with CRAZE filters unless marked RAW")
    for label, s in results_is:
        if s: pr(label, s, years=["2023", "2024", "2025", "2026"])

    # ====================================================================
    # PRINT OOS RESULTS
    # ====================================================================
    hdr("TRUE OOS DATA: 2021-2022 (data/unseen/bybit/)  — NEVER SEEN DURING DEVELOPMENT")
    for label, s in results_oos:
        if s: pr(label, s, years=["2021", "2022"])

    # ====================================================================
    # PRINT COMBINED IS/OOS COMPARISON
    # ====================================================================
    hdr("COMBINED: IS (2023-2026) vs TRUE OOS (2021-2022)")
    print("  %-30s  | %20s | %20s |  Ratio  Verdict" % (
        "Config", "IS 2023-2026", "OOS 2021-2022"))
    print("  " + "-" * 110)

    all_labels = [l for l, s in results_is]
    for i, label in enumerate(all_labels):
        s_is = results_is[i][1]
        s_oos = results_oos[i][1] if i < len(results_oos) else None
        if not s_is or not s_oos: continue

        is_net = s_is["net"]
        oos_net = s_oos["net"]
        ratio = is_net / max(oos_net, 0.01)
        verdict = "ANTI" if ratio < 1.0 else "PASS" if ratio < 3.0 else "FIT" if ratio < 5.0 else "OVERFIT"

        print("  %-30s  | %4dt %+8.1fR | %4dt %+8.1fR |  %5.2f  %s" % (
            label, s_is["n"], is_net, s_oos["n"], oos_net, ratio, verdict))

    # ====================================================================
    # BUG CHECK: verify dual gate actually removes trades
    # ====================================================================
    hdr("BUG CHECK: dual gate trade removal")
    for label_base in ["union ct=55", "union ct=55 RAW"]:
        idx_is = [i for i, (l, s) in enumerate(results_is) if l == label_base]
        idx_dual = [i for i, (l, s) in enumerate(results_is) if l == "dual" + label_base]
        if idx_is and idx_dual:
            s_union = results_is[idx_is[0]][1]
            s_dual = results_is[idx_dual[0]][1]
            if s_union and s_dual:
                removed_is = s_union["n"] - s_dual["n"]
                s_union_oos = results_oos[idx_is[0]][1]
                s_dual_oos = results_oos[idx_dual[0]][1]
                removed_oos = s_union_oos["n"] - s_dual_oos["n"] if s_union_oos and s_dual_oos else 0
                print("  %s: removed %d IS trades, %d OOS trades" % (
                    label_base, removed_is, removed_oos))
                if removed_is > 0 and removed_oos > 0:
                    print("    PASS: dual gate removes trades on BOTH datasets")
                elif removed_is > 0:
                    print("    WARN: dual gate only removes IS trades, none OOS")
                else:
                    print("    FAIL: dual gate removes nothing on IS")

    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
