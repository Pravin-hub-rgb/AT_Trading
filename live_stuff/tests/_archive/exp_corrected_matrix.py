import sys, time, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from test_experiments_craze import build_module, BASE, load_candles, _compute_swings, SWING, MB15, stats, INSTRUMENT
from engine.v18_params import get_v18_params as _gvp
from src.btc.btc_routes import _trade_costs, _load_fine_1m
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

_g = _gvp(INSTRUMENT)

def fund(tr):
    f = 0.0
    for t in tr:
        e, sl = float(t["entry_price"]), float(t["sl"]); rk = abs(e - sl)
        if rk > 0 and e > 0: f += (int(t.get("bars_held") or 0) * 0.25 / 8.0) * 0.0001 * (e / rk)
    return f

def net_r(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
    return g - c2 - fund(tr)

def full_stats(tr):
    s = stats(tr)
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    n = net_r(tr)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    big = len([t for t in rs if t >= 10.0])
    return {"n": s["n"], "gross": round(g, 1), "net": round(n, 1),
            "cost": round(g - n, 1), "wr": round(s["wr"], 1),
            "pf": round(pf, 2), "dd": round(s["dd"], 1), "mx": s["mx"], "big": big,
            "h1": round(s["h1"], 1), "h2": round(s["h2"], 1),
            "py": {k: round(v, 1) for k, v in sorted(s["py"].items())}}

def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw20 = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    sim = build_module()
    print("data ready (%0.0fs)" % (time.time() - t0))

    BP = dict(BASE); BP["chop_thresh"] = 58.0
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    r0 = sim(c1h, sw20, c15, sw15, fine_ltf=[], **BP)
    t0r = r0["ltf_trades"] if isinstance(r0, dict) else r0
    s0 = stats(t0r)
    s_ship = stats(t_ship)
    ok = (s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"])
    print("IDENTITY GATE: %s (n=%d, gross=%+.1f)" % ("PASS" if ok else "FAIL", s0["n"], s0["gross"]))
    assert ok

    CONFIGS = [
        ("SINGLE", "Shipped baseline (BP)", sw20, {**BP}),
        ("SINGLE", "Champion sw20 (atr_high+p7.5+ext3+cd8)", sw20, {
            **BP, "mode": "atr_high", "ext_stop_r": 3.0,
            "cooldown_bars": 8, "exp_partial_r": 7.5}),
        ("SINGLE", "Champion sw10 (atr_high+p7.5+ext3+cd8)", sw10, {
            **BP, "mode": "atr_high", "ext_stop_r": 3.0,
            "cooldown_bars": 8, "exp_partial_r": 7.5}),
        ("SINGLE", "Champion sw20 + w24", sw20, {
            **BP, "mode": "atr_high", "ext_stop_r": 3.0,
            "cooldown_bars": 8, "exp_partial_r": 7.5, "exp_wage_h": 24}),
        ("SINGLE", "Their lb30 ext2.5", sw20, {
            **BP, "ext_stop_r": 2.5, "exp31_lb": 30}),
        ("SINGLE", "Their lb30 curf6-24 ext2.5", sw20, {
            **BP, "ext_stop_r": 2.5, "exp31_lb": 30,
            "exp_curfew_a": 6.0, "exp_curfew_b": 24.0}),
        ("SINGLE", "Their A4 w24 ext1.5", sw10, {
            **BP, "ext_stop_r": 1.5, "exp31_lb": 30,
            "chop_thresh": 55.0, "exp_persist": 2, "exp_wage_h": 24}),
        ("SINGLE", "Their A4 w24 ext1.5 + partR=7.5", sw10, {
            **BP, "ext_stop_r": 1.5, "exp31_lb": 30,
            "chop_thresh": 55.0, "exp_persist": 2, "exp_wage_h": 24,
            "exp_partial_r": 7.5}),
        ("SINGLE", "Their lb14 w24", sw20, {
            **BP, "exp_wage_h": 24}),
        ("SINGLE", "Their lb30 defer24 ext1.5", sw20, {
            **BP, "ext_stop_r": 1.5, "exp31_lb": 30, "exp_defer_h": 24}),
        ("MULTI", "OPT-cd10 w24 ext1.5 (verified)", sw10, {
            **BP, "exp_mltf": True, "exp_persist": 2, "chop_thresh": 55.0,
            "cooldown_bars": 10, "exp_wage_h": 24, "ext_stop_r": 1.5}),
        ("MULTI", "Champion mltf+persist7 sw20", sw20, {
            **BP, "mode": "atr_high", "ext_stop_r": 3.0,
            "cooldown_bars": 8, "exp_partial_r": 7.5,
            "exp_mltf": True, "exp_persist": 7}),
        ("MULTI", "Champion mltf+persist7 sw10", sw10, {
            **BP, "mode": "atr_high", "ext_stop_r": 3.0,
            "cooldown_bars": 8, "exp_partial_r": 7.5,
            "exp_mltf": True, "exp_persist": 7}),
    ]

    results = []
    for lane, label, swh, cfg in CONFIGS:
        r = sim(c1h, swh, c15, sw15, fine_ltf=fine, **cfg)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = full_stats(tr)
        results.append({"lane": lane, "label": label, **s})
        print("  %-6s %-48s %3dt NET %+7.1fR  WR %4.1f%%  DD %5.1f  big=%d" % (
            lane, label, s["n"], s["net"], s["wr"], s["dd"], s["big"]))

    print()
    print("=" * 130)
    print("FULL TABLE")
    print("=" * 130)
    hdr = "  %-6s %-48s %4s  %7s %5s  %5s %5s  %5s %5s  %5s %5s  %4s %3s" % (
        "Lane", "Config", "Tr", "NET", "Cost", "WR", "PF", "DD", "Streak",
        "2023", "2024", "2025", "2026", "big")
    print(hdr)
    print("  " + "-" * 128)
    for r in results:
        py = r["py"]
        print("  %-6s %-48s %4d  %+7.1f %5.1f  %5.1f %5.2f  %5.1f %4d  %5s %5s %5s %5s  %3d" % (
            r["lane"], r["label"], r["n"], r["net"], r["cost"],
            r["wr"], r["pf"], r["dd"], r["mx"],
            ("%.0f" % py.get("2023", 0)) if "2023" in py else "-",
            ("%.0f" % py.get("2024", 0)) if "2024" in py else "-",
            ("%.0f" % py.get("2025", 0)) if "2025" in py else "-",
            ("%.0f" % py.get("2026", 0)) if "2026" in py else "-",
            r["big"]))

    print()
    print("=" * 100)
    print("EQUITY CURVE (cumulative NET R at trade #50 intervals)")
    print("=" * 100)
    equity_labels = [
        "Shipped baseline (BP)",
        "Champion sw20 (atr_high+p7.5+ext3+cd8)",
        "Champion sw10 (atr_high+p7.5+ext3+cd8)",
        "Champion sw20 + w24",
        "Their A4 w24 ext1.5 + partR=7.5",
        "Their lb30 ext2.5",
        "OPT-cd10 w24 ext1.5 (verified)",
    ]
    for label in equity_labels:
        r_match = [x for x in results if x["label"] == label]
        if not r_match: continue
        for lane, lbl, swh, cfg in CONFIGS:
            if lbl == label:
                run = sim(c1h, swh, c15, sw15, fine_ltf=fine, **cfg)
                tr = run["ltf_trades"] if isinstance(run, dict) else run
                rs = [float(t["r_multiple"]) for t in tr]
                g = sum(rs)
                c2, _ = _trade_costs(tr, _g["fee_pct"], 0.0, _g["entry_slip_pct"], _g["exit_slip_pct"])
                cum = 0.0
                pts = []
                fee_rate = _g["fee_pct"] / 100.0
                eslip = _g["entry_slip_pct"] / 100.0
                xslip = _g["exit_slip_pct"] / 100.0
                for i, t in enumerate(tr):
                    risk = abs(float(t["entry_price"]) - float(t["sl"]))
                    if risk <= 0: continue
                    epx = float(t["entry_price"])
                    xpx = float(t.get("exit_price", epx))
                    bars = int(t.get("bars_held") or 0)
                    entry_c = (epx * fee_rate + epx * eslip) / risk
                    exit_c = (xpx * fee_rate + xpx * xslip) / risk
                    fund_r = (bars * 0.25 / 8.0) * 0.0001 * (epx / risk)
                    cum += float(t["r_multiple"]) - entry_c - exit_c - fund_r
                    if (i + 1) % 50 == 0 or i == len(tr) - 1:
                        pts.append((i + 1, round(cum, 1)))
                header = "  %-48s" % label
                for tn, val in pts:
                    header += " t%-3d=%+.0f" % (tn, val)
                print(header)
                break

    out = {"configs": results, "generated": time.strftime("%Y-%m-%d %H:%M")}
    (ROOT / "live_stuff/tests/_corrected_matrix_results.json").write_text(json.dumps(out, indent=1))
    print("\n(corrected matrix done %.0fs)" % (time.time() - t0))

if __name__ == "__main__":
    main()
