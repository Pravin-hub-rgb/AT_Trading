"""EXP LA11: Extensions sweep on new champion (OPT atr_high + partR=5.0).

Sweep remaining levers on the best config found so far:
  A) Wage gate hours (20, 24, 28, 32)
  B) B3 relocation (k=2,4,6,8,10)
  C) Conviction filter (conv_r = 0.5, 1.0, 2.0)
  D) Curfew (a/b combos)
  E) Persist (1, 2, 3)
  F) Cooldown (5, 10, 15)
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

CHAMPION = {**BASE, "mode": "atr_high", "exp_partial_r": 5.0,
            "exp_mltf": True, "exp_persist": 2, "chop_thresh": 55.0, "cooldown_bars": 10}


def _load_module(text, name):
    p = Path(ROOT / "backtest/tests/_la11_tmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def _build_craze_partial(s):
    """CRAZE superset + partial exit patch."""
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
                  '    exp_partial_r=0.0,\n')
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
    t6e = '    chop=_chop_series_1h(candles_htf, lb=14)\n'
    assert s.count(t6e) == 1, "chop lb call"
    s = s.replace(t6e, '    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))\n')
    t6f = '        if not (s + 2700 < bar_ts <= e + 2700): continue\n'
    assert s.count(t6f) == 1, "window membership"
    s = s.replace(t6f, t6f +
                  '        if exp_wage_h>0 and (bar_ts-s)/3600.0 < exp_wage_h: continue\n'
                  '        if exp_curfew_b>0 and exp_curfew_a<=(bar_ts-s)/3600.0<exp_curfew_b: continue\n')
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

    # === PARTIAL EXIT PATCH ===
    t_pe_init = '        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None\n'
    assert s.count(t_pe_init) == 1, "pe init"
    s = s.replace(t_pe_init, t_pe_init +
                  '        _partial_taken=False; _partial_r=0.0\n')
    t_pe_coarse = ('            if direction==1:\n'
                   '                if hi>best: best=hi\n'
                   '            else:\n'
                   '                if lo<best: best=lo\n')
    pe_coarse = ('            if direction==1:\n'
                 '                if hi>best: best=hi\n'
                 '            else:\n'
                 '                if lo<best: best=lo\n'
                 '            if exp_partial_r>0 and not _partial_taken and risk>0:\n'
                 '                _cur_r=(best-entry)*direction/risk\n'
                 '                if _cur_r>=exp_partial_r:\n'
                 '                    _partial_taken=True; _partial_r=exp_partial_r\n')
    assert s.count(t_pe_coarse) == 1, "pe coarse"
    s = s.replace(t_pe_coarse, pe_coarse)
    t_pe_fine = ('                if direction==1:\n'
                 '                    if hi>best_f: best_f=hi\n'
                 '                else:\n'
                 '                    if lo<best_f: best_f=lo\n')
    pe_fine = ('                if direction==1:\n'
               '                    if hi>best_f: best_f=hi\n'
               '                else:\n'
               '                    if lo<best_f: best_f=lo\n'
               '                if exp_partial_r>0 and not _partial_taken and risk>0:\n'
               '                    _cur_rf=(best_f-entry)*direction/risk\n'
               '                    if _cur_rf>=exp_partial_r:\n'
               '                        _partial_taken=True; _partial_r=exp_partial_r\n')
    assert s.count(t_pe_fine) == 1, "pe fine"
    s = s.replace(t_pe_fine, pe_fine)
    t_r = ('        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
            '        r_multiple=move/risk if risk>0 else 0\n')
    assert s.count(t_r) == 1, "r calc"
    s = s.replace(t_r,
                  '        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
                  '        if _partial_taken and risk>0:\n'
                  '            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
                  '            r_multiple=_partial_r+(_rem_move/risk)*0.5\n'
                  '        else:\n'
                  '            r_multiple=move/risk if risk>0 else 0\n')
    assert s.count('exp_partial_r') >= 3, "partial_r refs"

    return s


def build_module():
    s = SRC
    s = _build_craze_partial(s)
    m, p = _load_module(s, "la11_ext")
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
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1)
    wins = [x for x in rs if x > 0]
    losses = [x for x in rs if x < 0]
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    return {"n": len(tr), "gross": g, "rs": rs, "wr": wr, "dd": dd, "mx": mx, "pf": pf}


def sweep(sim, c1h, sw1h, c15, sw15, fine, grid, label, base_champ):
    print("\n=== %s ===" % label)
    print("  %-22s %5s  %8s %8s  %5s %6s %6s" % ("Setting", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 80)
    best_net = -9999; best_cfg = None; best_info = None
    results = []
    for name, overrides in grid:
        cfg = {**base_champ, **overrides}
        r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr); net = _net(tr, _P)
        delta = net - base_net
        print("  %-22s %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
            name, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
        results.append({"name": name, "overrides": overrides, "n": s["n"],
            "net": round(net, 1), "delta": round(delta, 1), "wr": round(s["wr"], 1),
            "dd": round(s["dd"], 1), "pf": round(s["pf"], 2), "gross": round(s["gross"], 1)})
        if net > best_net:
            best_net = net; best_cfg = overrides
            best_info = {"name": name, "net": round(net, 1), "delta": round(delta, 1),
                         "n": s["n"], "wr": round(s["wr"], 1), "dd": round(s["dd"], 1),
                         "pf": round(s["pf"], 2), "gross": round(s["gross"], 1)}
    print("\n  BEST: %s NET=%+.1fR (delta=%+.1f)" % (best_info["name"] if best_info else "?",
                                                      best_info["net"] if best_info else 0,
                                                      best_info["delta"] if best_info else 0))
    return results, best_cfg, best_info


def main():
    global base_net
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
    print("  shipped: %dt  gross %+.1fR" % (s_ship["n"], s_ship["gross"]))

    sim0 = build_module()
    r0 = sim0(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t0r = r0["ltf_trades"] if isinstance(r0, dict) else r0
    s0 = stats(t0r)
    ok = (s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"])
    print("  CRAZE off: %dt  IDENTICAL=%s" % (s0["n"], ok))
    assert ok, "IDENTITY GATE FAILED"

    # Champion baseline
    r_champ = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **CHAMPION)
    t_champ = r_champ["ltf_trades"] if isinstance(r_champ, dict) else r_champ
    base_net = _net(t_champ, _P); s_champ = stats(t_champ)
    print("\n  CHAMPION baseline: %dt  NET %+.1fR  WR %.1f%%  DD %.1f  PF %.2f" % (
        s_champ["n"], base_net, s_champ["wr"], s_champ["dd"], s_champ["pf"]))
    champ_big = sorted([t for t in t_champ if float(t["r_multiple"]) >= 10.0],
                       key=lambda t: -float(t["r_multiple"]))
    print("  monsters (>10R): %d  R=%s" % (
        len(champ_big), "+".join("%.1f" % float(t["r_multiple"]) for t in champ_big)[:70]))

    all_results = {}

    # A) Wage gate hours
    w_grid = [("w20", {"exp_wage_h": 20}), ("w24", {"exp_wage_h": 24}),
              ("w28", {"exp_wage_h": 28}), ("w32", {"exp_wage_h": 32})]
    r, bc, bi = sweep(sim0, c1h, sw1h, c15, sw15, fine, w_grid, "A: Wage Gate Hours", CHAMPION)
    all_results["wage_gate"] = r

    # B) B3 relocation
    b3_grid = [("b3_k=2", {"b3_k": 2}), ("b3_k=4", {"b3_k": 4}),
               ("b3_k=6", {"b3_k": 6}), ("b3_k=8", {"b3_k": 8}),
               ("b3_k=10", {"b3_k": 10})]
    r, bc, bi = sweep(sim0, c1h, sw1h, c15, sw15, fine, b3_grid, "B: B3 Relocation", CHAMPION)
    all_results["b3"] = r

    # C) Curfew
    cf_grid = [("curfew 0-8", {"exp_curfew_a": 0.0, "exp_curfew_b": 8.0}),
               ("curfew 0-4", {"exp_curfew_a": 0.0, "exp_curfew_b": 4.0}),
               ("curfew 4-8", {"exp_curfew_a": 4.0, "exp_curfew_b": 8.0}),
               ("curfew 16-20", {"exp_curfew_a": 16.0, "exp_curfew_b": 20.0})]
    r, bc, bi = sweep(sim0, c1h, sw1h, c15, sw15, fine, cf_grid, "C: Curfew", CHAMPION)
    all_results["curfew"] = r

    # D) Persist
    p_grid = [("persist=1", {"exp_persist": 1, "exp_mltf": True}),
              ("persist=2", {"exp_persist": 2, "exp_mltf": True}),
              ("persist=3", {"exp_persist": 3, "exp_mltf": True}),
              ("persist=5", {"exp_persist": 5, "exp_mltf": True})]
    r, bc, bi = sweep(sim0, c1h, sw1h, c15, sw15, fine, p_grid, "D: Persist", CHAMPION)
    all_results["persist"] = r

    # E) Cooldown
    cd_grid = [("cd=5", {"cooldown_bars": 5}), ("cd=10", {"cooldown_bars": 10}),
               ("cd=15", {"cooldown_bars": 15}), ("cd=20", {"cooldown_bars": 20})]
    r, bc, bi = sweep(sim0, c1h, sw1h, c15, sw15, fine, cd_grid, "E: Cooldown", CHAMPION)
    all_results["cooldown"] = r

    # Find overall best extension
    all_best = []
    for sec, res in all_results.items():
        for r in res:
            all_best.append({**r, "section": sec})
    all_best.sort(key=lambda x: -x["net"])
    print("\n=== TOP 5 EXTENSIONS ===")
    print("  %-6s %-22s  %5s  %8s %8s  %5s %6s %6s" % ("Sec", "Setting", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    for x in all_best[:5]:
        print("  %-6s %-22s  %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
            x["section"], x["name"], x["n"], x["net"], x["delta"], x["wr"], x["dd"], x["pf"]))

    out = {
        "champion_baseline": {"net": round(base_net, 1), "n": s_champ["n"],
                              "wr": round(s_champ["wr"], 1), "dd": round(s_champ["dd"], 1),
                              "pf": round(s_champ["pf"], 2)},
        "results": all_results,
        "top5": [{"name": x["name"], "section": x["section"],
                   "net": x["net"], "delta": x["delta"]} for x in all_best[:5]],
    }
    (ROOT / "backtest/tests/_la11_results.json").write_text(json.dumps(out, indent=1))
    print("\n(la11 done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
