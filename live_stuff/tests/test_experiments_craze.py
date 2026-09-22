"""CRAZE harness — runs the SHIPPED engine source with minimal asserted patches.

Safety model (no retyped engine, no look-ahead):
- We load backend/src/btc/engines/htf_ltf/v18_streak_halt.py SOURCE TEXT.
- With no experiment flags, we exec the unmodified text -> byte-identical engine.
- Each experiment is a tiny, assertion-checked text patch (token counts asserted).
- Identity gate: patched-with-flags-off MUST reproduce the shipped engine's
  trade list exactly (same n, same R list) before any experiment result is shown.

Experiments:
  split_mb   : trail events from a slower/faster 15m swing chain (Exp 11)
  momentum   : 1h close vs 3-bar 1h MA agreement gate at entry (Exp 16)
"""
import sys, time, importlib.util
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

ENGINE = ROOT / "backend/src/btc/engines/htf_ltf/v18_streak_halt.py"
SRC = ENGINE.read_text(encoding="utf-8")

from replay_harness import load_candles, INSTRUMENT
from engine.v18_params import SWING, get_v18_params, V18_ENGINE
from src.btc.btc_routes import _compute_swings
import src.btc.engines.htf_ltf.v18_streak_halt as shipped_mod

_P = dict(get_v18_params(INSTRUMENT)); _P.update(V18_ENGINE)
BASE = {k: _P[k] for k in ["sl_buf_atr", "ext_stop_r", "chop_thresh",
                           "atr_low_thresh", "atr_high_thresh", "mode",
                           "cooldown_bars", "max_consecutive_losses",
                           "htf_rr", "window_end"] if k in _P}
MB15 = SWING["min_bars_15m"]


def _load_module(text, name):
    p = Path(ROOT / "live_stuff/tests/_craze_tmp.py")
    p.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m, p


