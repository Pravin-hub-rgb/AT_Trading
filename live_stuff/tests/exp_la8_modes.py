"""EXP LA8: Mode Variations -- test different regime routing strategies.

No CRAZE patch needed -- the shipped engine already supports these modes.
Just pass different `mode` values and compare.
"""
import sys, time, json
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


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = engine.simulate_htf_ltf_streak_halt
    print("data ready (%0.0fs)" % (time.time() - t0))

    OPT = dict(exp_mltf=True, exp_persist=2, chop_thresh=55.0, cooldown_bars=10)
    modes = ["chop", "b2_vs_flip_chop", "decisive_vs_flip_chop",
             "atr_low", "atr_high", "chop_or_atr_low", "chop_and_atr_low"]

    print("\n=== ANCHOR: Mode Variations ===")
    print("  %-26s %5s  %8s %8s  %5s %6s %6s" % ("Mode", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 72)
    # baseline
    r0 = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **BASE)
    t0r = r0["ltf_trades"] if isinstance(r0, dict) else r0
    n0 = _net(t0r, _P); s0 = stats(t0r)
    results_anc = [{"mode": "chop (default)", "n": s0["n"], "net": round(n0, 1),
                    "delta": 0.0, "wr": round(s0["wr"], 1), "dd": round(s0["dd"], 1),
                    "pf": round(s0["pf"], 2), "gross": round(s0["gross"], 1)}]
    print("  %-26s %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
        "chop (default)", s0["n"], n0, 0.0, s0["wr"], s0["dd"], s0["pf"]))

    for m in modes[1:]:
        try:
            b = {**BASE, "mode": m}
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            s = stats(tr); net = _net(tr, _P); delta = net - n0
            print("  %-26s %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
                m, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
            results_anc.append({"mode": m, "n": s["n"], "net": round(net, 1),
                                "delta": round(delta, 1), "wr": round(s["wr"], 1),
                                "dd": round(s["dd"], 1), "pf": round(s["pf"], 2),
                                "gross": round(s["gross"], 1)})
        except Exception as e:
            print("  %-26s  ERROR: %s" % (m, e))

    print("\n=== OPTIMAL (w24): Mode Variations ===")
    print("  %-26s %5s  %8s %8s  %5s %6s %6s" % ("Mode", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 72)
    # baseline — use CRAZE module for OPT params
    sim_craze = build_craze()
    r0o = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**BASE, **OPT, "exp_wage_h": 24})
    t0o = r0o["ltf_trades"] if isinstance(r0o, dict) else r0o
    n0o = _net(t0o, _P); s0o = stats(t0o)
    results_opt = [{"mode": "chop (default)", "n": s0o["n"], "net": round(n0o, 1),
                    "delta": 0.0, "wr": round(s0o["wr"], 1), "dd": round(s0o["dd"], 1),
                    "pf": round(s0o["pf"], 2), "gross": round(s0o["gross"], 1)}]
    print("  %-26s %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
        "chop (default)", s0o["n"], n0o, 0.0, s0o["wr"], s0o["dd"], s0o["pf"]))

    for m in modes[1:]:
        try:
            b = {**BASE, **OPT, "exp_wage_h": 24, "mode": m}
            r = sim_craze(c1h, sw1h, c15, sw15, fine_ltf=fine, **b)
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            s = stats(tr); net = _net(tr, _P); delta = net - n0o
            print("  %-26s %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
                m, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
            results_opt.append({"mode": m, "n": s["n"], "net": round(net, 1),
                                "delta": round(delta, 1), "wr": round(s["wr"], 1),
                                "dd": round(s["dd"], 1), "pf": round(s["pf"], 2),
                                "gross": round(s["gross"], 1)})
        except Exception as e:
            print("  %-26s  ERROR: %s" % (m, e))

    out = {"anchor": {"baseline_net": round(n0, 1), "results": results_anc},
           "optimal": {"baseline_net": round(n0o, 1), "results": results_opt}}
    (ROOT / "live_stuff/tests/_la8_results.json").write_text(json.dumps(out, indent=1))
    print("\n(la8 done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
