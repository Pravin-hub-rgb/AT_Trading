"""EXP LA12: Ultra-optimize the new champion (+379.3R).

Champion: atr_high + partR=5.0 + mltf + persist=2 + cd=10 + chop_thresh=55 + ext_stop=2.5
Test:
  A) partR sweep (3.0 to 7.0 in 0.5 steps) — is 5.0 truly optimal?
  B) ext_stop sweep (1.5 to 3.5) — is 2.5 optimal for atr_high?
  C) cooldown sweep on the champion (5 to 20)
  D) chop_thresh sweep (50, 55, 60, 65, 70)
  E) persist sweep (1, 2, 3, 5, 7)
  F) curfew 16-20 added
"""
import sys, time, json, importlib.util
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

CHAMPION = {**BASE, "mode": "atr_high", "exp_partial_r": 5.0,
            "exp_mltf": True, "exp_persist": 2, "chop_thresh": 55.0, "cooldown_bars": 10}


def _load_module(text, name):
    p = Path(ROOT / "live_stuff/tests/_la12_tmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def _build_full(s):
    """Full CRAZE + partial patch."""
    t1 = "    *,\n"
    assert s.count(t1) == 1
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
    s = s.replace("    import bisect as bs\n", "    import bisect as bs\n    if swings_trail is None: swings_trail=swings_ltf\n")
    s = s.replace("        for s in swings_ltf:\n", "        for s in swings_trail:\n")
    t4 = 'candle_ts_htf=[int(c["ts"]) for c in candles_htf]\n'
    s = s.replace(t4, t4+'    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]\n    closes_htf=[float(c["close"]) for c in candles_htf]\n')
    t5 = '    if sig["dir"] != d: continue\n'
    s = s.replace(t5, t5+
                  '        if exp_momentum:\n'
                  '            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+900)-1\n'
                  '            if _j>=2:\n'
                  '                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0\n'
                  '                if sig["dir"]==1 and closes_htf[_j]<_ma: continue\n'
                  '                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue\n')
    t6c = '        ev_idx=-1\n'
    s = s.replace(t6c, t6c+'        opp_events=[]\n        if exp27_mode:\n            for _s9 in swings_ltf:\n                for _b9 in _s9.get("breaks",[]):\n                    if _b9.get("time") and (1 if _b9["dir"]=="up" else -1)==-direction:\n                        opp_events.append((int(_b9["idx"]), _b9.get("kind","")))\n            opp_events.sort(key=lambda z: z[0])\n            opp_ev_idx=-1\n            while opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= i:\n                opp_ev_idx += 1\n')
    t6d = ('        for j in range(i+1, n if not fine_ltf else i+1):\n'
           '            c=candles_ltf[j]\n'
           '            hi=float(c["high"]); lo=float(c["low"])\n')
    s = s.replace(t6d, t6d+
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
    s = s.replace(t8, t8+'    _rg_s=None; _rg_c=0\n')
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
    assert s.count(t6) == 1
    s = s.replace(t6, t6+
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
    s = s.replace(t_pe_init, t_pe_init+'        _partial_taken=False; _partial_r=0.0\n')

    t_pe_coarse = ('            if direction==1:\n'
                   '                if hi>best: best=hi\n'
                   '            else:\n'
                   '                if lo<best: best=lo\n')
    s = s.replace(t_pe_coarse, t_pe_coarse+
        '            if exp_partial_r>0 and not _partial_taken and risk>0:\n'
        '                _cur_r=(best-entry)*direction/risk\n'
        '                if _cur_r>=exp_partial_r:\n'
        '                    _partial_taken=True; _partial_r=exp_partial_r\n')

    t_pe_fine = ('                if direction==1:\n'
                 '                    if hi>best_f: best_f=hi\n'
                 '                else:\n'
                 '                    if lo<best_f: best_f=lo\n')
    s = s.replace(t_pe_fine, t_pe_fine+
        '                if exp_partial_r>0 and not _partial_taken and risk>0:\n'
        '                    _cur_rf=(best_f-entry)*direction/risk\n'
        '                    if _cur_rf>=exp_partial_r:\n'
        '                        _partial_taken=True; _partial_r=exp_partial_r\n')

    t_r = ('        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
            '        r_multiple=move/risk if risk>0 else 0\n')
    s = s.replace(t_r,
        '        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
        '        if _partial_taken and risk>0:\n'
        '            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
        '            r_multiple=_partial_r+(_rem_move/risk)*0.5\n'
        '        else:\n'
        '            r_multiple=move/risk if risk>0 else 0\n')
    return s


def build_module():
    s = _build_full(SRC)
    m, p = _load_module(s, "la12_ultra")
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


def sweep(sim, c1h, sw1h, c15, sw15, fine, grid, label):
    print("\n=== %s ===" % label)
    print("  %-20s %5s  %8s %8s  %5s %6s %6s" % ("Setting", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 78)
    best_net = -9999; best_name = "?"; best_info = None
    results = []
    for name, overrides in grid:
        cfg = {**CHAMPION, **overrides}
        r = sim(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr); net = _net(tr, _P); delta = net - base_net
        print("  %-20s %5d  %+8.1f %+8.1f  %5.1f %6.1f %5.2f" % (
            name, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
        results.append({"name": name, "n": s["n"], "net": round(net, 1), "delta": round(delta, 1),
            "wr": round(s["wr"], 1), "dd": round(s["dd"], 1), "pf": round(s["pf"], 2),
            "gross": round(s["gross"], 1)})
        if net > best_net:
            best_net = net; best_name = name
            best_info = results[-1]
    print("  BEST: %s NET=%+.1fR" % (best_name, best_net))
    return results


def main():
    global base_net
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    print("data ready (%0.0fs)" % (time.time() - t0))

    # IDENTITY
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
    assert ok

    # Champion baseline
    r_ch = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **CHAMPION)
    t_ch = r_ch["ltf_trades"] if isinstance(r_ch, dict) else r_ch
    base_net = _net(t_ch, _P); s_ch = stats(t_ch)
    print("\n  CHAMPION baseline: %dt  NET %+.1fR  WR %.1f%%  DD %.1f  PF %.2f" % (
        s_ch["n"], base_net, s_ch["wr"], s_ch["dd"], s_ch["pf"]))
    champ_big = sorted([t for t in t_ch if float(t["r_multiple"]) >= 10.0],
                       key=lambda t: -float(t["r_multiple"]))
    print("  monsters (>10R): %d  R=%s" % (
        len(champ_big), "+".join("%.1f" % float(t["r_multiple"]) for t in champ_big)[:80]))

    all_results = {}

    # A) partR sweep
    pr_grid = [("partR=%.1f" % r, {"exp_partial_r": r}) for r in [x/10 for x in range(20, 80, 5)]]
    all_results["partR"] = sweep(sim0, c1h, sw1h, c15, sw15, fine, pr_grid, "A: partR Sweep (3.0 to 7.5)")

    # B) ext_stop sweep
    es_grid = [("ext=%.1f" % r, {"ext_stop_r": r}) for r in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]]
    all_results["ext_stop"] = sweep(sim0, c1h, sw1h, c15, sw15, fine, es_grid, "B: ext_stop Sweep")

    # C) cooldown sweep
    cd_grid = [("cd=%d" % c, {"cooldown_bars": c}) for c in [5, 8, 10, 12, 15, 20]]
    all_results["cooldown"] = sweep(sim0, c1h, sw1h, c15, sw15, fine, cd_grid, "C: Cooldown Sweep")

    # D) chop_thresh sweep
    ct_grid = [("ct=%d" % c, {"chop_thresh": float(c)}) for c in [50, 52, 55, 58, 60, 65]]
    all_results["chop_thresh"] = sweep(sim0, c1h, sw1h, c15, sw15, fine, ct_grid, "D: chop_thresh Sweep")

    # E) persist sweep
    pe_grid = [("p=%d" % p, {"exp_persist": p, "exp_mltf": True}) for p in [1, 2, 3, 5, 7]]
    all_results["persist"] = sweep(sim0, c1h, sw1h, c15, sw15, fine, pe_grid, "E: Persist Sweep")

    # F) Combined best extensions
    print("\n=== F: Best Extensions Stacked ===")
    # From A-E, find the best overrides and stack them
    best_per_sec = {}
    for sec, res in all_results.items():
        best_r = max(res, key=lambda x: x["net"])
        best_per_sec[sec] = best_r
        print("  %s best: %s NET=%+.1fR (delta=%+.1f)" % (sec, best_r["name"], best_r["net"], best_r["delta"]))

    # Try stacking all best overrides (skip if delta <= 0)
    stack = {}
    for sec, res in all_results.items():
        best_r = max(res, key=lambda x: x["net"])
        if best_r["delta"] > 0 and sec in ("partR", "ext_stop", "cooldown", "chop_thresh", "persist"):
            # Get the overrides from the grid
            grids = {"partR": pr_grid, "ext_stop": es_grid, "cooldown": cd_grid,
                     "chop_thresh": ct_grid, "persist": pe_grid}
            for name, overrides in grids[sec]:
                if name == best_r["name"]:
                    stack.update(overrides)
                    break

    if stack:
        print("\n  stacked overrides:", stack)
        cfg = {**CHAMPION, **stack}
        r = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr); net = _net(tr, _P); delta = net - base_net
        print("  STACKED: %dt NET=%+.1fR delta=%+.1f WR=%.1f%% DD=%.1f PF=%.2f" % (
            s["n"], net, delta, s["wr"], s["dd"], s["pf"]))
        big = sorted([t for t in tr if float(t["r_multiple"]) >= 10.0],
                     key=lambda t: -float(t["r_multiple"]))
        print("  monsters (>10R): %d  R=%s" % (
            len(big), "+".join("%.1f" % float(t["r_multiple"]) for t in big)[:80]))

    # Also test champion + curfew 16-20
    print("\n  --- Champion + curfew 16-20 ---")
    cfg2 = {**CHAMPION, "exp_curfew_a": 16.0, "exp_curfew_b": 20.0}
    r2 = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg2)
    tr2 = r2["ltf_trades"] if isinstance(r2, dict) else r2
    s2 = stats(tr2); net2 = _net(tr2, _P)
    print("  curfew 16-20: %dt NET=%+.1fR delta=%+.1f WR=%.1f%% DD=%.1f PF=%.2f" % (
        s2["n"], net2, net2-base_net, s2["wr"], s2["dd"], s2["pf"]))

    out = {
        "champion_baseline": {"net": round(base_net, 1), "n": s_ch["n"],
                              "wr": round(s_ch["wr"], 1), "dd": round(s_ch["dd"], 1),
                              "pf": round(s_ch["pf"], 2)},
        "results": all_results,
        "best_per_section": {k: {"name": v["name"], "net": v["net"], "delta": v["delta"]}
                            for k, v in best_per_sec.items()},
    }
    (ROOT / "live_stuff/tests/_la12_results.json").write_text(json.dumps(out, indent=1))
    print("\n(la12 done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