def build_module():
    """Shipped source + ONE super-set patch; every experiment is a runtime kwarg.

    All patches are no-ops at default kwargs, and main()'s identity gate proves
    defaults == shipped engine exactly.
    """
    s = SRC
    # 1) extra kwargs (default-off)
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
                  '    exp_defer_h=0.0,\n'
                  '    exp_legskip_r=0.0,\n'
                  '    exp_partial_r=0.0,\n'
                  '    exp_skipwin=0,\n'
                  '    exp_swingpause=0,\n'
                  '    exp_skipwin_halt=0,\n'
                  '    exp_skip_weekend=0,\n'
                  '    exp_kinds="",\n'
                  '    exp_skip_utc_sat=0,\n'
                  '    exp_skip_utc_sun=0,\n'
                  '    exp_risk_max_pct=0.0,\n'
                  '    exp_chop15_lo=0.0,\n'
                  '    exp_chop15_hi=0.0,\n'
                  '    exp_atr_ratio_max=0.0,\n'
                  '    exp_max_concurrent=0,\n'
                  '    exp_entry_candle_min=0.0,\n'
                  '    exp_entry_swing_age_max=0,\n'
                  '    exp_entry_skip_b2_doji=0,\n')
    # 2) split-mb: trail events from an optional second chain
    t2 = "    import bisect as bs\n"
    assert s.count(t2) == 1, "bisect"
    s = s.replace(t2, t2 + "    if swings_trail is None: swings_trail=swings_ltf\n")
    t3 = "        for s in swings_ltf:\n"
    assert s.count(t3) == 1, "trail loop"
    s = s.replace(t3, "        for s in swings_trail:\n")
    # 3) momentum gate (C14-aligned 1h close vs 3-bar MA)
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
    # 3b) Exp 18: 3-Mark Judgment System — signals from the breaks mark stream.
    # B1-anchored sequences resolve at the 3rd mark (arm "D": 2-mark flips).
    # SL attribution mirrors _collect_signals: same-dir mark -> swing start_px,
    # opposite-dir mark -> prev swing end_px, pre-start churn -> touchable
    # extreme since prev_end. filter_pre_fs honored. B1 decisions resolve
    # silently (B1s are not tradeable in v18 semantics).
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
    # 3c) Exp 22: conviction trail — ratchet each same-dir swing's trail level
    # at its B2 MARK (break) instead of its confirmation (which lags ~mb bars).
    # Same pivot, earlier activation; ratchet conditions still gate it.
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
    # 3e) Exp 27: opposite-mark stop accelerator (audit Q7). While in a trade,
    # exit at the close of the bar where the first OPPOSITE-dir swing break
    # mark confirms. Modes: "all" = any opposite mark; "loss" = only if
    # unrealized R < 0 at that bar; "fliploss" = FLIP-kind only + R < 0.
    # Coarse loop only (marks are 15m bars; fine promotion later if it earns it).
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
    # 3f) Exp 31: HTF chop lookback (lb) sweep — regime-detection responsiveness.
    # Shipped default 14. exp31_lb=0 keeps shipped (identity).
    t6e = '    chop=_chop_series_1h(candles_htf, lb=14)\n'
    assert s.count(t6e) == 1, "chop lb call"
    s = s.replace(t6e, '    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))\n')
    # 3g) N5/N6 wage gate: skip entries inside HTF windows younger than
    #     exp_wage_h hours. Age = signal-bar ts - RAW window start ts (the
    #     window's flip/b2 1h entry-bar OPEN; no +2700 shift). This is the
    #     FINAL convention: validated 4/4 exact vs the user's coarse matrix
    #     (265/294/304/307t) and 4/4 vs the user's fine table (196.3/
    #     231.1/197.2/179.1). See docs/EXP40C_EXP41_WAGE_EXT.md sections
    #     3.1 and 4.3. The deleted Exp40/41 harness's N5 rows (275t/+224.5
    #     etc.) used an unrecoverable convention and are non-authoritative;
    #     earlier +2700, closed-candle, canonical-parent and leg-anchor
    #     variants were all tested and rejected (audit trail: doc sec 4.3).
    t6f = '        if not (s + 2700 < bar_ts <= e + 2700): continue\n'
    assert s.count(t6f) == 1, "window membership"
    s = s.replace(t6f, t6f +
                  '        if exp_wage_h>0 and (bar_ts-s)/3600.0 < exp_wage_h: continue\n'
                  '        if exp_curfew_b>0 and exp_curfew_a<=(bar_ts-s)/3600.0<exp_curfew_b: continue\n'
                  '        if exp_legskip_r>0:\n'
                  '            _j2=idx\n'
                  '            while _j2>0 and intervals[_j2-1][2]==d: _j2-=1\n'
                  '            _anc=intervals[_j2][0]\n'
                  '            _li=bs.bisect_right(candle_ts_htf,_anc); _hi2=bs.bisect_right(candle_ts_htf,bar_ts)\n'
                  '            _hr=abs(pe-psl)\n'
                  '            if _hr>0 and _hi2>_li:\n'
                  '                _prog=(float(candles_ltf[bar]["close"])-_anc)*d/_hr\n'
                  '                if _prog>exp_legskip_r: continue\n')
    # 3h) deferred entry: a too-young signal is NOT dropped - it is requeued to
    #     the first 15m bar at/after s+defer_h*3600 (window still open, original
    #     SL pivot untouched meanwhile, ext re-checked at the defer bar). The
    #     ledger stays causal: filtered is re-sorted by FINAL bar after the
    #     loop (no-op when no deferral). Entry at the defer bar close; the
    #     walk's busy/cooldown/halt all apply there (entry-time data only).
    t6g = '        if sig["dir"] != d: continue\n'
    assert s.count(t6g) == 1, "dir gate"
    s = s.replace(t6g, t6g +
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
    t6h = '        filtered.append((sig, use))\n'
    assert s.count(t6h) == 1, "filtered append"
    s = s.replace(t6h, t6h +
                  '    filtered.sort(key=lambda z: ltf_store.pos(z[0]["bar"]))\n')
    # 3d) their-lane ports: regime persistence hysteresis + multi-LTF (no busy)
    t8 = '    chop_per_ltf=[50.0]*len(candles_ltf)\n'
    assert s.count(t8) == 1, "chop init"
    s = s.replace(t8, t8 + '    _rg_s=None; _rg_c=0\n')
    # 3d-2) D3 cooldown family: loss-triggered HTF-window skip + swing-confirm pause.
    #   exp_skipwin=N   : after a LOSS at exit time L, entries are blocked while
    #                     the covering HTF window is one of the first N windows
    #                     OPENED after L (skip the same broken bias track).
    #   exp_swingpause  : after a LOSS, block entries until at least one NEW 15m
    #                     swing has CONFIRMED after L (fresh structure exists).
    #   Both are causal: decided at entry time from past data only.
    t_c1 = '    candle_ts_ltf=[int(c["ts"]) for c in candles_ltf]\n'
    assert s.count(t_c1) == 1, "candle_ts_ltf"
    s = s.replace(t_c1, t_c1 +
                  '    _sw_pairs=sorted((candle_ts_ltf[int(sw["confirmed_at_idx"])], candle_ts_ltf[int(sw["seg"]["start_idx"])]) for sw in swings_ltf if sw.get("confirmed_at_idx") is not None and 0 <= int(sw["confirmed_at_idx"]) < len(candle_ts_ltf) and sw.get("seg") is not None and 0 <= int(sw["seg"].get("start_idx", -1)) < len(candle_ts_ltf))\n'
                  '    confs_ts=[p[0] for p in _sw_pairs]\n'
                  '    pivs_ts=[p[1] for p in _sw_pairs]\n')
    t_c2 = '    last_loss_bar=-999999\n'
    assert s.count(t_c2) == 1, "last_loss_bar"
    s = s.replace(t_c2, t_c2 + '    last_loss_ts=0\n    halt_ts=0\n    _open_count=0\n')
    t_c3 = '        if cooldown_bars > 0 and r_multiple < 0:\n            last_loss_bar = exit_idx\n'
    assert s.count(t_c3) == 1, "loss hook"
    s = s.replace(t_c3, t_c3 +
                  '        if r_multiple < 0:\n            last_loss_ts=int(exit_ts)\n')
    t_c3b = '                    halt_skip_next = True  # skip the NEXT entry\n'
    assert s.count(t_c3b) == 1, "halt hook"
    s = s.replace(t_c3b, t_c3b +
                  '                    if exp_skipwin_halt > 0:\n                        halt_ts = int(exit_ts)\n')
    t_c4 = '        direction=int(sig["dir"])\n'
    assert s.count(t_c4) == 1, "walk dir"
    s = s.replace(t_c4,
                  '        if exp_skipwin > 0 and last_loss_ts > 0:\n'
                  '            if use == "flip":\n'
                  '                _starts = starts_flip\n'
                  '            elif use == "b2":\n'
                  '                _starts = starts_b2\n'
                  '            else:\n'
                  '                _starts = starts_decisive\n'
                  '            _idx = bs.bisect_right(_starts, candle_ts[i]) - 1\n'
                  '            if _idx >= 0 and _idx - bs.bisect_right(_starts, last_loss_ts) + 1 <= exp_skipwin:\n'
                  '                continue\n'
                  '        if exp_skipwin_halt > 0 and halt_ts > 0:\n'
                  '            if use == "flip":\n'
                  '                _starts2 = starts_flip\n'
                  '            elif use == "b2":\n'
                  '                _starts2 = starts_b2\n'
                  '            else:\n'
                  '                _starts2 = starts_decisive\n'
                  '            _idx2 = bs.bisect_right(_starts2, candle_ts[i]) - 1\n'
                  '            if _idx2 >= 0 and _idx2 - bs.bisect_right(_starts2, halt_ts) + 1 <= exp_skipwin_halt:\n'
                  '                continue\n'
                   '        if exp_swingpause > 0 and last_loss_ts > 0:\n'
                   '            _si = bs.bisect_right(confs_ts, candle_ts[i]) - 1\n'
                   '            if _si < 0 or pivs_ts[_si] <= last_loss_ts:\n'
                   '                continue\n'
                  '        if exp_max_concurrent > 0:\n'
                  '            _now_ts = candle_ts[i]\n'
                  '            _open_now = sum(1 for _t in ltf_trades if int(_t["exit_ts"]) > _now_ts)\n'
                  '            if _open_now >= exp_max_concurrent:\n'
                  '                continue\n'
                  + t_c4)
    # 3d-3) D3 pattern gates from the loss autopsy: weekend skip + entry-kind filter.
    t_c5 = '    halt_ts=0\n'
    assert s.count(t_c5) == 1, "halt_ts init"
    s = s.replace(t_c5, t_c5 +
                  '    _wd_cache={}\n'
                  '    def _is_weekend(dstr):\n'
                  '        _d = dstr[:10]\n'
                  '        _w = _wd_cache.get(_d)\n'
                  '        if _w is None:\n'
                  '            import datetime as _dt\n'
                  '            _w = _dt.date(int(_d[:4]), int(_d[5:7]), int(_d[8:10])).weekday()\n'
                  '            _wd_cache[_d] = _w\n'
                  '        return _w\n'
                  '    def _utc_wd(dstr):\n'
                  '        import datetime as _dt\n'
                  '        _p = _dt.datetime.strptime(dstr[:16], "%Y-%m-%d %H:%M")\n'
                  '        return (_p - _dt.timedelta(hours=5, minutes=30)).weekday()\n')
    t_c6 = '        direction=int(sig["dir"])\n'
    assert s.count(t_c6) == 1, "walk dir2"
    s = s.replace(t_c6,
                  '        if exp_skip_weekend and _is_weekend(candles_ltf[i]["date"]) >= 5:\n'
                  '            continue\n'
                  '        if exp_skip_utc_sat and _utc_wd(candles_ltf[i]["date"]) == 5:\n'
                  '            continue\n'
                  '        if exp_skip_utc_sun and _utc_wd(candles_ltf[i]["date"]) == 6:\n'
                  '            continue\n'
                  '        if exp_kinds and sig["kind"] != exp_kinds:\n'
                  '            continue\n'
                  + t_c6)
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
    # 4) B3 relocation (no-op when b3_k=0): entry AFTER confirmation of the break.
    #    Scan bars i+1..i+b3_k for a trigger (close/wick beyond the signal bar's
    #    extreme). Dead if SL pivot touched first. Entry relocates to trigger bar;
    #    busy + cooldown re-checked there (causal — known at trigger close).
    t6 = '        sl_pivot=sig["swing_start_px"]\n'
    assert s.count(t6) == 1, "sl pivot"
    # 5) Partial exit (exp_partial_r): 50% sold at level, remaining runs half-weighted.
    #    Per-trade state init (after sl0/best init, before trail events)
    t_pe_init = '        sl0=sl; sl_cur=sl; best=entry\n'
    assert s.count(t_pe_init) == 1, "pe init"
    s = s.replace(t_pe_init, t_pe_init +
                  '        _partial_taken=False; _partial_r=0.0\n')
    #    Coarse partial check: AFTER best-update, BEFORE SL check
    t_pe_coarse = ('            if direction==1:\n'
                   '                if hi>best: best=hi\n'
                   '            else:\n'
                   '                if lo<best: best=lo\n')
    assert s.count(t_pe_coarse) == 1, "pe coarse"
    s = s.replace(t_pe_coarse, t_pe_coarse +
                  '            if exp_partial_r>0 and not _partial_taken and risk>0:\n'
                  '                _cur_r=(best-entry)*direction/risk\n'
                  '                if _cur_r>=exp_partial_r:\n'
                  '                    _partial_taken=True; _partial_r=exp_partial_r\n')
    #    Fine partial check: AFTER best_f-update, BEFORE fine SL check
    t_pe_fine = ('                if direction==1:\n'
                 '                    if hi>best_f: best_f=hi\n'
                 '                else:\n'
                 '                    if lo<best_f: best_f=lo\n')
    assert s.count(t_pe_fine) == 1, "pe fine"
    s = s.replace(t_pe_fine, t_pe_fine +
                  '                if exp_partial_r>0 and not _partial_taken and risk>0:\n'
                  '                    _cur_rf=(best_f-entry)*direction/risk\n'
                  '                    if _cur_rf>=exp_partial_r:\n'
                  '                        _partial_taken=True; _partial_r=exp_partial_r\n')
    #    R calculation: 0.5*partial_r + (total_move/risk)*0.5  (50% sold at partial_r)
    t_r = ('        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
            '        r_multiple=move/risk if risk>0 else 0\n')
    assert s.count(t_r) == 1, "r calc"
    s = s.replace(t_r,
                  '        move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
                  '        _partial_exit_price=0.0\n'
                  '        if _partial_taken and risk>0:\n'
                  '            _partial_exit_price=entry+direction*_partial_r*risk\n'
                  '            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)\n'
                  '            r_multiple=(_partial_r*0.5)+(_rem_move/risk)*0.5\n'
                  '        else:\n'
                  '            r_multiple=move/risk if risk>0 else 0\n')
    #    Trade dict: add partial_exit_price field
    t_dict = '            "bars_held": exit_idx - i,\n        })'
    assert s.count(t_dict) == 1, "trade dict"
    s = s.replace(t_dict,
                  '            "bars_held": exit_idx - i,\n'
                  '            "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,\n'
                  '        })')
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
                   '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n'
                   '            if exp_max_concurrent>0:\n'
                   '                _now_ts2=candle_ts[i]\n'
                   '                _open_now2=sum(1 for _t in ltf_trades if int(_t["exit_ts"])>_now_ts2)\n'
                   '                if _open_now2>=exp_max_concurrent: continue\n')
    # 3g-3) D3 CAUSAL SL — the user's fix: SL = running extreme from the last
    #     confirmed swing's END to the entry bar (inclusive). This is what a
    #     live trader computes at candle close without any declaration lag.
    #     Replaces the retroactive swing_start_px for SL computation.
    t_c12 = '    last_loss_bar=-999999\n'
    assert s.count(t_c12) == 1, "last_loss_bar anchor"
    s = s.replace(t_c12, t_c12 +
                  '    _csl = [0.0]*len(candles_ltf)\n'
                  '    _csh = [0.0]*len(candles_ltf)\n'
                  '    _conf_evs = []\n'
                  '    for _s in swings_ltf:\n'
                  '        _ca = _s.get("confirmed_at_idx")\n'
                  '        if _ca is not None and int(_ca) >= 0:\n'
                  '            _e = _s.get("seg", {}).get("end_idx", -1)\n'
                  '            if _e is not None and int(_e) >= 0:\n'
                  '                _conf_evs.append((int(_ca), int(_e)))\n'
                  '    _conf_evs.sort()\n'
                  '    _cref = 0\n'
                  '    _clo = float(candles_ltf[0]["low"])\n'
                  '    _chi = float(candles_ltf[0]["high"])\n'
                  '    _cei = 0\n'
                  '    for _ci in range(len(candles_ltf)):\n'
                  '        while _cei < len(_conf_evs) and _conf_evs[_cei][0] <= _ci:\n'
                  '            _cref = _conf_evs[_cei][1]\n'
                  '            _cei += 1\n'
                  '            if _cref < len(candles_ltf):\n'
                  '                _clo = float(candles_ltf[_cref]["low"])\n'
                  '                _chi = float(candles_ltf[_cref]["high"])\n'
                  '        _cl = float(candles_ltf[_ci]["low"])\n'
                  '        _ch2 = float(candles_ltf[_ci]["high"])\n'
                  '        if _cl < _clo: _clo = _cl\n'
                  '        if _ch2 > _chi: _chi = _ch2\n'
                  '        _csl[_ci] = _clo\n'
                  '        _csh[_ci] = _chi\n')
    t_c13 = '        sl_pivot=sig["swing_start_px"]\n'
    assert s.count(t_c13) == 1, "sl pivot anchor"
    s = s.replace(t_c13,
                  '        if exp_causal_sl:\n'
                  '            if direction == 1:\n'
                  '                sl_pivot = _csl[i]\n'
                  '            else:\n'
                  '                sl_pivot = _csh[i]\n'
                  '        else:\n'
                  '            sl_pivot = sig["swing_start_px"]\n')
    t_c13b = '    exp_risk_max_pct=0.0,\n'
    assert t_c13b in s, "kwargs anchor for causal_sl"
    s = s.replace(t_c13b, t_c13b + '    exp_causal_sl=0,\n')

    t_c10 = '    atr_pct=_atr_pct_15m(candles_ltf)\n'
    assert s.count(t_c10) == 1, "atr_pct anchor"
    s = s.replace(t_c10, t_c10 +
                  '    chop15_ser=_chop_series_1h(candles_ltf, lb=28)\n'
                  '    _tr15=[0.0]*len(candles_ltf)\n'
                  '    for _i, _c in enumerate(candles_ltf):\n'
                  '        _h, _l = float(_c["high"]), float(_c["low"])\n'
                  '        _pc = float(candles_ltf[_i-1]["close"]) if _i else _h\n'
                  '        _tr15[_i] = max(_h-_l, abs(_h-_pc), abs(_l-_pc))\n'
                  '    _a5 = [0.0]*len(candles_ltf); _a20 = [0.0]*len(candles_ltf); _ar15 = [1.0]*len(candles_ltf)\n'
                  '    for _i in range(len(candles_ltf)):\n'
                  '        _a5[_i] = sum(_tr15[max(0, _i-4):_i+1]) / min(5, _i+1)\n'
                  '        _a20[_i] = sum(_tr15[max(0, _i-19):_i+1]) / min(20, _i+1)\n'
                  '        _px = float(candles_ltf[_i]["close"])\n'
                  '        if _a20[_i] > 0:\n'
                  '            _ar15[_i] = _a5[_i] / _a20[_i]\n')
    t_c11 = '        direction=int(sig["dir"])\n'
    assert s.count(t_c11) == 1, "walk dir4"
    s = s.replace(t_c11,
                  '        if exp_chop15_hi > 0 and exp_chop15_lo <= chop15_ser[i] < exp_chop15_hi:\n'
                  '            continue\n'
                  '        if exp_atr_ratio_max > 0 and _ar15[i] > exp_atr_ratio_max:\n'
                  '            continue\n'
                  + t_c11)
    # 3f) D3 risk-width gate: skip entries whose LTF stop is wider than
    #     exp_risk_max_pct % of price (stale/stretched breaks: net-negative
    #     bucket, negligible big-win contribution on the single autopsy).
    t_c7 = '            if risk<0.0005*entry: continue\n'
    assert s.count(t_c7) == 2, "risk filter x2"
    s = s.replace(t_c7, t_c7 +
                  '            if exp_risk_max_pct>0 and risk/entry*100.0>exp_risk_max_pct: continue\n'
                  '            if exp_entry_candle_min>0:\n'
                  '                _cb=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))\n'
                  '                _crng=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])\n'
                  '                if _crng>0 and _cb/_crng<exp_entry_candle_min: continue\n'
                  '            if exp_entry_swing_age_max>0 and sig.get("swing_no") is not None:\n'
                  '                _sag=int(sig["swing_no"])\n'
                  '                if 0<=_sag<len(swings_ltf):\n'
                  '                    _ssi=swings_ltf[_sag].get("seg",{}).get("start_idx",-1)\n'
                  '                    if _ssi>=0 and (i-int(_ssi))>exp_entry_swing_age_max: continue\n'
                  '            if exp_entry_skip_b2_doji>0 and sig.get("kind","")=="B2":\n'
                  '                _cb2=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))\n'
                  '                _cr2=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])\n'
                  '                if _cr2>0 and _cb2/_cr2<0.3: continue\n')
    m, p = _load_module(s, "craze_superset")
    try:
        p.unlink()
    except OSError:
        pass
    return m.simulate_htf_ltf_streak_halt


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
    return {"n": len(tr), "gross": g, "rs": rs,
            "wr": 100.0 * len([x for x in rs if x > 0]) / max(len(rs), 1),
            "dd": dd, "mx": mx,
            "h1": py.get("2023", 0.0) + py.get("2024", 0.0),
            "h2": py.get("2025", 0.0) + py.get("2026", 0.0),
            "py": dict(py)}


