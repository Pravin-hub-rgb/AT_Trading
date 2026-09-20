"""FINAL COMPARISON: All top configs from both lanes, consistent cost model.

Single position vs Multi position. Full metrics, yearly splits.
"""
import sys, time, json, importlib.util, bisect
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

ENGINE = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"
SRC = ENGINE.read_text(encoding="utf-8")

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _trade_costs, _load_fine_1m, _compute_swings

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                            "atr_low_thresh", "atr_high_thresh", "mode",
                            "cooldown_bars", "max_consecutive_losses",
                            "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]


def _load_module(text, name):
    p = Path(ROOT / "live_stuff/tests/_final_cmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def _build_full(s):
    t1 = "    *,\n"
    assert s.count(t1) == 1
    s = s.replace(t1, t1 +
        '    swings_trail=None,\n    exp_momentum=False,\n    b3_k=0,\n'
        '    b3_mode="close",\n    exp18_arm=None,\n    exp22_conv=False,\n'
        '    exp_persist=0,\n    exp_mltf=False,\n    exp27_mode=None,\n'
        '    exp31_lb=0,\n    exp_wage_h=0,\n    exp_curfew_a=0.0,\n'
        '    exp_curfew_b=0.0,\n    exp_partial_r=0.0,\n    exp_defer_h=0.0,\n')
    s = s.replace("    import bisect as bs\n",
                  "    import bisect as bs\n    if swings_trail is None: swings_trail=swings_ltf\n")
    s = s.replace("        for s in swings_ltf:\n",
                  "        for s in swings_trail:\n")
    t4 = 'candle_ts_htf=[int(c["ts"]) for c in candles_htf]\n'
    s = s.replace(t4, t4 +
        '    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]\n'
        '    closes_htf=[float(c["close"]) for c in candles_htf]\n')
    t5 = '    if sig["dir"] != d: continue\n'
    s = s.replace(t5, t5 +
        '        if exp_momentum:\n'
        '            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+900)-1\n'
        '            if _j>=2:\n'
        '                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0\n'
        '                if sig["dir"]==1 and closes_htf[_j]<_ma: continue\n'
        '                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue\n')
    s = s.replace(t5, t5 +
        '        if exp_defer_h>0:\n'
        '            _age=(bar_ts-s)/3600.0\n'
        '            if _age < exp_defer_h:\n'
        '                _tsd=int(s)+int(exp_defer_h*3600)\n'
        '                _k=bs.bisect_left(candle_ts_ltf,_tsd)\n'
        '                if _k<len(candles_ltf) and candle_ts_ltf[_k]<=e+2700 and _k>bar:\n'
        '                    _slp=float(sig["swing_start_px"])\n'
        '                    _dead=False\n'
        '                    for _q in range(bar+1,_k+1):\n'
        '                        if d==1 and float(candles_ltf[_q]["low"])<=_slp:_dead=True;break\n'
        '                        if d==-1 and float(candles_ltf[_q]["high"])>=_slp:_dead=True;break\n'
        '                    if not _dead:\n'
        '                        _ok=True\n'
        '                        _hr=abs(pe-psl)\n'
        '                        if ext_stop_r>0 and _hr>0:\n'
        '                            _ex2=(float(candles_ltf[_k]["close"])-pe)*d/_hr\n'
        '                            if _ex2>ext_stop_r:_ok=False\n'
        '                        if _ok:\n'
        '                            _ns=dict(sig);_ns["bar"]=candles_ltf[_k]["date"]\n'
        '                            filtered.append((_ns,use))\n'
        '                continue\n')
    t6c = '        ev_idx=-1\n'
    s = s.replace(t6c, t6c +
        '        opp_events=[]\n'
        '        if exp27_mode:\n'
        '            for _s9 in swings_ltf:\n'
        '                for _b9 in _s9.get("breaks",[]):\n'
        '                    if _b9.get("time") and (1 if _b9["dir"]=="up" else -1)==-direction:\n'
        '                        opp_events.append((int(_b9["idx"]), _b9.get("kind","")))\n'
        '            opp_events.sort(key=lambda z: z[0])\n'
        '            opp_ev_idx=-1\n'
        '            while opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= i:\n'
        '                opp_ev_idx += 1\n')
    t6d = ('        for j in range(i+1, n if not fine_ltf else i+1):\n'
           '            c=candles_ltf[j]\n'
           '            hi=float(c["high"]); lo=float(c["low"])\n')
    s = s.replace(t6d, t6d +
        '            if exp27_mode and opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= j:\n'
        '                opp_ev_idx += 1\n'
        '                _eok = True\n'
        '                if exp27_mode in ("loss", "fliploss"):\n'
        '                    _cl = float(c["close"])\n'
        '                    _cr = ((_cl - entry) / risk) if direction == 1 else ((entry - _cl) / risk)\n'
        '                    if _cr >= 0.0: _eok = False\n'
        '                if exp27_mode == "fliploss" and opp_events[opp_ev_idx][1] != "FLIP": _eok = False\n'
        '                if _eok:\n'
        '                    exit_idx, exit_px, outcome = j, float(c["close"]), "accel27"\n'
        '                    break\n')
    t6e = '    chop=_chop_series_1h(candles_htf, lb=14)\n'
    s = s.replace(t6e, '    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))\n')
    t8 = '    chop_per_ltf=[50.0]*len(candles_ltf)\n'
    s = s.replace(t8, t8 + '    _rg_s=None; _rg_c=0\n')
    t9 = '        # pick intervals\n'
    s = s.replace(t9,
        '        if exp_persist>0:\n'
        '            if _rg_s is None: _rg_s=use\n'
        '            if use!=_rg_s:\n'
        '                _rg_c+=1\n'
        '                if _rg_c>=exp_persist: _rg_s=use; _rg_c=0\n'
        '            else: _rg_c=0\n'
        '            use=_rg_s\n' + t9)
    t10 = '        if busy_until and bar_time <= busy_until: continue\n'
    s = s.replace(t10, '        if (not exp_mltf) and busy_until and bar_time <= busy_until: continue\n')
    t6 = '        sl_pivot=sig["swing_start_px"]\n'
    s = s.replace(t6, t6 +
        '        if b3_k>0:\n'
        '            _lv=float(candles_ltf[i]["high"]) if direction==1 else float(candles_ltf[i]["low"])\n'
        '            _jj=None\n'
        '            for _k in range(i+1, min(i+1+b3_k, n-1)):\n'
        '                _hi=float(candles_ltf[_k]["high"]); _lo=float(candles_ltf[_k]["low"])\n'
        '                if direction==1 and _lo<=sl_pivot: break\n'
        '                if direction==-1 and _hi>=sl_pivot: break\n'
        '                _cl=float(candles_ltf[_k]["close"])\n'
        '                if b3_mode=="wick":\n'
        '                    _hit=(_hi>_lv) if direction==1 else (_lo<_lv)\n'
        '                else:\n'
        '                    _hit=(_cl>_lv) if direction==1 else (_cl<_lv)\n'
        '                if _hit:\n'
        '                    _jj=_k; break\n'
        '            if _jj is None: continue\n'
        '            i=_jj\n'
        '            bar_time=candles_ltf[i]["date"]\n'
        '            entry=float(candles_ltf[i]["close"])\n'
        '            if (not exp_mltf) and busy_until and bar_time<=busy_until: continue\n'
        '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n')
    t_pe_init = '        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None\n'
    s = s.replace(t_pe_init, t_pe_init +
        '        _partial_taken=False; _partial_r=0.0\n')
    t_pe_coarse = ('            if direction==1:\n'
                   '                if hi>best: best=hi\n'
                   '            else:\n'
                   '                if lo<best: best=lo\n')
    s = s.replace(t_pe_coarse, t_pe_coarse +
        '            if exp_partial_r>0 and not _partial_taken and risk>0:\n'
        '                _cur_r=(best-entry)*direction/risk\n'
        '                if _cur_r>=exp_partial_r:\n'
        '                    _partial_taken=True; _partial_r=exp_partial_r\n')
    t_pe_fine = ('                if direction==1:\n'
                 '                    if hi>best_f: best_f=hi\n'
                 '                else:\n'
                 '                    if lo<best_f: best_f=lo\n')
    s = s.replace(t_pe_fine, t_pe_fine +
        '                if exp_partial_r>0 and not _partial_taken and risk>0:\n'
        '                    _cur_rf=(best_f-entry)*direction/risk\n'
        '                    if _cur_rf>=exp_partial_r:\n'
        '                        _partial_taken=True; _partial_r=exp_partial_r\n')
    t_r = ('        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
            '        r_multiple=move/risk if risk>0 else 0\n')
    s = s.replace(t_r,
        '        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
        '        _partial_exit_price=0.0\n'
        '        if _partial_taken and risk>0:\n'
        '            _partial_exit_price=entry+direction*_partial_r*risk\n'
        '            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
        '            r_multiple=_partial_r+(_rem_move/risk)*0.5\n'
        '        else:\n'
        '            r_multiple=move/risk if risk>0 else 0\n')
    t_dict = '            "bars_held": exit_idx - i,\n        })'
    s = s.replace(t_dict,
        '            "bars_held": exit_idx - i,\n'
        '            "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,\n'
        '        })')
    return s


def build_module():
    s = _build_full(SRC)
    m, p = _load_module(s, "final_cmp")
    try: p.unlink()
    except OSError: pass
    return m.simulate_htf_ltf_streak_halt


def _net(tr, g):
    rs = [float(t["r_multiple"]) for t in tr]
    fee_rate = g["fee_pct"] / 100.0
    entry_slip = g["entry_slip_pct"] / 100.0
    exit_slip = g["exit_slip_pct"] / 100.0
    FUND_RATE = 0.0001
    total_cost = 0.0
    for t in tr:
        risk = abs(float(t["entry_price"]) - float(t["sl"]))
        if risk <= 0: continue
        epx = float(t["entry_price"])
        xpx = float(t.get("exit_price", epx))
        ppx = float(t.get("partial_exit_price", 0))
        bars = int(t.get("bars_held") or 0)
        entry_cost = (epx * fee_rate + epx * entry_slip) / risk
        if ppx > 0:
            exit_cost = (0.5 * ppx * (fee_rate + exit_slip) + 0.5 * xpx * (fee_rate + exit_slip)) / risk
        else:
            exit_cost = (xpx * fee_rate + xpx * exit_slip) / risk
        fund_r = (bars * 0.25 / 8.0) * FUND_RATE * (epx / risk)
        total_cost += entry_cost + exit_cost + fund_r
    return sum(rs) - total_cost


def full_stats(tr, g):
    rs = [float(t["r_multiple"]) for t in tr]
    gross = sum(rs)
    net = _net(tr, g)
    n = len(rs)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    wr = 100.0 * len(wins) / max(n, 1)
    avg_win = sum(wins) / max(len(wins), 1)
    avg_loss = sum(losses) / max(len(losses), 1)
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    peak = 0.0; cum = 0.0; dd = 0.0; cur = 0; mx = 0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
        if x < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    big = len([x for x in rs if x >= 10.0])
    py = defaultdict(float)
    for t in tr:
        yr = (t.get("exit_date") or t.get("entry_date") or "")[:4]
        py[yr] += float(t["r_multiple"])
    return {"n": n, "gross": round(gross, 1), "net": round(net, 1),
            "cost": round(gross - net, 1), "wr": round(wr, 1),
            "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
            "pf": round(pf, 2), "dd": round(dd, 1), "mx": mx, "big": big,
            "py": {k: round(v, 1) for k, v in py.items()},
            "h1": round(py.get("2023", 0) + py.get("2024", 0), 1),
            "h2": round(py.get("2025", 0) + py.get("2026", 0), 1)}


CONFIGS = [
    ("SINGLE", "Shipped baseline", {**BASE}),
    ("SINGLE", "Our champion (atr_high+p7.5+ext3+cd8)", {
        **BASE, "mode": "atr_high", "ext_stop_r": 3.0,
        "cooldown_bars": 8, "exp_partial_r": 7.5}),
    ("SINGLE", "Our champion + w24", {
        **BASE, "mode": "atr_high", "ext_stop_r": 3.0,
        "cooldown_bars": 8, "exp_partial_r": 7.5, "exp_wage_h": 24}),
    ("SINGLE", "Their lb30 ext2.5", {
        **BASE, "ext_stop_r": 2.5, "exp31_lb": 30}),
    ("SINGLE", "Their lb30 curf6-24", {
        **BASE, "ext_stop_r": 2.5, "exp31_lb": 30,
        "exp_curfew_a": 6.0, "exp_curfew_b": 24.0}),
    ("SINGLE", "Their lb30 curf6-24 ext2.5", {
        **BASE, "ext_stop_r": 2.5, "exp31_lb": 30,
        "exp_curfew_a": 6.0, "exp_curfew_b": 24.0}),
    ("SINGLE", "Their lb30 defer24 ext1.5", {
        **BASE, "ext_stop_r": 1.5, "exp31_lb": 30, "exp_defer_h": 24}),
    ("SINGLE", "Their A4 w24 ext1.5", {
        **BASE, "ext_stop_r": 1.5, "exp31_lb": 30,
        "chop_thresh": 55.0, "exp_persist": 2, "exp_wage_h": 24}),
    ("SINGLE", "Their A4 w24 ext1.5 + our partR=7.5", {
        **BASE, "ext_stop_r": 1.5, "exp31_lb": 30,
        "chop_thresh": 55.0, "exp_persist": 2, "exp_wage_h": 24,
        "exp_partial_r": 7.5}),
    ("SINGLE", "Their lb14 w24", {
        **BASE, "exp_wage_h": 24}),
    ("MULTI", "OPT-cd10 w24 ext1.5 (theirs)", {
        **BASE, "exp31_lb": 30, "chop_thresh": 55.0,
        "exp_persist": 2, "exp_wage_h": 24,
        "cooldown_bars": 10, "exp_mltf": True, "ext_stop_r": 1.5}),
    ("MULTI", "Our atr_high + partR=7.5 + mltf + persist=7", {
        **BASE, "mode": "atr_high", "ext_stop_r": 3.0,
        "cooldown_bars": 8, "exp_partial_r": 7.5,
        "exp_mltf": True, "exp_persist": 7}),
]


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    print("data ready (%0.0fs)" % (time.time() - t0))

    sim0 = build_module()

    # Identity gate
    from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt as ship_fn
    r_ship = ship_fn(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    r0 = sim0(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t0r = r0["ltf_trades"] if isinstance(r0, dict) else r0
    ok = (len(t0r) == len(t_ship) and
          [float(t["r_multiple"]) for t in t0r] == [float(t["r_multiple"]) for t in t_ship])
    print("  identity gate: %s" % ("PASS" if ok else "FAIL"))
    assert ok

    results = []
    for lane, label, cfg in CONFIGS:
        r = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = full_stats(tr, _P)
        results.append({"lane": lane, "label": label, **s})
        print("  %-6s %-40s %3dt NET %+7.1fR  WR %4.1f%%  DD %5.1f  PF %5.2f  big=%d" % (
            lane, label, s["n"], s["net"], s["wr"], s["dd"], s["pf"], s["big"]))

    # Print full table
    print("\n" + "=" * 140)
    print("FULL METRICS MATRIX")
    print("=" * 140)
    print("  %-6s %-40s %4s  %8s %6s  %5s %5s  %5s %5s  %5s  %5s %5s  %5s %5s  %5s %5s" % (
        "Lane", "Config", "Tr", "NET", "Cost", "WR", "PF",
        "2023", "2024", "2025", "2026", "DD", "H1", "H2",
        "WStr", "big"))
    print("  " + "-" * 138)
    for r in results:
        py = r["py"]
        print("  %-6s %-40s %4d  %+8.1f %6.1f  %5.1f %5.2f  %5s %5s %5s %5s  %5.1f  %5s %5s  %5d %3d" % (
            r["lane"], r["label"], r["n"], r["net"], r["cost"],
            r["wr"], r["pf"],
            ("%.0f" % py.get("2023", 0)) if "2023" in py else "-",
            ("%.0f" % py.get("2024", 0)) if "2024" in py else "-",
            ("%.0f" % py.get("2025", 0)) if "2025" in py else "-",
            ("%.0f" % py.get("2026", 0)) if "2026" in py else "-",
            r["dd"],
            ("%.0f" % r["h1"]), ("%.0f" % r["h2"]),
            r["mx"], r["big"]))

    # Equity curve: cumulative R by trade number
    print("\n" + "=" * 100)
    print("EQUITY CURVE (cumulative NET R at trade #50 intervals)")
    print("=" * 100)
    for r_label in ["Shipped baseline", "Our champion (atr_high+p7.5+ext3+cd8)",
                     "Their A4 w24 ext1.5", "Their A4 w24 ext1.5 + our partR=7.5",
                     "Their lb30 ext2.5",
                     "OPT-cd10 w24 ext1.5 (theirs)"]:
        r_match = [x for x in results if x["label"] == r_label]
        if not r_match: continue
        r = r_match[0]
        # Re-run to get trades
        for lane, label, cfg in CONFIGS:
            if label == r_label:
                run = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
                tr = run["ltf_trades"] if isinstance(run, dict) else run
                rs = [float(t["r_multiple"]) for t in tr]
                fee_rate = _P["fee_pct"] / 100.0
                entry_slip = _P["entry_slip_pct"] / 100.0
                exit_slip = _P["exit_slip_pct"] / 100.0
                cum = 0.0
                pts = []
                for i, t in enumerate(tr):
                    risk = abs(float(t["entry_price"]) - float(t["sl"]))
                    if risk <= 0: continue
                    epx = float(t["entry_price"])
                    xpx = float(t.get("exit_price", epx))
                    ppx = float(t.get("partial_exit_price", 0))
                    bars = int(t.get("bars_held") or 0)
                    entry_c = (epx * fee_rate + epx * entry_slip) / risk
                    if ppx > 0:
                        exit_c = (0.5 * ppx * (fee_rate + exit_slip) + 0.5 * xpx * (fee_rate + exit_slip)) / risk
                    else:
                        exit_c = (xpx * fee_rate + xpx * exit_slip) / risk
                    fund_r = (bars * 0.25 / 8.0) * 0.0001 * (epx / risk)
                    cum += float(t["r_multiple"]) - entry_c - exit_c - fund_r
                    if (i + 1) % 50 == 0 or i == len(tr) - 1:
                        pts.append((i + 1, round(cum, 1)))
                header = "  %-42s" % r_label
                for tn, val in pts:
                    header += " t%-3d=%+.0f" % (tn, val)
                print(header)
                break

    # Save JSON
    out = {"configs": results, "generated": time.strftime("%Y-%m-%d %H:%M")}
    (ROOT / "live_stuff/tests/_final_matrix_results.json").write_text(json.dumps(out, indent=1))
    print("\n(la-final-matrix done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
