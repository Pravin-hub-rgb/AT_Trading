"""Part 3-4 only: CRAZE filter tests + winner deep dive."""
import sys, time, json
from pathlib import Path

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
    is_cnt = sum(1 for t in tr if (t.get("exit_date") or "")[:4] < "2025" and float(t["r_multiple"]) > 0)
    oos_cnt = sum(1 for t in tr if (t.get("exit_date") or "")[:4] >= "2025" and float(t["r_multiple"]) > 0)
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
    sim_craze = build_craze()
    print("data ready (%0.0fs)" % (time.time() - t0))

    # ====================================================================
    # PART 3: CRAZE FILTERS
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 3: WITH CRAZE FILTERS (min_swing=3.0, wknd, bm05)")
    print("=" * 80)
    print("  %-30s %4s  %+6s %+6s  %4s %4s  %5s %5s" % (
        "Config", "Tr", "IS_R", "OOS_R", "IS", "OOS", "IS_WR", "OOS_WR"))
    print("  " + "-" * 82)

    OPT = dict(exp_mltf=True, exp_persist=2, cooldown_bars=10,
               exp_min_swing_ratio=3.0, exp_skip_weekend=1, exp_bias_momentum_min=0.5)

    # King baseline: union+filters
    r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine,
                  **{**BASE, **OPT, "mode": "union", "chop_thresh": 55.0})
    s_king = stats(r["ltf_trades"])
    king_oos = s_king["oos_r"]
    print("  %-30s %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%  <-- CURRENT KING" % (
        "union ct=55", s_king["n"], s_king["is_r"], s_king["oos_r"],
        s_king["is_n"], s_king["oos_n"], s_king["is_wr"], s_king["oos_wr"]))

    # Also test b2_vs_flip baseline with filters
    r0 = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine,
                   **{**BASE, **OPT, "mode": "b2_vs_flip_chop", "chop_thresh": 65.0})
    s0 = stats(r0["ltf_trades"])
    print("  %-30s %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%" % (
        "b2_vs_flip ct=65 (base+filt)", s0["n"], s0["is_r"], s0["oos_r"],
        s0["is_n"], s0["oos_n"], s0["is_wr"], s0["oos_wr"]))

    # Test new modes
    configs = []
    for mode in ["fd", "entropy", "session", "fd_inv", "entropy_inv"]:
        for ct in [45, 50, 55, 58, 61, 65, 70]:
            configs.append((mode, ct))
    # Also test union with different CTs
    for ct in [50, 55, 58, 61, 65]:
        configs.append(("union", ct))

    craze_results = []
    for mode, ct in configs:
        try:
            b = {**BASE, **OPT, "mode": mode, "chop_thresh": float(ct)}
            r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"]
            s = stats(tr)
            label = "%s ct=%d" % (mode, ct)
            marker = ""
            if s["oos_r"] > king_oos:
                king_oos = s["oos_r"]
                marker = " <-- NEW KING!"
            craze_results.append({"label": label, "mode": mode, "ct": ct,
                                  "is_r": round(s["is_r"], 1), "oos_r": round(s["oos_r"], 1),
                                  "n": s["n"], "is_n": s["is_n"], "oos_n": s["oos_n"]})
            print("  %-30s %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%%s" % (
                label, s["n"], s["is_r"], s["oos_r"], s["is_n"], s["oos_n"],
                s["is_wr"], s["oos_wr"], marker))
        except Exception as e:
            print("  %-30s  ERROR: %s" % (label, e))

    # ====================================================================
    # PART 4: TOP 3 DEEP DIVE
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 4: TOP 3 DEEP DIVE (year-by-year)")
    print("=" * 80)

    sorted_r = sorted(craze_results, key=lambda x: x["oos_r"], reverse=True)
    for rank, cfg in enumerate(sorted_r[:3]):
        print("\n  #%d: %s  OOS=%+.1fR  IS=%+.1fR  IS/OOS=%.2f" % (
            rank + 1, cfg["label"], cfg["oos_r"], cfg["is_r"],
            cfg["is_r"] / max(cfg["oos_r"], 0.01)))
        # Re-run to get year-by-year
        try:
            b = {**BASE, **OPT, "mode": cfg["mode"], "chop_thresh": float(cfg["ct"])}
            r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"]
            s = stats(tr)
            for yr in sorted(s["py"].keys()):
                yr_n = sum(1 for t in tr if (t.get("exit_date") or "")[:4] == yr)
                print("    %s: %+.1fR (%d trades)" % (yr, s["py"][yr], yr_n))
        except Exception:
            pass

    # ====================================================================
    # PART 5: NO FILTERS — pure fd vs b2_vs_flip comparison
    # ====================================================================
    print("\n" + "=" * 80)
    print("PART 5: NO FILTERS — fd vs b2_vs_flip (best CTs)")
    print("=" * 80)
    print("  %-24s %4s  %+6s %+6s  %4s %4s  %5s %5s" % (
        "Mode", "Tr", "IS_R", "OOS_R", "IS", "OOS", "IS_WR", "OOS_WR"))
    print("  " + "-" * 78)

    for mode, ct, cb in [("b2_vs_flip_chop", 65, 0), ("b2_vs_flip_chop", 65, 10),
                          ("fd", 58, 10), ("fd", 55, 10), ("fd", 65, 10),
                          ("fd", 70, 10), ("fd", 58, 0), ("fd", 58, 20)]:
        try:
            b = {**BASE, "mode": mode, "chop_thresh": float(ct), "cooldown_bars": cb}
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"]
            s = stats(tr)
            print("  %-24s %4d  %+6.1f %+6.1f  %4d %4d  %5.0f%% %5.0f%%" % (
                "%s ct=%d cb=%d" % (mode, ct, cb), s["n"], s["is_r"], s["oos_r"],
                s["is_n"], s["oos_n"], s["is_wr"], s["oos_wr"]))
        except Exception as e:
            print("  ERROR: %s" % e)

    out = {"craze_results": craze_results}
    (ROOT / "live_stuff/tests/_creative_part3_results.json").write_text(json.dumps(out, indent=1))
    print("\n(done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