def show(tag, s):
    print("  %-22s %4dt %+8.1fR  WR %4.1f%%  DD %5.1f  streak %2d  H1 %+7.1f H2 %+7.1f  %s"
          % (tag, s["n"], s["gross"], s["wr"], s["dd"], s["mx"], s["h1"], s["h2"],
             {k: round(v, 1) for k, v in sorted(s["py"].items())}))


def main():
    t0 = time.time()
    (c15, f15), (c1h, f1h) = load_candles()
    sw15 = _compute_swings(f15, "continuous", min_bars=MB15)
    sw1h = _compute_swings(f1h, "continuous", min_bars=SWING["min_bars_1h"])
    chains = {}
    for mb in (35, 40, 50, 65, 75, 100):
        chains[mb] = _compute_swings(f15, "continuous", min_bars=mb)
    print("swing chains ready (15m mb35..100 + 1h mb20) (%0.0fs)" % (time.time() - t0))

    # ---------- IDENTITY GATE ----------
    print("\n=== IDENTITY GATE (patched-off vs shipped, must be exact) ===")
    r_ship = shipped_mod.simulate_htf_ltf_streak_halt(c1h, sw1h, c15, sw15,
                                                      fine_ltf=[], **BASE)
    t_ship = r_ship["ltf_trades"] if isinstance(r_ship, dict) else r_ship
    s_ship = stats(t_ship)
    show("shipped", s_ship)
    assert s_ship["n"] == 340 and abs(s_ship["gross"] - 225.3) < 0.1, \
        "ANCHOR MISMATCH — aborting (got %dt %+.1fR)" % (s_ship["n"], s_ship["gross"])
    for flags in [dict(), dict(b3_k=4), dict(exp_momentum=True),
                  dict(b3_k=4, exp_momentum=True)]:
        sim = build_module()
        r = sim(c1h, sw1h, c15, sw15, fine_ltf=[], **{**BASE, **flags})
        t = r["ltf_trades"] if isinstance(r, dict) else r
        s = stats(t)
        ok = (s["n"] == s_ship["n"] and s["rs"] == s_ship["rs"])
        print("  flags=%-40s n=%d gross=%+.2f  IDENTICAL=%s%s" %
              (str(flags), s["n"], s["gross"], ok,
               "" if not flags else "  (expected: changed)"))
        if not flags:
            assert ok, "IDENTITY GATE FAILED: all-off must equal shipped"

    # ---------- Exp 11: split-mb ----------
    print("\n=== EXP 11 split-mb (entry-mb -> trail-mb) ===")
    sim_mb = build_module()
    grid = [(50, 50), (50, 35), (50, 75), (50, 100),
            (40, 50), (65, 50), (40, 75), (65, 100)]
    for e, tmb in grid:
        r = sim_mb(c1h, sw1h, c15, chains[e], fine_ltf=[],
                   swings_trail=chains[tmb], **BASE)
        show("e=%d trail=%d" % (e, tmb),
             stats(r["ltf_trades"] if isinstance(r, dict) else r))

    # ---------- Exp 16: 1h momentum gate ----------
    print("\n=== EXP 16 momentum gate ===")
    sim_mo = build_module()
    r = sim_mo(c1h, sw1h, c15, sw15, fine_ltf=[], exp_momentum=True, **BASE)
    show("momentum ON", stats(r["ltf_trades"] if isinstance(r, dict) else r))
    show("anchor (off)", s_ship)

    print("\n(harness done %.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    main()
