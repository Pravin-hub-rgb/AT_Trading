"""v11_conditional_htf — HTF conditional break: when to use B2 vs Flip vs Decisive.
HTF 1h: if regime is chop (HIGH chop >61.8 or LOW vol) -> use Decisive (B2|FLIP) window, else use Flip window.
LTF 15m: decisive MB50 0.25ATR ext-stop1.5 MB50 trail, same as v5.
Costs 0.05%+2pt, 1m fine, stream.
Separate engine, never disturb v5.
Ref: permutation fix choppy 2023 decisive×decisive +37.7 vs flip×decisive -7.2 (+44.9R) but total 122 vs 168 (-46R) fix/permutation_htf_ltf.md:7, Exp4 LOW vol 309 +133 vs HIGH vol 17 +12, MED chop 366 +130 vs HIGH chop 24 +9.9 fix/v5:172, firstswing chop v4_chop.py:26, ATR% 15m.
"""
from __future__ import annotations
import bisect
from typing import Optional

def _chop_series_1h(candles_1h, lb=14):
    n=len(candles_1h)
    # TR for 1h
    tr=[0.0]*n
    for i in range(n):
        hi=float(candles_1h[i]["high"]); lo=float(candles_1h[i]["low"])
        if i==0:
            tr[i]=hi-lo
        else:
            pc=float(candles_1h[i-1]["close"])
            tr[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
    chop=[50.0]*n
    import math
    for i in range(lb, n):
        tr_sum=sum(tr[i-lb+1:i+1])
        hi_max=max(float(candles_1h[j]["high"]) for j in range(i-lb+1, i+1))
        lo_min=min(float(candles_1h[j]["low"]) for j in range(i-lb+1, i+1))
        rang=hi_max-lo_min
        if rang>0 and tr_sum>0:
            try:
                chop[i]=100*math.log10(tr_sum/rang)/math.log10(lb)
            except:
                chop[i]=50.0
        else:
            chop[i]=50.0
    return chop

def _atr_pct_15m(candles_15m):
    n=len(candles_15m)
    tr=[0.0]*n
    for i in range(n):
        hi=float(candles_15m[i]["high"]); lo=float(candles_15m[i]["low"])
        if i==0:
            tr[i]=hi-lo
        else:
            pc=float(candles_15m[i-1]["close"])
            tr[i]=max(hi-lo, abs(hi-pc), abs(lo-pc))
    atr=[0.0]*n
    for i in range(n):
        lo_i=max(0,i-13)
        atr[i]=sum(tr[lo_i:i+1])/(i-lo_i+1)
    pct=[atr[i]/float(candles_15m[i]["close"])*100 if float(candles_15m[i]["close"])!=0 else 0 for i in range(n)]
    return pct

def _hmm_regime_1h(candles_1h, train_frac=0.45, n_iter=40, seed=0):
    """Idea A — 2-state Gaussian HMM on 1h log-returns. Range vs trend router.

    Train Baum-Welch on the first train_frac only (rest never seen by params),
    then causal forward-filter the WHOLE series with frozen params. numpy only.
    Returns P(range)*100 per 1h bar (0..100). Range = state with lower
    |mu|/sigma (less directional drift per unit vol).
    """
    import numpy as np
    n = len(candles_1h)
    if n < 80:
        return [50.0] * n
    cl = np.fromiter((float(c["close"]) for c in candles_1h), dtype=np.float64, count=n)
    ret = np.zeros(n, dtype=np.float64)
    np.log(cl[1:] / cl[:-1], out=ret[1:], where=cl[:-1] > 0)
    n_train = max(60, int(n * train_frac))
    x = ret[1:n_train]
    T = len(x)
    if T < 40:
        return [50.0] * n
    ax = np.abs(x)
    z = (ax <= np.median(ax)).astype(np.int64)

    def _mu_var(sel):
        xs = x[sel]
        if xs.size < 2:
            return 0.0, 1e-4
        m = float(xs.mean())
        return m, float(xs.var()) + 1e-8

    mu = np.array([_mu_var(z == 0)[0], _mu_var(z == 1)[0]])
    var = np.array([_mu_var(z == 0)[1], _mu_var(z == 1)[1]])
    A = np.array([[0.95, 0.05], [0.05, 0.95]], dtype=np.float64)
    pi = np.array([0.5, 0.5], dtype=np.float64)

    def log_gauss(v, m, s2):
        return -0.5 * (np.log(2.0 * np.pi * s2) + (v - m) ** 2 / s2)

    def fwd(logB, A_, pi_):
        T_ = logB.shape[0]
        la = np.empty((T_, 2), dtype=np.float64)
        lA = np.log(A_ + 1e-300)
        la[0] = np.log(pi_ + 1e-300) + logB[0]
        for t in range(1, T_):
            m = la[t - 1][:, None] + lA
            mx = m.max(axis=0)
            la[t] = logB[t] + mx + np.log(np.exp(m - mx).sum(axis=0) + 1e-300)
        return la

    def bwd(logB, A_):
        T_ = logB.shape[0]
        lb = np.zeros((T_, 2), dtype=np.float64)
        lA = np.log(A_ + 1e-300)
        for t in range(T_ - 2, -1, -1):
            m = lA + (logB[t + 1] + lb[t + 1])[None, :]
            row = m.max(axis=1)
            lb[t] = row + np.log(np.exp(m - row[:, None]).sum(axis=1) + 1e-300)
        return lb

    logB = np.column_stack([log_gauss(x, mu[0], var[0]), log_gauss(x, mu[1], var[1])])
    for _ in range(n_iter):
        la = fwd(logB, A, pi)
        lb = bwd(logB, A)
        lg = la + lb
        lg -= lg.max(axis=1, keepdims=True)
        gam = np.exp(lg)
        gam /= gam.sum(axis=1, keepdims=True) + 1e-300
        lxi = (la[:-1, :, None] + np.log(A + 1e-300)[None, :, :]
               + (logB[1:] + lb[1:])[:, None, :])
        lxi -= lxi.max(axis=(1, 2), keepdims=True)
        xi = np.exp(lxi)
        xi /= xi.sum(axis=(1, 2), keepdims=True) + 1e-300
        A = xi.sum(axis=0)
        A /= A.sum(axis=1, keepdims=True) + 1e-300
        pi = gam[0] / (gam[0].sum() + 1e-300)
        for k in range(2):
            w = gam[:, k]
            ws = w.sum() + 1e-300
            mu[k] = float((w * x).sum()) / ws
            var[k] = float((w * (x - mu[k]) ** 2).sum()) / ws + 1e-8
        logB = np.column_stack([log_gauss(x, mu[0], var[0]), log_gauss(x, mu[1], var[1])])
    snr = np.abs(mu) / np.sqrt(var)
    range_k = int(np.argmin(snr))
    logBf = np.column_stack([log_gauss(ret[1:], mu[0], var[0]),
                             log_gauss(ret[1:], mu[1], var[1])])
    laf = fwd(logBf, A, pi)
    out = [50.0] * n
    for t in range(laf.shape[0]):
        row = laf[t] - laf[t].max()
        p = np.exp(row)
        out[t + 1] = float(p[range_k] / (p.sum() + 1e-300) * 100.0)
    return out


def _garch_regime_1h(candles_1h, train_frac=0.45, a=0.1, b=0.85, lb=96):
    """Idea F — GARCH(1,1) predicted-vol regime score on 1h closes.

    omega/alpha/beta frozen from train prefix (path-true); recursive
    sigma2 filter over full series. Returns range-score 0..100 per 1h bar
    (high = low predicted vol = quiet/range), comparable to chop_thresh.
    numpy-free.
    """
    n = len(candles_1h)
    if n < 80:
        return [50.0] * n
    cl = [float(c["close"]) for c in candles_1h]
    ret = [0.0] * n
    for i in range(1, n):
        ret[i] = (cl[i] - cl[i - 1]) / cl[i - 1] if cl[i - 1] > 0 else 0.0
    n_train = max(60, int(n * train_frac))
    x = ret[1:n_train]
    if len(x) < 40:
        return [50.0] * n
    var = sum(v * v for v in x) / len(x)
    omega = max(var * (1.0 - a - b), 1e-14)
    sig2 = [var] * n
    for i in range(1, n):
        sig2[i] = omega + a * ret[i - 1] * ret[i - 1] + b * sig2[i - 1]
    out = [50.0] * n
    for i in range(lb, n):
        w = sig2[i - lb:i + 1]
        cur = sig2[i]
        below = sum(1 for v in w if v < cur)
        out[i] = 100.0 * (1.0 - below / float(len(w)))
    return out


def _r_touch_end(trade, fine_ltf, fine_ts, ext_r):
    """HTF window end = first ts price touches ext_r (1.5R) from HTF entry.
    'We reach 1.5R -> we are done, look for new bias.'
    If SL/cap exit comes first (level never reached), window ends there (bias dead)."""
    d=1 if trade["dir"]=="long" else -1
    pe=float(trade["entry_price"]); psl=float(trade["sl"])
    hrisk=abs(pe-psl)
    if hrisk<=0 or ext_r<=0 or not fine_ltf:
        return int(trade["exit_ts"])
    level=pe+ext_r*hrisk*d
    e_ts=int(trade["exit_ts"])
    import bisect as _b
    k=_b.bisect_right(fine_ts, int(trade["entry_ts"]))
    while k < len(fine_ltf):
        ts=int(fine_ltf[k]["ts"])
        if ts > e_ts: break
        hi=float(fine_ltf[k]["high"]); lo=float(fine_ltf[k]["low"])
        if (d==1 and hi>=level) or (d==-1 and lo<=level):
            return ts
        k+=1
    return e_ts

def simulate_htf_ltf_streak_halt(
    candles_htf, swings_htf, candles_ltf, swings_ltf, fine_ltf=None,
    *,
    htf_bar_secs=3600, ltf_bar_secs=900,
    swings_trail=None,
    exp_momentum=False,
    b3_k=0,
    b3_mode="close",
    exp18_arm=None,
    exp22_conv=False,
    exp_persist=0,
    exp_mltf=False,
    exp27_mode=None,
    exp31_lb=0,
    exp_wage_h=0,
    exp_curfew_a=0.0,
    exp_curfew_b=0.0,
    exp_defer_h=0.0,
    exp_legskip_r=0.0,
    exp_partial_r=0.0,
    exp_skipwin=0,
    exp_swingpause=0,
    exp_skipwin_halt=0,
    exp_skip_weekend=0,
    exp_kinds="",
    exp_skip_utc_sat=0,
    exp_skip_utc_sun=0,
    exp_risk_max_pct=0.0,
    exp_chop15_lo=0.0,
    exp_chop15_hi=0.0,
    exp_atr_ratio_max=0.0,
    exp_max_concurrent=0,
    exp_cohort_swingpause=0,
    exp_cohort_rearm=0,
    exp_cohort_loss_n=1,
    exp_5m_confirm=0,
    exp_5m_wait_min=240,
    exp_5m_data=None,
    exp_5m_stats=None,
    exp_window_r_cap=0.0,
    exp_window_entry_cap=0,
    exp_window_budget_mode="realized",
    exp_campaign_require_marked_r=None,
    exp_campaign_max_addons=0,
    exp_campaign_max_total=0,
    exp_campaign_block_mixed=0,
    exp_campaign_stats=None,
    exp_window_loss_kill_n=0,
    exp_window_loss_kill_scope="window",
    exp_window_loss_kill_action="soft",
    exp_window_win_kill_n=0,
    exp_window_win_kill_scope="window",
    exp_window_win_kill_action="soft",
    exp_window_win_kill_stats=None,
    exp_window_loss_kill_stats=None,
    exp_shadow_book=False,
    exp_geom_mode="",
    exp_geom_b1_max=-1,
    exp_geom_b1_min=-1,
    exp_geom_mag_min_atr=0.0,
    exp_geom_start_dist_max_atr=0.0,
    exp_geom_stats=None,
    exp_b1_b2_mode="",
    exp_b1_b2_stats=None,
    exp_ma_trail_period=0,
    exp_weekly_state_action="",
    exp_loss_streak_n=0,
    exp_loss_streak_mode="global",
    exp_loss_streak_action="",
    exp_event_mode="",
    exp_event_timestamps=(),
    exp_event_dates=(),
    exp_event_shift_min=0,
    exp_event_stats=None,
    exp_entry_candle_min=0.0,
    exp_entry_swing_age_max=0,
    exp_entry_skip_b2_doji=0,
    exp_bias_momentum_min=0.0,
    exp_union_dual_only=0,
    exp_bm_causal=0,
    exp_min_swing_ratio=0.0,
    exp_wick_reject=0.0,
    exp_causal_sl=0,
    exp_trail_max_dist=0.0,
    exp_trail_delay_r=0.0,
    exp_trail_delay_prevbar=0,
    exp_trail_skip_n=0,
    exp_trail_half=0,
    exp_retest_fill=0.0,
    exp_retest_wait=240,
    exp_profit_stage_r=0.0,
    exp_profit_stage_distance_r=0.0,
    exp_require_dir_match=0,
    exp_dir_causal=0,
    exp_max_swing_age=0,
    exp_max_running_mag=0.0,
    exp_halt_skip_n=1,
    exp_skip_decisive=0,
    exp_flip_break=0,
    exp_regime_skip=0.0,
    exp_pivot_trail=0,
    exp_eth_skip=0.0,
    exp_eth_lb=24,
    exp_eth_closes=None,
    exp_vol_b2_rvol=0.0,
    exp_vol_pct_min=0.0,
    exp_vol_route=0.0,
    exp_vol_exit_r=0.0,
    exp_vol_dry_exit=0.0,
    exp_vol_dry_bars=8,
    exp_vol_dry_be=0.0,
    exp_vol_nospk=0.0,
    exp_vol_nospk_bars=12,
    exp_pb_lo=0.0,
    exp_pb_hi=0.0,
    exp_mtf_mode=0,
    exp_struct_mag_min=0.0,
    exp_struct_freq_max=0.0,
    sl_buf_atr=0.25, ext_stop_r=1.5,
    chop_thresh=61.8, atr_low_thresh=0.35, atr_high_thresh=0.65,
    mode="chop",  # chop, atr_low, atr_both, chop_or_atr, soft_chop, soft_atr, soft_ensemble, garch, garch_inv
    soft_width=4.0,  # Idea D: half-width of soft band (0 = hard switch)
    cooldown_bars=0,
    max_consecutive_losses=0,  # 0 = no halt, N = halt after N consecutive losses
    htf_rr=3.0,  # HTF (1h) fixed R target — controls when window closes
    window_end="exit",  # "exit" = HTF trade exit (SL/target/16-day cap) [default, +331R];
                        # "r_touch" = first touch of ext_stop_r 1.5R [tested: +200.6R, -130R vs exit]
):
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    import bisect as bs
    if swings_trail is None: swings_trail=swings_ltf
    # Build HTF intervals for both flip and decisive
    htf_trades_flip = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="flip", sl_mode="swing", rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine_ltf, cap_days=16)
    htf_trades_decisive = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="decisive", sl_mode="swing", rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine_ltf, cap_days=16)
    htf_trades_b2 = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="b2", sl_mode="swing", rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True, fine=fine_ltf, cap_days=16)
    fine_ts=[int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    def to_intervals(trades):
        # Window end: "exit" = HTF trade exit (SL/target/cap) — default, best R.
        # "r_touch" = first touch of 1.5R — tested 2026-09-08: +200.6R vs +331R (removed 88 trades avg +1.48R). Rejected.
        # "bias_flip" = next OPPOSITE-direction HTF entry (bias-based, not trade-based).
        # Tested 2026-09-08: 485t +368.6R vs exit 330t +331.1R (+37.5R) BUT added cohort t=1.21 (not significant),
        # 2026 worse (+55.1/DD7.3 vs +69.0/DD5.0), 2023 flat R at 85% more churn. net/DD 38.6 vs 34.0. NOT adopted.
        iv=[]
        last_htf_ts=int(candles_htf[-1]["ts"]) if candles_htf else 0
        for t in trades:
            if t["outcome"]=="open":
                # L1: still-open HTF window = active bias through end of slice.
                # Truncated causal slices always end with the governing window
                # open; dropping it zeroed every LTF gate (C10 L1).
                iv.append([int(t["entry_ts"]), last_htf_ts + 3600,
                           1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])])
                continue
            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) if window_end=="r_touch" else int(t["exit_ts"])
            iv.append([int(t["entry_ts"]), wend, 1 if t["dir"]=="long" else -1, float(t["entry_price"]), float(t["sl"])])
        iv.sort(key=lambda x: x[0])
        if window_end=="bias_flip":
            last_ts=int(candles_htf[-1]["ts"])
            for i,w in enumerate(iv):
                nxt=None
                for j in range(i+1,len(iv)):
                    if iv[j][2]!=w[2]:
                        nxt=iv[j][0]; break
                w[1]=(nxt-1) if nxt is not None else max(w[1], last_ts)
        return [tuple(w) for w in iv]
    intervals_flip=to_intervals(htf_trades_flip)
    intervals_decisive=to_intervals(htf_trades_decisive)
    intervals_b2=to_intervals(htf_trades_b2)
    starts_flip=[s for s,_,_,_,_ in intervals_flip]
    starts_decisive=[s for s,_,_,_,_ in intervals_decisive]
    starts_b2=[s for s,_,_,_,_ in intervals_b2]
    # Regime series: chop 1h and atr% 15m mapped to LTF bar ts
    chop=_chop_series_1h(candles_htf, lb=(exp31_lb or 14))
    atr_pct=_atr_pct_15m(candles_ltf)
    chop15_ser=_chop_series_1h(candles_ltf, lb=28)
    _tr15=[0.0]*len(candles_ltf)
    for _i, _c in enumerate(candles_ltf):
        _h, _l = float(_c["high"]), float(_c["low"])
        _pc = float(candles_ltf[_i-1]["close"]) if _i else _h
        _tr15[_i] = max(_h-_l, abs(_h-_pc), abs(_l-_pc))
    _a5 = [0.0]*len(candles_ltf); _a20 = [0.0]*len(candles_ltf); _ar15 = [1.0]*len(candles_ltf)
    for _i in range(len(candles_ltf)):
        _a5[_i] = sum(_tr15[max(0, _i-4):_i+1]) / min(5, _i+1)
        _a20[_i] = sum(_tr15[max(0, _i-19):_i+1]) / min(20, _i+1)
        _px = float(candles_ltf[_i]["close"])
        if _a20[_i] > 0:
            _ar15[_i] = _a5[_i] / _a20[_i]
    _bm_mags=[]
    for _bm_s in swings_htf:
        _bm_seg=_bm_s.get("seg") or {}
        _bm_spx=float(_bm_seg.get("start_px",0) or 0)
        _bm_epx=float(_bm_seg.get("end_px",0) or 0)
        _bm_mags.append(abs(_bm_epx-_bm_spx))
    _bm_breaks=[]
    for _bmi in range(len(swings_htf)):
        if _bmi<1 or _bm_mags[_bmi-1]<=0: continue
        _bm_ratio=_bm_mags[_bmi]/_bm_mags[_bmi-1]
        for _bmb in (swings_htf[_bmi].get("breaks") or []):
            _bmbt=_bmb.get("time","")
            if _bmbt: _bm_breaks.append((_bmbt[:19],_bm_ratio,int(swings_htf[_bmi].get("confirmed_at_idx",-1))))
    _bm_breaks.sort(key=lambda z:z[0])
    _bm_times=[z[0] for z in _bm_breaks]
    _knowwin = htf_bar_secs - ltf_bar_secs  # C15: HTF close - LTF close
    candle_ts_ltf=[int(c["ts"]) for c in candles_ltf]
    _sw_pairs=sorted((candle_ts_ltf[int(sw["confirmed_at_idx"])], candle_ts_ltf[int(sw["seg"]["start_idx"])]) for sw in swings_ltf if sw.get("confirmed_at_idx") is not None and 0 <= int(sw["confirmed_at_idx"]) < len(candle_ts_ltf) and sw.get("seg") is not None and 0 <= int(sw["seg"].get("start_idx", -1)) < len(candle_ts_ltf))
    confs_ts=[p[0] for p in _sw_pairs]
    pivs_ts=[p[1] for p in _sw_pairs]
    if exp_5m_data:
        _exp_5m_sorted=sorted(exp_5m_data,key=lambda _c:int(_c["ts"])+300)
        _exp_5m_ts=[int(_c["ts"])+300 for _c in _exp_5m_sorted]
        _exp_5m_by_close={int(_c["ts"])+300:_c for _c in _exp_5m_sorted}
    _ma15=[None]*len(candles_ltf)
    _ma_period=int(exp_ma_trail_period)
    if _ma_period>0:
        _ma_sum=0.0
        for _mi,_mc in enumerate(candles_ltf):
            _ma_sum += float(_mc["close"])
            if _mi >= _ma_period: _ma_sum -= float(candles_ltf[_mi-_ma_period]["close"])
            if _mi >= _ma_period-1: _ma15[_mi]=_ma_sum/_ma_period
    candle_ts_htf=[int(c["ts"]) for c in candles_htf]
    candle_ts_htf_close=[t+htf_bar_secs for t in candle_ts_htf]
    closes_htf=[float(c["close"]) for c in candles_htf]
    htf_hi=[float(c["high"]) for c in candles_htf]
    htf_lo=[float(c["low"]) for c in candles_htf]
    # C14: regime gate at the ENTRY INSTANT (signal bar close = next candle open).
    # Only 1h candles that CLOSED by the entry instant may set the regime -
    # the running 1h candle's final chop is future data (up to 45 min lookahead).
    # Precompute chop per LTF bar from the last 1h bar CLOSED by ts+ltf_bar_secs.
    candle_ts_htf_close=[t+htf_bar_secs for t in candle_ts_htf]
    chop_per_ltf=[50.0]*len(candles_ltf)
    _rg_s=None; _rg_c=0
    _eth_mom=[0.0]*len(candles_ltf)
    if exp_eth_skip>0 and exp_eth_closes is not None and len(exp_eth_closes)==len(candles_htf):
        _er=[]
        for _i in range(len(candles_htf)):
            _bc=float(candles_htf[_i]["close"]); _er.append(float(exp_eth_closes[_i])/_bc if _bc>0 else 0.0)
        _elb=max(1,int(exp_eth_lb))
        for _bi in range(len(candles_ltf)):
            _j=bs.bisect_right(candle_ts_htf, candle_ts_ltf[_bi])-1
            _k=bs.bisect_right(candle_ts_htf, candle_ts_ltf[_bi]-_elb*3600)-1
            if _j>=0 and _k>=0 and _er[_k]>0: _eth_mom[_bi]=(_er[_j]/_er[_k])-1.0
    _vol15=[float(c.get("volume") or 0.0) for c in candles_ltf]
    _rvol15=[1.0]*len(candles_ltf)
    _pct15=[50.0]*len(candles_ltf)
    _vw=96
    _vp=[0.0]
    for _vv in _vol15: _vp.append(_vp[-1]+_vv)
    for _vi in range(len(candles_ltf)):
        _lo=max(0,_vi-_vw)
        if _vi-_lo<8: continue
        _cur=_vol15[_vi]
        _win=_vol15[_lo:_vi]
        _pct15[_vi]=100.0*sum(1 for _x in _win if _x<=_cur)/len(_win)
        _mean=(_vp[_vi]-_vp[_lo])/(_vi-_lo)
        if _mean>0: _rvol15[_vi]=_cur/_mean
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+ltf_bar_secs)-1
        if j>=0 and j < len(chop):
            chop_per_ltf[i]=chop[max(0,j)]
    # --- NEW MODE DATA: swing direction/magnitude per LTF bar ---
    import datetime as _dt
    def _sw_ts_dir_mag(swings):
        tss,ds,ms=[],[],[]
        for sw in swings:
            t=sw.get("confirmed_at_time","")
            if isinstance(t,str) and len(t)>=19:
                try: ts=int(_dt.datetime.strptime(t[:19],"%Y-%m-%d %H:%M:%S").timestamp())
                except: continue
            elif isinstance(t,(int,float)): ts=int(t)
            else: continue
            d=1 if sw.get("dir")=="up" else -1
            seg=sw.get("seg",{})
            sp=float(seg.get("start_px",0)); ep=float(seg.get("end_px",0))
            mag=abs(ep-sp)/sp if sp>0 else 0
            tss.append(ts); ds.append(d); ms.append(mag)
        return tss,ds,ms
    htf_sw_ts,htf_sw_dir,htf_sw_mag=_sw_ts_dir_mag(swings_htf)
    ltf_sw_ts,ltf_sw_dir,ltf_sw_mag=_sw_ts_dir_mag(swings_ltf)
    htf_dir_per_ltf=[0]*len(candles_ltf)
    htf_mag_per_ltf=[0.0]*len(candles_ltf)
    ltf_dir_per_ltf=[0]*len(candles_ltf)
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(htf_sw_ts, ts+ltf_bar_secs)-1
        if j>=0: htf_dir_per_ltf[i]=htf_sw_dir[j]; htf_mag_per_ltf[i]=htf_sw_mag[j]
        j2=bs.bisect_right(ltf_sw_ts, ts+ltf_bar_secs)-1
        if j2>=0: ltf_dir_per_ltf[i]=ltf_sw_dir[j2]
    # Rolling percentile of chop (for dynamic_chop mode)
    chop_pct_per_ltf=[50.0]*len(candles_ltf)
    _lookback=672
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+ltf_bar_secs)-1
        if j>=0:
            _s=max(0,j-_lookback); _w=chop[_s:j+1]
            if _w:
                _cur=chop[j]; _below=sum(1 for c in _w if c<_cur)
                chop_pct_per_ltf[i]=_below/len(_w)*100.0
    # --- Session per LTF bar (Idea H): 0=Asia(0-7), 1=London(7-14), 2=NY(14-21), 3=Night(21-24) ---
    session_per_ltf=[0]*len(candles_ltf)
    import datetime as _dts
    for i,ts in enumerate(candle_ts_ltf):
        _hr=_dts.datetime.utcfromtimestamp(ts).hour
        if _hr<7: session_per_ltf[i]=0      # Asia: range→B2
        elif _hr<14: session_per_ltf[i]=1   # London: trend→FLIP
        elif _hr<21: session_per_ltf[i]=2   # NY: trend→FLIP
        else: session_per_ltf[i]=3           # Night: range→B2
    # --- Rolling entropy of 1h returns (Idea L) --- computed per HTF bar, mapped to LTF
    import math
    _ret_1h=[]
    for i in range(1,len(candles_htf)):
        p0=float(candles_htf[i-1]["close"]); p1=float(candles_htf[i]["close"])
        _ret_1h.append((p1-p0)/p0 if p0>0 else 0.0)
    _ent_lb=96  # 4 days — compute per HTF bar (not per LTF bar) for speed
    _ent_htf=[50.0]*len(candles_htf)
    _nhtf=len(candles_htf)
    for i in range(_ent_lb, len(_ret_1h)):
        _wins=_ret_1h[i-_ent_lb:i]
        if not _wins: continue
        _nbins=min(15,max(5,int(math.sqrt(len(_wins)))))
        _mn=min(_wins); _mx=max(_wins); _rng=_mx-_mn
        if _rng<=0: continue
        _bins=[0]*_nbins
        for v in _wins:
            bi=min(int((v-_mn)/_rng*_nbins), _nbins-1)
            _bins[bi]+=1
        _tot=float(len(_wins)); _ent=0.0
        for c in _bins:
            if c>0:
                p=c/_tot; _ent -= p*math.log2(p)
        _max_ent=math.log2(_nbins) if _nbins>1 else 1.0
        _ei=i+1
        if _ei<_nhtf:
            _ent_htf[_ei]=(_ent/_max_ent)*100.0 if _max_ent>0 else 50.0
    entropy_per_ltf=[50.0]*len(candles_ltf)
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+ltf_bar_secs)-1
        if j>=0 and j<len(_ent_htf):
            entropy_per_ltf[i]=_ent_htf[j]
    # --- Rolling fractal dimension of 1h candles (Idea K) --- computed per HTF bar, mapped
    fd_per_ltf=[50.0]*len(candles_ltf)
    _fd_lb=48  # 2 days — reduced for speed
    _fd_htf=[50.0]*len(candles_htf)
    for i in range(_fd_lb, len(candles_htf)):
        _cl=[float(candles_htf[k]["close"]) for k in range(i-_fd_lb, i+1)]
        if len(_cl)<4: continue
        _mn=min(_cl); _mx=max(_cl); _rng2=_mx-_mn
        if _rng2<=0: continue
        _ds=[]; _ps=[]
        for _step in (1,2,4):
            _sum=0.0; _cnt=0
            for _k in range(_step, len(_cl)):
                _sum+=abs(_cl[_k]-_cl[_k-_step]); _cnt+=1
            if _cnt>0 and _rng2>0:
                _ds.append(math.log(_sum/_cnt/_rng2+1e-12))
                _ps.append(math.log(1.0/_step))
        if len(_ds)>=2:
            _ss=sum(_ds); _sps=sum(_ps)
            _sps2=sum(p*p for p in _ps); _ssp=sum(d*p for d,p in zip(_ds,_ps))
            _den=len(_ds)*_sps2-_sps*_sps
            if abs(_den)>1e-15:
                _slope=(len(_ds)*_ssp-_ss*_sps)/_den
                fd=1.0-abs(_slope)
                _fd_htf[i]=max(0.0,min(100.0,(1.0-fd)*100.0))
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+ltf_bar_secs)-1
        if j>=0 and j<len(_fd_htf):
            fd_per_ltf[i]=_fd_htf[j]
    # --- HMM regime (Idea A): train prefix, forward-filter full series ---
    hmm_per_ltf=[50.0]*len(candles_ltf)
    if mode in ("hmm","hmm_inv"):
        _hmm_htf=_hmm_regime_1h(candles_htf)
        for i,ts in enumerate(candle_ts_ltf):
            j=bs.bisect_right(candle_ts_htf_close, ts+ltf_bar_secs)-1
            if j>=0 and j<len(_hmm_htf):
                hmm_per_ltf[i]=_hmm_htf[j]
    # --- GARCH regime (Idea F): predicted-vol range score, train-frozen params ---
    garch_per_ltf=[50.0]*len(candles_ltf)
    if mode in ("garch","garch_inv"):
        _garch_htf=_garch_regime_1h(candles_htf)
        for i,ts in enumerate(candle_ts_ltf):
            j=bs.bisect_right(candle_ts_htf_close, ts+ltf_bar_secs)-1
            if j>=0 and j<len(_garch_htf):
                garch_per_ltf[i]=_garch_htf[j]
    # LTF signals (decisive)
    from src.btc.btc_engine import CandleStore
    ltf_store = CandleStore(candles_ltf)
    ltf_sigs=_collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)
    if exp18_arm:
        _mk=[]
        for _si,_s in enumerate(swings_ltf):
            for _b in _s.get("breaks",[]):
                if _b.get("time"):
                    _mk.append((int(_b["idx"]),_si,_b["kind"],
                        1 if _b["dir"]=="up" else -1))
        _mk.sort(key=lambda z:(z[0],z[1]))
        _seq=[]; ltf_sigs=[]
        for _mi,_si,_mkind,_md in _mk:
            _s=swings_ltf[_si]
            _sdir=1 if _s.get("dir")=="up" else -1
            _prev=swings_ltf[_si-1] if _si>0 else None
            if int(_s.get("swing_index",_si))<1 or _prev is None:
                _seq=[]; continue
            _pfs=int(_prev.get("confirmed_at_idx",-1))
            if _pfs>=0 and _mi<_pfs:
                _seq=[]; continue
            _res=False; _tdir=0
            if not _seq:
                if _mkind=="B1": _seq=[_md]
            else:
                _seq.append(_md)
                if len(_seq)==2 and exp18_arm=="D" and _seq[0]!=_seq[1]:
                    _tdir=_md; _res=True
                elif len(_seq)>=3:
                    _a,_b2,_c=_seq[0],_seq[1],_seq[2]
                    if exp18_arm=="full": _tdir=_c
                    elif exp18_arm=="P1": _tdir=_c if (_a==_b2==_c) else 0
                    elif exp18_arm=="P2b": _tdir=(0 if (_a==_b2!=_c) else _c)
                    elif exp18_arm=="D": _tdir=_c
                    _res=True
            if _res:
                if _tdir!=0:
                    _pe=int(_prev["seg"]["end_idx"]) if _prev is not None else 0
                    _rng=range(max(0,_pe),min(_mi,len(candles_ltf)-1)+1)
                    _piv=(min(float(candles_ltf[k]["low"]) for k in _rng) if _tdir==1
                          else max(float(candles_ltf[k]["high"]) for k in _rng))
                    if _piv>0:
                        ltf_sigs.append({"bar":candles_ltf[_mi]["date"],
                            "dir":_tdir,"swing_start_px":_piv,
                            "swing_no":_si,"kind":_mkind})
                _seq=[]
    _exp_weekly_state_rows=[]
    filtered=[]
    _exp_event_stats={"blocked":0,"mode":exp_event_mode}
    for sig in ltf_sigs:
        bar_time=sig["bar"]  # datetime string
        bar=ltf_store.pos(bar_time)  # position via timestamp lookup
        if bar < 0 or bar >= len(candles_ltf): continue
        bar_ts=candle_ts_ltf[bar]
        # regime at bar
        ch=chop_per_ltf[bar] if bar < len(chop_per_ltf) else 50.0
        atrp=atr_pct[bar] if bar < len(atr_pct) else 0.5
        # decide which HTF interval set to use
        use="flip"
        if mode=="chop":
            use="decisive" if ch > chop_thresh else "flip"
        elif mode=="atr_low":
            use="decisive" if atrp < atr_low_thresh else "flip"
        elif mode=="atr_high":
            use="decisive" if atrp > atr_high_thresh else "flip"
        elif mode=="chop_or_atr_low":
            use="decisive" if (ch > chop_thresh or atrp < atr_low_thresh) else "flip"
        elif mode=="chop_and_atr_low":
            use="decisive" if (ch > chop_thresh and atrp < atr_low_thresh) else "flip"
        elif mode=="b2_vs_flip_chop":
            # HTF B2 vs Flip conditional: use B2 when chop high else Flip
            use="b2" if ch > chop_thresh else "flip"
        elif mode=="decisive_vs_flip_chop":
            use="decisive" if ch > chop_thresh else "flip"
        elif mode=="htf_dir":
            use="b2" if htf_dir_per_ltf[bar]==1 else "flip"
        elif mode=="htf_mag":
            use="b2" if htf_mag_per_ltf[bar]>(chop_thresh/10000.0) else "flip"
        elif mode=="htf_mag_inv":
            use="flip" if htf_mag_per_ltf[bar]>(chop_thresh/10000.0) else "b2"
        elif mode=="flip_quality":
            use="b2" if ch > chop_thresh else "flip"
            if use=="flip" and htf_mag_per_ltf[bar]<(chop_thresh/10000.0):
                continue
        elif mode=="ltf_dir":
            use="b2" if ltf_dir_per_ltf[bar]==1 else "flip"
        elif mode=="dynamic_chop":
            use="b2" if chop_pct_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="union":
            use="union"
        elif mode=="session":
            # Idea H: Asia(0,3)=range→B2, London/NY(1,2)=trend→flip
            _s=session_per_ltf[bar]
            use="b2" if _s in (0,3) else "flip"
        elif mode=="session_flip":
            # Inverted: Asia→flip, London/NY→B2
            _s=session_per_ltf[bar]
            use="flip" if _s in (0,3) else "b2"
        elif mode=="entropy":
            # Idea L: low entropy=range→B2, high entropy=trend→flip
            use="b2" if entropy_per_ltf[bar]<chop_thresh else "flip"
        elif mode=="entropy_inv":
            use="flip" if entropy_per_ltf[bar]<chop_thresh else "b2"
        elif mode=="fd":
            # Idea K: low FD=trend→flip, high FD=range→B2
            use="b2" if fd_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="fd_inv":
            use="flip" if fd_per_ltf[bar]>chop_thresh else "b2"
        elif mode=="hmm":
            # Idea A: P(range)*100 > chop_thresh → range → B2 else flip
            use="b2" if hmm_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="hmm_inv":
            use="flip" if hmm_per_ltf[bar]>chop_thresh else "b2"
        elif mode=="garch":
            # Idea F: low predicted vol (high range-score) → B2, high vol → flip
            use="b2" if garch_per_ltf[bar]>chop_thresh else "flip"
        elif mode=="garch_inv":
            use="flip" if garch_per_ltf[bar]>chop_thresh else "b2"
        elif mode=="soft_chop":
            # Idea D: soft band around chop_thresh — uncertain zone uses both windows
            _hw=max(float(soft_width),0.0)
            if ch>chop_thresh+_hw: use="b2"
            elif ch<chop_thresh-_hw: use="flip"
            else: use="decisive"
        elif mode=="soft_atr":
            # Idea D soft on production atr_high path; band falls back to chop
            _hw=max(float(soft_width),0.0)
            if atrp>atr_high_thresh+_hw: use="decisive"
            elif atrp<atr_high_thresh-_hw: use="flip"
            else: use="decisive" if ch>chop_thresh else "flip"
        elif mode=="soft_ensemble":
            # Idea D: blend chop + ATR% + entropy + FD into one range score (0-100),
            # soft-route: high→B2, low→FLIP, band→decisive (both).
            _hw=max(float(soft_width),1e-6)
            def _ramp(x,thr,half=1.0):
                if half<=0: return 1.0 if x>thr else 0.0
                if x>=thr+half: return 1.0
                if x<=thr-half: return 0.0
                return 0.5+0.5*(x-thr)/half
            _p=0.25*(
                _ramp(ch,chop_thresh,_hw)
                + _ramp(atrp*100.0,atr_high_thresh*100.0,_hw)
                + _ramp(100.0-entropy_per_ltf[bar],50.0,_hw)
                + _ramp(fd_per_ltf[bar],50.0,_hw)
            )*100.0
            if _p>50.0+_hw: use="b2"
            elif _p<50.0-_hw: use="flip"
            else: use="decisive"
        else:
            use="flip"
        if exp_vol_route>0:
            use="flip" if _rvol15[bar]<exp_vol_route else "b2"
        elif exp_vol_route<0:
            use="b2" if _rvol15[bar]<(-exp_vol_route) else "flip"
        if exp_persist>0:
            if _rg_s is None: _rg_s=use
            if use!=_rg_s:
                _rg_c+=1
                if _rg_c>=exp_persist: _rg_s=use; _rg_c=0
            else: _rg_c=0
            use=_rg_s
        if exp_event_mode:
            _event_now=int(bar_ts)+900
            if exp_event_mode=="exact" and any(int(_ets)+int(exp_event_shift_min)*60-3600 <= _event_now <= int(_ets)+int(exp_event_shift_min)*60+1800 for _ets in exp_event_timestamps):
                _exp_event_stats["blocked"] += 1
                continue
            if exp_event_mode=="day":
                import datetime as _event_dt
                _event_day=_event_dt.datetime.fromtimestamp(_event_now, _event_dt.timezone.utc).date().isoformat()
                if _event_day in exp_event_dates:
                    _exp_event_stats["blocked"] += 1
                    continue
        # pick intervals
        if use=="union":
            # Idea 2: check BOTH B2 and FLIP intervals
            _union_matched = False
            _matched_b2 = False
            _matched_flip = False
            for _iv,_st,_typ in [(intervals_b2,starts_b2,"b2"),(intervals_flip,starts_flip,"flip")]:
                if not _iv: continue
                _idx=bs.bisect_right(_st,bar_ts)-1
                if _idx<0: continue
                _s,_e,_d,_pe,_psl=_iv[_idx]
                if (_s+_knowwin<bar_ts<=_e+_knowwin) and sig["dir"]==_d:
                    _union_matched=True
                    if _typ=="b2": _matched_b2=True
                    else: _matched_flip=True
                    pe=_pe; psl=_psl; d=_d
            if not _union_matched: continue
            if exp_union_dual_only and _matched_flip and not _matched_b2:
                continue
            if ext_stop_r>0:
                hrisk=abs(pe-psl)
                if hrisk>0:
                    ext=(float(candles_ltf[bar]["close"])-pe)*d/hrisk
                    if ext>ext_stop_r: continue
            filtered.append((sig,use))
            continue
        elif use=="flip":
            intervals=intervals_flip; starts=starts_flip
        elif use=="b2":
            intervals=intervals_b2; starts=starts_b2
        else:
            intervals=intervals_decisive; starts=starts_decisive
        if not intervals:
            continue
        idx=bs.bisect_right(starts, bar_ts)-1
        if idx<0: continue
        s,e,d,pe,psl=intervals[idx]
        # C15: the window is knowable from the flip candle CLOSE (entry_ts + 3600);
        # the LTF entry instant is bar_ts + 900. Gate in knowable-instant space.
        if not (s + _knowwin < bar_ts <= e + _knowwin): continue
        if exp_wage_h>0 and (bar_ts-s)/3600.0 < exp_wage_h: continue
        if exp_curfew_b>0 and exp_curfew_a<=(bar_ts-s)/3600.0<exp_curfew_b: continue
        if exp_legskip_r>0:
            _j2=idx
            while _j2>0 and intervals[_j2-1][2]==d: _j2-=1
            _anc=intervals[_j2][0]
            _li=bs.bisect_right(candle_ts_htf,_anc); _hi2=bs.bisect_right(candle_ts_htf,bar_ts)
            _hr=abs(pe-psl)
            if _hr>0 and _hi2>_li:
                _prog=(float(candles_ltf[bar]["close"])-_anc)*d/_hr
                if _prog>exp_legskip_r: continue
        if exp_loss_streak_action in ("override", "opposite", "augment") and sig["dir"] != d:
            _exp_ns = dict(sig)
            _exp_ns["_exp_htf_dir"] = int(d)
            _exp_ns["_exp_opposite_candidate"] = True
            filtered.append((_exp_ns, use))
        if sig["dir"] != d: continue
        if exp_defer_h>0:
            _age=(bar_ts-s)/3600.0
            if _age < exp_defer_h:
                _tsd=int(s)+int(exp_defer_h*3600)
                _k=bs.bisect_left(candle_ts_ltf,_tsd)
                if _k<len(candles_ltf) and candle_ts_ltf[_k]<=e+_knowwin and _k>bar:
                    _slp=float(sig["swing_start_px"])
                    _dead=False
                    for _q in range(bar+1,_k+1):
                        if d==1 and float(candles_ltf[_q]["low"])<=_slp:_dead=True;break
                        if d==-1 and float(candles_ltf[_q]["high"])>=_slp:_dead=True;break
                    if not _dead:
                        _ok=True
                        _hr=abs(pe-psl)
                        if ext_stop_r>0 and _hr>0:
                            _ex2=(float(candles_ltf[_k]["close"])-pe)*d/_hr
                            if _ex2>ext_stop_r:_ok=False
                        if _ok:
                            _ns=dict(sig);_ns["bar"]=candles_ltf[_k]["date"]
                            filtered.append((_ns,use))
                continue
        if exp_loss_streak_action in ("override", "opposite", "augment"):
            _exp_ns = dict(sig)
            _exp_ns["_exp_htf_dir"] = int(d)
            _exp_ns["_exp_opposite_candidate"] = False
            sig = _exp_ns
        if exp_momentum:
            _j=bs.bisect_right(candle_ts_htf_close, bar_ts+ltf_bar_secs)-1
            if _j>=2:
                _ma=(closes_htf[_j-2]+closes_htf[_j-1]+closes_htf[_j])/3.0
                if sig["dir"]==1 and closes_htf[_j]<_ma: continue
                if sig["dir"]==-1 and closes_htf[_j]>_ma: continue
        if ext_stop_r>0:
            hrisk=abs(pe-psl)
            if hrisk>0:
                ext=(float(candles_ltf[bar]["close"])-pe)*d/hrisk
                if ext > ext_stop_r: continue
        if exp_pb_lo>0 or exp_pb_hi>0:
            _hr=abs(pe-psl)
            if _hr>0:
                _j=idx
                while _j>0 and intervals[_j-1][2]==d: _j-=1
                _anc=intervals[_j][0]
                _li=bs.bisect_right(candle_ts_htf, _anc)
                _hi=bs.bisect_right(candle_ts_htf, bar_ts)
                if _hi>_li:
                    _cl=float(candles_ltf[bar]["close"])
                    if d==1:
                        _ext=max(htf_hi[_li:_hi]); _pb=(_ext-_cl)/_hr
                    else:
                        _ext=min(htf_lo[_li:_hi]); _pb=(_cl-_ext)/_hr
                    _skip=False
                    if exp_pb_lo>0 and exp_pb_hi>0:
                        _skip=exp_pb_lo<=_pb<=exp_pb_hi
                    elif exp_pb_lo>0: _skip=_pb>=exp_pb_lo
                    elif exp_pb_hi>0: _skip=_pb<=exp_pb_hi
                    if _skip: continue
        if exp_geom_mode:
            _gs_idx=int(sig.get("swing_no",-1))
            _gs=swings_ltf[_gs_idx] if 0<=_gs_idx<len(swings_ltf) else None
            _gseg=(_gs.get("seg") or {}) if _gs is not None else {}
            _gstart=int(_gseg.get("start_idx",bar))
            _gstart_px=float(_gseg.get("start_px",candles_ltf[bar]["close"]))
            _gb1=max((m for m in ((_gs.get("breaks") or []) if _gs is not None else []) if m.get("kind")=="B1" and int(m.get("idx",-1))<=bar),key=lambda m:int(m.get("idx",-1)),default=None)
            _gb1age=(int(_gb1.get("idx"))-_gstart) if _gb1 is not None else None
            _gatr=max(float(candles_ltf[j]["high"])-float(candles_ltf[j]["low"]) for j in range(max(0,bar-13),bar+1)) if bar>=0 else 1.0
            _gatr=max(_gatr,1e-9)
            _gmag=(max(float(candles_ltf[j]["high"]) for j in range(max(0,_gstart),bar+1))-min(float(candles_ltf[j]["low"]) for j in range(max(0,_gstart),bar+1)))/_gatr if bar>=_gstart else None
            _gdist=abs(float(candles_ltf[bar]["close"])-_gstart_px)/_gatr
            _gok=True
            _gm=set(exp_geom_mode.split("+"))
            if "fresh_b1" in _gm and (_gb1age is None or (exp_geom_b1_max>=0 and _gb1age>exp_geom_b1_max)): _gok=False
            if "not_stale_b1" in _gm and _gb1age is not None and exp_geom_b1_min>=0 and _gb1age>=exp_geom_b1_min: _gok=False
            if "large_mag" in _gm and (_gmag is None or _gmag<exp_geom_mag_min_atr): _gok=False
            if "not_large_mag" in _gm and (_gmag is not None and _gmag>=exp_geom_mag_min_atr): _gok=False
            if "near_start" in _gm and _gdist>exp_geom_start_dist_max_atr: _gok=False
            if exp_geom_stats is not None: exp_geom_stats.append({"entry_idx":bar,"swing_no":_gs_idx,"b1_age":_gb1age,"mag_atr":_gmag,"start_dist_atr":_gdist,"allowed":int(_gok),"mode":exp_geom_mode})
            if not _gok: continue
        if exp_b1_b2_mode and sig.get("kind")=="B2":
            _bs_idx=int(sig.get("swing_no",-1))
            _bs=swings_ltf[_bs_idx] if 0<=_bs_idx<len(swings_ltf) else None
            _bm1=max((m for m in ((_bs.get("breaks") or []) if _bs is not None else []) if m.get("kind")=="B1" and int(m.get("idx",-1))<bar),key=lambda m:int(m.get("idx",-1)),default=None)
            _want_dir="up" if int(sig.get("dir",0))>0 else "down"
            _bm2=next((m for m in ((_bs.get("breaks") or []) if _bs is not None else []) if m.get("kind")=="B2" and m.get("dir")==_want_dir and int(m.get("idx",-1))==bar),None)
            _b1b2=(int(_bm2.get("idx"))-int(_bm1.get("idx"))) if _bm1 is not None and _bm2 is not None else None
            _bok=True
            if exp_b1_b2_mode=="block_immediate" and _b1b2 is not None and _b1b2<=2: _bok=False
            if exp_b1_b2_mode.startswith("block_age") and _b1b2 is not None and _b1b2==int(exp_b1_b2_mode[-1]): _bok=False
            if exp_b1_b2_mode=="block_0_1" and _b1b2 is not None and 0<=_b1b2<=1: _bok=False
            if exp_b1_b2_mode=="only_delayed_3_8" and (_b1b2 is None or _b1b2<3 or _b1b2>8): _bok=False
            if exp_b1_b2_stats is not None: exp_b1_b2_stats.append({"entry_idx":bar,"swing_no":_bs_idx,"b1_b2_bars":_b1b2,"allowed":int(_bok),"mode":exp_b1_b2_mode})
            if not _bok: continue
        if exp_flip_break:
            _cl_fb=float(candles_ltf[bar]["close"])
            if int(sig["dir"])==1 and not (_cl_fb > pe): continue
            if int(sig["dir"])==-1 and not (_cl_fb < pe): continue
        if exp_weekly_state_action:
            import datetime as _dt
            _cutoff=int(bar_ts)+900
            _cdt=_dt.datetime.fromtimestamp(_cutoff,_dt.timezone.utc)
            _cs=int((_cdt-_dt.timedelta(days=_cdt.weekday(),hours=_cdt.hour,minutes=_cdt.minute,seconds=_cdt.second,microseconds=_cdt.microsecond)).timestamp())
            _ps=_cs-7*86400
            _prior=[_c for _c in candles_ltf if _ps<=int(_c["ts"])<_cs]
            _cur=[_c for _c in candles_ltf if _cs<=int(_c["ts"])<_cutoff]
            _ph=max(float(_c["high"]) for _c in _prior) if _prior else None
            _pl=min(float(_c["low"]) for _c in _prior) if _prior else None
            _price=float(candles_ltf[bar]["close"])
            _ws="unknown"; _wb={}
            if _ph is not None and _pl is not None and _ph>_pl:
                _ch=max(float(_c["high"]) for _c in _cur) if _cur else None
                _cl=min(float(_c["low"]) for _c in _cur) if _cur else None
                _hc=[_c for _c in candles_htf if _cs<=int(_c["ts"]) and int(_c["ts"])+3600<=_cutoff]
                _hi_break=_ch is not None and _ch>_ph
                _lo_break=_cl is not None and _cl<_pl
                _hi_acc=_hi_break and any(float(_c["close"])>_ph for _c in _hc)
                _lo_acc=_lo_break and any(float(_c["close"])<_pl for _c in _hc)
                if _hi_acc: _ws="accepted_now" if _price>_ph else "accepted_then_back_inside"
                elif _lo_acc: _ws="accepted_now" if _price<_pl else "accepted_then_back_inside"
                elif _hi_break: _ws="rejected_now" if _price<=_ph else "rejected_but_close_above"
                elif _lo_break: _ws="rejected_now" if _price>=_pl else "rejected_but_close_below"
                else: _ws="middle_or_other"
                _wb={"prior_high":_ph,"prior_low":_pl,"current_high":_ch,"current_low":_cl,"price":_price}
            _allow=True
            if exp_weekly_state_action=="skip_back_inside" and _ws=="accepted_then_back_inside": _allow=False
            elif exp_weekly_state_action=="accepted_now_only" and _ws!="accepted_now": _allow=False
            _exp_weekly_state_rows.append({"entry_ts":int(bar_ts),"entry_idx":bar,"direction":int(sig["dir"]),"use":use,"state":_ws,"allowed":_allow,"action":exp_weekly_state_action,"boundary":_wb})
            if not _allow: continue
        if exp_regime_skip>0 and bar>=4 and abs(chop_per_ltf[bar]-chop_per_ltf[bar-4])>exp_regime_skip: continue
        if exp_eth_skip>0 and _eth_mom[bar]>exp_eth_skip: continue
        if exp_vol_b2_rvol>0 and sig.get("kind")=="B2" and _rvol15[bar]<exp_vol_b2_rvol: continue
        if exp_vol_pct_min>0 and _pct15[bar]<exp_vol_pct_min: continue
        if exp_mtf_mode:
            _ej=bs.bisect_right(htf_sw_ts, bar_ts+ltf_bar_secs)-1
            if _ej<0: continue
            if exp_mtf_mode==1:
                if htf_sw_dir[_ej]!=sig["dir"]: continue
            else:
                if _ej<1: continue
                if htf_sw_dir[_ej]!=htf_sw_dir[_ej-1]: continue
                if htf_sw_dir[_ej]!=sig["dir"]: continue
        if exp_struct_mag_min>0 or exp_struct_freq_max>0:
            _sj=bs.bisect_right(ltf_sw_ts, bar_ts+ltf_bar_secs)-1
            if _sj>=7:
                _w0=_sj-7
                _mags=ltf_sw_mag[_w0:_sj+1]
                _f4=sum(_mags[:4])/4.0
                _s4=sum(_mags[4:])/4.0
                _mt=_s4/_f4 if _f4>0 else 1.0
                if exp_struct_mag_min>0 and _mt<exp_struct_mag_min: continue
                if exp_struct_freq_max>0:
                    _span=(ltf_sw_ts[_sj]-ltf_sw_ts[_w0])/900.0
                    _freq=8.0/max(_span,1.0)
                    if _freq>exp_struct_freq_max: continue
        filtered.append((sig, use))
    filtered.sort(key=lambda z: ltf_store.pos(z[0]["bar"]))
    # Now simulate LTF with filtered signals (same as v1_15m LTF walk, swing trail)
    n=len(candles_ltf)
    if n==0:
        return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
                "ltf_trades": [], "intervals": intervals_flip}
    candle_ts=candle_ts_ltf
    # ATR for SL buffer
    tr_l=[0.0]*n
    for _i in range(n):
        _c=candles_ltf[_i]
        if _i==0: tr_l[_i]=float(_c["high"])-float(_c["low"])
        else:
            _pc=float(candles_ltf[_i-1]["close"])
            tr_l[_i]=max(float(_c["high"])-float(_c["low"]), abs(float(_c["high"])-_pc), abs(float(_c["low"])-_pc))
    atr15=[0.0]*n
    for _i in range(n):
        _lo=max(0,_i-13)
        atr15[_i]=sum(tr_l[_lo:_i+1])/(_i-_lo+1)
    fine_ts=[int(c["ts"]) for c in fine_ltf] if fine_ltf else []
    ltf_trades=[]
    busy_until=""  # datetime string — timestamp-based, not index
    retest_stats={"filled":0,"timeout":0}
    last_loss_bar=-999999
    _csl = [0.0]*len(candles_ltf)
    _csh = [0.0]*len(candles_ltf)
    _conf_evs = []
    for _s in swings_ltf:
        _ca = _s.get("confirmed_at_idx")
        if _ca is not None and int(_ca) >= 0:
            _e = _s.get("seg", {}).get("end_idx", -1)
            if _e is not None and int(_e) >= 0:
                _conf_evs.append((int(_ca), int(_e)))
    _conf_evs.sort()
    _cref = 0
    _clo = float(candles_ltf[0]["low"])
    _chi = float(candles_ltf[0]["high"])
    _cei = 0
    for _ci in range(len(candles_ltf)):
        while _cei < len(_conf_evs) and _conf_evs[_cei][0] <= _ci:
            _cref = _conf_evs[_cei][1]
            _cei += 1
            if _cref < len(candles_ltf):
                _clo = float(candles_ltf[_cref]["low"])
                _chi = float(candles_ltf[_cref]["high"])
        _cl = float(candles_ltf[_ci]["low"])
        _ch2 = float(candles_ltf[_ci]["high"])
        if _cl < _clo: _clo = _cl
        if _ch2 > _chi: _chi = _ch2
        _csl[_ci] = _clo
        _csh[_ci] = _chi
    last_loss_ts=0
    halt_ts=0
    _wd_cache={}
    def _is_weekend(dstr):
        _d = dstr[:10]
        _w = _wd_cache.get(_d)
        if _w is None:
            import datetime as _dt
            _w = _dt.date(int(_d[:4]), int(_d[5:7]), int(_d[8:10])).weekday()
            _wd_cache[_d] = _w
        return _w
    def _utc_wd(dstr):
        import datetime as _dt
        _p = _dt.datetime.strptime(dstr[:16], "%Y-%m-%d %H:%M")
        return (_p - _dt.timedelta(hours=5, minutes=30)).weekday()
    _open_count=0
    _window_budget={}
    _exp_streak_used_map={}
    _exp_cohort_loss_ts=0
    _exp_cohort_loss_seen=0
    _exp_5m_stats={"candidates":0,"confirmed":0,"stop_cancelled":0,"timeout":0,"delayed":0}
    _exp_cohort_stats={"loss_triggers":0,"fresh_rearms":0,"blocked":0}
    _exp_cohort_loss_count=0
    _exp_shadow_rows=[]
    _exp_campaign_stats={"blocked_mixed":0,"blocked_total":0,"blocked_addons":0,"blocked_state":0}
    _exp_loss_window_kill_stats={"triggered":0,"blocked_entries":0,"hard_closed":0}
    _exp_loss_window_killed=set()
    _exp_loss_window_epoch_ts=0
    _exp_win_window_kill_stats={"triggered":0,"blocked_entries":0,"hard_closed":0,"skipped":0}
    _exp_win_window_killed=set()
    _exp_win_window_epoch_ts=0
    _exp_win_skip_used=False
    consecutive_losses=0
    halt_skip_rem=0  # >0: skip this many more entries after N-loss halt
    from src.btc.btc_engine import _trail_events as _te
    import bisect
    _pb_long=[]; _pb_short=[]
    if exp_pivot_trail:
        for _ps in swings_trail:
            _seg=_ps.get("seg") or {}
            _conf=int(_ps.get("confirmed_at_idx",-1))
            _ei=int(_seg.get("end_idx",-1))
            if _conf<0 or _ei<0 or _ei>=n: continue
            _ep=float(_seg.get("end_px",0))
            if _ps.get("dir")=="up":
                _j=_ei+1
                while _j<n and float(candles_ltf[_j]["high"])<=_ep: _j+=1
                if _j<n: _pb_long.append((_j,_ep))
            else:
                _j=_ei+1
                while _j<n and float(candles_ltf[_j]["low"])>=_ep: _j+=1
                if _j<n: _pb_short.append((_j,_ep))
        _pb_long.sort(); _pb_short.sort()
    for sig, use in filtered:
        bar_time=sig["bar"]  # datetime string
        i=ltf_store.pos(bar_time)  # position via timestamp lookup
        _sr=None
        if exp_shadow_book and 0<=i<n:
            _now=int(candles_ltf[i]["ts"])
            _active=[_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)>_now]
            _sr={"signal":dict(sig),"use":use,"bar_time":bar_time,"entry_idx":i,"entry_ts":_now,"active_count":len(_active),"active": [{"dir":_t.get("dir"),"entry_ts":_t.get("entry_ts"),"exit_ts":_t.get("exit_ts"),"r_multiple":_t.get("r_multiple"),"entry_price":_t.get("entry_price"),"sl":_t.get("sl")} for _t in _active],"reason":"accepted"}
            _exp_shadow_rows.append(_sr)
        if i < 0 or i>=n-1: continue
        if (not exp_mltf) and busy_until and bar_time <= busy_until:
            if exp_shadow_book: _sr["reason"]="busy"
            continue
        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars:
            if exp_shadow_book: _sr["reason"]="cooldown"
            continue
        # Streak halt (causal): after N consecutive losses BOOKED, skip NEXT entry
        if halt_skip_rem > 0:
            halt_skip_rem-=1
            consecutive_losses=0
            if exp_shadow_book: _sr["reason"]="halt"
            continue
        if exp_skip_decisive and use=="decisive":
            continue
        if exp_skipwin > 0 and last_loss_ts > 0:
            if use == "flip":
                _starts = starts_flip
            elif use == "b2":
                _starts = starts_b2
            else:
                _starts = starts_decisive
            _idx = bs.bisect_right(_starts, candle_ts[i]) - 1
            if _idx >= 0 and _idx - bs.bisect_right(_starts, last_loss_ts) + 1 <= exp_skipwin:
                continue
        if exp_skipwin_halt > 0 and halt_ts > 0:
            if use == "flip":
                _starts2 = starts_flip
            elif use == "b2":
                _starts2 = starts_b2
            else:
                _starts2 = starts_decisive
            _idx2 = bs.bisect_right(_starts2, candle_ts[i]) - 1
            if _idx2 >= 0 and _idx2 - bs.bisect_right(_starts2, halt_ts) + 1 <= exp_skipwin_halt:
                continue
        if exp_swingpause > 0 and last_loss_ts > 0:
            _si = bs.bisect_right(confs_ts, candle_ts[i]) - 1
            if _si < 0 or pivs_ts[_si] <= last_loss_ts:
                continue
        if exp_max_concurrent > 0:
            _now_ts = candle_ts[i]
            _open_now = sum(1 for _t in ltf_trades if int(_t["exit_ts"]) > _now_ts)
            if _open_now >= exp_max_concurrent:
                continue
        _window_key=None
        if use == "flip":
            _wb_ivs, _wb_starts = intervals_flip, starts_flip
        elif use == "b2":
            _wb_ivs, _wb_starts = intervals_b2, starts_b2
        else:
            _wb_ivs, _wb_starts = intervals_decisive, starts_decisive
        _wb_idx = bs.bisect_right(_wb_starts, candle_ts[i]) - 1
        if _wb_idx >= 0:
            _wb = _wb_ivs[_wb_idx]
            if int(_wb[0]) + _knowwin < candle_ts[i] <= int(_wb[1]) + _knowwin and int(_wb[2]) == int(sig.get("_exp_htf_dir", sig["dir"])):
                _window_key="%s:%d:%d:%d" % (use, int(_wb[0]), int(_wb[1]), int(_wb[2]))
        if _window_key is not None and (exp_window_r_cap > 0 or exp_window_entry_cap > 0):
            _ws = _window_budget.setdefault(_window_key, {"entries": 0, "realized_r": 0.0})
            if exp_window_entry_cap > 0 and _ws["entries"] >= exp_window_entry_cap:
                _ws["blocked_entries"] = _ws.get("blocked_entries", 0) + 1
                continue
            if exp_window_r_cap > 0:
                _now = int(candles_ltf[i]["ts"])
                _budget_r = 0.0
                for _t in ltf_trades:
                    if _t.get("window_key") != _window_key:
                        continue
                    if int(_t.get("exit_ts") or 0) <= _now:
                        _budget_r += float(_t.get("r_multiple") or 0.0)
                    elif exp_window_budget_mode == "marked":
                        _e=float(_t["entry_price"]); _sl=float(_t["sl"]); _rk=abs(_e-_sl)
                        if _rk > 0:
                            _cl=float(candles_ltf[i]["close"]); _dd=1 if _t["dir"] == "long" else -1
                            _budget_r += (_cl-_e)*_dd/_rk
                if _budget_r >= exp_window_r_cap:
                    _ws["blocked_budget"] = _ws.get("blocked_budget", 0) + 1
                    continue
        _exp_now=int(candles_ltf[i]["ts"])
        _exp_done=sorted([_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)<=_exp_now], key=lambda _t:(int(_t.get("exit_ts") or 0), int(_t.get("trade_no") or 0)))
        if exp_loss_streak_mode == "window":
            _exp_done=[_t for _t in _exp_done if _t.get("window_key") == _window_key]
        elif exp_loss_streak_mode == "regime":
            _exp_done=[_t for _t in _exp_done if _t.get("htf_regime") == use]
        _exp_streak=0
        for _t in reversed(_exp_done):
            if float(_t.get("r_multiple") or 0.0)<=0: _exp_streak+=1
            else: break
        _exp_trigger=(exp_loss_streak_n>0 and _exp_streak>=exp_loss_streak_n)
        if exp_loss_streak_mode == "window": _exp_streak_key=_window_key or "none"
        elif exp_loss_streak_mode == "regime": _exp_streak_key=use
        else: _exp_streak_key="global"
        _exp_streak_used=_exp_streak_used_map.get(_exp_streak_key,False)
        if exp_loss_streak_n>0 and not _exp_trigger: _exp_streak_used=False
        _exp_streak_used_map[_exp_streak_key]=_exp_streak_used
        _exp_opposite=0
        if exp_loss_streak_action == "opposite":
            _exp_opposite=1 if sig.get("_exp_opposite_candidate") else 0
            if _exp_trigger and not _exp_streak_used:
                if not _exp_opposite: continue
                _exp_streak_used=True
            elif not _exp_trigger:
                if _exp_opposite: continue
            elif _exp_opposite: continue
        elif exp_loss_streak_action == "augment":
            _exp_opposite=1 if sig.get("_exp_opposite_candidate") else 0
            if not _exp_trigger:
                if _exp_opposite: continue
            elif _exp_opposite:
                if _exp_streak_used: continue
                _exp_streak_used=True
        elif exp_loss_streak_action == "skip" and _exp_trigger and not _exp_streak_used:
            _exp_streak_used=True
            _exp_streak_used_map[_exp_streak_key]=_exp_streak_used
            continue
            _exp_streak_used_map[_exp_streak_key]=_exp_streak_used
        if exp_cohort_swingpause and _exp_cohort_loss_ts>0:
            _csi=bs.bisect_right(confs_ts, int(candles_ltf[i]["ts"])+900)-1
            if _csi<0 or confs_ts[_csi]<=_exp_cohort_loss_ts:
                _exp_cohort_stats["blocked"] += 1; continue
            if exp_cohort_rearm:
                _exp_cohort_loss_ts=0; _exp_cohort_loss_count=0; _exp_cohort_stats["fresh_rearms"] += 1
        _campaign_marked=0.0; _campaign_state="first"; _campaign_total=0; _campaign_addons=0; _campaign_active=0; _campaign_mixed=0
        if _window_key is not None and (exp_campaign_require_marked_r is not None or exp_campaign_max_addons>0 or exp_campaign_max_total>0 or exp_campaign_block_mixed or exp_window_loss_kill_n>0 or exp_window_win_kill_n>0):
            _cw=_window_budget.setdefault(_window_key, {"entries":0,"realized_r":0.0})
            _campaign_total=int(_cw.get("entries",0)); _campaign_addons=max(0,_campaign_total)
            _cnow=int(candles_ltf[i]["ts"])+900; _cactive=[_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)>_cnow]
            _campaign_active=len(_cactive); _cdir=1 if sig.get("dir")==1 else -1
            _csame=[_t for _t in _cactive if (1 if _t.get("dir")=="long" else -1)==_cdir]
            _copp=[_t for _t in _cactive if (1 if _t.get("dir")=="long" else -1)!=_cdir]
            _campaign_mixed=1 if _copp else 0
            _cfi=bisect.bisect_right(fine_ts,_cnow)-1 if fine_ts else -1
            if _cfi>=0:
                _cpx=float(fine_ltf[_cfi]["close"])
                for _ct in _csame:
                    _ce=float(_ct.get("entry_price")); _csl=float(_ct.get("sl")); _cr=abs(_ce-_csl)
                    if _cr>0: _campaign_marked+=((_cpx-_ce) if _cdir>0 else (_ce-_cpx))/_cr
            _campaign_state="mixed" if _copp else "green" if _campaign_marked>0 else "red" if _campaign_marked<0 else "flat"
            if exp_campaign_block_mixed and _campaign_mixed:
                _exp_campaign_stats["blocked_mixed"]+=1; continue
            if exp_campaign_max_total>0 and _campaign_total>=int(exp_campaign_max_total):
                _exp_campaign_stats["blocked_total"]+=1; continue
            if exp_campaign_max_addons>0 and _campaign_total>=int(exp_campaign_max_addons)+1:
                _exp_campaign_stats["blocked_addons"]+=1; continue
            if exp_campaign_require_marked_r is not None and _csame and _campaign_marked<float(exp_campaign_require_marked_r):
                _exp_campaign_stats["blocked_state"]+=1; continue
            if exp_window_loss_kill_n>0 and _window_key is not None:
                _lw_now=int(candles_ltf[i]["ts"])+900
                _lw_done=sorted([_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)<=_lw_now], key=lambda _t:(int(_t.get("exit_ts") or 0),int(_t.get("trade_no") or 0)))
                if exp_window_loss_kill_scope=="window": _lw_done=[_t for _t in _lw_done if _t.get("window_key")==_window_key]
                elif exp_window_loss_kill_scope=="global": _lw_done=[_t for _t in _lw_done if int(_t.get("exit_ts") or 0)>_exp_loss_window_epoch_ts]
                _lw_streak=0
                for _t in reversed(_lw_done):
                    if float(_t.get("r_multiple") or 0.0)<=0: _lw_streak+=1
                    else: break
                if _lw_streak>=int(exp_window_loss_kill_n) and _window_key not in _exp_loss_window_killed:
                    if exp_window_loss_kill_scope=="global": _exp_loss_window_epoch_ts=_lw_now
                    _exp_loss_window_killed.add(_window_key); _exp_loss_window_kill_stats["triggered"]+=1
                    if exp_window_loss_kill_action=="hard":
                        _lw_fi=bisect.bisect_right(fine_ts,_lw_now)-1
                        if _lw_fi>=0:
                            _lw_px=float(fine_ltf[_lw_fi]["close"])
                            for _t in ltf_trades:
                                if _t.get("window_key")!=_window_key or int(_t.get("exit_ts") or 0)<=_lw_now: continue
                                _lw_e=float(_t.get("entry_price")); _lw_s=float(_t.get("sl")); _lw_r=abs(_lw_e-_lw_s); _lw_d=1 if _t.get("dir")=="long" else -1
                                if _lw_r>0:
                                    _lw_x=((_lw_px-_lw_e)*_lw_d)/_lw_r
                                    _t["exit_ts"]=int(fine_ltf[_lw_fi]["ts"]); _t["exit_date"]=fine_ltf[_lw_fi].get("date") or _t.get("exit_date"); _t["exit_price"]=round(_lw_px,2); _t["r_multiple"]=round(_lw_x,3); _t["outcome"]="loss_window_hard_close"; _exp_loss_window_kill_stats["hard_closed"]+=1
                            if not exp_mltf: busy_until=fine_ltf[_lw_fi].get("date") or busy_until
                if _window_key in _exp_loss_window_killed:
                    _exp_loss_window_kill_stats["blocked_entries"]+=1
                    continue
            if exp_window_win_kill_n>0 and _window_key is not None:
                _ww_now=int(candles_ltf[i]["ts"])+900
                _ww_done=sorted([_t for _t in ltf_trades if int(_t.get("exit_ts") or 0)<=_ww_now], key=lambda _t:(int(_t.get("exit_ts") or 0),int(_t.get("trade_no") or 0)))
                if exp_window_win_kill_scope=="window": _ww_done=[_t for _t in _ww_done if _t.get("window_key")==_window_key]
                elif exp_window_win_kill_scope=="global": _ww_done=[_t for _t in _ww_done if int(_t.get("exit_ts") or 0)>_exp_win_window_epoch_ts]
                _ww_streak=0
                for _t in reversed(_ww_done):
                    if float(_t.get("r_multiple") or 0.0)>0: _ww_streak+=1
                    else: break
                _ww_trigger=_ww_streak>=int(exp_window_win_kill_n)
                if not _ww_trigger: _exp_win_skip_used=False
                if _ww_trigger and exp_window_win_kill_action=="skip" and not _exp_win_skip_used:
                    _exp_win_skip_used=True; _exp_win_window_kill_stats["triggered"]+=1; _exp_win_window_kill_stats["skipped"]+=1
                    if exp_window_win_kill_scope=="global": _exp_win_window_epoch_ts=_ww_now
                    continue
                if _ww_trigger and exp_window_win_kill_action in ("soft","hard") and _window_key not in _exp_win_window_killed:
                    if exp_window_win_kill_scope=="global": _exp_win_window_epoch_ts=_ww_now
                    _exp_win_window_killed.add(_window_key); _exp_win_window_kill_stats["triggered"]+=1
                    if exp_window_win_kill_action=="hard":
                        _ww_fi=bisect.bisect_right(fine_ts,_ww_now)-1
                        if _ww_fi>=0:
                            _ww_px=float(fine_ltf[_ww_fi]["close"])
                            for _t in ltf_trades:
                                if _t.get("window_key")!=_window_key or int(_t.get("exit_ts") or 0)<=_ww_now: continue
                                _ww_e=float(_t.get("entry_price")); _ww_s=float(_t.get("sl")); _ww_r=abs(_ww_e-_ww_s); _ww_d=1 if _t.get("dir")=="long" else -1
                                if _ww_r>0:
                                    _ww_x=((_ww_px-_ww_e)*_ww_d)/_ww_r
                                    _t["exit_ts"]=int(fine_ltf[_ww_fi]["ts"]); _t["exit_date"]=fine_ltf[_ww_fi].get("date") or _t.get("exit_date"); _t["exit_price"]=round(_ww_px,2); _t["r_multiple"]=round(_ww_x,3); _t["outcome"]="win_window_hard_close"; _exp_win_window_kill_stats["hard_closed"]+=1
                            if not exp_mltf: busy_until=fine_ltf[_ww_fi].get("date") or busy_until
                if _window_key in _exp_win_window_killed:
                    _exp_win_window_kill_stats["blocked_entries"]+=1
                    continue
        if exp_skip_weekend and _is_weekend(candles_ltf[i]["date"]) >= 5:
            continue
        if exp_skip_utc_sat and _utc_wd(candles_ltf[i]["date"]) == 5:
            if exp_shadow_book: _sr["reason"]="utc_saturday"
            continue
        if exp_skip_utc_sun and _utc_wd(candles_ltf[i]["date"]) == 6:
            if exp_shadow_book: _sr["reason"]="utc_sunday"
            continue
        if exp_kinds and sig["kind"] != exp_kinds:
            if exp_shadow_book: _sr["reason"]="kind"
            continue
        if exp_chop15_hi > 0 and exp_chop15_lo <= chop15_ser[i] < exp_chop15_hi:
            continue
        if exp_atr_ratio_max > 0 and _ar15[i] > exp_atr_ratio_max:
            continue
        if exp_bias_momentum_min > 0 and _bm_breaks:
            _bm_idx = bs.bisect_right(_bm_times, sig["bar"][:19]) - 1
            if exp_bm_causal:
                _bm_ets = candle_ts_ltf[i] + 900  # entry instant = signal bar close
                while _bm_idx >= 0:
                    _bm_c = _bm_breaks[_bm_idx][2]
                    if 0 <= _bm_c < len(candle_ts_htf) and candle_ts_htf[_bm_c] + 3600 <= _bm_ets:
                        break
                    _bm_idx -= 1  # owner unconfirmed at entry: walk to last DECLARED break
            if _bm_idx >= 0 and _bm_breaks[_bm_idx][1] < exp_bias_momentum_min:
                continue
        if exp_min_swing_ratio > 0 and sig.get("swing_no") is not None:
            _sni = int(sig["swing_no"])
            if 0 <= _sni < len(swings_ltf):
                _sw = swings_ltf[_sni]
                _seg = _sw.get("seg", {})
                _spx = float(_seg.get("start_px", 0) or 0)
                _epx = float(_seg.get("end_px", 0) or 0)
                _swing_mag = abs(_epx - _spx)
                _atr_s = max(0, i - 19)
                _atr_h = max(float(candles_ltf[j]["high"]) for j in range(_atr_s, i + 1))
                _atr_l = min(float(candles_ltf[j]["low"]) for j in range(_atr_s, i + 1))
                _atr = _atr_h - _atr_l if _atr_h > _atr_l else 1.0
                if _atr > 0 and _swing_mag / _atr < exp_min_swing_ratio:
                    continue
        direction=int(sig["dir"])
        _gen_dir = 0
        _gen_start = -1
        for _gs in swings_ltf:
            _gsi = int((_gs.get("seg") or {}).get("start_idx", -1))
            if 0 <= _gsi <= i:
                if exp_dir_causal:
                    _gconf = int(_gs.get("confirmed_at_idx", -1))
                    if _gconf < 0 or _gconf > i:
                        continue
                _gen_dir = 1 if _gs.get("dir") == "up" else -1
                _gen_start = _gsi
        if exp_require_dir_match and _gen_dir != 0 and _gen_dir != direction:
            continue
        if exp_max_swing_age > 0 and _gen_start >= 0 and (i - _gen_start) > exp_max_swing_age:
            continue
        if exp_max_running_mag > 0 and _gen_start >= 0:
            if direction == 1:
                _rmin = min(float(candles_ltf[_k]["low"]) for _k in range(max(0, _gen_start), i + 1))
                _rmag = (float(candles_ltf[i]["close"]) - _rmin) / float(candles_ltf[i]["close"]) * 100.0
            else:
                _rmax = max(float(candles_ltf[_k]["high"]) for _k in range(max(0, _gen_start), i + 1))
                _rmag = (_rmax - float(candles_ltf[i]["close"])) / float(candles_ltf[i]["close"]) * 100.0
            if _rmag > exp_max_running_mag:
                continue
        direction=int(sig["dir"])
        entry=float(candles_ltf[i]["close"])
        if exp_causal_sl:
            if direction == 1:
                sl_pivot = _csl[i]
            else:
                sl_pivot = _csh[i]
        else:
            sl_pivot = sig["swing_start_px"]
        if b3_k>0:
            _lv=float(candles_ltf[i]["high"]) if direction==1 else float(candles_ltf[i]["low"])
            _sig_close=float(candles_ltf[i]["close"])
            _jj=None
            for _k in range(i+1, min(i+1+b3_k, n-1)):
                _hi=float(candles_ltf[_k]["high"]); _lo=float(candles_ltf[_k]["low"])
                if direction==1 and _lo<=sl_pivot: break
                if direction==-1 and _hi>=sl_pivot: break
                _cl=float(candles_ltf[_k]["close"])
                if b3_mode=="limit":
                    if direction==1 and _lo<=_sig_close: _jj=_k; break
                    if direction==-1 and _hi>=_sig_close: _jj=_k; break
                elif b3_mode=="wick":
                    if (_hi>_lv) if direction==1 else (_lo<_lv): _jj=_k; break
                else:
                    if (_cl>_lv) if direction==1 else (_cl<_lv): _jj=_k; break
            if _jj is None: continue
            i=_jj
            bar_time=candles_ltf[i]["date"]
            entry=_sig_close if b3_mode=="limit" else float(candles_ltf[i]["close"])
            if busy_until and bar_time<=busy_until: continue
            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue
            if exp_max_concurrent>0:
                _now_ts2=candle_ts[i]
                _open_now2=sum(1 for _t in ltf_trades if int(_t["exit_ts"])>_now_ts2)
                if _open_now2>=exp_max_concurrent: continue
        if direction==1:
            sl=sl_pivot - sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl>=entry: continue
            risk=entry-sl
            if risk<0.0005*entry: continue
            if exp_risk_max_pct>0 and risk/entry*100.0>exp_risk_max_pct:
                if exp_shadow_book: _sr["reason"]="risk_max"
                continue
            if exp_entry_candle_min>0:
                _cb=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))
                _crng=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])
                if _crng>0 and _cb/_crng<exp_entry_candle_min:
                    if exp_shadow_book: _sr["reason"]="candle_min"
                    continue
            if exp_entry_swing_age_max>0 and sig.get("swing_no") is not None:
                _sag=int(sig["swing_no"])
                if 0<=_sag<len(swings_ltf):
                    _ssi=swings_ltf[_sag].get("seg",{}).get("start_idx",-1)
                    if _ssi>=0 and (i-int(_ssi))>exp_entry_swing_age_max:
                        if exp_shadow_book: _sr["reason"]="swing_age"
                        continue
            if exp_entry_skip_b2_doji>0 and sig.get("kind","")=="B2":
                _cb2=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))
                _cr2=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])
                if _cr2>0 and _cb2/_cr2<0.3: continue
            target=entry+3.0*risk
        else:
            sl=sl_pivot + sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl<=entry: continue
            risk=sl-entry
            if risk<0.0005*entry: continue
            if exp_risk_max_pct>0 and risk/entry*100.0>exp_risk_max_pct:
                if exp_shadow_book: _sr["reason"]="risk_max"
                continue
            if exp_entry_candle_min>0:
                _cb=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))
                _crng=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])
                if _crng>0 and _cb/_crng<exp_entry_candle_min:
                    if exp_shadow_book: _sr["reason"]="candle_min"
                    continue
            if exp_entry_swing_age_max>0 and sig.get("swing_no") is not None:
                _sag=int(sig["swing_no"])
                if 0<=_sag<len(swings_ltf):
                    _ssi=swings_ltf[_sag].get("seg",{}).get("start_idx",-1)
                    if _ssi>=0 and (i-int(_ssi))>exp_entry_swing_age_max:
                        if exp_shadow_book: _sr["reason"]="swing_age"
                        continue
            if exp_entry_skip_b2_doji>0 and sig.get("kind","")=="B2":
                _cb2=abs(float(candles_ltf[i]["close"])-float(candles_ltf[i]["open"]))
                _cr2=float(candles_ltf[i]["high"])-float(candles_ltf[i]["low"])
                if _cr2>0 and _cb2/_cr2<0.3: continue
            target=entry-3.0*risk
        _retest_fill_k=None
        if exp_retest_fill>0 and fine_ltf:
            _rlim = entry - exp_retest_fill*risk if direction==1 else entry + exp_retest_fill*risk
            _rdl = candle_ts[i] + 900 + exp_retest_wait*60
            _rfs = bisect.bisect_left(fine_ts, candle_ts[i+1]) if i+1 < n else len(fine_ts)
            for _k in range(_rfs, len(fine_ltf)):
                if int(fine_ltf[_k]["ts"]) > _rdl: break
                _op=float(fine_ltf[_k]["open"])
                if direction==1:
                    if float(fine_ltf[_k]["low"]) <= _rlim: _retest_fill_k=_k; entry=min(_rlim,_op); break
                else:
                    if float(fine_ltf[_k]["high"]) >= _rlim: _retest_fill_k=_k; entry=max(_rlim,_op); break
            if _retest_fill_k is None:
                retest_stats["timeout"] += 1
                continue
            if direction==1:
                risk=entry-sl
            else:
                risk=sl-entry
            if risk < 0.0005*entry:
                continue
            target = entry+3.0*risk if direction==1 else entry-3.0*risk
            i = bisect.bisect_right(candle_ts, fine_ts[_retest_fill_k]) - 1
            retest_stats["filled"] += 1
        sl0=sl; sl_cur=sl; best=entry
        _partial_taken=False; _partial_r=0.0
        _profit_stage_fired=False
        _trail_skip_rem=exp_trail_skip_n
        _exp_5m_entry_k=None
        if exp_5m_confirm>0 and fine_ltf and exp_5m_data:
            _exp_5m_stats["candidates"] += 1
            _exp_entry_inst=int(candles_ltf[i]["ts"])+900
            _exp_deadline=_exp_entry_inst+int(exp_5m_wait_min)*60
            if not _exp_5m_ts or _exp_5m_ts[0]>_exp_entry_inst or _exp_5m_ts[-1]<_exp_entry_inst:
                _exp_5m_stats["timeout"] += 1; continue
            _exp_k0=bisect.bisect_left(_exp_5m_ts,_exp_entry_inst)
            _exp_k1=bisect.bisect_right(_exp_5m_ts,_exp_deadline)
            _exp_f0=bisect.bisect_left(fine_ts,_exp_entry_inst)
            _exp_confirm_close=None
            for _exp_k in range(_exp_k0,_exp_k1):
                if _exp_k < 3: continue
                _exp_prev=_exp_5m_sorted[_exp_k-3:_exp_k]
                _exp_hi=max(float(_exp_c["high"]) for _exp_c in _exp_prev)
                _exp_lo=min(float(_exp_c["low"]) for _exp_c in _exp_prev)
                _exp_close=float(_exp_5m_sorted[_exp_k]["close"])
                if (direction==1 and _exp_close>_exp_hi) or (direction==-1 and _exp_close<_exp_lo):
                    _exp_confirm_close=int(_exp_5m_ts[_exp_k]); break
            if _exp_confirm_close is None:
                _exp_5m_stats["timeout"] += 1; continue
            _exp_5m_entry_k=bisect.bisect_left(fine_ts,_exp_confirm_close)
            if _exp_5m_entry_k>=len(fine_ltf):
                _exp_5m_stats["timeout"] += 1; continue
            for _exp_fk in range(_exp_f0,_exp_5m_entry_k):
                _exp_fc=fine_ltf[_exp_fk]
                if direction==1 and float(_exp_fc["low"])<=sl:
                    _exp_5m_stats["stop_cancelled"] += 1; _exp_confirm_close=None; break
                if direction==-1 and float(_exp_fc["high"])>=sl:
                    _exp_5m_stats["stop_cancelled"] += 1; _exp_confirm_close=None; break
            if _exp_confirm_close is None: continue
            entry=float(fine_ltf[_exp_5m_entry_k]["open"])
            i=max(i,bisect.bisect_right(candle_ts,int(fine_ltf[_exp_5m_entry_k]["ts"]))-1)
            bar_time=candles_ltf[i]["date"]
            if busy_until and bar_time<=busy_until: continue
            if cooldown_bars>0 and i-last_loss_bar<cooldown_bars: continue
            if exp_max_concurrent>0 and sum(1 for _t in ltf_trades if int(_t["exit_ts"])>int(candles_ltf[i]["ts"]))>=exp_max_concurrent: continue
            risk=entry-sl if direction==1 else sl-entry
            if risk<0.0005*entry:
                _exp_5m_stats["stop_cancelled"] += 1; continue
            target=entry+3.0*risk if direction==1 else entry-3.0*risk
            sl0=sl; sl_cur=sl; best=entry
            _exp_5m_stats["confirmed"] += 1; _exp_5m_stats["delayed"] += 1
        # Trail events: timestamp-based (confirmed_at_time → position via store)
        want_dir = "up" if direction == 1 else "down"
        events = []
        if exp_pivot_trail:
            _brks=_pb_long if direction==1 else _pb_short
            _seg=i
            for _brk,_ppx in _brks:
                if _brk<=i: continue
                if direction==1:
                    _lvl=min(float(candles_ltf[k]["low"]) for k in range(_seg,_brk+1))
                else:
                    _lvl=max(float(candles_ltf[k]["high"]) for k in range(_seg,_brk+1))
                events.append((_brk,_lvl))
                _seg=_brk
        for s in ([] if exp_pivot_trail else swings_trail):
            if s.get("dir") != want_dir:
                continue
            ct = s.get("confirmed_at_time", "")
            if not ct:
                continue
            cidx = ltf_store.pos(ct)
            if cidx >= 0:
                _tl = float(s["seg"]["start_px"])
                _td = abs(entry - _tl) / entry * 100.0
                if exp_trail_max_dist > 0 and _td > exp_trail_max_dist:
                    continue
                events.append((cidx, _tl))
        events.sort(key=lambda x: x[0])
        if exp22_conv:
            for _s2 in swings_trail:
                if _s2.get("dir") != want_dir: continue
                for _b2 in _s2.get("breaks",[]):
                    if _b2.get("kind")!="B2": continue
                    if (1 if _b2["dir"]=="up" else -1)!=direction: continue
                    _b2i=int(_b2["idx"])
                    if i<_b2i:
                        events.append((_b2i,float(_s2["seg"]["start_px"])))
            events.sort(key=lambda x: x[0])
        ev_idx=-1
        opp_events=[]
        if exp27_mode:
            for _s9 in swings_ltf:
                for _b9 in _s9.get("breaks",[]):
                    if _b9.get("time") and (1 if _b9["dir"]=="up" else -1)==-direction:
                        opp_events.append((int(_b9["idx"]), _b9.get("kind","")))
            opp_events.sort(key=lambda z: z[0])
            opp_ev_idx=-1
            while opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= i:
                opp_ev_idx += 1
        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None
        _climax_hit=False
        _rmax_v=_rvol15[i]
        for j in range(i+1, n if not fine_ltf else i+1):
            if _rvol15[j]>_rmax_v: _rmax_v=_rvol15[j]
            if exp_vol_exit_r>0 and not _climax_hit and _rvol15[j]>=exp_vol_exit_r:
                _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)
                if _cl<0:
                    exit_idx,exit_px,outcome=j,float(c["close"]),"volx"
                    _climax_hit=True
                    break
            if exp_vol_dry_exit>0 and (j-i)>=exp_vol_dry_bars:
                _b0=max(0,i-96)
                _base=(_vp[i]-_vp[_b0])/max(1,i-_b0)
                _run=(_vp[j+1]-_vp[i])/max(1,j-i+1)
                if _base>0 and (_run/_base)<exp_vol_dry_exit:
                    if exp_vol_dry_be>0:
                        _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)
                        if _cl>0:
                            if direction==1: sl_cur=max(sl_cur,entry)
                            else: sl_cur=min(sl_cur,entry)
                    else:
                        exit_idx,exit_px,outcome=j,float(c["close"]),"voldry"
                        break
            if exp_vol_nospk>0 and (j-i)>=exp_vol_nospk_bars and _rmax_v<exp_vol_nospk:
                _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)
                if _cl<=0:
                    exit_idx,exit_px,outcome=j,float(c["close"]),"volns"
                    break
            c=candles_ltf[j]
            hi=float(c["high"]); lo=float(c["low"])
            if exp27_mode and opp_ev_idx+1 < len(opp_events) and opp_events[opp_ev_idx+1][0] <= j:
                opp_ev_idx += 1
                _eok = True
                if exp27_mode in ("loss", "fliploss"):
                    _cl = float(c["close"])
                    _cr = ((_cl - entry) / risk) if direction == 1 else ((entry - _cl) / risk)
                    if _cr >= 0.0: _eok = False
                if exp27_mode == "fliploss" and opp_events[opp_ev_idx][1] != "FLIP": _eok = False
                if _eok:
                    exit_idx, exit_px, outcome = j, float(c["close"]), "accel27"
                    break
            if direction==1:
                if hi>best: best=hi
            else:
                if lo<best: best=lo
            if exp_partial_r>0 and not _partial_taken and risk>0:
                _cur_r=(best-entry)*direction/risk
                if _cur_r>=exp_partial_r:
                    _partial_taken=True; _partial_r=exp_partial_r
            if direction==1:
                # D3 ordering fix 2026-09-20: the ratchet applies BEFORE the SL
                # check — the stop is armed the instant the swing confirms (bar
                # open), so this same bar is enforced against the new level.
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    _tr_ok=True
                    if _trail_skip_rem>0:
                        _trail_skip_rem-=1; _tr_ok=False
                    if _tr_ok and exp_trail_delay_r>0 and risk>0:
                        if ((best-entry)*direction/risk) < exp_trail_delay_r:
                            _tr_ok=False
                    if _tr_ok:
                        if exp_trail_half:
                            if sl_cur < cand: sl_cur=0.5*(sl_cur+cand)
                        elif sl_cur < cand:
                            sl_cur=cand
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "trail"
                    break
                if exp_ma_trail_period>0 and _ma15[j] is not None and float(c["close"]) < _ma15[j]:
                    exit_idx,exit_px=j,float(c["close"])
                    outcome="ma_trail"
                    break
            else:
                # D3 ordering fix 2026-09-20 (short mirror): see long-side comment.
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    _tr_ok=True
                    if _trail_skip_rem>0:
                        _trail_skip_rem-=1; _tr_ok=False
                    if _tr_ok and exp_trail_delay_r>0 and risk>0:
                        if ((best-entry)*direction/risk) < exp_trail_delay_r:
                            _tr_ok=False
                    if _tr_ok:
                        if exp_trail_half:
                            if cand < sl_cur: sl_cur=0.5*(sl_cur+cand)
                        elif cand < sl_cur:
                            sl_cur=cand
                if hi >= sl_cur:
                    fill=max(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur >= sl0 else "trail"
                    break
                if exp_ma_trail_period>0 and _ma15[j] is not None and float(c["close"]) > _ma15[j]:
                    exit_idx,exit_px=j,float(c["close"])
                    outcome="ma_trail"
                    break
        if fine_ltf:
            bar_ts=int(candles_ltf[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events if candle_ts[min(e+1,n-1)] > bar_ts]
            f_start=_retest_fill_k if _retest_fill_k is not None else (_exp_5m_entry_k if _exp_5m_entry_k is not None else bisect.bisect_left(fine_ts, candle_ts[i+1]))
            best_f=entry; sl_cur_f=sl_cur; ev_idx_f=-1; fk=None; exit_px_f=None; outcome_f="open"
            _rmax_f=_rvol15[i]
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                ts=int(c["ts"])
                _bj=bs.bisect_right(candle_ts,ts)-1
                if _bj>=0 and _rvol15[_bj]>_rmax_f: _rmax_f=_rvol15[_bj]
                if exp_vol_dry_exit>0 and _bj>=0 and (_bj-i)>=exp_vol_dry_bars:
                    _b0=max(0,i-96)
                    _base=(_vp[i]-_vp[_b0])/max(1,i-_b0)
                    _run=(_vp[_bj+1]-_vp[i])/max(1,_bj-i+1)
                    if _base>0 and (_run/_base)<exp_vol_dry_exit:
                        if exp_vol_dry_be>0:
                            _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)
                            if _cl>0:
                                if direction==1: sl_cur_f=max(sl_cur_f,entry)
                                else: sl_cur_f=min(sl_cur_f,entry)
                        else:
                            fk,exit_px_f,outcome_f=k,float(c["close"]),"voldry"
                            break
                if exp_vol_nospk>0 and _bj>=0 and (_bj-i)>=exp_vol_nospk_bars and _rmax_f<exp_vol_nospk:
                    _cl=((float(c["close"])-entry)/risk) if direction==1 else ((entry-float(c["close"]))/risk)
                    if _cl<=0:
                        fk,exit_px_f,outcome_f=k,float(c["close"]),"volns"
                        break
                c=fine_ltf[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                _best_f_prev=best_f
                if direction==1:
                    if hi>best_f: best_f=hi
                else:
                    if lo<best_f: best_f=lo
                if exp_partial_r>0 and not _partial_taken and risk>0:
                    _cur_rf=(best_f-entry)*direction/risk
                    if _cur_rf>=exp_partial_r:
                        _partial_taken=True; _partial_r=exp_partial_r
                if exp_profit_stage_r>0 and exp_profit_stage_distance_r>0 and risk>0:
                    _stage_prev_r=(_best_f_prev-entry)*direction/risk
                    if _stage_prev_r>=exp_profit_stage_r:
                        _profit_stage_fired=True
                        _stage_px=_best_f_prev-direction*exp_profit_stage_distance_r*risk
                        if direction>0:
                            if _stage_px>sl_cur_f: sl_cur_f=_stage_px
                        else:
                            if _stage_px<sl_cur_f: sl_cur_f=_stage_px
                if direction==1:
                    # D3 ordering fix 2026-09-20: ratchet BEFORE the SL check —
                    # the stop is armed at the activation instant (bar open), so
                    # this same 1m bar is enforced against the new level. Combined
                    # with the unconditional ratchet this is the full live-faithful
                    # semantics: armed at confirmation, enforced immediately.
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        _tr_ok=True
                        if _trail_skip_rem>0:
                            _trail_skip_rem-=1; _tr_ok=False
                        if _tr_ok and exp_trail_delay_r>0 and risk>0:
                            if ((_best_f_prev if exp_trail_delay_prevbar else best_f)-entry)*direction/risk < exp_trail_delay_r:
                                _tr_ok=False
                        if _tr_ok:
                            if exp_trail_half:
                                if sl_cur_f < cand: sl_cur_f=0.5*(sl_cur_f+cand)
                            elif sl_cur_f < cand:
                                sl_cur_f=cand
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "trail")
                        break
                    if exp_ma_trail_period>0:
                        _mj=bs.bisect_right(candle_ts, ts-900)-1
                        if _mj>=i and candle_ts[_mj]+900==ts and _ma15[_mj] is not None and float(candles_ltf[_mj]["close"]) < _ma15[_mj]:
                            fk,exit_px_f,outcome_f=k,float(candles_ltf[_mj]["close"]),"ma_trail"
                            break
                else:
                    # D3 ordering fix 2026-09-20 (short mirror): see long-side comment.
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        _tr_ok=True
                        if _trail_skip_rem>0:
                            _trail_skip_rem-=1; _tr_ok=False
                        if _tr_ok and exp_trail_delay_r>0 and risk>0:
                            if ((_best_f_prev if exp_trail_delay_prevbar else best_f)-entry)*direction/risk < exp_trail_delay_r:
                                _tr_ok=False
                        if _tr_ok:
                            if exp_trail_half:
                                if cand < sl_cur_f: sl_cur_f=0.5*(sl_cur_f+cand)
                            elif cand < sl_cur_f:
                                sl_cur_f=cand
                    if hi >= sl_cur_f:
                        fill=max(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f >= sl0 else "trail")
                        break
                    if exp_ma_trail_period>0:
                        _mj=bs.bisect_right(candle_ts, ts-900)-1
                        if _mj>=i and candle_ts[_mj]+900==ts and _ma15[_mj] is not None and float(candles_ltf[_mj]["close"]) > _ma15[_mj]:
                            fk,exit_px_f,outcome_f=k,float(candles_ltf[_mj]["close"]),"ma_trail"
                            break
            if fk is None:
                outcome="open"
                exit_idx=n-1
                exit_px=float(fine_ltf[-1]["close"])
                exit_ts=int(fine_ltf[-1]["ts"])
                exit_date=fine_ltf[-1].get("date") or candles_ltf[-1]["date"]
            else:
                outcome=outcome_f
                exit_px=exit_px_f
                exit_ts=int(fine_ltf[fk]["ts"])
                exit_date=fine_ltf[fk].get("date")
                exit_idx=bisect.bisect_right(candle_ts, exit_ts)-1
                exit_idx=max(0, min(exit_idx, n-1))
                if not exit_date:
                    exit_date=candles_ltf[exit_idx]["date"]
        elif exit_idx is None:
            exit_idx=n-1
            exit_px=float(candles_ltf[-1]["close"])
            outcome="open"
        if not fine_ltf:
            exit_ts=int(candles_ltf[exit_idx]["ts"])
            exit_date=candles_ltf[exit_idx]["date"]
        move=(exit_px-entry) if direction==1 else (entry-exit_px)
        _partial_exit_price=0.0
        if _partial_taken and risk>0:
            _partial_exit_price=entry+direction*_partial_r*risk
            _rem_move=(exit_px-entry) if direction==1 else (entry-exit_px)
            r_multiple=(_partial_r*0.5)+(_rem_move/risk)*0.5
        else:
            r_multiple=move/risk if risk>0 else 0
        # Streak halt (causal): book EVERY trade, then check streak
        if max_consecutive_losses > 0:
            if r_multiple <= 0:
                consecutive_losses += 1
                if consecutive_losses >= max_consecutive_losses:
                    halt_skip_rem = exp_halt_skip_n  # skip next N entries
                    if exp_skipwin_halt > 0:
                        halt_ts = int(exit_ts)
                    consecutive_losses = 0  # reset after halt
                else:
                    pass
            else:
                consecutive_losses = 0
        ltf_trades.append({
            "trade_no": len(ltf_trades)+1,
            "dir": "long" if direction==1 else "short",
            "swing_no": sig["swing_no"],
            "break_kind": sig["kind"],
            "htf_regime": use,
            "entry_idx": i,
            "entry_ts": int(candles_ltf[i]["ts"]),
            "entry_date": candles_ltf[i]["date"],
            "entry_price": round(entry,2),
            "sl": round(sl0,2),
            "target": round(target,2),
            "exit_idx": exit_idx,
            "exit_ts": int(exit_ts),
            "exit_date": exit_date,
            "exit_price": round(float(exit_px),2),
            "outcome": outcome,
            "r_multiple": round(float(r_multiple),3),
            "bars_held": exit_idx - i,
            "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,
            "window_key": _window_key,
            "loss_streak_at_entry": _exp_streak,
            "loss_streak_triggered": int(_exp_trigger),
            "opposite_override": _exp_opposite,
            "profit_stage_fired": int(_profit_stage_fired),
        })
        busy_until=candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
        if cooldown_bars > 0 and r_multiple < 0:
            last_loss_bar = exit_idx
        if r_multiple < 0:
            last_loss_ts=int(exit_ts)
        if exp_cohort_swingpause and r_multiple <= 0:
            _other_open=any(int(_t.get("entry_ts") or 0) < int(exit_ts) and int(_t.get("exit_ts") or 0) > int(exit_ts) for _t in ltf_trades)
            if _other_open and _exp_cohort_loss_count < int(exp_cohort_loss_n):
                _exp_cohort_loss_count += 1
                if _exp_cohort_loss_count >= int(exp_cohort_loss_n):
                    _exp_cohort_loss_ts=int(exit_ts)
                    _exp_cohort_stats["loss_triggers"] += 1
        if _window_key is not None:
            _ws2=_window_budget.setdefault(_window_key, {"entries": 0, "realized_r": 0.0})
            _ws2["entries"] += 1
    # For each LTF trade, find its parent HTF interval.
    # Pass 1: flip intervals (direction-matched). Pass 2: b2 intervals as-is
    # for trades not covered by a flip. No trimming — b2 fills the gaps.
    _parent_ivs = {}
    _flip_starts = [s for s,_,_,_,_ in intervals_flip]
    _b2_starts = [s for s,_,_,_,_ in intervals_b2]
    # Pass 1: flip intervals for trades inside a same-direction flip
    for t in ltf_trades:
        ts = t["entry_ts"]
        td = 1 if t["dir"] == "long" else -1
        idx = bs.bisect_right(_flip_starts, ts) - 1
        if idx >= 0:
            iv = intervals_flip[idx]
            if iv[0] < ts <= iv[1] and iv[2] == td:
                key = (iv[0], iv[1], iv[2])
                if key not in _parent_ivs:
                    _parent_ivs[key] = iv
    # Pass 2: b2 intervals for trades not yet covered, no trimming.
    # B2 fills the gaps between flip windows. Some overlap with flip is OK.
    for t in ltf_trades:
        ts = t["entry_ts"]
        td = 1 if t["dir"] == "long" else -1
        regime = t.get("htf_regime", "flip")
        if regime == "b2" and intervals_b2:
            if any(iv[0] < ts <= iv[1] for iv in _parent_ivs.values()):
                continue
            idx = bs.bisect_right(_b2_starts, ts) - 1
            if idx >= 0:
                iv = intervals_b2[idx]
                if iv[0] < ts <= iv[1] and iv[2] == td:
                    key = (iv[0], iv[1], iv[2])
                    if key not in _parent_ivs:
                        _parent_ivs[key] = iv
    parent_intervals = sorted(_parent_ivs.values(), key=lambda x: x[0])

    return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
             "ltf_trades": ltf_trades, "intervals": parent_intervals,
             "retest_stats": retest_stats,
             "five_m_stats": _exp_5m_stats, "cohort_stats": _exp_cohort_stats,
             "shadow_rows": _exp_shadow_rows, "weekly_state_rows": _exp_weekly_state_rows,
             "event_stats": _exp_event_stats, "campaign_stats": _exp_campaign_stats,
             "loss_window_kill_stats": _exp_loss_window_kill_stats,
             "win_window_kill_stats": _exp_win_window_kill_stats}

