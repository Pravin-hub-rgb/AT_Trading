"""EXP LA14: Deferred entry on atr_high config.

Instead of w24 (drop signals <24h), requeue them to enter at 24h if window still alive.
Test defer horizons {6, 12, 24}h on:
  A) atr_high champion (ext=3.0, cd=8, partR=7.5)
  B) atr_high + w24 (to compare: does defer beat w24?)
"""
import sys, time, json, importlib.util, bisect
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

CHAMPION = {**BASE, "mode": "atr_high", "ext_stop_r": 3.0,
            "cooldown_bars": 8, "exp_partial_r": 7.5}


def _load_module(text, name):
    p = Path(ROOT / "backtest/tests/_la14_tmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def _build_full(s):
    """Full CRAZE + partial + defer patch."""
    t1 = "    *,\n"
    assert s.count(t1) == 1
    s = s.replace(t1, t1 +
                  '    swings_trail=None,\n    exp_momentum=False,\n    b3_k=0,\n    b3_mode="close",\n'
                  '    exp18_arm=None,\n    exp22_conv=False,\n    exp_persist=0,\n    exp_mltf=False,\n'
                  '    exp27_mode=None,\n    exp31_lb=0,\n    exp_wage_h=0,\n'
                  '    exp_curfew_a=0.0,\n    exp_curfew_b=0.0,\n    exp_partial_r=0.0,\n    exp_defer_h=0.0,\n')
    s = s.replace("    import bisect as bs\n", "    import bisect as bs\n    if swings_trail is None: swings_trail=swings_ltf\n")
    s = s.replace("        for s in swings_ltf:\n", "        for s in swings_trail:\n")
    t4 = 'candle_ts_htf=[int(c["ts"]) for c in candles_htf]\n'
    s = s.replace(t4, t4+'    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]\n    closes_htf=[float(c["close"]) for c in candles_htf]\n')
    t5 = '    if sig["dir"] != d: continue\n'
    s = s.replace(t5, t5+
        '        if exp_momentum:\n            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+900)-1\n            if _j>=2:\n                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0\n                if sig["dir"]==1 and closes_htf[_j]<_ma: continue\n                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue\n')

    # DEFER PATCH: requeue young signals instead of dropping
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
    t10 = '        if busy_until and bar_time <= busy_until: continue\n'
    s = s.replace(t10, '        if (not exp_mltf) and busy_until and bar_time <= busy_until: continue\n')
    t6 = '        sl_pivot=sig["swing_start_px"]\n'
    s = s.replace(t6, t6+
        '        if b3_k>0:\n            _lv=float(candles_ltf[i]["high"]) if direction==1 else float(candles_ltf[i]["low"])\n'
        '            _jj=None\n            for _k in range(i+1, min(i+1+b3_k, n-1)):\n'
        '                _hi=float(candles_ltf[_k]["high"]); _lo=float(candles_ltf[_k]["low"])\n'
        '                if direction==1 and _lo<=sl_pivot: break\n                if direction==-1 and _hi>=sl_pivot: break\n'
        '                _cl=float(candles_ltf[_k]["close"])\n                if b3_mode=="wick":\n'
        '                    _hit=(_hi>_lv) if direction==1 else (_lo<_lv)\n                else:\n'
        '                    _hit=(_cl>_lv) if direction==1 else (_cl<_lv)\n                if _hit:\n'
        '                    _jj=_k; break\n            if _jj is None: continue\n'
        '            i=_jj\n            bar_time=candles_ltf[i]["date"]\n'
        '            entry=float(candles_ltf[i]["close"])\n'
        '            if (not exp_mltf) and busy_until and bar_time<=busy_until: continue\n'
        '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n')
    t_pe_init = '        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None\n'
    s = s.replace(t_pe_init, t_pe_init+'        _partial_taken=False; _partial_r=0.0\n')
    t_pe_coarse = ('            if direction==1:\n                if hi>best: best=hi\n'
                   '            else:\n                if lo<best: best=lo\n')
    s = s.replace(t_pe_coarse, t_pe_coarse+
        '            if exp_partial_r>0 and not _partial_taken and risk>0:\n                _cur_r=(best-entry)*direction/risk\n                if _cur_r>=exp_partial_r:\n                    _partial_taken=True; _partial_r=exp_partial_r\n')
    t_pe_fine = ('                if direction==1:\n                    if hi>best_f: best_f=hi\n'
                 '                else:\n                    if lo<best_f: best_f=lo\n')
    s = s.replace(t_pe_fine, t_pe_fine+
        '                if exp_partial_r>0 and not _partial_taken and risk>0:\n                    _cur_rf=(best_f-entry)*direction/risk\n                    if _cur_rf>=exp_partial_r:\n                        _partial_taken=True; _partial_r=exp_partial_r\n')
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
    m, p = _load_module(s, "la14_defer")
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


def stats(tr):
    rs = [float(t["r_multiple"]) for t in tr]
    g = sum(rs)
    peak = 0.0; cum = 0.0; dd = 0.0
    for x in rs:
        cum += x; peak = max(peak, cum); dd = max(dd, peak - cum)
    wr = 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1)
    wins = [x for x in rs if x > 0]; losses = [x for x in rs if x < 0]
    pf = sum(wins) / max(abs(sum(losses)), 1e-9)
    return {"n": len(tr), "gross": g, "wr": wr, "dd": dd, "pf": pf, "rs": rs}


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    fine = _load_fine_1m(min(c1h[0]["ts"], c15[0]["ts"]),
                         max(c1h[-1]["ts"], c15[-1]["ts"]), symbol=INSTRUMENT)
    print("data ready (%0.0fs)" % (time.time() - t0))

    sim0 = build_module()

    # IDENTITY
    from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt as ship_fn
    r_ship = ship_fn(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    r0 = sim0(c1h, sw1h, c15, sw15, fine_ltf=[], **BASE)
    t0r = r0["ltf_trades"] if isinstance(r0, dict) else r0
    s0 = stats(t0r)
    ok = (s0["n"] == s_ship["n"] and s0["rs"] == s_ship["rs"])
    print("  shipped: %dt  gross %+.1fR" % (s_ship["n"], s_ship["gross"]))
    print("  CRAZE off: %dt  IDENTICAL=%s" % (s0["n"], ok))
    assert ok, "IDENTITY GATE FAILED"

    # Baselines
    r_base = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **CHAMPION)
    t_base = r_base["ltf_trades"] if isinstance(r_base, dict) else r_base
    base_net = _net(t_base, _P); s_base = stats(t_base)

    r_w24 = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **{**CHAMPION, "exp_wage_h": 24})
    t_w24 = r_w24["ltf_trades"] if isinstance(r_w24, dict) else r_w24
    net_w24 = _net(t_w24, _P); s_w24 = stats(t_w24)

    print("\n  Baseline (no gate):  %dt  NET %+.1fR  WR %.1f%%  DD %.1f  PF %.2f" % (
        s_base["n"], base_net, s_base["wr"], s_base["dd"], s_base["pf"]))
    print("  w24 (drop <24h):     %dt  NET %+.1fR  WR %.1f%%  DD %.1f  PF %.2f" % (
        s_w24["n"], net_w24, s_w24["wr"], s_w24["dd"], s_w24["pf"]))

    # Defer sweep
    print("\n=== Deferred Entry Sweep (atr_high champion) ===")
    print("  %-12s %5s  %8s %8s  %5s  %6s  %6s" % ("Variant", "Tr", "NET", "Delta", "WR", "DD", "PF"))
    print("  " + "-" * 68)
    for label, defer_h, wage_h in [("w0", 0, 0), ("w24", 0, 24),
                                    ("d6", 6, 0), ("d12", 12, 0), ("d24", 24, 0)]:
        cfg = {**CHAMPION}
        if wage_h > 0: cfg["exp_wage_h"] = wage_h
        if defer_h > 0: cfg["exp_defer_h"] = defer_h
        r = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
        tr = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(tr); net = _net(tr, _P); delta = net - base_net
        print("  %-12s %5d  %+8.1fR %+8.1f  %5.1f%%  %5.1fR  %5.2f" % (
            label, s["n"], net, delta, s["wr"], s["dd"], s["pf"]))

    # Also test defer x ext combos
    print("\n=== Defer x Ext Combos ===")
    for ext in [1.5, 2.0, 2.5, 3.0]:
        for label, defer_h, wage_h in [("w0", 0, 0), ("w24", 0, 24), ("d24", 24, 0)]:
            cfg = {**BASE, "mode": "atr_high", "cooldown_bars": 8,
                   "exp_partial_r": 7.5, "ext_stop_r": ext}
            if wage_h > 0: cfg["exp_wage_h"] = wage_h
            if defer_h > 0: cfg["exp_defer_h"] = defer_h
            r = sim0(c1h, sw1h, c15, sw15, fine_ltf=fine, **cfg)
            tr = r["ltf_trades"] if isinstance(r, dict) else r
            s = stats(tr); net = _net(tr, _P)
            print("  ext=%.1f %-6s %4dt NET=%+8.1fR WR=%.1f%% DD=%.1f PF=%.2f" % (
                ext, label, s["n"], net, s["wr"], s["dd"], s["pf"]))
        print()

    print("\n(la14 done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
