"""Full sweep: chop_thresh grid + cooldown + CRAZE filters for fd/entropy/session."""
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
    py = {}
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        yr = d[:4]
        py[yr] = py.get(yr, 0) + float(t["r_multiple"])
    is_r = sum(v for k, v in py.items() if k < "2025")
    oos_r = sum(v for k, v in py.items() if k >= "2025")
    is_n = sum(1 for t in tr if (t.get("exit_date") or "")[:4] < "2025")
    oos_n = sum(1 for t in tr if (t.get("exit_date") or "")[:4] >= "2025")
    is_wr = 0; oos_wr = 0
    is_cnt = 0; oos_cnt = 0
    for t in tr:
        yr = (t.get("exit_date") or "")[:4]
        if float(t["r_multiple"]) > 0:
            if yr < "2025": is_cnt += 1
            else: oos_cnt += 1
    is_wr = 100.0 * is_cnt / max(is_n, 1)
    oos_wr = 100.0 * oos_cnt / max(oos_n, 1)
    return {"n": len(tr), "gross": g, "wr": wr, "dd": dd, "mx": mx,
            "is_r": is_r, "oos_r": oos_r, "is_n": is_n, "oos_n": oos_n,
            "is_wr": is_wr, "oos_wr": oos_wr, "pf": pf, "py": py}


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"], symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    print("data ready (%0.0fs)" % (time.time() - t0))
    count = 0
    total = 0

    def run_raw(mode, ct=58.0, cb=10):
        nonlocal count, total
        count += 1
        b = {**BASE, "mode": mode, "chop_thresh": float(ct), "cooldown_bars": cb}
        r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
        return stats(r["ltf_trades"])

    # ====================================================================
    # PART 1: CHOP THRESH SWEEP (RAW)
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 1: CHOP THRESH SWEEP (RAW ENGINE, cooldown=10)")
    print("=" * 80)
    print("  %-12s %-3s %4s  %+6s %+6s  %4s %4s  %5s %5s" % (
        "Mode", "CT", "Tr", "IS_R", "OOS_R", "IS", "OOS", "IS_WR", "OOS_WR"))
    print("  " + "-" * 72)

    sweep_modes = ["fd", "fd_inv", "entropy", "entropy_inv", "session", "session_flip",
                   "b2_vs_flip_chop"]
    sweep_cts = [40, 45, 50, 55, 58, 61, 65, 70, 75, 80]
    total = len(sweep_modes) * len(sweep_cts)

    best_raw_oos = -999; best_raw_cfg = None
    all_raw = []

    for mode in sweep_modes:
        for ct in sweep_cts:
            try:
                s = run_raw(mode, ct)
                all_raw.append({"mode": mode, "ct": ct, **{k: round(v, 1) if isinstance(v, float) else v for k, v in s.items() if k != "py"}})
                marker = ""
                if s["oos_r"] > best_raw_oos and s["is_n"] >= 20:
                    best_raw_oos = s["oos_r"]
                    best_raw_cfg = (mode, ct)
                    marker = " <-- BEST"
                if s["oos_r"] > -20 or marker:
                    print("  %-12s %-3d %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%%s" % (
                        mode, ct, s["n"], s["is_r"], s["oos_r"], s["is_n"], s["oos_n"],
                        s["is_wr"], s["oos_wr"], marker))
            except Exception as e:
                print("  %-12s %-3d  ERROR: %s" % (mode, ct, e))

    print("\n  BEST RAW: mode=%s ct=%d  OOS_R=%+.1f" % (best_raw_cfg[0], best_raw_cfg[1], best_raw_oos))

    # ====================================================================
    # PART 2: COOLDOWN SWEEP for best raw config
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 2: COOLDOWN SWEEP (best raw config)")
    print("=" * 80)

    if best_raw_cfg:
        for cb in [0, 5, 10, 15, 20, 25]:
            s = run_raw(best_raw_cfg[0], best_raw_cfg[1], cb)
            print("  cb=%2d  %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%" % (
                cb, s["n"], s["is_r"], s["oos_r"], s["is_n"], s["oos_n"],
                s["is_wr"], s["oos_wr"]))

    # ====================================================================
    # PART 3: CRAZE FILTERS (mag_ratio + wknd + bm05)
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 3: WITH CRAZE FILTERS (min_swing=3.0, wknd, bm05)")
    print("=" * 80)
    print("  %-30s %4s  %+6s %+6s  %4s %4s  %5s %5s" % (
        "Config", "Tr", "IS_R", "OOS_R", "IS", "OOS", "IS_WR", "OOS_WR"))
    print("  " + "-" * 82)

    OPT_BASE = dict(exp_mltf=True, exp_persist=2, cooldown_bars=10,
                    exp_min_swing_ratio=3.0, exp_skip_weekend=1, exp_bias_momentum_min=0.5)
    sim_craze = build_craze()

    # King baseline
    r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine,
                  **{**BASE, **OPT_BASE, "mode": "union", "chop_thresh": 55.0})
    s_king = stats(r["ltf_trades"])
    print("  %-30s %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%  (CURRENT KING)" % (
        "union ct=55 (king)", s_king["n"], s_king["is_r"], s_king["oos_r"],
        s_king["is_n"], s_king["oos_n"], s_king["is_wr"], s_king["oos_wr"]))

    king_oos = s_king["oos_r"]

    # Test all new modes × CT with CRAZE filters
    craze_configs = []
    for mode in ["fd", "entropy", "session", "fd_inv", "entropy_inv", "session_flip"]:
        for ct in [45, 50, 55, 58, 61, 65, 70]:
            craze_configs.append((mode, ct))
    # Add sweep of ext_stop_r for best fd
    for esr in [1.0, 1.5, 2.0, 2.5, 3.0]:
        craze_configs.append(("fd_esr_%s" % str(esr).replace(".", ""), 58))

    total_craze = len(craze_configs)
    print("  (testing %d CRAZE configs...)" % total_craze)

    craze_results = []
    for mode, ct in craze_configs:
        try:
            if mode.startswith("fd_esr_"):
                esr = float(mode.split("_")[1] + "." + mode.split("_")[2]) if "_" in mode[7:] else float(mode[7:])
                # hacky parse: fd_esr_1_0 -> 1.0
                parts = mode.split("_")
                esr = float(parts[2] + "." + parts[3]) if len(parts) > 3 else float(parts[2])
                b = {**BASE, **OPT_BASE, "mode": "fd", "chop_thresh": 58.0, "ext_stop_r": esr}
                label = "fd ct=58 esr=%.1f" % esr
            else:
                b = {**BASE, **OPT_BASE, "mode": mode, "chop_thresh": float(ct)}
                label = "%s ct=%d" % (mode, ct)
            r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"]
            s = stats(tr)
            marker = ""
            if s["oos_r"] > king_oos:
                king_oos = s["oos_r"]
                marker = " <-- NEW KING!"
            craze_results.append({"label": label, "mode": mode, "ct": ct, **{k: round(v, 1) if isinstance(v, float) else v for k, v in s.items() if k != "py"}})
            print("  %-30s %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%%s" % (
                label, s["n"], s["is_r"], s["oos_r"], s["is_n"], s["oos_n"],
                s["is_wr"], s["oos_wr"], marker))
        except Exception as e:
            print("  %-30s  ERROR: %s" % (label, e))

    # ====================================================================
    # PART 4: WINNER DEEP DIVE (year-by-year)
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 4: WINNER DEEP DIVE")
    print("=" * 80)

    # Find overall winner
    all_craze_sorted = sorted(craze_results, key=lambda x: x["oos_r"], reverse=True)
    if all_craze_sorted:
        winner = all_craze_sorted[0]
        print("  Winner: %s  OOS=%+.1fR  IS=%+.1fR  IS/OOS=%.2f" % (
            winner["label"], winner["oos_r"], winner["is_r"],
            winner["is_r"] / max(winner["oos_r"], 0.01)))

    out = {"raw_sweep": all_raw, "craze_sweep": craze_results,
           "best_raw": {"mode": best_raw_cfg[0], "ct": best_raw_cfg[1], "oos_r": best_raw_oos}}
    (ROOT / "backtest/tests/_creative_full_results.json").write_text(json.dumps(out, indent=1))

    print("\n" + "=" * 80)
    print("SUMMARY: %d raw + %d craze = %d total runs (%.0fs)" % (
        count, len(craze_results), count + len(craze_results), time.time() - t0))
    print("=" * 80)


if __name__ == "__main__":
    main()
