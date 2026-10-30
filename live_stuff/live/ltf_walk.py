"""LTF walk extracted from _vendored/unified.py (brick 3b).

Module-level function so it can be reused and made stateful incrementally.
"""
import bisect as bs

from _vendored.btc_engine import CandleStore


def run_ltf_walk(
    _bm_breaks,
    _bm_times,
    _fs_confirm_at,
    bar,
    candle_ts_htf,
    candle_ts_ltf,
    candles_ltf,
    cooldown_bars,
    exit_fs_max_gap_h,
    exp_bias_momentum_min,
    exp_bm_causal,
    exp_causal_sl,
    exp_fs_gray,
    exp_fs_small_swing,
    exp_fs_trail_trigger,
    exp_ltf_no_entry,
    exp_max_concurrent,
    exp_min_sl_pct,
    exp_no_opposite,
    exp_partial_r,
    exp_skip_weekend,
    exp_stop_slip_bps,
    exp_trail_delay_prevbar,
    exp_trail_delay_r,
    exp_trail_half,
    exp_trail_skip_n,
    filtered,
    fine_ltf,
    fs_dn_ts,
    fs_up_ts,
    htf_trades_b2,
    htf_trades_decisive,
    htf_trades_flip,
    intervals_b2,
    intervals_flip,
    max_consecutive_losses,
    max_positions,
    sl_buf_atr,
    swings_ltf,
    state=None,
):
    ltf_store = CandleStore(candles_ltf)
    n=len(candles_ltf)
    if n==0:
        return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
                "htf_trades_decisive": htf_trades_decisive,
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
    # Incremental path: only when state provided, no fine_ltf, and prefix grew.
    _state = state
    if (_state is not None and isinstance(_state, dict)
            and not fine_ltf
            and isinstance(candles_ltf, (list, tuple)) and len(candles_ltf) >= 1):
        _prev_n = _state.get("processed_n", 0)
        if (isinstance(_prev_n, int) and _prev_n > 0 and _prev_n <= n
                and _state.get("open") is not None):
            import copy as _copy
            _finalized = [dict(t) for t in _state.get("finalized", [])]
            _open = [_copy.deepcopy(t) for t in _state.get("open", [])]
            _sc = _state.get("scalars", {}) or {}
            _consec = _sc.get("consecutive_losses", 0)
            _halt = _sc.get("halt_skip_next", False)
            _last_loss = _sc.get("last_loss_bar", -999999)
            _busy = _sc.get("busy_until", "")
            _open_ivs = [tuple(x) for x in _sc.get("_open_ivs", [])]
            _open_dirs = [tuple(x) for x in _sc.get("_open_dirs", [])]
            _ctx = {
                "candles_ltf": candles_ltf, "atr15": atr15, "sl_buf_atr": sl_buf_atr,
                "exp_partial_r": exp_partial_r, "exp_trail_delay_r": exp_trail_delay_r,
                "exp_trail_half": exp_trail_half, "exp_stop_slip_bps": exp_stop_slip_bps,
            }
            _last_close = float(candles_ltf[-1]["close"])
            for _j in range(_prev_n, n):
                for _T in _open:
                    if _T.get("_finalized"):
                        continue
                    if not _T.get("_exited"):
                        step_one_bar(_T, _j, _ctx)
                for _T in list(_open):
                    if _T.get("_finalized") or not _T.get("_exited"):
                        continue
                    _i = _T["i"]
                    _direction = _T["direction"]
                    _entry = _T["entry"]
                    _sl0 = _T["sl0"]
                    _sl_cur = _T["sl_cur"]
                    _risk = _T["risk"]
                    _target = _T["target"]
                    _exit_idx = _T["exit_idx"]
                    _exit_px = _T["exit_px"]
                    _outcome = _T["outcome"]
                    if not fine_ltf:
                        _exit_ts = int(candles_ltf[_exit_idx]["ts"])
                        _exit_date = candles_ltf[_exit_idx]["date"]
                    else:
                        _exit_ts = int(candles_ltf[_exit_idx]["ts"])
                        _exit_date = candles_ltf[_exit_idx].get("date") or candles_ltf[_exit_idx]["date"]
                    _move = (_exit_px - _entry) if _direction == 1 else (_entry - _exit_px)
                    _partial_exit_price = 0.0
                    if _T.get("_partial_taken") and _risk > 0:
                        _partial_r = _T["_partial_r"]
                        _partial_exit_price = _entry + _direction * _partial_r * _risk
                        _rem_move = (_exit_px - _entry) if _direction == 1 else (_entry - _exit_px)
                        _r_multiple = (_partial_r * 0.5) + (_rem_move / _risk) * 0.5
                    else:
                        _r_multiple = _move / _risk if _risk > 0 else 0.0
                    if max_consecutive_losses > 0:
                        if _r_multiple <= 0:
                            _consec += 1
                            if _consec >= max_consecutive_losses:
                                _halt = True
                                _consec = 0
                        else:
                            _consec = 0
                    _gray = _T.get("_gray_until", "")
                    _trade = {
                        "trade_no": 0,
                        "dir": "long" if _direction == 1 else "short",
                        "swing_no": _T["sig"]["swing_no"],
                        "break_kind": _T["sig"]["kind"],
                        "htf_regime": _T["use"],
                        "window_start": int(_T["win_start"]),
                        "window_end": int(_T["win_end"]),
                        "entry_idx": _i,
                        "entry_ts": int(candles_ltf[_i]["ts"]),
                        "entry_date": candles_ltf[_i]["date"],
                        "entry_price": round(_entry, 2),
                        "sl": round(_T["sl0"], 2),
                        "target": round(_target, 2),
                        "exit_idx": _exit_idx,
                        "exit_ts": int(_exit_ts),
                        "exit_date": _exit_date,
                        "exit_price": round(float(_exit_px), 2),
                        "outcome": _outcome,
                        "r_multiple": round(float(_r_multiple), 3),
                        "bars_held": _exit_idx - _i,
                        "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,
                    }
                    _finalized.append(_trade)
                    _busy = candles_ltf[_exit_idx]["date"] if _exit_idx is not None and _exit_idx < n else ""
                    if exp_max_concurrent > 0:
                        _open_ivs.append((int(candles_ltf[_i]["ts"]),
                                          int(candles_ltf[_exit_idx]["ts"]) if _exit_idx is not None and _exit_idx < n
                                          else int(candles_ltf[_i]["ts"])))
                    if exp_no_opposite:
                        _open_dirs.append((int(candles_ltf[_i]["ts"]),
                                           int(candles_ltf[_exit_idx]["ts"]) if _exit_idx is not None and _exit_idx < n
                                           else int(candles_ltf[_i]["ts"]),
                                           _direction))
                    if _gray and (not _busy or _gray > _busy):
                        _busy = _gray
                    if cooldown_bars > 0 and _r_multiple < 0:
                        _last_loss = _exit_idx
                    _T["_finalized"] = True
                _open = [t for t in _open if not t.get("_finalized")]

            _open_trades_list = []
            for _T in _open:
                _i = _T["i"]
                _direction = _T["direction"]
                _entry = _T["entry"]
                _sl0 = _T["sl0"]
                _risk = _T["risk"]
                _target = _T["target"]
                _exit_idx = n - 1
                _exit_px = _last_close
                _move = (_exit_px - _entry) if _direction == 1 else (_entry - _exit_px)
                _partial_exit_price = 0.0
                if _T.get("_partial_taken") and _risk > 0:
                    _partial_r = _T["_partial_r"]
                    _partial_exit_price = _entry + _direction * _partial_r * _risk
                    _rem_move = (_exit_px - _entry) if _direction == 1 else (_entry - _exit_px)
                    _r_multiple = (_partial_r * 0.5) + (_rem_move / _risk) * 0.5
                else:
                    _r_multiple = _move / _risk if _risk > 0 else 0.0
                _trade = {
                    "trade_no": 0,
                    "dir": "long" if _direction == 1 else "short",
                    "swing_no": _T["sig"]["swing_no"],
                    "break_kind": _T["sig"]["kind"],
                    "htf_regime": _T["use"],
                    "window_start": int(_T["win_start"]),
                    "window_end": int(_T["win_end"]),
                    "entry_idx": _i,
                    "entry_ts": int(candles_ltf[_i]["ts"]),
                    "entry_date": candles_ltf[_i]["date"],
                    "entry_price": round(_entry, 2),
                    "sl": round(_sl0, 2),
                    "target": round(_target, 2),
                    "exit_idx": _exit_idx,
                    "exit_ts": int(candles_ltf[_exit_idx]["ts"]),
                    "exit_date": candles_ltf[_exit_idx]["date"],
                    "exit_price": round(float(_exit_px), 2),
                    "outcome": "open",
                    "r_multiple": round(float(_r_multiple), 3),
                    "bars_held": _exit_idx - _i,
                    "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,
                }
                _open_trades_list.append(_trade)
            _all_trades = _finalized + _open_trades_list
            _all_trades.sort(key=lambda t: t.get("entry_idx", 0))
            for _idx, _t in enumerate(_all_trades, 1):
                _t["trade_no"] = _idx
            _parent_ivs = {}
            _flip_starts = [s for s, _, _, _, _ in intervals_flip]
            _b2_starts = [s for s, _, _, _, _ in intervals_b2]
            for _t in _all_trades:
                _ts = _t["entry_ts"]
                _td = 1 if _t["dir"] == "long" else -1
                _idx = bs.bisect_right(_flip_starts, _ts) - 1
                if _idx >= 0:
                    _iv = intervals_flip[_idx]
                    if _iv[0] < _ts <= _iv[1] and _iv[2] == _td:
                        _key = (_iv[0], _iv[1], _iv[2])
                        if _key not in _parent_ivs:
                            _parent_ivs[_key] = _iv
            for _t in _all_trades:
                _ts = _t["entry_ts"]
                _td = 1 if _t["dir"] == "long" else -1
                _regime = _t.get("htf_regime", "flip")
                if _regime == "b2" and intervals_b2:
                    if any(_iv[0] < _ts <= _iv[1] for _iv in _parent_ivs.values()):
                        continue
                    _idx = bs.bisect_right(_b2_starts, _ts) - 1
                    if _idx >= 0:
                        _iv = intervals_b2[_idx]
                        if _iv[0] < _ts <= _iv[1] and _iv[2] == _td:
                            _key = (_iv[0], _iv[1], _iv[2])
                            if _key not in _parent_ivs:
                                _parent_ivs[_key] = _iv
            _parent_intervals = sorted(_parent_ivs.values(), key=lambda x: x[0])
            _open_state = []
            for _T in _open:
                _T.pop("_finalized", None)
                _T["_exited"] = False
                _T["exit_idx"] = None
                _T["exit_px"] = None
                _T["outcome"] = "open"
                _open_state.append(_T)
            _new_state = {
                "finalized": _finalized,
                "open": _open_state,
                "processed_n": n,
                "scalars": {
                    "consecutive_losses": _consec,
                    "halt_skip_next": _halt,
                    "last_loss_bar": _last_loss,
                    "busy_until": _busy,
                    "_open_ivs": _open_ivs,
                    "_open_dirs": _open_dirs,
                },
            }
            _result = {
                "htf_trades": htf_trades_flip,
                "htf_trades_b2": htf_trades_b2,
                "htf_trades_decisive": htf_trades_decisive,
                "ltf_trades": _all_trades,
                "intervals": _parent_intervals,
                "_state": _new_state,
            }
            return _result
    # end incremental path

    ltf_trades=[]
    _open_state_list=[]
    _gray_until=""   # set only by an exp_fs_gray exit; empty means "slot is free"
    # v19 causal SL: running extreme since the last CONFIRMED swing.
    # A swing's confirmed_at_idx is the instant the swing becomes knowable, so at
    # bar i the value below depends only on candles up to i. Ported verbatim from
    # backtest/tests/_w1h_gray_tmp.py:995-1021, the harness copy that produced
    # the 484fe2a numbers. When a swing confirms, the running extreme RESETS to
    # that swing's seg end, then tracks from there.
    _csl=[0.0]*n; _csh=[0.0]*n
    if exp_causal_sl:
        _conf_evs=[]
        for _s in swings_ltf:
            _ca=_s.get("confirmed_at_idx")
            if _ca is not None and int(_ca)>=0:
                _e=_s.get("seg",{}).get("end_idx",-1)
                if _e is not None and int(_e)>=0:
                    _conf_evs.append((int(_ca),int(_e)))
        _conf_evs.sort()
        _cref=0; _cei=0
        _clo=float(candles_ltf[0]["low"]); _chi=float(candles_ltf[0]["high"])
        for _ci in range(n):
            while _cei<len(_conf_evs) and _conf_evs[_cei][0]<=_ci:
                # +1: the forming swing starts on the bar AFTER the finished leg.
                # Resetting to seg end put the running extreme on the low of a
                # candle belonging to a leg that had already completed, which is
                # the retroactive pivot one swing earlier - not a causal value.
                # Checked: across all 2900 swings, seg_end + 1 is never after
                # confirmed_at_idx, so this cannot read a future bar.
                _cref=_conf_evs[_cei][1]+1; _cei+=1
                if _cref<=_ci and _cref<n:
                    # Scan _cref.._ci, not just _cref. The old code took only the
                    # single candle at _cref, so every bar between the swing end
                    # and the confirm instant was skipped - and the lowest of
                    # those is usually the one that matters. On 30 Nov 2023 the
                    # reset fired at 22:15 pointing at 19:45, and the 21:15 low
                    # in between was never read; the engine used the 22:45 low
                    # instead, 118 points higher. That alone turned a +18.61R
                    # winner into a -1.00R stop-out.
                    _clo=min(float(candles_ltf[k]["low"]) for k in range(_cref,_ci+1))
                    _chi=max(float(candles_ltf[k]["high"]) for k in range(_cref,_ci+1))
            _cl=float(candles_ltf[_ci]["low"]); _ch2=float(candles_ltf[_ci]["high"])
            if _cl<_clo: _clo=_cl
            if _ch2>_chi: _chi=_ch2
            _csl[_ci]=_clo; _csh[_ci]=_chi
    # v19: no position limit - busy_until stays empty and is never armed
    # UNIFIED: v19 deleted this initialisation along with the gate but kept
    # the assignment at the end of the loop, so restoring the gate without
    # this line raises UnboundLocalError on the first entry. The line itself is
    # kept VERBATIM from v18:572 because test_experiments_craze.py anchors on it.
    busy_until=""  # datetime string — timestamp-based, not index
    # UNIFIED: booked-trade intervals backing exp_max_concurrent. Stays empty at
    # N=0 so the gate never fires and the shipped pins are untouched.
    _open_ivs=[]  # (entry_ts:int, exit_ts:int) for trades booked so far
    # UNIFIED: same intervals but carrying direction, backing exp_no_opposite.
    # Kept separate from _open_ivs rather than widening that one because
    # _open_ivs' 2-tuple shape is read by the exp_max_concurrent gate and by
    # harnesses that unpack it positionally; adding a third element would break
    # both for no benefit. Filled under the same "never populate when the knob is
    # off" rule so the shipped path allocates nothing extra per entry.
    _open_dirs=[]  # (entry_ts:int, exit_ts:int, dir:int)
    last_loss_bar=-999999
    consecutive_losses=0
    halt_skip_next=False  # True after Nth loss: skip NEXT entry, then reset
    # Weekday helper for exp_skip_weekend, memoised per calendar DAY: the walk
    # re-evaluates the same date once per LTF bar, and strptime/date() per bar
    # is pure overhead on a 4-year replay. The cache is keyed on the date
    # substring only, so it holds one int per distinct day and cannot grow per
    # bar. A local function rather than a module-level one because the cache is
    # per-simulate() call and must not be shared across books.
    _wd_cache={}
    def _is_weekend(dstr):
        _d = dstr[:10]
        _w = _wd_cache.get(_d)
        if _w is None:
            import datetime as _dt
            _w = _dt.date(int(_d[:4]), int(_d[5:7]), int(_d[8:10])).weekday()
            _wd_cache[_d] = _w
        return _w
    # Window bounds for the audit trail, carried on every booked trade.
    # Captured into their own names rather than read from s/e at the append
    # site: the union branch (mode=="union") unpacks into _s/_e and only
    # carries pe, psl and d forward, so s and e still hold the PREVIOUS bar's
    # window there. Reading s/e directly would publish a stale window on every
    # union book. Nothing reads these names for control flow - they are
    # reporting only, and they must not be able to move a number.
    win_start=0; win_end=0
    try:
        from _vendored.btc_engine import _trail_events as _te
    except Exception:
        from btc_engine import _trail_events as _te
    import bisect
    # win_start/win_end ride along with the signal: the window bounds are bound in the
    # filtering loop above, not here, so they cannot be read from s/e at booking time.
    for sig, use, win_start, win_end in filtered:
        bar_time=sig["bar"]  # datetime string
        i=ltf_store.pos(bar_time)  # position via timestamp lookup
        if i < 0 or i>=n-1: continue
        # UNIFIED: the position gate, restored from v18:582 under a parameter.
        # max_positions=1 reproduces v18 exactly; 0 is v19 (unlimited).
        if max_positions > 0 and busy_until and bar_time <= busy_until: continue
        # UNIFIED: simultaneous-open cap. Distinct from the serial gate above,
        # which knows only when the last booked trade closed. Counts trades
        # already booked whose [entry_ts, exit_ts] contains this entry bar.
        # Causal: every exit_ts in _open_ivs was settled before this entry was
        # considered, since trades are booked in stream order.
        if exp_max_concurrent > 0 and _open_ivs:
            _bt=int(candles_ltf[i]["ts"])
            _nopen=sum(1 for (_a,_b) in _open_ivs if _a <= _bt <= _b)
            if _nopen >= exp_max_concurrent: continue
        # UNIFIED: opposite-direction lock. A new entry is refused only if a trade
        # in the OTHER direction is open right now; trades in the same direction
        # do not block it. Placed after the position gates because those are
        # stronger and cheaper, and before the signal's direction is read below
        # only in the sense that it uses sig["dir"] directly.
        if exp_no_opposite and _open_dirs:
            _bt2=int(candles_ltf[i]["ts"])
            _d2=int(sig["dir"])
            if any(_dd != _d2 and _a <= _bt2 <= _b for (_a,_b,_dd) in _open_dirs):
                continue
        # CRAZE ANCHOR: the line above is the v18 gate restored verbatim, so
        # test_experiments_craze.py's t10 anchor (which rewrites the bare
        # `if busy_until and bar_time <= busy_until: continue` form) does not
        # match. That anchor exists to inject exp_mltf gating. It is the ONE
        # anchor of 62 that Phase 2 had to touch, and it is touched here rather
        # than in the harness so the harness stays engine-agnostic.
        if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue
        # Streak halt (causal): after N consecutive losses BOOKED, skip NEXT entry
        if halt_skip_next:
            halt_skip_next=False
            consecutive_losses=0
            continue
        if exp_skip_weekend and _is_weekend(candles_ltf[i]["date"]) >= 5:
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
        direction=int(sig["dir"])
        entry=float(candles_ltf[i]["close"])
        # SL pivot. RETRO = the swing's true origin (lookahead). CAUSAL = the running
        # extreme as of bar i (knowable in real time).
        if exp_causal_sl:
            # _ci must exist before it is read. Defining it after this line
            # compiles fine and never runs when exp_causal_sl=0, which is why it
            # reached a commit.
            _ci = i - 1 if (exp_ltf_no_entry and i > 0) else i
            sl_pivot = _csl[_ci] if direction==1 else _csh[_ci]
        else:
            sl_pivot = sig["swing_start_px"]
        if direction==1:
            sl=sl_pivot - sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl>=entry: continue
            risk=entry-sl
            if risk<0.0005*entry: continue
            # UNIFIED: minimum stop distance, exp_min_sl_pct as a fraction of
            # entry price. Kept as its OWN line so the shipped guard above stays
            # byte-identical: test_experiments_craze.py anchors on that exact
            # line and asserts it appears twice, then injects the D3 risk-width
            # gate after it. Folding the two together broke that contract and the
            # harness caught it. The two are additive - both must pass.
            if exp_min_sl_pct>0 and risk<exp_min_sl_pct*entry: continue
            target=entry+3.0*risk
        else:
            sl=sl_pivot + sl_buf_atr*atr15[i] if sl_buf_atr>0 else sl_pivot
            if sl<=entry: continue
            risk=sl-entry
            if risk<0.0005*entry: continue
            # UNIFIED: same minimum stop distance as the long branch above, and
            # the same reason it is a separate line - the harness anchor counts
            # the `risk<0.0005*entry` line twice across the function.
            if exp_min_sl_pct>0 and risk<exp_min_sl_pct*entry: continue
            target=entry-3.0*risk
        sl0=sl; sl_cur=sl; best=entry
        # ── exp_fs_trail_trigger: ratchet the STOP, never delay the ENTRY ──────
        # Computed once per trade. The trigger bar is where the FS candle's own
        # extreme broke, which _fs_confirm_at already resolved at a bar no later
        # than itself; the level is applied inside the bar loop only for bars at
        # or after it, so nothing here is knowable earlier than it is used.
        _fs_trig_bar=-1; _fs_trig_px=0.0; _fs_trig_ts=None
        if exp_fs_trail_trigger and sig.get("kind")=="FS":
            _sn=int(sig.get("swing_no",-1))
            _ent=_fs_confirm_at.get(_sn)
            if _ent is not None and _ent[0]>=0:
                for _s in swings_ltf:
                    if int(_s.get("swing_index",-1))!=_sn: continue
                    _fi=int(_s.get("fs_at_idx",-1))
                    if not (0<=_fi<len(candles_ltf)): break
                    _fs_trig_bar=_ent[0]
                    _fs_trig_ts=int(candles_ltf[_fs_trig_bar]["ts"])
                    _fs_trig_px=(float(candles_ltf[_fi]["low"]) if direction==1
                                 else float(candles_ltf[_fi]["high"])) if exp_fs_trail_trigger>=2.0 else entry
                    break
        _partial_taken=False; _partial_r=0.0
        _trail_skip_rem=exp_trail_skip_n
        # Trail events: timestamp-based (confirmed_at_time â†’ position via store)
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
        T = {
            "direction": direction, "entry": entry, "sl0": sl0, "sl_cur": sl_cur,
            "best": best, "risk": risk, "i": i, "events": events, "ev_idx": ev_idx,
            "_partial_taken": _partial_taken, "_partial_r": _partial_r,
            "_trail_skip_rem": _trail_skip_rem,
            "_fs_trig_bar": _fs_trig_bar, "_fs_trig_px": _fs_trig_px, "_fs_trig_ts": _fs_trig_ts,
            "exit_idx": None, "exit_px": None, "outcome": "open", "_exited": False,
            "sig": sig, "use": use, "win_start": win_start, "win_end": win_end, "target": target,
        }
        ctx = {
            "candles_ltf": candles_ltf, "atr15": atr15, "sl_buf_atr": sl_buf_atr,
            "exp_partial_r": exp_partial_r, "exp_trail_delay_r": exp_trail_delay_r,
            "exp_trail_half": exp_trail_half, "exp_stop_slip_bps": exp_stop_slip_bps,
            "exp_fs_trail_trigger": exp_fs_trail_trigger,
        }
        for j in range(i + 1, n if not fine_ltf else i + 1):
            if step_one_bar(T, j, ctx):
                break
        best = T["best"]; sl_cur = T["sl_cur"]; ev_idx = T["ev_idx"]
        _partial_taken = T["_partial_taken"]; _partial_r = T["_partial_r"]
        _trail_skip_rem = T["_trail_skip_rem"]
        _fs_trig_bar = T["_fs_trig_bar"]; _fs_trig_px = T["_fs_trig_px"]; _fs_trig_ts = T["_fs_trig_ts"]
        if T["_exited"]:
            exit_idx = T["exit_idx"]; exit_px = T["exit_px"]; outcome = T["outcome"]
        if outcome == "open" and not fine_ltf:
            import copy as _cp
            _open_state_list.append(_cp.deepcopy(T))
        if fine_ltf:
            bar_ts=int(candles_ltf[i]["ts"])
            events_ts=[(candle_ts[min(e+1,n-1)], px) for e,px in events if candle_ts[min(e+1,n-1)] > bar_ts]
            f_start=bisect.bisect_left(fine_ts, candle_ts[i+1])
            best_f=entry; sl_cur_f=sl_cur; ev_idx_f=-1; fk=None; exit_px_f=None; outcome_f="open"
            _gray_until=""
            for k in range(f_start, len(fine_ltf)):
                c=fine_ltf[k]
                hi=float(c["high"]); lo=float(c["low"]); ts=int(c["ts"])
                if exp_fs_small_swing>0:
                    # OWNER PROPOSAL. Enter as the book does; when the swing that
                    # opened the trade CONFIRMS, measure how big that swing turned
                    # out to be and exit if it was small. Unlike the room-threshold
                    # exit already closed (CLOSED_DO_NOT_REPEAT.md), the quantity
                    # here is the swing's OWN leg, not the distance from our entry,
                    # and - this is the point - it is genuinely knowable at the FS
                    # bar: end_px and start_px are both settled at or before
                    # confirmed_at_idx, and the FS bar has closed.
                    #
                    # Gray mode: closing early frees the slot, and with
                    # cooldown_bars / max_consecutive_losses the next signal then
                    # starts a brand-new trade that displaces the winners we were
                    # protecting. That crossover is what made the earlier exit
                    # arms lose. With exp_fs_gray the exit also arms busy_until so
                    # the engine stays occupied and nothing new enters.
                    _fsg=fs_up_ts if direction==1 else fs_dn_ts
                    _fgi=bs.bisect_left(_fsg, ts)
                    if _fgi<len(_fsg) and _fsg[_fgi]==ts:
                        _swn=None
                        for _ss in swings_ltf:
                            _si2=int(_ss.get("fs_at_idx",-1))
                            if _si2>=0 and _si2<len(candles_ltf) and int(candles_ltf[_si2]["ts"])==ts:
                                _swn=_ss; break
                        if _swn is not None:
                            _sg2=_swn.get("seg",{}) or {}
                            _sp2=float(_sg2.get("start_px",0) or 0)
                            _ep2=float(_sg2.get("end_px",0) or 0)
                            _as=max(0,i-19)
                            _ah=max(float(candles_ltf[_q]["high"]) for _q in range(_as,i+1))
                            _al=min(float(candles_ltf[_q]["low"]) for _q in range(_as,i+1))
                            _atr2=(_ah-_al) if _ah>_al else 1.0
                            if _atr2>0 and abs(_ep2-_sp2)/_atr2 < exp_fs_small_swing:
                                fk, exit_px_f, outcome_f = k, float(c["close"]), "fs_small_swing"
                                if exp_fs_gray:
                                    _gray_until=c["date"]
                                break
                if exit_fs_max_gap_h>=0:
                    _fsd=fs_up_ts if direction==1 else fs_dn_ts
                    _fsl=bisect.bisect_left(_fsd, ts)
                    if _fsl<len(_fsd) and _fsd[_fsl]==ts:
                        _gap=(ts-bar_ts)/3600.0
                        if exit_fs_max_gap_h<=0 or _gap<=float(exit_fs_max_gap_h):
                            fk, exit_px_f, outcome_f = k, float(c["close"]), "fs_exit"
                            break
                _best_f_prev=best_f
                if direction==1:
                    if hi>best_f: best_f=hi
                else:
                    if lo<best_f: best_f=lo
                if exp_partial_r>0 and not _partial_taken and risk>0:
                    _cur_rf=(best_f-entry)*direction/risk
                    if _cur_rf>=exp_partial_r:
                        _partial_taken=True; _partial_r=exp_partial_r
                # Same FS-extreme stop trigger as the 15m loop above, keyed on the
                # TRIGGER BAR'S TIMESTAMP because this loop walks 1m fine candles.
                # `_partial_taken`/`risk` are shared with the outer loop and are
                # not touched here. Only ever tightens, only to a level on the
                # losing side of the 1m price, so it cannot arm and take out in
                # the same bar.
                if _fs_trig_ts is not None and ts>=_fs_trig_ts:
                    _tf=_fs_trig_px
                    if sl_buf_atr>0:
                        _atr_f=(atr15[bar] if 0<=bar<len(atr15) else 0.0)
                        _tf=(_tf-_atr_f*sl_buf_atr) if direction==1 else (_tf+_atr_f*sl_buf_atr)
                    if direction==1:
                        if _tf>sl_cur_f and _tf<lo: sl_cur_f=_tf
                    else:
                        if _tf<sl_cur_f and _tf>hi: sl_cur_f=_tf
                if direction==1:
                    # D3 ordering fix 2026-09-20: ratchet BEFORE the SL check â€”
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
                        if exp_stop_slip_bps: fill=fill*(1.0-exp_stop_slip_bps/10000.0)
                        fk,exit_px_f,outcome_f=k,fill,("sl" if sl_cur_f <= sl0 else "trail")
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
                        if exp_stop_slip_bps: fill=fill*(1.0+exp_stop_slip_bps/10000.0)
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
        # Partial accounting. When the half was taken, the booked R is half the
        # trigger plus half the remaining move - the position really was cut, so
        # scoring it as a whole position would overstate every partial book.
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
            # Window this trade was taken in. window_start + 3600 is when the
            # governing 1h bias candle closed, i.e. the earliest instant the
            # trade could have been known. entry_ts - that is the lead time.
            "window_start": int(win_start),
            "window_end": int(win_end),
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
            # 0.0 when exp_partial_r never armed. run_experiment.py counts and
            # reports partials off this field, so it has to be present even on
            # the books that never take one.
            "partial_exit_price": round(_partial_exit_price, 2) if _partial_exit_price > 0 else 0.0,
        })
        busy_until=candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
        if exp_max_concurrent > 0:
            _open_ivs.append((int(candles_ltf[i]["ts"]),
                              int(candles_ltf[exit_idx]["ts"]) if exit_idx is not None and exit_idx < n
                              else int(candles_ltf[i]["ts"])))
        if exp_no_opposite:
            _open_dirs.append((int(candles_ltf[i]["ts"]),
                               int(candles_ltf[exit_idx]["ts"]) if exit_idx is not None and exit_idx < n
                               else int(candles_ltf[i]["ts"]),
                               direction))
        if _gray_until and (not busy_until or _gray_until > busy_until):
            busy_until=_gray_until
        if cooldown_bars > 0 and r_multiple < 0:
            last_loss_bar = exit_idx
    # For each LTF trade, find its parent HTF interval.
    # Pass 1: flip intervals (direction-matched). Pass 2: b2 intervals as-is
    # for trades not covered by a flip. No trimming â€” b2 fills the gaps.
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

    _state_out = None
    if not fine_ltf:
        _finalized_list = [t for t in ltf_trades if t.get("outcome") != "open"]
        _state_out = {
            "finalized": _finalized_list,
            "open": _open_state_list,
            "processed_n": n,
            "scalars": {
                "consecutive_losses": consecutive_losses,
                "halt_skip_next": halt_skip_next,
                "last_loss_bar": last_loss_bar,
                "busy_until": busy_until,
                "_open_ivs": _open_ivs,
                "_open_dirs": _open_dirs,
            },
        }
    _ret = {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
            "htf_trades_decisive": htf_trades_decisive,
            "ltf_trades": ltf_trades, "intervals": parent_intervals}
    if _state_out is not None:
        _ret["_state"] = _state_out
    return _ret



