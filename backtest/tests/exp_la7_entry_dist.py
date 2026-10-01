"""EXP LA7: Entry Distance Gate -- skip entries late in the swing.

Theory: Late entries (signal fires deep into the swing) are more likely to be
fast deaths. v16_entry_dist.py tested this but never in CRAZE.

Mechanism:
- Compute dist = (signal_bar - swing_start_bar) / swing_length
- If dist > exp_entry_dist_max: skip the entry
- This is a PRE-ENTRY filter (no lookahead) — uses swing start index which is known.

Test: sweep exp_entry_dist_max [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8] on anchor + OPTIMAL
"""
import sys, time, json, importlib.util
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
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
    p = Path(ROOT / "backtest/tests/_la7_tmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def _build_entry_dist(s):
    """CRAZE superset + entry distance gate patch."""
    # 1) extra kwargs
    t1 = "    *,\n"
    assert s.count(t1) == 1, "sig star"
    s = s.replace(t1, t1 +
                  '    swings_trail=None,\n'
                  '    exp_momentum=False,\n'
                  '    b3_k=0,\n'
                  '    b3_mode="close",\n'
                  '    exp18_arm=None,\n'
                  '    exp22_conv=False,\n'
                  '    exp_persist=0,\n'
                  '    exp_mltf=False,\n'
                  '    exp27_mode=None,\n'
                  '    exp31_lb=0,\n'
                  '    exp_wage_h=0,\n'
                  '    exp_curfew_a=0.0,\n'
                  '    exp_curfew_b=0.0,\n'
                  '    exp_entry_dist_max=0.0,\n')
    # 2) split-mb
    t2 = "    import bisect as bs\n"
    assert s.count(t2) == 1, "bisect"
    s = s.replace(t2, t2 + "    if swings_trail is None: swings_trail=swings_ltf\n")
    t3 = "        for s in swings_ltf:\n"
    assert s.count(t3) == 1, "trail loop"
    s = s.replace(t3, "        for s in swings_trail:\n")
    # 3) momentum gate
    t4 = 'candle_ts_htf=[int(c["ts"]) for c in candles_htf]\n'
    assert s.count(t4) == 1, "htf ts"
    s = s.replace(t4, t4 +
                  '    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]\n'
                  '    closes_htf=[float(c["close"]) for c in candles_htf]\n')
    t5 = '    if sig["dir"] != d: continue\n'
    assert s.count(t5) == 1, "gate"
    s = s.replace(t5, t5 +
                  '        if exp_momentum:\n'
                  '            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+900)-1\n'
                  '            if _j>=2:\n'
                  '                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0\n'
                  '                if sig["dir"]==1 and closes_htf[_j]<_ma: continue\n'
                  '                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue\n')
    # 3b) Exp 18
    t6 = '    ltf_sigs=_collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)\n'
    assert s.count(t6) == 1, "collect sigs"
    s = s.replace(t6, t6 +
        '    if exp18_arm:\n'
        '        _mk=[]\n'
        '        for _si,_s in enumerate(swings_ltf):\n'
        '            for _b in _s.get("breaks",[]):\n'
        '                if _b.get("time"):\n'
        '                    _mk.append((int(_b["idx"]),_si,_b["kind"],\n'
        '                        1 if _b["dir"]=="up" else -1))\n'
        '        _mk.sort(key=lambda z:(z[0],z[1]))\n'
        '        _seq=[]; ltf_sigs=[]\n'
        '        for _mi,_si,_mkind,_md in _mk:\n'
        '            _s=swings_ltf[_si]\n'
        '            _sdir=1 if _s.get("dir")=="up" else -1\n'
        '            _prev=swings_ltf[_si-1] if _si>0 else None\n'
        '            if int(_s.get("swing_index",_si))<1 or _prev is None:\n'
        '                _seq=[]; continue\n'
        '            _pfs=int(_prev.get("confirmed_at_idx",-1))\n'
        '            if _pfs>=0 and _mi<_pfs:\n'
        '                _seq=[]; continue\n'
        '            _res=False; _tdir=0\n'
        '            if not _seq:\n'
        '                if _mkind=="B1": _seq=[_md]\n'
        '            else:\n'
        '                _seq.append(_md)\n'
        '                if len(_seq)==2 and exp18_arm=="D" and _seq[0]!=_seq[1]:\n'
        '                    _tdir=_md; _res=True\n'
        '                elif len(_seq)>=3:\n'
        '                    _a,_b2,_c=_seq[0],_seq[1],_seq[2]\n'
        '                    if exp18_arm=="full": _tdir=_c\n'
        '                    elif exp18_arm=="P1": _tdir=_c if (_a==_b2==_c) else 0\n'
        '                    elif exp18_arm=="P2b": _tdir=(0 if (_a==_b2!=_c) else _c)\n'
        '                    elif exp18_arm=="D": _tdir=_c\n'
        '                    _res=True\n'
        '            if _res:\n'
        '                if _tdir!=0:\n'
        '                    _pe=int(_prev["seg"]["end_idx"]) if _prev is not None else 0\n'
        '                    _rng=range(max(0,_pe),min(_mi,len(candles_ltf)-1)+1)\n'
        '                    _piv=(min(float(candles_ltf[k]["low"]) for k in _rng) if _tdir==1\n'
        '                          else max(float(candles_ltf[k]["high"]) for k in _rng))\n'
        '                    if _piv>0:\n'
        '                        ltf_sigs.append({"bar":candles_ltf[_mi]["date"],\n'
        '                            "dir":_tdir,"swing_start_px":_piv,\n'
        '                            "swing_no":_si,"kind":_mkind})\n'
        '                _seq=[]\n')
    # 3c) Exp 22
    t6b = '        events.sort(key=lambda x: x[0])\n'
    assert s.count(t6b) == 1, "events sort"
    s = s.replace(t6b, t6b +
        '        if exp22_conv:\n'
        '            for _s2 in swings_trail:\n'
        '                if _s2.get("dir") != want_dir: continue\n'
        '                for _b2 in _s2.get("breaks",[]):\n'
        '                    if _b2.get("kind")!="B2": continue\n'
        '                    if (1 if _b2["dir"]=="up" else -1)!=direction: continue\n'
        '                    _b2i=int(_b2["idx"])\n'
        '                    if i<_b2i:\n'
        '                        events.append((_b2i,float(_s2["seg"]["start_px"])))\n'
        '            events.sort(key=lambda x: x[0])\n')
    # 3e) Exp 27
    t6c = '        ev_idx=-1\n'
    assert s.count(t6c) == 1, "ev init"
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
    assert s.count(t6d) == 1, "coarse loop"
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
    # 3f) Exp 31
    t6e = '    chop=_chop_series_1h(candles_htf, lb=14)\n'
    assert s.count(t6e) == 1, "chop lb call"
    s = s.replace(t6e, '    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))\n')
    # 3g) wage gate
    t6f = '        if not (s + 2700 < bar_ts <= e + 2700): continue\n'
    assert s.count(t6f) == 1, "window membership"
    s = s.replace(t6f, t6f +
                  '        if exp_wage_h>0 and (bar_ts-s)/3600.0 < exp_wage_h: continue\n'
                  '        if exp_curfew_b>0 and exp_curfew_a<=(bar_ts-s)/3600.0<exp_curfew_b: continue\n')
    # 3d) persist + mltf
    t8 = '    chop_per_ltf=[50.0]*len(candles_ltf)\n'
    assert s.count(t8) == 1, "chop init"
    s = s.replace(t8, t8 + '    _rg_s=None; _rg_c=0\n')
    t9 = '        # pick intervals\n'
    assert s.count(t9) == 1, "pick intervals"
    s = s.replace(t9,
        '        if exp_persist>0:\n'
        '            if _rg_s is None: _rg_s=use\n'
        '            if use!=_rg_s:\n'
        '                _rg_c+=1\n'
        '                if _rg_c>=exp_persist: _rg_s=use; _rg_c=0\n'
        '            else: _rg_c=0\n'
        '            use=_rg_s\n' + t9)
    t10 = '        if busy_until and bar_time <= busy_until: continue\n'
    assert s.count(t10) == 1, "busy gate"
    s = s.replace(t10, '        if (not exp_mltf) and busy_until and bar_time <= busy_until: continue\n')
    # 4) B3 relocation
    t6 = '        sl_pivot=sig["swing_start_px"]\n'
    assert s.count(t6) == 1, "sl pivot"
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
                  '            if busy_until and bar_time<=busy_until: continue\n'
                  '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n')

    # === ENTRY DISTANCE GATE PATCH ===
    # Place after regime routing (sig["dir"] != d gate) but before sl_pivot
    # The signal's swing_no gives us the swing index in swings_ltf
    t_ed = '        sl_pivot=sig["swing_start_px"]\n'
    ed_patch = ('        if exp_entry_dist_max>0 and exp_entry_dist_max<1.0:\n'
                '            _sw_ed=swings_ltf[sig["swing_no"]] if sig["swing_no"]<len(swings_ltf) else None\n'
                '            if _sw_ed is not None:\n'
                '                _si_ed=int(_sw_ed["seg"]["start_idx"])\n'
                '                _ei_ed=int(_sw_ed["seg"]["end_idx"])\n'
                '                _slen=_ei_ed-_si_ed\n'
                '                if _slen>0 and (i-_si_ed)/_slen>exp_entry_dist_max: continue\n')
    assert s.count(t_ed) == 1, "entry dist anchor"
    s = s.replace(t_ed, ed_patch + t_ed)

    assert s.count('exp_entry_dist_max') >= 3, "entry_dist refs"
    return s


