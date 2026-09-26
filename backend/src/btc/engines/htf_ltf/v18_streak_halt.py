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
    sl_buf_atr=0.25, ext_stop_r=1.5,
    chop_thresh=61.8, atr_low_thresh=0.35, atr_high_thresh=0.65,
    mode="chop",  # chop, atr_low, atr_both, chop_or_atr
    cooldown_bars=0,
    max_consecutive_losses=0,  # 0 = no halt, N = halt after N consecutive losses
    htf_rr=3.0,  # HTF (1h) fixed R target — controls when window closes
    window_end="exit",  # "exit" = HTF trade exit (SL/target/16-day cap) [default, +331R];
                        # "r_touch" = first touch of ext_stop_r 1.5R [tested: +200.6R, -130R vs exit]
):
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    from src.btc.btc_engine import _collect_signals, _trail_events, trade_stats
    import bisect as bs
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
    chop=_chop_series_1h(candles_htf, lb=14)
    atr_pct=_atr_pct_15m(candles_ltf)
    candle_ts_ltf=[int(c["ts"]) for c in candles_ltf]
    candle_ts_htf=[int(c["ts"]) for c in candles_htf]
    # C14: regime gate at the ENTRY INSTANT (signal bar close = next candle open).
    # Only 1h candles that CLOSED by the entry instant may set the regime -
    # the running 1h candle's final chop is future data (up to 45 min lookahead).
    # Precompute chop per LTF bar from the last 1h bar CLOSED by ts+900.
    candle_ts_htf_close=[t+3600 for t in candle_ts_htf]
    chop_per_ltf=[50.0]*len(candles_ltf)
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
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
        j=bs.bisect_right(htf_sw_ts, ts+900)-1
        if j>=0: htf_dir_per_ltf[i]=htf_sw_dir[j]; htf_mag_per_ltf[i]=htf_sw_mag[j]
        j2=bs.bisect_right(ltf_sw_ts, ts+900)-1
        if j2>=0: ltf_dir_per_ltf[i]=ltf_sw_dir[j2]
    # Rolling percentile of chop (for dynamic_chop mode)
    chop_pct_per_ltf=[50.0]*len(candles_ltf)
    _lookback=672
    for i,ts in enumerate(candle_ts_ltf):
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
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
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
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
        j=bs.bisect_right(candle_ts_htf_close, ts+900)-1
        if j>=0 and j<len(_fd_htf):
            fd_per_ltf[i]=_fd_htf[j]
    # LTF signals (decisive)
    from src.btc.btc_engine import CandleStore
    ltf_store = CandleStore(candles_ltf)
    ltf_sigs=_collect_signals(swings_ltf, "decisive", skip_first=True, selection="stream", candles=candles_ltf)
    filtered=[]
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
        else:
            use="flip"
        # pick intervals
        if use=="union":
            # Idea 2: check BOTH B2 and FLIP intervals
            _union_matched=False
            for _iv,_st in [(intervals_b2,starts_b2),(intervals_flip,starts_flip)]:
                if not _iv: continue
                _idx=bs.bisect_right(_st,bar_ts)-1
                if _idx<0: continue
                _s,_e,_d,_pe,_psl=_iv[_idx]
                if (_s+2700<bar_ts<=_e+2700) and sig["dir"]==_d:
                    _union_matched=True
                    # keep _pe,_psl for extension check
                    pe=_pe; psl=_psl; d=_d
                    break
            if not _union_matched: continue
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
        if not (s + 2700 < bar_ts <= e + 2700): continue
        if sig["dir"] != d: continue
        if ext_stop_r>0:
            hrisk=abs(pe-psl)
            if hrisk>0:
                ext=(float(candles_ltf[bar]["close"])-pe)*d/hrisk
                if ext > ext_stop_r: continue
        filtered.append((sig, use))
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
    last_loss_bar=-999999
    consecutive_losses=0
    halt_skip_next=False  # True after Nth loss: skip NEXT entry, then reset
    from src.btc.btc_engine import _trail_events as _te
    import bisect
    for sig, use in filtered:
        bar_time=sig["bar"]  # datetime string
        i=ltf_store.pos(bar_time)  # position via timestamp lookup
        if i < 0 or i>=n-1: continue
        if busy_until and bar_time <= busy_until: continue
        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue
        # Streak halt (causal): after N consecutive losses BOOKED, skip NEXT entry
        if halt_skip_next:
            halt_skip_next=False
            consecutive_losses=0
            continue
        direction=int(sig["dir"])
        entry=float(candles_ltf[i]["close"])
        sl_pivot=sig["swing_start_px"]
        if direction==1:
            sl=sl_pivot - sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl>=entry: continue
            risk=entry-sl
            if risk<0.0005*entry: continue
            target=entry+3.0*risk
        else:
            sl=sl_pivot + sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl<=entry: continue
            risk=sl-entry
            if risk<0.0005*entry: continue
            target=entry-3.0*risk
        sl0=sl; sl_cur=sl; best=entry
        # Trail events: timestamp-based (confirmed_at_time → position via store)
        want_dir = "up" if direction == 1 else "down"
        events = []
        for s in swings_ltf:
            if s.get("dir") != want_dir:
                continue
            ct = s.get("confirmed_at_time", "")
            if not ct:
                continue
            cidx = ltf_store.pos(ct)
            if cidx >= 0:
                events.append((cidx, float(s["seg"]["start_px"])))
        events.sort(key=lambda x: x[0])
        ev_idx=-1
        exit_idx=None; exit_px=None; outcome="open"; exit_ts=None; exit_date=None
        for j in range(i+1, n if not fine_ltf else i+1):
            c=candles_ltf[j]
            hi=float(c["high"]); lo=float(c["low"])
            if direction==1:
                if hi>best: best=hi
            else:
                if lo<best: best=lo
            if direction==1:
                # D3 ordering fix 2026-09-20: the ratchet applies BEFORE the SL
                # check — the stop is armed the instant the swing confirms (bar
                # open), so this same bar is enforced against the new level.
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    if sl_cur < cand:
                        sl_cur=cand
                if lo <= sl_cur:
                    fill=min(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur <= sl0 else "trail"
                    break
            else:
                # D3 ordering fix 2026-09-20 (short mirror): see long-side comment.
                while ev_idx+1 < len(events) and events[ev_idx+1][0] <= j:
                    ev_idx+=1
                    if events[ev_idx][0] < i: continue
                    cand=events[ev_idx][1]
                    if cand < sl_cur:
                        sl_cur=cand
                if hi >= sl_cur:
                    fill=max(sl_cur, float(c["open"]))
                    exit_idx,exit_px=j,fill
                    outcome="sl" if sl_cur >= sl0 else "trail"
                    break
        if fine_ltf:
            bar_ts=int(candles_ltf[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events if candle_ts[min(e+1,n-1)] > bar_ts]
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry; sl_cur_f=sl_cur; ev_idx_f=-1; fk=None; exit_px_f=None; outcome_f="open"
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                if direction==1:
                    if hi>best_f: best_f=hi
                else:
                    if lo<best_f: best_f=lo
                if direction==1:
                    # D3 ordering fix 2026-09-20: ratchet BEFORE the SL check —
                    # the stop is armed at the activation instant (bar open), so
                    # this same 1m bar is enforced against the new level. Combined
                    # with the unconditional ratchet this is the full live-faithful
                    # semantics: armed at confirmation, enforced immediately.
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        if sl_cur_f < cand:
                            sl_cur_f=cand
                    if lo <= sl_cur_f:
                        fill=min(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "trail")
                        break
                else:
                    # D3 ordering fix 2026-09-20 (short mirror): see long-side comment.
                    while ev_idx_f+1 < len(events_ts) and events_ts[ev_idx_f+1][0] <= ts:
                        ev_idx_f+=1
                        cand=events_ts[ev_idx_f][1]
                        if cand < sl_cur_f:
                            sl_cur_f=cand
                    if hi >= sl_cur_f:
                        fill=max(sl_cur_f, float(c["open"]))
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f >= sl0 else "trail")
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
        r_multiple=move/risk if risk>0 else 0
        # Streak halt (causal): book EVERY trade, then check streak
        if max_consecutive_losses > 0:
            if r_multiple <= 0:
                consecutive_losses += 1
                if consecutive_losses >= max_consecutive_losses:
                    halt_skip_next = True  # skip the NEXT entry
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
        })
        busy_until=candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
        if cooldown_bars > 0 and r_multiple < 0:
            last_loss_bar = exit_idx
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
            "ltf_trades": ltf_trades, "intervals": parent_intervals}