PARAMS = ['_bm_breaks', '_bm_times', '_fs_confirm_at', 'bar', 'candle_ts_htf', 'candle_ts_ltf', 'candles_ltf', 'cooldown_bars', 'exit_fs_max_gap_h', 'exp_bias_momentum_min', 'exp_bm_causal', 'exp_causal_sl', 'exp_fs_gray', 'exp_fs_small_swing', 'exp_fs_trail_trigger', 'exp_ltf_no_entry', 'exp_max_concurrent', 'exp_min_sl_pct', 'exp_no_opposite', 'exp_partial_r', 'exp_skip_weekend', 'exp_stop_slip_bps', 'exp_trail_delay_prevbar', 'exp_trail_delay_r', 'exp_trail_half', 'exp_trail_skip_n', 'filtered', 'fine_ltf', 'fs_dn_ts', 'fs_up_ts', 'htf_trades_b2', 'htf_trades_decisive', 'htf_trades_flip', 'intervals_b2', 'intervals_flip', 'max_consecutive_losses', 'max_positions', 'sl_buf_atr', 'swings_ltf']

def step_one_bar(T, j, ctx):
    candles_ltf = ctx["candles_ltf"]
    atr15 = ctx["atr15"]
    sl_buf_atr = ctx["sl_buf_atr"]
    exp_partial_r = ctx["exp_partial_r"]
    exp_trail_delay_r = ctx["exp_trail_delay_r"]
    exp_trail_half = ctx["exp_trail_half"]
    exp_stop_slip_bps = ctx["exp_stop_slip_bps"]

    c = candles_ltf[j]
    hi = float(c["high"]); lo = float(c["low"])
    direction = T["direction"]
    if direction == 1:
        if hi > T["best"]:
            T["best"] = hi
    else:
        if lo < T["best"]:
            T["best"] = lo
    if exp_partial_r > 0 and not T["_partial_taken"] and T["risk"] > 0:
        _cur_r = (T["best"] - T["entry"]) * direction / T["risk"]
        if _cur_r >= exp_partial_r:
            T["_partial_taken"] = True
            T["_partial_r"] = exp_partial_r
    if T["_fs_trig_bar"] >= 0 and j >= T["_fs_trig_bar"]:
        _ft = (T["_fs_trig_px"] - sl_buf_atr * atr15[j]) if (direction == 1 and sl_buf_atr > 0) else T["_fs_trig_px"]
        if direction != 1 and sl_buf_atr > 0:
            _ft = T["_fs_trig_px"] + sl_buf_atr * atr15[j]
        if direction == 1:
            if _ft > T["sl_cur"] and _ft < T["best"]:
                T["sl_cur"] = _ft
        else:
            if _ft < T["sl_cur"] and _ft > T["best"]:
                T["sl_cur"] = _ft
    i = T["i"]
    events = T["events"]
    ev_idx = T["ev_idx"]
    if direction == 1:
        while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
            ev_idx += 1
            if events[ev_idx][0] < i:
                continue
            cand = events[ev_idx][1]
            _tr_ok = True
            if T["_trail_skip_rem"] > 0:
                T["_trail_skip_rem"] -= 1
                _tr_ok = False
            if _tr_ok and exp_trail_delay_r > 0 and T["risk"] > 0:
                if ((T["best"] - T["entry"]) * direction / T["risk"]) < exp_trail_delay_r:
                    _tr_ok = False
            if _tr_ok:
                if exp_trail_half:
                    if T["sl_cur"] < cand:
                        T["sl_cur"] = 0.5 * (T["sl_cur"] + cand)
                elif T["sl_cur"] < cand:
                    T["sl_cur"] = cand
        T["ev_idx"] = ev_idx
        if lo <= T["sl_cur"]:
            fill = min(T["sl_cur"], float(c["open"]))
            if exp_stop_slip_bps:
                fill = fill * (1.0 - exp_stop_slip_bps / 10000.0)
            T["exit_idx"] = j
            T["exit_px"] = fill
            T["outcome"] = "sl" if T["sl_cur"] <= T["sl0"] else "trail"
            T["_exited"] = True
            return True
    else:
        while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
            ev_idx += 1
            if events[ev_idx][0] < i:
                continue
            cand = events[ev_idx][1]
            _tr_ok = True
            if T["_trail_skip_rem"] > 0:
                T["_trail_skip_rem"] -= 1
                _tr_ok = False
            if _tr_ok and exp_trail_delay_r > 0 and T["risk"] > 0:
                if ((T["best"] - T["entry"]) * direction / T["risk"]) < exp_trail_delay_r:
                    _tr_ok = False
            if _tr_ok:
                if exp_trail_half:
                    if cand < T["sl_cur"]:
                        T["sl_cur"] = 0.5 * (T["sl_cur"] + cand)
                elif cand < T["sl_cur"]:
                    T["sl_cur"] = cand
        T["ev_idx"] = ev_idx
        if hi >= T["sl_cur"]:
            fill = max(T["sl_cur"], float(c["open"]))
            if exp_stop_slip_bps:
                fill = fill * (1.0 + exp_stop_slip_bps / 10000.0)
            T["exit_idx"] = j
            T["exit_px"] = fill
            T["outcome"] = "sl" if T["sl_cur"] >= T["sl0"] else "trail"
            T["_exited"] = True
            return True
    return False