def build_module_entry_dist():
    s = SRC
    s = _build_entry_dist(s)
    m, p = _load_module(s, "la7_edist")
    try: p.unlink()
    except OSError: pass
    return m.simulate_htf_ltf_streak_halt


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
    py = defaultdict(float)
    for t in tr:
        d = t.get("exit_date") or t.get("entry_date") or ""
        py[d[:4]] += float(t["r_multiple"])
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
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
    print("data ready (%0.0fs)" % (time.time() - t0))

    # --- IDENTITY GATE ---
    print("\n=== IDENTITY GATE ===")
    from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt as ship_fn
    r_ship = ship_fn(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    print("  shipped: %dt  gross %+.1fR  WR %.1f%%  DD %.1f" % (s_ship["n"], s_ship["gross"], s_ship["wr"], s_ship["dd"]))

    sim0 = build_module_entry_dist()
    r0 = sim0(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t0r = r0["ltf_trades"] if isinstance(r0, dict) else r0
    s0 = stats(t0r)
    ok = (s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"])
    print("  CRAZE off: %dt  IDENTICAL=%s" % (s0["n"], ok))
    assert ok, "IDENTITY GATE FAILED"

    OPT = dict(exp_mltf=True, exp_persist=2, chop_thresh=55.0, cooldown_bars=10)

    r_anc = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **BASE)
    t_anc = r_anc["ltf_trades"] if isinstance(r_anc, dict) else r_anc
    n_anc = _net(t_anc, _P)
    s_anc = stats(t_anc)
    print("\n  ANCHOR baseline: %dt  NET %+.1fR  WR %.1f%%  DD %.1f" % (s_anc["n"], n_anc, s_anc["wr"], s_anc["dd"]))

    r_opt = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**BASE, **OPT, "exp_wage_h": 24})
    t_opt = r_opt["ltf_trades"] if isinstance(r_opt, dict) else r_opt
    n_opt = _net(t_opt, _P)
    s_opt = stats(t_opt)
    print("  OPT baseline (w24): %dt  NET %+.1fR  WR %.1f%%  DD %.1f" % (s_opt["n"], n_opt, s_opt["wr"], s_opt["dd"]))

    # === SWEEP ===
    dists = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

    print("\n=== ANCHOR: Entry Distance Gate Sweep ===")
    print("  %5s %5s  %8s %8s  %5s %6s %6s" % ("Dist", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 58)
    results_anc = []
    for d in dists:
        try:
            sim = build_module_entry_dist()
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine,
                    **{**BASE, "exp_entry_dist_max": d})
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            s = stats(tr)
            net = _net(tr, _P)
            delta = net - n_anc
            print("  %5.1f %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
                d, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
            results_anc.append({"dist": d, "n": s["n"], "net": round(net, 1),
                                "delta": round(delta, 1), "wr": round(s["wr"], 1),
                                "dd": round(s["dd"], 1), "pf": round(s["pf"], 2),
                                "gross": round(s["gross"], 1)})
        except Exception as e:
            print("  %5.1f  ERROR: %s" % (d, e))

    print("\n=== OPTIMAL (w24): Entry Distance Gate Sweep ===")
    print("  %5s %5s  %8s %8s  %5s %6s %6s" % ("Dist", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 58)
    results_opt = []
    for d in dists:
        try:
            sim = build_module_entry_dist()
            r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine,
                    **{**BASE, **OPT, "exp_wage_h": 24, "exp_entry_dist_max": d})
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            s = stats(tr)
            net = _net(tr, _P)
            delta = net - n_opt
            print("  %5.1f %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
                d, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
            results_opt.append({"dist": d, "n": s["n"], "net": round(net, 1),
                                "delta": round(delta, 1), "wr": round(s["wr"], 1),
                                "dd": round(s["dd"], 1), "pf": round(s["pf"], 2),
                                "gross": round(s["gross"], 1)})
        except Exception as e:
            print("  %5.1f  ERROR: %s" % (d, e))

    out = {
        "anchor": {"baseline_net": round(n_anc, 1), "baseline_n": s_anc["n"],
                    "baseline_wr": round(s_anc["wr"], 1), "baseline_dd": round(s_anc["dd"], 1)},
        "optimal": {"baseline_net": round(n_opt, 1), "baseline_n": s_opt["n"],
                    "baseline_wr": round(s_opt["wr"], 1), "baseline_dd": round(s_opt["dd"], 1)},
        "anchor_results": results_anc,
        "optimal_results": results_opt,
    }
    (ROOT / "backtest/tests/_la7_results.json").write_text(json.dumps(out, indent=1))
    print("\n(la7 done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
