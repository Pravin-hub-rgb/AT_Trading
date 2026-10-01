"""CRAZE harness â€” runs the SHIPPED engine source with minimal asserted patches.

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
sys.path.insert(0, str(ROOT / "backtest"))
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
    p = Path(ROOT / "backtest/tests/_craze_tmp.py")
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
                  '    exp_cohort_swingpause=0,\n'
                  '    exp_cohort_rearm=0,\n'
                  '    exp_cohort_loss_n=1,\n'
                  '    exp_5m_confirm=0,\n'
                  '    exp_5m_wait_min=240,\n'
                  '    exp_5m_data=None,\n'
                  '    exp_5m_stats=None,\n'
                  '    exp_window_r_cap=0.0,\n'
                  '    exp_window_entry_cap=0,\n'
                  '    exp_window_budget_mode="realized",\n'
                  '    exp_campaign_require_marked_r=None,\n'
                  '    exp_campaign_max_addons=0,\n'
                  '    exp_campaign_max_total=0,\n'
                  '    exp_campaign_block_mixed=0,\n'
                  '    exp_campaign_stats=None,\n'
                  '    exp_window_loss_kill_n=0,\n'
                  '    exp_window_loss_kill_scope="window",\n'
                  '    exp_window_loss_kill_action="soft",\n'
                  '    exp_window_win_kill_n=0,\n'
                  '    exp_window_win_kill_scope="window",\n'
                  '    exp_window_win_kill_action="soft",\n'
                  '    exp_window_win_kill_stats=None,\n'
                  '    exp_window_loss_kill_stats=None,\n'
                  '    exp_shadow_book=False,\n'
                  '    exp_geom_mode="",\n'
                  '    exp_geom_b1_max=-1,\n'
                  '    exp_geom_b1_min=-1,\n'
                  '    exp_geom_mag_min_atr=0.0,\n'
                  '    exp_geom_start_dist_max_atr=0.0,\n'
                  '    exp_geom_stats=None,\n'
                  '    exp_b1_b2_mode="",\n'
                  '    exp_b1_b2_stats=None,\n'
                  '    exp_ma_trail_period=0,\n'
                  '    exp_weekly_state_action="",\n'
                  '    exp_loss_streak_n=0,\n'
                  '    exp_loss_streak_mode="global",\n'
                  '    exp_loss_streak_action="",\n'
                  '    exp_event_mode="",\n'
                  '    exp_event_timestamps=(),\n'
                  '    exp_event_dates=(),\n'
                  '    exp_event_shift_min=0,\n'
                  '    exp_event_stats=None,\n'
                  '    exp_entry_candle_min=0.0,\n'
                  '    exp_entry_swing_age_max=0,\n'
    '    exp_entry_skip_b2_doji=0,\n'
    '    exp_bias_momentum_min=0.0,\n'
    '    exp_min_swing_ratio=0.0,\n'
    '    exp_wick_reject=0.0,\n'
    '    exp_causal_sl=0,\n'
    '    exp_trail_max_dist=0.0,\n'
    '    exp_trail_delay_r=0.0,\n'
    '    exp_trail_delay_prevbar=0,\n'
    '    exp_trail_skip_n=0,\n'
    '    exp_trail_half=0,\n'
    '    exp_retest_fill=0.0,\n'
    '    exp_retest_wait=240,\n'
                  '    exp_profit_stage_r=0.0,\n'
                  '    exp_profit_stage_distance_r=0.0,\n'
    '    exp_require_dir_match=0,\n'
    '    exp_dir_causal=0,\n'
    '    exp_max_swing_age=0,\n'
    '    exp_max_running_mag=0.0,\n'
    '    exp_halt_skip_n=1,\n'
    '    exp_skip_decisive=0,\n'
    '    exp_flip_break=0,\n'
    '    exp_regime_skip=0.0,\n'
    '    exp_pivot_trail=0,\n'
    '    exp_eth_skip=0.0,\n'
    '    exp_eth_lb=24,\n'
    '    exp_eth_closes=None,\n'
    '    exp_vol_b2_rvol=0.0,\n'
    '    exp_vol_pct_min=0.0,\n'
    '    exp_vol_route=0.0,\n'
    '    exp_vol_exit_r=0.0,\n'
    '    exp_vol_dry_exit=0.0,\n'
    '    exp_vol_dry_bars=8,\n'
    '    exp_vol_dry_be=0.0,\n'
    '    exp_vol_nospk=0.0,\n'
    '    exp_vol_nospk_bars=12,\n'
    '    exp_pb_lo=0.0,\n'
    '    exp_pb_hi=0.0,\n'
    '    exp_mtf_mode=0,\n'
    '    exp_struct_mag_min=0.0,\n'
    '    exp_struct_freq_max=0.0,\n')
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
                  '    closes_htf=[float(c["close"]) for c in candles_htf]\n'
                  '    htf_hi=[float(c["high"]) for c in candles_htf]\n'
                  '    htf_lo=[float(c["low"]) for c in candles_htf]\n')
    # A4 pullback gate: skip if pullback off leg extreme in [lo, hi] R.
    # Causal: leg anchor = first window of same-dir streak; HTF extreme known at bar_ts.
    t_pb = '        filtered.append((sig, use))\n'
    assert s.count(t_pb) == 1, "filtered append"
    s = s.replace(t_pb,
                  '        if exp_pb_lo>0 or exp_pb_hi>0:\n'
                  '            _hr=abs(pe-psl)\n'
                  '            if _hr>0:\n'
                  '                _j=idx\n'
                  '                while _j>0 and intervals[_j-1][2]==d: _j-=1\n'
                  '                _anc=intervals[_j][0]\n'
                  '                _li=bs.bisect_right(candle_ts_htf, _anc)\n'
                  '                _hi=bs.bisect_right(candle_ts_htf, bar_ts)\n'
                  '                if _hi>_li:\n'
                  '                    _cl=float(candles_ltf[bar]["close"])\n'
                  '                    if d==1:\n'
                  '                        _ext=max(htf_hi[_li:_hi]); _pb=(_ext-_cl)/_hr\n'
                  '                    else:\n'
                  '                        _ext=min(htf_lo[_li:_hi]); _pb=(_cl-_ext)/_hr\n'
                  '                    _skip=False\n'
                  '                    if exp_pb_lo>0 and exp_pb_hi>0:\n'
                  '                        _skip=exp_pb_lo<=_pb<=exp_pb_hi\n'
                  '                    elif exp_pb_lo>0: _skip=_pb>=exp_pb_lo\n'
                  '                    elif exp_pb_hi>0: _skip=_pb<=exp_pb_hi\n'
                  '                    if _skip: continue\n'
                  + t_pb)
    t5 = '        if sig["dir"] != d: continue\n'
    assert s.count(t5) == 1, "gate"
    s = s.replace(t5,
                  '        if exp_loss_streak_action in ("override", "opposite", "augment") and sig["dir"] != d:\n'
                  '            _exp_ns = dict(sig)\n'
                  '            _exp_ns["_exp_htf_dir"] = int(d)\n'
                  '            _exp_ns["_exp_opposite_candidate"] = True\n'
                  '            filtered.append((_exp_ns, use))\n'
                  '        if sig["dir"] != d: continue\n'
                  '        if exp_loss_streak_action in ("override", "opposite", "augment"):\n'
                  '            _exp_ns = dict(sig)\n'
                  '            _exp_ns["_exp_htf_dir"] = int(d)\n'
                  '            _exp_ns["_exp_opposite_candidate"] = False\n'
                  '            sig = _exp_ns\n'
                  '        if exp_momentum:\n'
                  '            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+900)-1\n'
                  '            if _j>=2:\n'
                  '                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0\n'
                  '                if sig["dir"]==1 and closes_htf[_j]<_ma: continue\n'
                  '                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue\n')
    # 3b) Exp 18: 3-Mark Judgment System â€” signals from the breaks mark stream.
    # B1-anchored sequences resolve at the 3rd mark (arm "D": 2-mark flips).
    # SL attribution mirrors _collect_signals: same-dir mark -> swing start_px,
    # opposite-dir mark -> prev swing end_px, pre-start churn -> touchable
    # extreme since prev_end. filter_pre_fs honored. B1 decisions resolve
    # silently (B1s are not tradeable in v18 semantics).
    # Post-C16 this call takes pivot_rule explicitly (64a061a). The engine used
    # to read the swing start unconditionally; the parameter now defaults to
    # "leg" and the anchor has to match the shipped line exactly or the whole
    # source-patching harness silently stops patching.
    t6 = '    ltf_sigs=_collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf, pivot_rule=pivot_rule)\n'
    assert s.count(t6) == 1, "collect sigs"
    s = s.replace(t6, t6 +
                  '    _exp_weekly_state_rows=[]\n')
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
    # 3c) Exp 22: conviction trail â€” ratchet each same-dir swing's trail level
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
    # 3f) Exp 31: HTF chop lookback (lb) sweep â€” regime-detection responsiveness.
    # Shipped default 14. exp31_lb=0 keeps shipped (identity).
    t6e = '    chop=_chop_series_1h(candles_htf, lb=14)\n'
    assert s.count(t6e) == 1, "chop lb call"
    s = s.replace(t6e, '    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))\n')
    # 3i) Old-engine ports 2026-09-23: only exp_flip_break KEPT (marginal
    # both-sides on swingpause). ADX/session/htf4/v9 REVERTED (dead = clutter).
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
    s = s.replace(t6h,
                  '        if exp_geom_mode:\n'
                  '            _gs_idx=int(sig.get("swing_no",-1))\n'
                  '            _gs=swings_ltf[_gs_idx] if 0<=_gs_idx<len(swings_ltf) else None\n'
                  '            _gseg=(_gs.get("seg") or {}) if _gs is not None else {}\n'
                  '            _gstart=int(_gseg.get("start_idx",bar))\n'
                  '            _gstart_px=float(_gseg.get("start_px",candles_ltf[bar]["close"]))\n'
                  '            _gb1=max((m for m in ((_gs.get("breaks") or []) if _gs is not None else []) if m.get("kind")=="B1" and int(m.get("idx",-1))<=bar),key=lambda m:int(m.get("idx",-1)),default=None)\n'
                  '            _gb1age=(int(_gb1.get("idx"))-_gstart) if _gb1 is not None else None\n'
                  '            _gatr=max(float(candles_ltf[j]["high"])-float(candles_ltf[j]["low"]) for j in range(max(0,bar-13),bar+1)) if bar>=0 else 1.0\n'
                  '            _gatr=max(_gatr,1e-9)\n'
                  '            _gmag=(max(float(candles_ltf[j]["high"]) for j in range(max(0,_gstart),bar+1))-min(float(candles_ltf[j]["low"]) for j in range(max(0,_gstart),bar+1)))/_gatr if bar>=_gstart else None\n'
                  '            _gdist=abs(float(candles_ltf[bar]["close"])-_gstart_px)/_gatr\n'
                  '            _gok=True\n'
                  '            _gm=set(exp_geom_mode.split("+"))\n'
                  '            if "fresh_b1" in _gm and (_gb1age is None or (exp_geom_b1_max>=0 and _gb1age>exp_geom_b1_max)): _gok=False\n'
                  '            if "not_stale_b1" in _gm and _gb1age is not None and exp_geom_b1_min>=0 and _gb1age>=exp_geom_b1_min: _gok=False\n'
                  '            if "large_mag" in _gm and (_gmag is None or _gmag<exp_geom_mag_min_atr): _gok=False\n'
                  '            if "not_large_mag" in _gm and (_gmag is not None and _gmag>=exp_geom_mag_min_atr): _gok=False\n'
                  '            if "near_start" in _gm and _gdist>exp_geom_start_dist_max_atr: _gok=False\n'
                  '            if exp_geom_stats is not None: exp_geom_stats.append({"entry_idx":bar,"swing_no":_gs_idx,"b1_age":_gb1age,"mag_atr":_gmag,"start_dist_atr":_gdist,"allowed":int(_gok),"mode":exp_geom_mode})\n'
                  '            if not _gok: continue\n'
                  '        if exp_b1_b2_mode and sig.get("kind")=="B2":\n'
                  '            _bs_idx=int(sig.get("swing_no",-1))\n'
                  '            _bs=swings_ltf[_bs_idx] if 0<=_bs_idx<len(swings_ltf) else None\n'
                  '            _bm1=max((m for m in ((_bs.get("breaks") or []) if _bs is not None else []) if m.get("kind")=="B1" and int(m.get("idx",-1))<bar),key=lambda m:int(m.get("idx",-1)),default=None)\n'
                  '            _want_dir="up" if int(sig.get("dir",0))>0 else "down"\n'
                  '            _bm2=next((m for m in ((_bs.get("breaks") or []) if _bs is not None else []) if m.get("kind")=="B2" and m.get("dir")==_want_dir and int(m.get("idx",-1))==bar),None)\n'
                  '            _b1b2=(int(_bm2.get("idx"))-int(_bm1.get("idx"))) if _bm1 is not None and _bm2 is not None else None\n'
                  '            _bok=True\n'
                  '            if exp_b1_b2_mode=="block_immediate" and _b1b2 is not None and _b1b2<=2: _bok=False\n'
                  '            if exp_b1_b2_mode.startswith("block_age") and _b1b2 is not None and _b1b2==int(exp_b1_b2_mode[-1]): _bok=False\n'
                  '            if exp_b1_b2_mode=="block_0_1" and _b1b2 is not None and 0<=_b1b2<=1: _bok=False\n'
                  '            if exp_b1_b2_mode=="only_delayed_3_8" and (_b1b2 is None or _b1b2<3 or _b1b2>8): _bok=False\n'
                  '            if exp_b1_b2_stats is not None: exp_b1_b2_stats.append({"entry_idx":bar,"swing_no":_bs_idx,"b1_b2_bars":_b1b2,"allowed":int(_bok),"mode":exp_b1_b2_mode})\n'
                  '            if not _bok: continue\n'
                  '        if exp_flip_break:\n'
                  '            _cl_fb=float(candles_ltf[bar]["close"])\n'
                  '            if int(sig["dir"])==1 and not (_cl_fb > pe): continue\n'
                  '            if int(sig["dir"])==-1 and not (_cl_fb < pe): continue\n'
                  '        if exp_weekly_state_action:\n'
                  '            import datetime as _dt\n'
                  '            _cutoff=int(bar_ts)+900\n'
                  '            _cdt=_dt.datetime.fromtimestamp(_cutoff,_dt.timezone.utc)\n'
                  '            _cs=int((_cdt-_dt.timedelta(days=_cdt.weekday(),hours=_cdt.hour,minutes=_cdt.minute,seconds=_cdt.second,microseconds=_cdt.microsecond)).timestamp())\n'
                  '            _ps=_cs-7*86400\n'
                  '            _prior=[_c for _c in candles_ltf if _ps<=int(_c["ts"])<_cs]\n'
                  '            _cur=[_c for _c in candles_ltf if _cs<=int(_c["ts"])<_cutoff]\n'
                  '            _ph=max(float(_c["high"]) for _c in _prior) if _prior else None\n'
                  '            _pl=min(float(_c["low"]) for _c in _prior) if _prior else None\n'
                  '            _price=float(candles_ltf[bar]["close"])\n'
                  '            _ws="unknown"; _wb={}\n'
                  '            if _ph is not None and _pl is not None and _ph>_pl:\n'
                  '                _ch=max(float(_c["high"]) for _c in _cur) if _cur else None\n'
                  '                _cl=min(float(_c["low"]) for _c in _cur) if _cur else None\n'
                  '                _hc=[_c for _c in candles_htf if _cs<=int(_c["ts"]) and int(_c["ts"])+3600<=_cutoff]\n'
                  '                _hi_break=_ch is not None and _ch>_ph\n'
                  '                _lo_break=_cl is not None and _cl<_pl\n'
                  '                _hi_acc=_hi_break and any(float(_c["close"])>_ph for _c in _hc)\n'
                  '                _lo_acc=_lo_break and any(float(_c["close"])<_pl for _c in _hc)\n'
                  '                if _hi_acc: _ws="accepted_now" if _price>_ph else "accepted_then_back_inside"\n'
                  '                elif _lo_acc: _ws="accepted_now" if _price<_pl else "accepted_then_back_inside"\n'
                  '                elif _hi_break: _ws="rejected_now" if _price<=_ph else "rejected_but_close_above"\n'
                  '                elif _lo_break: _ws="rejected_now" if _price>=_pl else "rejected_but_close_below"\n'
                  '                else: _ws="middle_or_other"\n'
                  '                _wb={"prior_high":_ph,"prior_low":_pl,"current_high":_ch,"current_low":_cl,"price":_price}\n'
                  '            _allow=True\n'
                  '            if exp_weekly_state_action=="skip_back_inside" and _ws=="accepted_then_back_inside": _allow=False\n'
                  '            elif exp_weekly_state_action=="accepted_now_only" and _ws!="accepted_now": _allow=False\n'
                  '            _exp_weekly_state_rows.append({"entry_ts":int(bar_ts),"entry_idx":bar,"direction":int(sig["dir"]),"use":use,"state":_ws,"allowed":_allow,"action":exp_weekly_state_action,"boundary":_wb})\n'
                  '            if not _allow: continue\n'
                  + t6h +
                  '    filtered.sort(key=lambda z: ltf_store.pos(z[0]["bar"]))\n')
    # 3j) Idea E: regime-TRANSITION skip — |Δchop| over last 4x15m bars > thresh
    # (defensive; skip while regime is CHANGING, not based on its state).
    t_e = '        filtered.append((sig, use))\n    filtered.sort'
    assert s.count(t_e) == 1, "regime skip anchor"
    s = s.replace(t_e,
                  '        if exp_regime_skip>0 and bar>=4 and abs(chop_per_ltf[bar]-chop_per_ltf[bar-4])>exp_regime_skip: continue\n'
                  '        if exp_eth_skip>0 and _eth_mom[bar]>exp_eth_skip: continue\n'
                  '        if exp_vol_b2_rvol>0 and sig.get("kind")=="B2" and _rvol15[bar]<exp_vol_b2_rvol: continue\n'
                  '        if exp_vol_pct_min>0 and _pct15[bar]<exp_vol_pct_min: continue\n'
                  # MTF path-true: last confirmed 1h swing (mode 1) or last TWO
                  # agreeing + matching trade (mode 2). Causal via confirmed_at.
                  '        if exp_mtf_mode:\n'
                  '            _ej=bs.bisect_right(htf_sw_ts, bar_ts+900)-1\n'
                  '            if _ej<0: continue\n'
                  '            if exp_mtf_mode==1:\n'
                  '                if htf_sw_dir[_ej]!=sig["dir"]: continue\n'
                  '            else:\n'
                  '                if _ej<1: continue\n'
                  '                if htf_sw_dir[_ej]!=htf_sw_dir[_ej-1]: continue\n'
                  '                if htf_sw_dir[_ej]!=sig["dir"]: continue\n'
                  # Structure path-true: mag_trend floor / swing-freq ceiling on
                  # last 8 confirmed 15m swings (ltf_sw_ts causal via confirmed_at).
                  '        if exp_struct_mag_min>0 or exp_struct_freq_max>0:\n'
                  '            _sj=bs.bisect_right(ltf_sw_ts, bar_ts+900)-1\n'
                  '            if _sj>=7:\n'
                  '                _w0=_sj-7\n'
                  '                _mags=ltf_sw_mag[_w0:_sj+1]\n'
                  '                _f4=sum(_mags[:4])/4.0\n'
                  '                _s4=sum(_mags[4:])/4.0\n'
                  '                _mt=_s4/_f4 if _f4>0 else 1.0\n'
                  '                if exp_struct_mag_min>0 and _mt<exp_struct_mag_min: continue\n'
                  '                if exp_struct_freq_max>0:\n'
                  '                    _span=(ltf_sw_ts[_sj]-ltf_sw_ts[_w0])/900.0\n'
                  '                    _freq=8.0/max(_span,1.0)\n'
                  '                    if _freq>exp_struct_freq_max: continue\n'
                  + t_e)
    # 3k3) Volume ROUTER (regime gate): override B2/FLIP selection by 15m rvol.
    #   exp_vol_route>0: rvol < t -> flip else b2 (quiet=flip, loud=b2)
    #   exp_vol_route<0: inverted (quiet=b2, loud=flip)
    t_r = '        # pick intervals\n'
    assert s.count(t_r) == 1, "pick intervals anchor"
    s = s.replace(t_r,
                  '        if exp_vol_route>0:\n'
                  '            use="flip" if _rvol15[bar]<exp_vol_route else "b2"\n'
                  '        elif exp_vol_route<0:\n'
                  '            use="b2" if _rvol15[bar]<(-exp_vol_route) else "flip"\n'
                  + t_r)
    # 3k4) Volume climax EXIT: close at bar close if adverse 15m rvol spike
    # while unrealized R < 0 (dump protection; exit-side, not entry-quality).
    # 3k5) Volume-DRY trail/exit (loss autopsy): running hold expansion after
    # exp_vol_dry_bars 15m bars < exp_vol_dry_exit -> exit close ("voldry");
    # exp_vol_dry_be>0 -> same condition moves SL to entry (trail BE on dry).
    # exp_vol_nospk>0: max rvol since entry < nospk after nospk_bars & not
    # working -> exit (the r_max<2 certain-death cohort).
    t_x = '        for j in range(i+1, n if not fine_ltf else i+1):\n'
    assert s.count(t_x) == 1, "coarse walk"
    s = s.replace(t_x,
                  '        _climax_hit=False\n'
                  '        _rmax_v=_rvol15[i]\n'
                  + t_x +
                  '            if _rvol15[j]>_rmax_v: _rmax_v=_rvol15[j]\n'
                  '            if exp_vol_exit_r>0 and not _climax_hit and _rvol15[j]>=exp_vol_exit_r:\n'
                  '                _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)\n'
                  '                if _cl<0:\n'
                  '                    exit_idx,exit_px,outcome=j,float(c["close"]),"volx"\n'
                  '                    _climax_hit=True\n'
                  '                    break\n'
                  '            if exp_vol_dry_exit>0 and (j-i)>=exp_vol_dry_bars:\n'
                  '                _b0=max(0,i-96)\n'
                  '                _base=(_vp[i]-_vp[_b0])/max(1,i-_b0)\n'
                  '                _run=(_vp[j+1]-_vp[i])/max(1,j-i+1)\n'
                  '                if _base>0 and (_run/_base)<exp_vol_dry_exit:\n'
                  '                    if exp_vol_dry_be>0:\n'
                  '                        _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)\n'
                  '                        if _cl>0:\n'
                  '                            if direction==1: sl_cur=max(sl_cur,entry)\n'
                  '                            else: sl_cur=min(sl_cur,entry)\n'
                  '                    else:\n'
                  '                        exit_idx,exit_px,outcome=j,float(c["close"]),"voldry"\n'
                  '                        break\n'
                  '            if exp_vol_nospk>0 and (j-i)>=exp_vol_nospk_bars and _rmax_v<exp_vol_nospk:\n'
                  '                _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)\n'
                  '                if _cl<=0:\n'
                  '                    exit_idx,exit_px,outcome=j,float(c["close"]),"volns"\n'
                  '                    break\n')
    # Fine walk (production): same dry/nospk logic on 15m index mapped by ts
    t_f = '            for k in range(f_start, len(fine_ltf)):\n'
    assert s.count(t_f) == 1, "fine walk"
    s = s.replace(t_f,
                  '            _rmax_f=_rvol15[i]\n'
                  + t_f +
                  '                c=fine_ltf[k]\n'
                  '                ts=int(c["ts"])\n'
                  '                _bj=bs.bisect_right(candle_ts,ts)-1\n'
                  '                if _bj>=0 and _rvol15[_bj]>_rmax_f: _rmax_f=_rvol15[_bj]\n'
                  '                if exp_vol_dry_exit>0 and _bj>=0 and (_bj-i)>=exp_vol_dry_bars:\n'
                  '                    _b0=max(0,i-96)\n'
                  '                    _base=(_vp[i]-_vp[_b0])/max(1,i-_b0)\n'
                  '                    _run=(_vp[_bj+1]-_vp[i])/max(1,_bj-i+1)\n'
                  '                    if _base>0 and (_run/_base)<exp_vol_dry_exit:\n'
                  '                        if exp_vol_dry_be>0:\n'
                  '                            _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)\n'
                  '                            if _cl>0:\n'
                  '                                if direction==1: sl_cur_f=max(sl_cur_f,entry)\n'
                  '                                else: sl_cur_f=min(sl_cur_f,entry)\n'
                  '                        else:\n'
                  '                            fk,exit_px_f,outcome_f=k,float(c["close"]),"voldry"\n'
                  '                            break\n'
                  '                if exp_vol_nospk>0 and _bj>=0 and (_bj-i)>=exp_vol_nospk_bars and _rmax_f<exp_vol_nospk:\n'
                  '                    _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)\n'
                  '                    if _cl<=0:\n'
                  '                        fk,exit_px_f,outcome_f=k,float(c["close"]),"volns"\n'
                  '                        break\n')
    # 3k2) Volume features: causal trailing 15m rvol + percentile (entry-bar only)
    t_v = '    chop_per_ltf=[50.0]*len(candles_ltf)\n'
    assert s.count(t_v) == 1, "chop init vol"
    s = s.replace(t_v, t_v +
                  '    _vol15=[float(c.get("volume") or 0.0) for c in candles_ltf]\n'
                  '    _rvol15=[1.0]*len(candles_ltf)\n'
                  '    _pct15=[50.0]*len(candles_ltf)\n'
                  '    _vw=96\n'
                  '    _vp=[0.0]\n'
                  '    for _vv in _vol15: _vp.append(_vp[-1]+_vv)\n'
                  '    for _vi in range(len(candles_ltf)):\n'
                  '        _lo=max(0,_vi-_vw)\n'
                  '        if _vi-_lo<8: continue\n'
                  '        _cur=_vol15[_vi]\n'
                  '        _win=_vol15[_lo:_vi]\n'
                  '        _pct15[_vi]=100.0*sum(1 for _x in _win if _x<=_cur)/len(_win)\n'
                  '        _mean=(_vp[_vi]-_vp[_lo])/(_vi-_lo)\n'
                  '        if _mean>0: _rvol15[_vi]=_cur/_mean\n')
    # 3k) Idea G: ETH/BTC ratio momentum — precompute eth_mom per LTF bar
    # (path-true: uses only closes up to bar_ts). Default exp_eth_skip=0 = no-op.
    t_em = '    chop_per_ltf=[50.0]*len(candles_ltf)\n'
    assert s.count(t_em) == 1, "chop init"
    s = s.replace(t_em, t_em +
                  '    _eth_mom=[0.0]*len(candles_ltf)\n'
                  '    if exp_eth_skip>0 and exp_eth_closes is not None and len(exp_eth_closes)==len(candles_htf):\n'
                  '        _er=[]\n'
                  '        for _i in range(len(candles_htf)):\n'
                  '            _bc=float(candles_htf[_i]["close"]); _er.append(float(exp_eth_closes[_i])/_bc if _bc>0 else 0.0)\n'
                  '        _elb=max(1,int(exp_eth_lb))\n'
                  '        for _bi in range(len(candles_ltf)):\n'
                  '            _j=bs.bisect_right(candle_ts_htf, candle_ts_ltf[_bi])-1\n'
                  '            _k=bs.bisect_right(candle_ts_htf, candle_ts_ltf[_bi]-_elb*3600)-1\n'
                  '            if _j>=0 and _k>=0 and _er[_k]>0: _eth_mom[_bi]=(_er[_j]/_er[_k])-1.0\n')
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
                  '    pivs_ts=[p[1] for p in _sw_pairs]\n'
                  '    if exp_5m_data:\n'
                  '        _exp_5m_sorted=sorted(exp_5m_data,key=lambda _c:int(_c["ts"])+300)\n'
                  '        _exp_5m_ts=[int(_c["ts"])+300 for _c in _exp_5m_sorted]\n'
                  '        _exp_5m_by_close={int(_c["ts"])+300:_c for _c in _exp_5m_sorted}\n'
                  '    _ma15=[None]*len(candles_ltf)\n'
                  '    _ma_period=int(exp_ma_trail_period)\n'
                  '    if _ma_period>0:\n'
                  '        _ma_sum=0.0\n'
                  '        for _mi,_mc in enumerate(candles_ltf):\n'
                  '            _ma_sum += float(_mc["close"])\n'
                  '            if _mi >= _ma_period: _ma_sum -= float(candles_ltf[_mi-_ma_period]["close"])\n'
                  '            if _mi >= _ma_period-1: _ma15[_mi]=_ma_sum/_ma_period\n')
    t_ev_init = '    filtered=[]\n'
    assert s.count(t_ev_init) == 1, "event stats init anchor"
    s = s.replace(t_ev_init, t_ev_init +
                  '    _exp_event_stats={"blocked":0,"mode":exp_event_mode}\n')
    t_c2 = '    last_loss_bar=-999999\n'
    assert s.count(t_c2) == 1, "last_loss_bar"
    s = s.replace(t_c2, t_c2 + '    last_loss_ts=0\n    halt_ts=0\n    _open_count=0\n    _window_budget={}\n    _exp_streak_used_map={}\n    _exp_cohort_loss_ts=0\n    _exp_cohort_loss_seen=0\n    _exp_5m_stats={"candidates":0,"confirmed":0,"stop_cancelled":0,"timeout":0,"delayed":0}\n    _exp_cohort_stats={"loss_triggers":0,"fresh_rearms":0,"blocked":0}\n    _exp_cohort_loss_count=0\n    _exp_shadow_rows=[]\n    _exp_campaign_stats={"blocked_mixed":0,"blocked_total":0,"blocked_addons":0,"blocked_state":0}\n    _exp_loss_window_kill_stats={"triggered":0,"blocked_entries":0,"hard_closed":0}\n    _exp_loss_window_killed=set()\n    _exp_loss_window_epoch_ts=0\n    _exp_win_window_kill_stats={"triggered":0,"blocked_entries":0,"hard_closed":0,"skipped":0}\n    _exp_win_window_killed=set()\n    _exp_win_window_epoch_ts=0\n    _exp_win_skip_used=False\n')
    # 3d-2b) halt_skip_n: skip N entries after max_consecutive_losses (default 1 = shipped)
    t_hs_init = '    halt_skip_next=False  # True after Nth loss: skip NEXT entry, then reset\n'
    assert s.count(t_hs_init) == 1, "halt init"
    s = s.replace(t_hs_init, '    halt_skip_rem=0  # >0: skip this many more entries after N-loss halt\n')
    t_shadow = '        i=ltf_store.pos(bar_time)  # position via timestamp lookup\n'
    assert s.count(t_shadow) == 1, "shadow anchor"
    s = s.replace(t_shadow,
                  '        i=ltf_store.pos(bar_time)  # position via timestamp lookup\n'
                  '        _sr=None\n'
                  '        if exp_shadow_book and 0<=i<n:\n'
                  '            _now=int(candles_ltf[i]["ts"])\n'
                  '            _active=[_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)>_now]\n'
                  '            _sr={"signal":dict(sig),"use":use,"bar_time":bar_time,"entry_idx":i,"entry_ts":_now,"active_count":len(_active),"active": [{"dir":_t.get("dir"),"entry_ts":_t.get("entry_ts"),"exit_ts":_t.get("exit_ts"),"r_multiple":_t.get("r_multiple"),"entry_price":_t.get("entry_price"),"sl":_t.get("sl")} for _t in _active],"reason":"accepted"}\n'
                  '            _exp_shadow_rows.append(_sr)\n')
    t_cd = '        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue\n'
    assert s.count(t_cd) == 1, "cooldown anchor"
    s = s.replace(t_cd,
                  '        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars:\n'
                  '            if exp_shadow_book: _sr["reason"]="cooldown"\n'
                  '            continue\n')
    t_hs_chk = ('        if halt_skip_next:\n'
                '            halt_skip_next=False\n'
                '            consecutive_losses=0\n'
                '            continue\n')
    assert s.count(t_hs_chk) == 1, "halt chk"
    s = s.replace(t_hs_chk,
                  '        if halt_skip_rem > 0:\n'
                  '            halt_skip_rem-=1\n'
                  '            consecutive_losses=0\n'
                  '            if exp_shadow_book: _sr["reason"]="halt"\n'
                  '            continue\n'
                  '        if exp_skip_decisive and use=="decisive":\n'
                  '            continue\n')
    t_c3 = '        if cooldown_bars > 0 and r_multiple < 0:\n            last_loss_bar = exit_idx\n'
    # Campaign policy is inserted after the window-key selection below.

    assert s.count(t_c3) == 1, "loss hook"
    s = s.replace(t_c3, t_c3 +
                  '        if r_multiple < 0:\n'
                  '            last_loss_ts=int(exit_ts)\n'
                  '        if exp_cohort_swingpause and r_multiple <= 0:\n'
                  '            _other_open=any(int(_t.get("entry_ts") or 0) < int(exit_ts) and int(_t.get("exit_ts") or 0) > int(exit_ts) for _t in ltf_trades)\n'
                  '            if _other_open and _exp_cohort_loss_count < int(exp_cohort_loss_n):\n'
                  '                _exp_cohort_loss_count += 1\n'
                  '                if _exp_cohort_loss_count >= int(exp_cohort_loss_n):\n'
                  '                    _exp_cohort_loss_ts=int(exit_ts)\n'
                  '                    _exp_cohort_stats["loss_triggers"] += 1\n'
                  '        if _window_key is not None:\n'
                  '            _ws2=_window_budget.setdefault(_window_key, {"entries": 0, "realized_r": 0.0})\n'
                  '            _ws2["entries"] += 1\n')
    t_c3b = '                    halt_skip_next = True  # skip the NEXT entry\n'
    assert s.count(t_c3b) == 1, "halt hook"
    s = s.replace(t_c3b,
                  '                    halt_skip_rem = exp_halt_skip_n  # skip next N entries\n'
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
                   '        _window_key=None\n'
                   '        if use == "flip":\n'
                   '            _wb_ivs, _wb_starts = intervals_flip, starts_flip\n'
                   '        elif use == "b2":\n'
                   '            _wb_ivs, _wb_starts = intervals_b2, starts_b2\n'
                   '        else:\n'
                   '            _wb_ivs, _wb_starts = intervals_decisive, starts_decisive\n'
                   '        _wb_idx = bs.bisect_right(_wb_starts, candle_ts[i]) - 1\n'
                   '        if _wb_idx >= 0:\n'
                   '            _wb = _wb_ivs[_wb_idx]\n'
                   '            if int(_wb[0]) + 2700 < candle_ts[i] <= int(_wb[1]) + 2700 and int(_wb[2]) == int(sig.get("_exp_htf_dir", sig["dir"])):\n'
                   '                _window_key="%s:%d:%d:%d" % (use, int(_wb[0]), int(_wb[1]), int(_wb[2]))\n'
                   '        if _window_key is not None and (exp_window_r_cap > 0 or exp_window_entry_cap > 0):\n'
                   '            _ws = _window_budget.setdefault(_window_key, {"entries": 0, "realized_r": 0.0})\n'
                   '            if exp_window_entry_cap > 0 and _ws["entries"] >= exp_window_entry_cap:\n'
                   '                _ws["blocked_entries"] = _ws.get("blocked_entries", 0) + 1\n'
                   '                continue\n'
                   '            if exp_window_r_cap > 0:\n'
                   '                _now = int(candles_ltf[i]["ts"])\n'
                   '                _budget_r = 0.0\n'
                   '                for _t in ltf_trades:\n'
                   '                    if _t.get("window_key") != _window_key:\n'
                   '                        continue\n'
                   '                    if int(_t.get("exit_ts") or 0) <= _now:\n'
                   '                        _budget_r += float(_t.get("r_multiple") or 0.0)\n'
                   '                    elif exp_window_budget_mode == "marked":\n'
                   '                        _e=float(_t["entry_price"]); _sl=float(_t["sl"]); _rk=abs(_e-_sl)\n'
                   '                        if _rk > 0:\n'
                   '                            _cl=float(candles_ltf[i]["close"]); _dd=1 if _t["dir"] == "long" else -1\n'
                   '                            _budget_r += (_cl-_e)*_dd/_rk\n'
                   '                if _budget_r >= exp_window_r_cap:\n'
                   '                    _ws["blocked_budget"] = _ws.get("blocked_budget", 0) + 1\n'
                   '                    continue\n'
                   '        _exp_now=int(candles_ltf[i]["ts"])\n'
                   '        _exp_done=sorted([_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)<=_exp_now], key=lambda _t:(int(_t.get("exit_ts") or 0), int(_t.get("trade_no") or 0)))\n'
                   '        if exp_loss_streak_mode == "window":\n'
                   '            _exp_done=[_t for _t in _exp_done if _t.get("window_key") == _window_key]\n'
                   '        elif exp_loss_streak_mode == "regime":\n'
                   '            _exp_done=[_t for _t in _exp_done if _t.get("htf_regime") == use]\n'
                   '        _exp_streak=0\n'
                   '        for _t in reversed(_exp_done):\n'
                   '            if float(_t.get("r_multiple") or 0.0)<=0: _exp_streak+=1\n'
                   '            else: break\n'
                   '        _exp_trigger=(exp_loss_streak_n>0 and _exp_streak>=exp_loss_streak_n)\n'
                   '        if exp_loss_streak_mode == "window": _exp_streak_key=_window_key or "none"\n'
                   '        elif exp_loss_streak_mode == "regime": _exp_streak_key=use\n'
                   '        else: _exp_streak_key="global"\n'
                   '        _exp_streak_used=_exp_streak_used_map.get(_exp_streak_key,False)\n'
                   '        if exp_loss_streak_n>0 and not _exp_trigger: _exp_streak_used=False\n'
                   '        _exp_streak_used_map[_exp_streak_key]=_exp_streak_used\n'
                    '        _exp_opposite=0\n'
                    '        if exp_loss_streak_action == "opposite":\n'
                    '            _exp_opposite=1 if sig.get("_exp_opposite_candidate") else 0\n'
                    '            if _exp_trigger and not _exp_streak_used:\n'
                    '                if not _exp_opposite: continue\n'
                    '                _exp_streak_used=True\n'
                    '            elif not _exp_trigger:\n'
                    '                if _exp_opposite: continue\n'
                    '            elif _exp_opposite: continue\n'
                    '        elif exp_loss_streak_action == "augment":\n'
                    '            _exp_opposite=1 if sig.get("_exp_opposite_candidate") else 0\n'
                    '            if not _exp_trigger:\n'
                    '                if _exp_opposite: continue\n'
                    '            elif _exp_opposite:\n'
                    '                if _exp_streak_used: continue\n'
                    '                _exp_streak_used=True\n'
                    '        elif exp_loss_streak_action == "skip" and _exp_trigger and not _exp_streak_used:\n'
                   '            _exp_streak_used=True\n'
                   '            _exp_streak_used_map[_exp_streak_key]=_exp_streak_used\n'
                   '            continue\n'
                   '            _exp_streak_used_map[_exp_streak_key]=_exp_streak_used\n'
                  '        if exp_cohort_swingpause and _exp_cohort_loss_ts>0:\n'
                  '            _csi=bs.bisect_right(confs_ts, int(candles_ltf[i]["ts"])+900)-1\n'
                  '            if _csi<0 or confs_ts[_csi]<=_exp_cohort_loss_ts:\n'
                  '                _exp_cohort_stats["blocked"] += 1; continue\n'
                  '            if exp_cohort_rearm:\n'
                  '                _exp_cohort_loss_ts=0; _exp_cohort_loss_count=0; _exp_cohort_stats["fresh_rearms"] += 1\n'
                  '        _campaign_marked=0.0; _campaign_state="first"; _campaign_total=0; _campaign_addons=0; _campaign_active=0; _campaign_mixed=0\n'
                  '        if _window_key is not None and (exp_campaign_require_marked_r is not None or exp_campaign_max_addons>0 or exp_campaign_max_total>0 or exp_campaign_block_mixed or exp_window_loss_kill_n>0 or exp_window_win_kill_n>0):\n'
                  '            _cw=_window_budget.setdefault(_window_key, {"entries":0,"realized_r":0.0})\n'
                  '            _campaign_total=int(_cw.get("entries",0)); _campaign_addons=max(0,_campaign_total)\n'
                  '            _cnow=int(candles_ltf[i]["ts"])+900; _cactive=[_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)>_cnow]\n'
                  '            _campaign_active=len(_cactive); _cdir=1 if sig.get("dir")==1 else -1\n'
                  '            _csame=[_t for _t in _cactive if (1 if _t.get("dir")=="long" else -1)==_cdir]\n'
                  '            _copp=[_t for _t in _cactive if (1 if _t.get("dir")=="long" else -1)!=_cdir]\n'
                  '            _campaign_mixed=1 if _copp else 0\n'
                  '            _cfi=bisect.bisect_right(fine_ts,_cnow)-1 if fine_ts else -1\n'
                  '            if _cfi>=0:\n'
                  '                _cpx=float(fine_ltf[_cfi]["close"])\n'
                  '                for _ct in _csame:\n'
                  '                    _ce=float(_ct.get("entry_price")); _csl=float(_ct.get("sl")); _cr=abs(_ce-_csl)\n'
                  '                    if _cr>0: _campaign_marked+=((_cpx-_ce) if _cdir>0 else (_ce-_cpx))/_cr\n'
                  '            _campaign_state="mixed" if _copp else "green" if _campaign_marked>0 else "red" if _campaign_marked<0 else "flat"\n'
                  '            if exp_campaign_block_mixed and _campaign_mixed:\n'
                  '                _exp_campaign_stats["blocked_mixed"]+=1; continue\n'
                  '            if exp_campaign_max_total>0 and _campaign_total>=int(exp_campaign_max_total):\n'
                  '                _exp_campaign_stats["blocked_total"]+=1; continue\n'
                  '            if exp_campaign_max_addons>0 and _campaign_total>=int(exp_campaign_max_addons)+1:\n'
                  '                _exp_campaign_stats["blocked_addons"]+=1; continue\n'
                  '            if exp_campaign_require_marked_r is not None and _csame and _campaign_marked<float(exp_campaign_require_marked_r):\n'
                  '                _exp_campaign_stats["blocked_state"]+=1; continue\n'
                   '            if exp_window_loss_kill_n>0 and _window_key is not None:\n'
                   '                _lw_now=int(candles_ltf[i]["ts"])+900\n'
                   '                _lw_done=sorted([_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)<=_lw_now], key=lambda _t:(int(_t.get("exit_ts") or 0),int(_t.get("trade_no") or 0)))\n'
                   '                if exp_window_loss_kill_scope=="window": _lw_done=[_t for _t in _lw_done if _t.get("window_key")==_window_key]\n'
                   '                elif exp_window_loss_kill_scope=="global": _lw_done=[_t for _t in _lw_done if int(_t.get("exit_ts") or 0)>_exp_loss_window_epoch_ts]\n'
                   '                _lw_streak=0\n'
                   '                for _t in reversed(_lw_done):\n'
                   '                    if float(_t.get("r_multiple") or 0.0)<=0: _lw_streak+=1\n'
                   '                    else: break\n'
                   '                if _lw_streak>=int(exp_window_loss_kill_n) and _window_key not in _exp_loss_window_killed:\n'
                   '                    if exp_window_loss_kill_scope=="global": _exp_loss_window_epoch_ts=_lw_now\n'
                   '                    _exp_loss_window_killed.add(_window_key); _exp_loss_window_kill_stats["triggered"]+=1\n'
                   '                    if exp_window_loss_kill_action=="hard":\n'
                   '                        _lw_fi=bisect.bisect_right(fine_ts,_lw_now)-1\n'
                   '                        if _lw_fi>=0:\n'
                   '                            _lw_px=float(fine_ltf[_lw_fi]["close"])\n'
                   '                            for _t in ltf_trades:\n'
                   '                                if _t.get("window_key")!=_window_key or int(_t.get("exit_ts") or 0)<=_lw_now: continue\n'
                   '                                _lw_e=float(_t.get("entry_price")); _lw_s=float(_t.get("sl")); _lw_r=abs(_lw_e-_lw_s); _lw_d=1 if _t.get("dir")=="long" else -1\n'
                   '                                if _lw_r>0:\n'
                   '                                    _lw_x=((_lw_px-_lw_e)*_lw_d)/_lw_r\n'
                   '                                    _t["exit_ts"]=int(fine_ltf[_lw_fi]["ts"]); _t["exit_date"]=fine_ltf[_lw_fi].get("date") or _t.get("exit_date"); _t["exit_price"]=round(_lw_px,2); _t["r_multiple"]=round(_lw_x,3); _t["outcome"]="loss_window_hard_close"; _exp_loss_window_kill_stats["hard_closed"]+=1\n'
                   '                            if not exp_mltf: busy_until=fine_ltf[_lw_fi].get("date") or busy_until\n'
                   '                if _window_key in _exp_loss_window_killed:\n'
                   '                    _exp_loss_window_kill_stats["blocked_entries"]+=1\n'
                   '                    continue\n'
                   '            if exp_window_win_kill_n>0 and _window_key is not None:\n'
                   '                _ww_now=int(candles_ltf[i]["ts"])+900\n'
                   '                _ww_done=sorted([_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)<=_ww_now], key=lambda _t:(int(_t.get("exit_ts") or 0),int(_t.get("trade_no") or 0)))\n'
                   '                if exp_window_win_kill_scope=="window": _ww_done=[_t for _t in _ww_done if _t.get("window_key")==_window_key]\n'
                   '                elif exp_window_win_kill_scope=="global": _ww_done=[_t for _t in _ww_done if int(_t.get("exit_ts") or 0)>_exp_win_window_epoch_ts]\n'
                   '                _ww_streak=0\n'
                   '                for _t in reversed(_ww_done):\n'
                   '                    if float(_t.get("r_multiple") or 0.0)>0: _ww_streak+=1\n'
                   '                    else: break\n'
                   '                _ww_trigger=_ww_streak>=int(exp_window_win_kill_n)\n'
                   '                if not _ww_trigger: _exp_win_skip_used=False\n'
                   '                if _ww_trigger and exp_window_win_kill_action=="skip" and not _exp_win_skip_used:\n'
                   '                    _exp_win_skip_used=True; _exp_win_window_kill_stats["triggered"]+=1; _exp_win_window_kill_stats["skipped"]+=1\n'
                   '                    if exp_window_win_kill_scope=="global": _exp_win_window_epoch_ts=_ww_now\n'
                   '                    continue\n'
                   '                if _ww_trigger and exp_window_win_kill_action in ("soft","hard") and _window_key not in _exp_win_window_killed:\n'
                   '                    if exp_window_win_kill_scope=="global": _exp_win_window_epoch_ts=_ww_now\n'
                   '                    _exp_win_window_killed.add(_window_key); _exp_win_window_kill_stats["triggered"]+=1\n'
                   '                    if exp_window_win_kill_action=="hard":\n'
                   '                        _ww_fi=bisect.bisect_right(fine_ts,_ww_now)-1\n'
                   '                        if _ww_fi>=0:\n'
                   '                            _ww_px=float(fine_ltf[_ww_fi]["close"])\n'
                   '                            for _t in ltf_trades:\n'
                   '                                if _t.get("window_key")!=_window_key or int(_t.get("exit_ts") or 0)<=_ww_now: continue\n'
                   '                                _ww_e=float(_t.get("entry_price")); _ww_s=float(_t.get("sl")); _ww_r=abs(_ww_e-_ww_s); _ww_d=1 if _t.get("dir")=="long" else -1\n'
                   '                                if _ww_r>0:\n'
                   '                                    _ww_x=((_ww_px-_ww_e)*_ww_d)/_ww_r\n'
                   '                                    _t["exit_ts"]=int(fine_ltf[_ww_fi]["ts"]); _t["exit_date"]=fine_ltf[_ww_fi].get("date") or _t.get("exit_date"); _t["exit_price"]=round(_ww_px,2); _t["r_multiple"]=round(_ww_x,3); _t["outcome"]="win_window_hard_close"; _exp_win_window_kill_stats["hard_closed"]+=1\n'
                   '                            if not exp_mltf: busy_until=fine_ltf[_ww_fi].get("date") or busy_until\n'
                   '                if _window_key in _exp_win_window_killed:\n'
                   '                    _exp_win_window_kill_stats["blocked_entries"]+=1\n'
                   '                    continue\n'
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
                  '            if exp_shadow_book: _sr["reason"]="utc_saturday"\n'
                  '            continue\n'
                  '        if exp_skip_utc_sun and _utc_wd(candles_ltf[i]["date"]) == 6:\n'
                  '            if exp_shadow_book: _sr["reason"]="utc_sunday"\n'
                  '            continue\n'
                  '        if exp_kinds and sig["kind"] != exp_kinds:\n'
                  '            if exp_shadow_book: _sr["reason"]="kind"\n'
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
        '            use=_rg_s\n'
        '        if exp_event_mode:\n'
        '            _event_now=int(bar_ts)+900\n'
        '            if exp_event_mode=="exact" and any(int(_ets)+int(exp_event_shift_min)*60-3600 <= _event_now <= int(_ets)+int(exp_event_shift_min)*60+1800 for _ets in exp_event_timestamps):\n'
        '                _exp_event_stats["blocked"] += 1\n'
        '                continue\n'
        '            if exp_event_mode=="day":\n'
        '                import datetime as _event_dt\n'
        '                _event_day=_event_dt.datetime.fromtimestamp(_event_now, _event_dt.timezone.utc).date().isoformat()\n'
        '                if _event_day in exp_event_dates:\n'
        '                    _exp_event_stats["blocked"] += 1\n'
        '                    continue\n' + t9)
    t10 = '        if busy_until and bar_time <= busy_until: continue\n'
    assert s.count(t10) == 1, "busy gate"
    s = s.replace(t10, '        if (not exp_mltf) and busy_until and bar_time <= busy_until:\n            if exp_shadow_book: _sr["reason"]="busy"\n            continue\n')
    # 4a) retest fill bookkeeping (per-sim-call counters, returned to harness)
    t_bu = '    busy_until=""  # datetime string — timestamp-based, not index\n'
    assert s.count(t_bu) == 1, "busy_until init"
    s = s.replace(t_bu, t_bu +
                  '    retest_stats={"filled":0,"timeout":0}\n')
    # 4a-2) fine walk starts AT the retest fill minute (rest of fill bar managed);
    #       baseline (no fill) keeps candle_ts[i+1] — identity-safe.
    t_fs = '            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])\n'
    assert s.count(t_fs) == 1, "f_start"
    s = s.replace(t_fs,
                  '            f_start=_retest_fill_k if _retest_fill_k is not None else (_exp_5m_entry_k if _exp_5m_entry_k is not None else bisect.bisect_left(fine_ts, candle_ts[i+1]))\n')
    # 4) B3 relocation (no-op when b3_k=0): entry AFTER confirmation of the break.
    #    Scan bars i+1..i+b3_k for a trigger (close/wick beyond the signal bar's
    #    extreme). Dead if SL pivot touched first. Entry relocates to trigger bar;
    #    busy + cooldown re-checked there (causal â€” known at trigger close).
    t6 = '        sl_pivot=sig["swing_start_px"]\n'
    assert s.count(t6) == 1, "sl pivot"
    # 5) Partial exit (exp_partial_r): 50% sold at level, remaining runs half-weighted.
    #    Per-trade state init (after sl0/best init, before trail events)
    t_pe_init = '        sl0=sl; sl_cur=sl; best=entry\n'
    assert s.count(t_pe_init) == 1, "pe init"
    # 4b) RETEST LIMIT FILL (exp_retest_fill>0): after signal at bar close, rest
    #     a limit at entry -/+ exp_retest_fill*risk (long below / short above).
    #     Walk fine 1m bars up to exp_retest_wait minutes after signal close;
    #     first touch fills at min(limit, open) long / max(limit, open) short
    #     (gap fills at the better price). SL price UNCHANGED — risk/target are
    #     recomputed at the fill price (better entry = smaller risk = more R per
    #     same move). Timeout = cancel, no trade (counted in retest_stats).
    #     Entry relocates to the fill's 15m bar; trail events only from there
    #     (same rule as signal-bar entry). Fine-only (coarse runs = no-op).
    s = s.replace(t_pe_init,
                  '        _retest_fill_k=None\n'
                  '        if exp_retest_fill>0 and fine_ltf:\n'
                  '            _rlim = entry - exp_retest_fill*risk if direction==1 else entry + exp_retest_fill*risk\n'
                  '            _rdl = candle_ts[i] + 900 + exp_retest_wait*60\n'
                  '            _rfs = bisect.bisect_left(fine_ts, candle_ts[i+1]) if i+1 < n else len(fine_ts)\n'
                  '            for _k in range(_rfs, len(fine_ltf)):\n'
                  '                if int(fine_ltf[_k]["ts"]) > _rdl: break\n'
                  '                _op=float(fine_ltf[_k]["open"])\n'
                  '                if direction==1:\n'
                  '                    if float(fine_ltf[_k]["low"]) <= _rlim: _retest_fill_k=_k; entry=min(_rlim,_op); break\n'
                  '                else:\n'
                  '                    if float(fine_ltf[_k]["high"]) >= _rlim: _retest_fill_k=_k; entry=max(_rlim,_op); break\n'
                  '            if _retest_fill_k is None:\n'
                  '                retest_stats["timeout"] += 1\n'
                  '                continue\n'
                  '            if direction==1:\n'
                  '                risk=entry-sl\n'
                  '            else:\n'
                  '                risk=sl-entry\n'
                  '            if risk < 0.0005*entry:\n'
                  '                continue\n'
                  '            target = entry+3.0*risk if direction==1 else entry-3.0*risk\n'
                  '            i = bisect.bisect_right(candle_ts, fine_ts[_retest_fill_k]) - 1\n'
                  '            retest_stats["filled"] += 1\n'
                  + t_pe_init)
    s = s.replace(t_pe_init, t_pe_init +
                  '        _partial_taken=False; _partial_r=0.0\n'
                   '        _profit_stage_fired=False\n'
                  '        _trail_skip_rem=exp_trail_skip_n\n'
                  '        _exp_5m_entry_k=None\n'
                  '        if exp_5m_confirm>0 and fine_ltf and exp_5m_data:\n'
                  '            _exp_5m_stats["candidates"] += 1\n'
                  '            _exp_entry_inst=int(candles_ltf[i]["ts"])+900\n'
                  '            _exp_deadline=_exp_entry_inst+int(exp_5m_wait_min)*60\n'
                  '            if not _exp_5m_ts or _exp_5m_ts[0]>_exp_entry_inst or _exp_5m_ts[-1]<_exp_entry_inst:\n'
                  '                _exp_5m_stats["timeout"] += 1; continue\n'
                  '            _exp_k0=bisect.bisect_left(_exp_5m_ts,_exp_entry_inst)\n'
                  '            _exp_k1=bisect.bisect_right(_exp_5m_ts,_exp_deadline)\n'
                  '            _exp_f0=bisect.bisect_left(fine_ts,_exp_entry_inst)\n'
                  '            _exp_confirm_close=None\n'
                  '            for _exp_k in range(_exp_k0,_exp_k1):\n'
                  '                if _exp_k < 3: continue\n'
                  '                _exp_prev=_exp_5m_sorted[_exp_k-3:_exp_k]\n'
                  '                _exp_hi=max(float(_exp_c["high"]) for _exp_c in _exp_prev)\n'
                  '                _exp_lo=min(float(_exp_c["low"]) for _exp_c in _exp_prev)\n'
                  '                _exp_close=float(_exp_5m_sorted[_exp_k]["close"])\n'
                  '                if (direction==1 and _exp_close>_exp_hi) or (direction==-1 and _exp_close<_exp_lo):\n'
                  '                    _exp_confirm_close=int(_exp_5m_ts[_exp_k]); break\n'
                  '            if _exp_confirm_close is None:\n'
                  '                _exp_5m_stats["timeout"] += 1; continue\n'
                  '            _exp_5m_entry_k=bisect.bisect_left(fine_ts,_exp_confirm_close)\n'
                  '            if _exp_5m_entry_k>=len(fine_ltf):\n'
                  '                _exp_5m_stats["timeout"] += 1; continue\n'
                  '            for _exp_fk in range(_exp_f0,_exp_5m_entry_k):\n'
                  '                _exp_fc=fine_ltf[_exp_fk]\n'
                  '                if direction==1 and float(_exp_fc["low"])<=sl:\n'
                  '                    _exp_5m_stats["stop_cancelled"] += 1; _exp_confirm_close=None; break\n'
                  '                if direction==-1 and float(_exp_fc["high"])>=sl:\n'
                  '                    _exp_5m_stats["stop_cancelled"] += 1; _exp_confirm_close=None; break\n'
                  '            if _exp_confirm_close is None: continue\n'
                  '            entry=float(fine_ltf[_exp_5m_entry_k]["open"])\n'
                  '            i=max(i,bisect.bisect_right(candle_ts,int(fine_ltf[_exp_5m_entry_k]["ts"]))-1)\n'
                  '            bar_time=candles_ltf[i]["date"]\n'
                  '            if busy_until and bar_time<=busy_until: continue\n'
                  '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n'
                  '            if exp_max_concurrent>0 and sum(1 for _t in ltf_trades if int(_t["exit_ts"])>int(candles_ltf[i]["ts"]))>=exp_max_concurrent: continue\n'
                  '            risk=entry-sl if direction==1 else sl-entry\n'
                  '            if risk<0.0005*entry:\n'
                  '                _exp_5m_stats["stop_cancelled"] += 1; continue\n'
                  '            target=entry+3.0*risk if direction==1 else entry-3.0*risk\n'
                  '            sl0=sl; sl_cur=sl; best=entry\n'
                  '            _exp_5m_stats["confirmed"] += 1; _exp_5m_stats["delayed"] += 1\n')
    #    Coarse partial check: AFTER best-update, BEFORE SL check
    t_ma_long = ('                if lo <= sl_cur:\n'
                 '                    fill=min(sl_cur, float(c["open"]))\n'
                 '                    exit_idx,exit_px=j,fill\n'
                 '                    outcome="sl" if sl_cur <= sl0 else "trail"\n'
                 '                    break\n')
    assert s.count(t_ma_long) == 1, "coarse long stop anchor"
    s = s.replace(t_ma_long, t_ma_long +
                  '                if exp_ma_trail_period>0 and _ma15[j] is not None and float(c["close"]) < _ma15[j]:\n'
                  '                    exit_idx,exit_px=j,float(c["close"])\n'
                  '                    outcome="ma_trail"\n'
                  '                    break\n')
    t_ma_short = ('                if hi >= sl_cur:\n'
                  '                    fill=max(sl_cur, float(c["open"]))\n'
                  '                    exit_idx,exit_px=j,fill\n'
                  '                    outcome="sl" if sl_cur >= sl0 else "trail"\n'
                  '                    break\n')
    assert s.count(t_ma_short) == 1, "coarse short stop anchor"
    s = s.replace(t_ma_short, t_ma_short +
                  '                if exp_ma_trail_period>0 and _ma15[j] is not None and float(c["close"]) > _ma15[j]:\n'
                  '                    exit_idx,exit_px=j,float(c["close"])\n'
                  '                    outcome="ma_trail"\n'
                  '                    break\n')
    t_ma_fine_long = ('                    if lo <= sl_cur_f:\n'
                      '                        fill=min(sl_cur_f, float(c["open"]))\n'
                      '                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "trail")\n'
                      '                        break\n')
    assert s.count(t_ma_fine_long) == 1, "fine long stop anchor"
    s = s.replace(t_ma_fine_long, t_ma_fine_long +
                  '                    if exp_ma_trail_period>0:\n'
                  '                        _mj=bs.bisect_right(candle_ts, ts-900)-1\n'
                  '                        if _mj>=i and candle_ts[_mj]+900==ts and _ma15[_mj] is not None and float(candles_ltf[_mj]["close"]) < _ma15[_mj]:\n'
                  '                            fk,exit_px_f,outcome_f=k,float(candles_ltf[_mj]["close"]),"ma_trail"\n'
                  '                            break\n')
    t_ma_fine_short = ('                    if hi >= sl_cur_f:\n'
                       '                        fill=max(sl_cur_f, float(c["open"]))\n'
                       '                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f >= sl0 else "trail")\n'
                       '                        break\n')
    assert s.count(t_ma_fine_short) == 1, "fine short stop anchor"
    s = s.replace(t_ma_fine_short, t_ma_fine_short +
                  '                    if exp_ma_trail_period>0:\n'
                  '                        _mj=bs.bisect_right(candle_ts, ts-900)-1\n'
                  '                        if _mj>=i and candle_ts[_mj]+900==ts and _ma15[_mj] is not None and float(candles_ltf[_mj]["close"]) > _ma15[_mj]:\n'
                  '                            fk,exit_px_f,outcome_f=k,float(candles_ltf[_mj]["close"]),"ma_trail"\n'
                  '                            break\n')
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
    s = s.replace(t_pe_fine,
                  '                _best_f_prev=best_f\n' +
                  t_pe_fine +
                  '                if exp_partial_r>0 and not _partial_taken and risk>0:\n'
                  '                    _cur_rf=(best_f-entry)*direction/risk\n'
                  '                    if _cur_rf>=exp_partial_r:\n'
                  '                        _partial_taken=True; _partial_r=exp_partial_r\n'
                  '                if exp_profit_stage_r>0 and exp_profit_stage_distance_r>0 and risk>0:\n'
                  '                    _stage_prev_r=(_best_f_prev-entry)*direction/risk\n'
                  '                    if _stage_prev_r>=exp_profit_stage_r:\n'
                  '                        _profit_stage_fired=True\n'
                  '                        _stage_px=_best_f_prev-direction*exp_profit_stage_distance_r*risk\n'
                  '                        if direction>0:\n'
                  '                            if _stage_px>sl_cur_f: sl_cur_f=_stage_px\n'
                  '                        else:\n'
                  '                            if _stage_px<sl_cur_f: sl_cur_f=_stage_px\n')
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
                  '            "window_key": _window_key,\n'
                   '            "loss_streak_at_entry": _exp_streak,\n'
                   '            "loss_streak_triggered": int(_exp_trigger),\n'
                   '            "opposite_override": _exp_opposite,\n'
                  '            "profit_stage_fired": int(_profit_stage_fired),\n'
                  '        })')
    s = s.replace(t6, t6 +
                  '        if b3_k>0:\n'
                  '            _lv=float(candles_ltf[i]["high"]) if direction==1 else float(candles_ltf[i]["low"])\n'
                  '            _sig_close=float(candles_ltf[i]["close"])\n'
                  '            _jj=None\n'
                  '            for _k in range(i+1, min(i+1+b3_k, n-1)):\n'
                  '                _hi=float(candles_ltf[_k]["high"]); _lo=float(candles_ltf[_k]["low"])\n'
                  '                if direction==1 and _lo<=sl_pivot: break\n'
                  '                if direction==-1 and _hi>=sl_pivot: break\n'
                  '                _cl=float(candles_ltf[_k]["close"])\n'
                  '                if b3_mode=="limit":\n'
                  '                    if direction==1 and _lo<=_sig_close: _jj=_k; break\n'
                  '                    if direction==-1 and _hi>=_sig_close: _jj=_k; break\n'
                  '                elif b3_mode=="wick":\n'
                  '                    if (_hi>_lv) if direction==1 else (_lo<_lv): _jj=_k; break\n'
                  '                else:\n'
                  '                    if (_cl>_lv) if direction==1 else (_cl<_lv): _jj=_k; break\n'
                  '            if _jj is None: continue\n'
                  '            i=_jj\n'
                  '            bar_time=candles_ltf[i]["date"]\n'
                  '            entry=_sig_close if b3_mode=="limit" else float(candles_ltf[i]["close"])\n'
                   '            if busy_until and bar_time<=busy_until: continue\n'
                   '            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue\n'
                   '            if exp_max_concurrent>0:\n'
                   '                _now_ts2=candle_ts[i]\n'
                   '                _open_now2=sum(1 for _t in ltf_trades if int(_t["exit_ts"])>_now_ts2)\n'
                   '                if _open_now2>=exp_max_concurrent: continue\n')
    # 3g-3) D3 CAUSAL SL â€” the user's fix: SL = running extreme from the last
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
    # NOTE: exp_causal_sl and exp_trail_max_dist kwargs already added in the
    # kwargs block above — this replace would create duplicates. No-op.

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
                  '            _ar15[_i] = _a5[_i] / _a20[_i]\n'
                  '    _bm_mags=[]\n'
                  '    for _bm_s in swings_htf:\n'
                  '        _bm_seg=_bm_s.get("seg") or {}\n'
                  '        _bm_spx=float(_bm_seg.get("start_px",0) or 0)\n'
                  '        _bm_epx=float(_bm_seg.get("end_px",0) or 0)\n'
                  '        _bm_mags.append(abs(_bm_epx-_bm_spx))\n'
                  '    _bm_breaks=[]\n'
                  '    for _bmi in range(len(swings_htf)):\n'
                  '        if _bmi<1 or _bm_mags[_bmi-1]<=0: continue\n'
                  '        _bm_ratio=_bm_mags[_bmi]/_bm_mags[_bmi-1]\n'
                  '        for _bmb in (swings_htf[_bmi].get("breaks") or []):\n'
                  '            _bmbt=_bmb.get("time","")\n'
                  '            if _bmbt: _bm_breaks.append((_bmbt[:19],_bm_ratio,int(swings_htf[_bmi].get("confirmed_at_idx",-1))))\n'
                  '    _bm_breaks.sort(key=lambda z:z[0])\n'
                  '    _bm_times=[z[0] for z in _bm_breaks]\n')
    # 3g-5) D3 UNION DUAL-QUALIFICATION: track which window type matched
    #     (B2, FLIP, or BOTH) and optionally skip FLIP-only matches (the
    #     fragile cell from the 2x2 autopsy: FLIP-mark-in-FLIP-window is
    #     IS +79R but OOS -2R). exp_union_dual_only skips FLIP-only matches.
    t_u1 = '    exp_bias_momentum_min=0.0,\n'
    assert t_u1 in s, "bm kwarg anchor"
    s = s.replace(t_u1, t_u1 + '    exp_union_dual_only=0,\n    exp_bm_causal=0,\n')
    t_u2 = ('            _union_matched=False\n'
            '            for _iv,_st in [(intervals_b2,starts_b2),(intervals_flip,starts_flip)]:\n'
            '                if not _iv: continue\n'
            '                _idx=bs.bisect_right(_st,bar_ts)-1\n'
            '                if _idx<0: continue\n'
            '                _s,_e,_d,_pe,_psl=_iv[_idx]\n'
            '                if (_s+2700<bar_ts<=_e+2700) and sig["dir"]==_d:\n'
            '                    _union_matched=True\n'
            '                    # keep _pe,_psl for extension check\n'
            '                    pe=_pe; psl=_psl; d=_d\n'
            '                    break\n'
            '            if not _union_matched: continue\n')
    assert s.count(t_u2) == 1, "union gate anchor"
    t_u2_new = ('            _union_matched = False\n'
                '            _matched_b2 = False\n'
                '            _matched_flip = False\n'
                '            for _iv,_st,_typ in [(intervals_b2,starts_b2,"b2"),(intervals_flip,starts_flip,"flip")]:\n'
                '                if not _iv: continue\n'
                '                _idx=bs.bisect_right(_st,bar_ts)-1\n'
                '                if _idx<0: continue\n'
                '                _s,_e,_d,_pe,_psl=_iv[_idx]\n'
                '                if (_s+2700<bar_ts<=_e+2700) and sig["dir"]==_d:\n'
                '                    _union_matched=True\n'
                '                    if _typ=="b2": _matched_b2=True\n'
                '                    else: _matched_flip=True\n'
                '                    pe=_pe; psl=_psl; d=_d\n'
                '            if not _union_matched: continue\n'
                '            if exp_union_dual_only and _matched_flip and not _matched_b2:\n'
                '                continue\n')
    s = s.replace(t_u2, t_u2_new)

    t_c11 = '        direction=int(sig["dir"])\n'
    assert s.count(t_c11) == 1, "walk dir4"
    s = s.replace(t_c11,
                  '        if exp_chop15_hi > 0 and exp_chop15_lo <= chop15_ser[i] < exp_chop15_hi:\n'
                  '            continue\n'
                  '        if exp_atr_ratio_max > 0 and _ar15[i] > exp_atr_ratio_max:\n'
                  '            continue\n'
                  '        if exp_bias_momentum_min > 0 and _bm_breaks:\n'
                  '            _bm_idx = bs.bisect_right(_bm_times, sig["bar"][:19]) - 1\n'
                  '            if exp_bm_causal:\n'
                  '                _bm_ets = candle_ts_ltf[i] + 900  # entry instant = signal bar close\n'
                  '                while _bm_idx >= 0:\n'
                  '                    _bm_c = _bm_breaks[_bm_idx][2]\n'
                  '                    if 0 <= _bm_c < len(candle_ts_htf) and candle_ts_htf[_bm_c] + 3600 <= _bm_ets:\n'
                  '                        break\n'
                  '                    _bm_idx -= 1  # owner unconfirmed at entry: walk to last DECLARED break\n'
                  '            if _bm_idx >= 0 and _bm_breaks[_bm_idx][1] < exp_bias_momentum_min:\n'
                  '                continue\n'
                  '        if exp_min_swing_ratio > 0 and sig.get("swing_no") is not None:\n'
                  '            _sni = int(sig["swing_no"])\n'
                  '            if 0 <= _sni < len(swings_ltf):\n'
                  '                _sw = swings_ltf[_sni]\n'
                  '                _seg = _sw.get("seg", {})\n'
                  '                _spx = float(_seg.get("start_px", 0) or 0)\n'
                  '                _epx = float(_seg.get("end_px", 0) or 0)\n'
                  '                _swing_mag = abs(_epx - _spx)\n'
                  '                _atr_s = max(0, i - 19)\n'
                  '                _atr_h = max(float(candles_ltf[j]["high"]) for j in range(_atr_s, i + 1))\n'
                  '                _atr_l = min(float(candles_ltf[j]["low"]) for j in range(_atr_s, i + 1))\n'
                  '                _atr = _atr_h - _atr_l if _atr_h > _atr_l else 1.0\n'
                   '                if _atr > 0 and _swing_mag / _atr < exp_min_swing_ratio:\n'
                   '                    continue\n'
                   + t_c11)
    # 3g-6) D3 STRUCTURAL ALIGNMENT — three fixes from the pre-entry autopsy:
    #     1. dir match: entries where the forming swing direction OPPOSES the
    #        trade direction are 100% losers (125/125). Never take them.
    #     2. swing age: entries on swings > exp_max_swing_age bars old are
    #        premature (age 51+ = avg -0.65R, WR 9.8%).
    #     3. running magnitude: entries chasing legs already moved >
    #        exp_max_running_mag % are chasing extended moves (avg -0.49R).
    #     All computed causally at entry bar from the causal chain.
    t_alg1 = '        direction=int(sig["dir"])\n'
    assert s.count(t_alg1) == 1, "alignment anchor"
    alignment_code = (
        '        _gen_dir = 0\n'
        '        _gen_start = -1\n'
        '        for _gs in swings_ltf:\n'
        '            _gsi = int((_gs.get("seg") or {}).get("start_idx", -1))\n'
        '            if 0 <= _gsi <= i:\n'
        '                _gen_dir = 1 if _gs.get("dir") == "up" else -1\n'
        '                _gen_start = _gsi\n'
        '        if exp_require_dir_match and _gen_dir != 0 and _gen_dir != direction:\n'
        '            continue\n'
        '        if exp_max_swing_age > 0 and _gen_start >= 0 and (i - _gen_start) > exp_max_swing_age:\n'
        '            continue\n'
        '        if exp_max_running_mag > 0 and _gen_start >= 0:\n'
        '            if direction == 1:\n'
        '                _rmin = min(float(candles_ltf[_k]["low"]) for _k in range(max(0, _gen_start), i + 1))\n'
        '                _rmag = (float(candles_ltf[i]["close"]) - _rmin) / float(candles_ltf[i]["close"]) * 100.0\n'
        '            else:\n'
        '                _rmax = max(float(candles_ltf[_k]["high"]) for _k in range(max(0, _gen_start), i + 1))\n'
        '                _rmag = (_rmax - float(candles_ltf[i]["close"])) / float(candles_ltf[i]["close"]) * 100.0\n'
        '            if _rmag > exp_max_running_mag:\n'
        '                continue\n'
        + t_alg1)
    s = s.replace(t_alg1,
                  '        direction=int(sig["dir"])\n'
                  '        _gen_dir = 0\n'
                  '        _gen_start = -1\n'
                  '        for _gs in swings_ltf:\n'
                  '            _gsi = int((_gs.get("seg") or {}).get("start_idx", -1))\n'
                  '            if 0 <= _gsi <= i:\n'
                  '                if exp_dir_causal:\n'
                  '                    _gconf = int(_gs.get("confirmed_at_idx", -1))\n'
                  '                    if _gconf < 0 or _gconf > i:\n'
                  '                        continue\n'
                  '                _gen_dir = 1 if _gs.get("dir") == "up" else -1\n'
                  '                _gen_start = _gsi\n'
                  '        if exp_require_dir_match and _gen_dir != 0 and _gen_dir != direction:\n'
                  '            continue\n'
                  '        if exp_max_swing_age > 0 and _gen_start >= 0 and (i - _gen_start) > exp_max_swing_age:\n'
                  '            continue\n'
                  '        if exp_max_running_mag > 0 and _gen_start >= 0:\n'
                  '            if direction == 1:\n'
                  '                _rmin = min(float(candles_ltf[_k]["low"]) for _k in range(max(0, _gen_start), i + 1))\n'
                  '                _rmag = (float(candles_ltf[i]["close"]) - _rmin) / float(candles_ltf[i]["close"]) * 100.0\n'
                  '            else:\n'
                  '                _rmax = max(float(candles_ltf[_k]["high"]) for _k in range(max(0, _gen_start), i + 1))\n'
                  '                _rmag = (_rmax - float(candles_ltf[i]["close"])) / float(candles_ltf[i]["close"]) * 100.0\n'
        '            if _rmag > exp_max_running_mag:\n'
        '                continue\n'
        + t_alg1)
    # 3f) D3 risk-width gate: skip entries whose LTF stop is wider than
    #     exp_risk_max_pct % of price (stale/stretched breaks: net-negative
    #     bucket, negligible big-win contribution on the single autopsy).
    t_c7 = '            if risk<0.0005*entry: continue\n'
    assert s.count(t_c7) == 2, "risk filter x2"
    s = s.replace(t_c7, t_c7 +
                  '            if exp_risk_max_pct>0 and risk/entry*100.0>exp_risk_max_pct:\n'
                  '                if exp_shadow_book: _sr["reason"]="risk_max"\n'
                  '                continue\n'
                  '            if exp_entry_candle_min>0:\n'
                  '                _cb=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))\n'
                  '                _crng=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])\n'
                  '                if _crng>0 and _cb/_crng<exp_entry_candle_min:\n'
                  '                    if exp_shadow_book: _sr["reason"]="candle_min"\n'
                  '                    continue\n'
                  '            if exp_entry_swing_age_max>0 and sig.get("swing_no") is not None:\n'
                  '                _sag=int(sig["swing_no"])\n'
                  '                if 0<=_sag<len(swings_ltf):\n'
                  '                    _ssi=swings_ltf[_sag].get("seg",{}).get("start_idx",-1)\n'
                  '                    if _ssi>=0 and (i-int(_ssi))>exp_entry_swing_age_max:\n'
                  '                        if exp_shadow_book: _sr["reason"]="swing_age"\n'
                  '                        continue\n'
                  '            if exp_entry_skip_b2_doji>0 and sig.get("kind","")=="B2":\n'
                  '                _cb2=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))\n'
                  '                _cr2=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])\n'
                  '                if _cr2>0 and _cb2/_cr2<0.3: continue\n')
    # 3g-5) Pivot-break trail (fix/more ideas.md): trail to intervening extreme
    # when opposite pivot breaks — precompute break bars once per direction.
    t_pb = "    for sig, use in filtered:\n"
    assert s.count(t_pb) == 1, "filtered loop anchor"
    s = s.replace(t_pb,
                  '    _pb_long=[]; _pb_short=[]\n'
                  '    if exp_pivot_trail:\n'
                  '        for _ps in swings_trail:\n'
                  '            _seg=_ps.get("seg") or {}\n'
                  '            _conf=int(_ps.get("confirmed_at_idx",-1))\n'
                  '            _ei=int(_seg.get("end_idx",-1))\n'
                  '            if _conf<0 or _ei<0 or _ei>=n: continue\n'
                  '            _ep=float(_seg.get("end_px",0))\n'
                  '            if _ps.get("dir")=="up":\n'
                  '                _j=_ei+1\n'
                  '                while _j<n and float(candles_ltf[_j]["high"])<=_ep: _j+=1\n'
                  '                if _j<n: _pb_long.append((_j,_ep))\n'
                  '            else:\n'
                  '                _j=_ei+1\n'
                  '                while _j<n and float(candles_ltf[_j]["low"])>=_ep: _j+=1\n'
                  '                if _j<n: _pb_short.append((_j,_ep))\n'
                  '        _pb_long.sort(); _pb_short.sort()\n'
                  + t_pb)
    # 3g-5b) per-trade: segment min/max from entry to each pivot break
    t_ev = '        events = []\n        for s in swings_trail:\n'
    assert s.count(t_ev) == 1, "events build anchor"
    s = s.replace(t_ev,
                  '        events = []\n'
                  '        if exp_pivot_trail:\n'
                  '            _brks=_pb_long if direction==1 else _pb_short\n'
                  '            _seg=i\n'
                  '            for _brk,_ppx in _brks:\n'
                  '                if _brk<=i: continue\n'
                  '                if direction==1:\n'
                  '                    _lvl=min(float(candles_ltf[k]["low"]) for k in range(_seg,_brk+1))\n'
                  '                else:\n'
                  '                    _lvl=max(float(candles_ltf[k]["high"]) for k in range(_seg,_brk+1))\n'
                  '                events.append((_brk,_lvl))\n'
                  '                _seg=_brk\n'
                  '        for s in ([] if exp_pivot_trail else swings_trail):\n')
    # 3g-4) D3 TRAIL QUALITY: skip trail levels too far from entry
    t_trail = '                events.append((cidx, float(s["seg"]["start_px"])))\n'
    assert s.count(t_trail) == 1, "trail event anchor"
    s = s.replace(t_trail,
                  '                _tl = float(s["seg"]["start_px"])\n'
                  '                _td = abs(entry - _tl) / entry * 100.0\n'
                  '                if exp_trail_max_dist > 0 and _td > exp_trail_max_dist:\n'
                  '                    continue\n'
                   '                events.append((cidx, _tl))\n')
    # 3g-6) Slower/wider trail: delay_r (only ratchet after unrealized R),
    # skip_n (drop first N post-entry events), half (ratchet halfway).
    t_tr_long = ('                    if events[ev_idx][0] < i: continue\n'
                 '                    cand=events[ev_idx][1]\n'
                 '                    if sl_cur < cand:\n'
                 '                        sl_cur=cand\n')
    assert s.count(t_tr_long) == 1, "trail long coarse"
    s = s.replace(t_tr_long,
                  '                    if events[ev_idx][0] < i: continue\n'
                  '                    cand=events[ev_idx][1]\n'
                  '                    _tr_ok=True\n'
                  '                    if _trail_skip_rem>0:\n'
                  '                        _trail_skip_rem-=1; _tr_ok=False\n'
                  '                    if _tr_ok and exp_trail_delay_r>0 and risk>0:\n'
                  '                        if ((best-entry)*direction/risk) < exp_trail_delay_r:\n'
                  '                            _tr_ok=False\n'
                  '                    if _tr_ok:\n'
                  '                        if exp_trail_half:\n'
                  '                            if sl_cur < cand: sl_cur=0.5*(sl_cur+cand)\n'
                  '                        elif sl_cur < cand:\n'
                  '                            sl_cur=cand\n')
    t_tr_short = ('                    if events[ev_idx][0] < i: continue\n'
                  '                    cand=events[ev_idx][1]\n'
                  '                    if cand < sl_cur:\n'
                  '                        sl_cur=cand\n')
    assert s.count(t_tr_short) == 1, "trail short coarse"
    s = s.replace(t_tr_short,
                  '                    if events[ev_idx][0] < i: continue\n'
                  '                    cand=events[ev_idx][1]\n'
                  '                    _tr_ok=True\n'
                  '                    if _trail_skip_rem>0:\n'
                  '                        _trail_skip_rem-=1; _tr_ok=False\n'
                  '                    if _tr_ok and exp_trail_delay_r>0 and risk>0:\n'
                  '                        if ((best-entry)*direction/risk) < exp_trail_delay_r:\n'
                  '                            _tr_ok=False\n'
                  '                    if _tr_ok:\n'
                  '                        if exp_trail_half:\n'
                  '                            if cand < sl_cur: sl_cur=0.5*(sl_cur+cand)\n'
                  '                        elif cand < sl_cur:\n'
                  '                            sl_cur=cand\n')
    t_tr_f_long = ('                        cand=events_ts[ev_idx_f][1]\n'
                   '                        if sl_cur_f < cand:\n'
                   '                            sl_cur_f=cand\n')
    assert s.count(t_tr_f_long) == 1, "trail long fine"
    s = s.replace(t_tr_f_long,
                  '                        cand=events_ts[ev_idx_f][1]\n'
                  '                        _tr_ok=True\n'
                  '                        if _trail_skip_rem>0:\n'
                  '                            _trail_skip_rem-=1; _tr_ok=False\n'
                  '                        if _tr_ok and exp_trail_delay_r>0 and risk>0:\n'
                  '                            if ((_best_f_prev if exp_trail_delay_prevbar else best_f)-entry)*direction/risk < exp_trail_delay_r:\n'
                  '                                _tr_ok=False\n'
                  '                        if _tr_ok:\n'
                  '                            if exp_trail_half:\n'
                  '                                if sl_cur_f < cand: sl_cur_f=0.5*(sl_cur_f+cand)\n'
                  '                            elif sl_cur_f < cand:\n'
                  '                                sl_cur_f=cand\n')
    t_tr_f_short = ('                        cand=events_ts[ev_idx_f][1]\n'
                    '                        if cand < sl_cur_f:\n'
                    '                            sl_cur_f=cand\n')
    assert s.count(t_tr_f_short) == 1, "trail short fine"
    s = s.replace(t_tr_f_short,
                  '                        cand=events_ts[ev_idx_f][1]\n'
                  '                        _tr_ok=True\n'
                  '                        if _trail_skip_rem>0:\n'
                  '                            _trail_skip_rem-=1; _tr_ok=False\n'
                  '                        if _tr_ok and exp_trail_delay_r>0 and risk>0:\n'
                  '                            if ((_best_f_prev if exp_trail_delay_prevbar else best_f)-entry)*direction/risk < exp_trail_delay_r:\n'
                  '                                _tr_ok=False\n'
                  '                        if _tr_ok:\n'
                  '                            if exp_trail_half:\n'
                  '                                if cand < sl_cur_f: sl_cur_f=0.5*(sl_cur_f+cand)\n'
                  '                            elif cand < sl_cur_f:\n'
                  '                                sl_cur_f=cand\n')
    t_ret = '    return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,\n            "ltf_trades": ltf_trades, "intervals": parent_intervals}'
    assert s.count(t_ret) == 1, "ret"
    s = s.replace(t_ret, '    return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,\n             "ltf_trades": ltf_trades, "intervals": parent_intervals,\n             "retest_stats": retest_stats,\n             "five_m_stats": _exp_5m_stats, "cohort_stats": _exp_cohort_stats,\n             "shadow_rows": _exp_shadow_rows, "weekly_state_rows": _exp_weekly_state_rows,\n             "event_stats": _exp_event_stats, "campaign_stats": _exp_campaign_stats,\n             "loss_window_kill_stats": _exp_loss_window_kill_stats,\n             "win_window_kill_stats": _exp_win_window_kill_stats}\n')
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
        "ANCHOR MISMATCH â€” aborting (got %dt %+.1fR)" % (s_ship["n"], s_ship["gross"])
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
