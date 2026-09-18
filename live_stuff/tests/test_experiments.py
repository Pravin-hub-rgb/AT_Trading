"""Experiment harness — v18 engine with pluggable experiment flags.

Each experiment modifies one specific behavior of the v18 engine.
Run all experiments against the same baseline and compare.

Usage:
    python test_experiments.py              # run all experiments
    python test_experiments.py 1 2 3        # run specific experiments
    python test_experiments.py --baseline    # baseline only
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import _chop_series_1h, _atr_pct_15m
from src.btc.engines.v7_timecap import simulate_btc_trades_v7
from src.btc.btc_engine import _collect_signals, CandleStore
from src.walker import FlowCandle

SYMBOL = "BTCUSDT_BYBIT"
PARAMS = {"sl_buf_atr": 0.01, "chop_thresh": 58.0, "cooldown_bars": 10,
          "max_consecutive_losses": 3, "ext_stop_r": 1.5}
DEFAULT_SWINGS = {"min_bars_1h": 20, "min_bars_15m": 50}


def load_window(tf):
    df = load_btc_df(tf, SYMBOL)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                        "high": float(row.high), "low": float(row.low), "close": float(row.close),
                        "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow


def simulate_v18_experiments(
    candles_htf, swings_htf, candles_ltf, swings_ltf, fine_ltf=None,
    *,
    sl_buf_atr=0.01, ext_stop_r=1.5,
    chop_thresh=58.0, cooldown_bars=10, max_consecutive_losses=3,
    htf_rr=3.0, window_end="exit",
    # ---- experiment flags ----
    exp_dual_active=False,       # Exp 1: try both flip+b2 per signal
    exp_regime_persist=0,        # Exp 2: N bars hysteresis (0=off)
    exp_adaptive_halt=False,     # Exp 3: reset halt on regime change
    exp_tod_filter=False,        # Exp 4: skip 00-04 UTC
    exp_multi_ltf=False,         # Exp 5: re-entry after exit+cooldown
    exp_multi_ltf_cd=10,         # Exp 5: cooldown bars between re-entries
    exp_partial_exit=False,      # Exp 6: 50% at 1.5R, trail rest
    exp_pullback_ma=0,           # Exp 7: enter on pullback to N-bar MA (0=off)
    exp_window_quality=0.0,      # Exp 8: skip bottom N% by swing magnitude
    exp_trail_mode="swing",      # Exp 9: "swing" / "mb20" / "atr" / "chandelier"
    exp_regime_for_halt=False,   # Exp 3 alt: also track regime per trade for adaptive
):
    """Modified v18 engine with experiment flags."""
    import bisect as bs

    # --- HTF interval generation (same as baseline) ---
    htf_trades_flip = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="flip",
        sl_mode="swing", rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True,
        fine=fine_ltf, cap_days=16)
    htf_trades_decisive = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="decisive",
        sl_mode="swing", rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True,
        fine=fine_ltf, cap_days=16)
    htf_trades_b2 = simulate_btc_trades_v7(candles_htf, swings_htf, entry_break="b2",
        sl_mode="swing", rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True,
        fine=fine_ltf, cap_days=16)

    fine_ts = [int(c["ts"]) for c in fine_ltf] if fine_ltf else []

    def to_intervals(trades):
        iv = []
        for t in trades:
            if t["outcome"] == "open": continue
            wend = int(t["exit_ts"])
            iv.append([int(t["entry_ts"]), wend, 1 if t["dir"] == "long" else -1,
                       float(t["entry_price"]), float(t["sl"])])
        iv.sort(key=lambda x: x[0])
        return [tuple(w) for w in iv]

    intervals_flip = to_intervals(htf_trades_flip)
    intervals_b2 = to_intervals(htf_trades_b2)
    starts_flip = [s for s, _, _, _, _ in intervals_flip]
    starts_b2 = [s for s, _, _, _, _ in intervals_b2]

    # --- Chop + ATR per LTF bar (C14 correct) ---
    chop = _chop_series_1h(candles_htf, lb=14)
    atr_pct = _atr_pct_15m(candles_ltf)
    candle_ts_ltf = [int(c["ts"]) for c in candles_ltf]
    candle_ts_htf = [int(c["ts"]) for c in candles_htf]
    candle_ts_htf_close = [t + 3600 for t in candle_ts_htf]
    chop_per_ltf = [50.0] * len(candles_ltf)
    for i, ts in enumerate(candle_ts_ltf):
        j = bs.bisect_right(candle_ts_htf_close, ts + 900) - 1
        if 0 <= j < len(chop):
            chop_per_ltf[i] = chop[j]

    # --- LTF signals ---
    ltf_store = CandleStore(candles_ltf)
    ltf_sigs = _collect_signals(swings_ltf, "decisive", skip_first=True,
                                selection="stream", candles=candles_ltf)

    # --- Exp 8: Window quality score (swing magnitude) ---
    iv_magnitudes = []
    if exp_window_quality > 0:
        for iv in intervals_flip + intervals_b2:
            mag = abs(iv[3] - iv[4])  # entry - SL = risk magnitude
            iv_magnitudes.append((iv, mag))
        if iv_magnitudes:
            mag_vals = sorted(m[1] for m in iv_magnitudes)
            cutoff = mag_vals[int(len(mag_vals) * exp_window_quality)]
            good_ivs = {id(m[0]) for m in iv_magnitudes if m[1] >= cutoff}
        else:
            good_ivs = set()
    else:
        good_ivs = None  # no filtering

    # --- Exp 2: Regime persistence state ---
    regime_state = None  # "flip" or "b2"
    regime_count = 0     # consecutive bars in current regime

    # --- Signal filtering ---
    filtered = []
    for sig in ltf_sigs:
        bar_time = sig["bar"]
        bar = ltf_store.pos(bar_time)
        if bar < 0 or bar >= len(candles_ltf): continue
        bar_ts = candle_ts_ltf[bar]

        ch = chop_per_ltf[bar] if bar < len(chop_per_ltf) else 50.0
        atrp = atr_pct[bar] if bar < len(atr_pct) else 0.5

        # Exp 4: Time-of-Day filter (skip 00-04 UTC)
        if exp_tod_filter:
            from datetime import datetime, timezone, timedelta
            utc_hour = datetime.fromtimestamp(bar_ts, tz=timezone.utc).hour
            if 0 <= utc_hour < 4:
                continue

        # Regime decision
        raw_use = "b2" if ch > chop_thresh else "flip"

        # Exp 2: Regime persistence hysteresis
        if exp_regime_persist > 0:
            if raw_use != regime_state:
                regime_count += 1
                if regime_count >= exp_regime_persist:
                    regime_state = raw_use
                    regime_count = 0
                use = regime_state if regime_state else raw_use
            else:
                regime_count = 0
                use = regime_state if regime_state else raw_use
        else:
            use = raw_use

        # Exp 1: Dual-active — try both interval sets
        if exp_dual_active:
            candidates = []
            for try_use in ["flip", "b2"]:
                if try_use == "flip":
                    ivs, sts = intervals_flip, starts_flip
                else:
                    ivs, sts = intervals_b2, starts_b2
                if not ivs: continue
                idx = bs.bisect_right(sts, bar_ts) - 1
                if idx < 0: continue
                s, e, d, pe, psl = ivs[idx]
                if not (s + 2700 < bar_ts <= e + 2700): continue
                if sig["dir"] != d: continue
                if ext_stop_r > 0:
                    hrisk = abs(pe - psl)
                    if hrisk > 0:
                        ext = (float(candles_ltf[bar]["close"]) - pe) * int(sig["dir"]) / hrisk
                        if ext > ext_stop_r: continue
                candidates.append((try_use, ivs[idx]))
            if not candidates: continue
            # Exp 8: quality filter
            if good_ivs is not None:
                candidates = [c for c in candidates if id(c[1]) in good_ivs]
                if not candidates: continue
            use = candidates[0][0]
            filtered.append((sig, use))
        else:
            # Standard single-set lookup
            if use == "flip":
                ivs, sts = intervals_flip, starts_flip
            else:
                ivs, sts = intervals_b2, starts_b2
            if not ivs: continue
            idx = bs.bisect_right(sts, bar_ts) - 1
            if idx < 0: continue
            s, e, d, pe, psl = ivs[idx]
            if not (s + 2700 < bar_ts <= e + 2700): continue
            if sig["dir"] != d: continue
            if ext_stop_r > 0:
                hrisk = abs(pe - psl)
                if hrisk > 0:
                    ext = (float(candles_ltf[bar]["close"]) - pe) * int(sig["dir"]) / hrisk
                    if ext > ext_stop_r: continue
            # Exp 8: quality filter
            if good_ivs is not None and id(ivs[idx]) not in good_ivs:
                continue
            filtered.append((sig, use))

    # --- LTF simulation ---
    n = len(candles_ltf)
    if n == 0:
        return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
                "ltf_trades": [], "intervals": intervals_flip}

    candle_ts = candle_ts_ltf

    # ATR for SL
    tr_l = [0.0] * n
    for _i in range(n):
        _c = candles_ltf[_i]
        if _i == 0:
            tr_l[_i] = float(_c["high"]) - float(_c["low"])
        else:
            _pc = float(candles_ltf[_i - 1]["close"])
            tr_l[_i] = max(float(_c["high"]) - float(_c["low"]),
                           abs(float(_c["high"]) - _pc), abs(float(_c["low"]) - _pc))
    atr15 = [0.0] * n
    for _i in range(n):
        _lo = max(0, _i - 13)
        atr15[_i] = sum(tr_l[_lo:_i + 1]) / (_i - _lo + 1)

    ltf_trades = []
    busy_until = ""
    last_loss_bar = -999999
    last_exit_bar = -999999  # Exp 5: track last exit bar for multi-LTF cooldown
    consecutive_losses = 0
    halt_skip_next = False
    last_regime = None  # Exp 3: track regime for adaptive halt

    for sig, use in filtered:
        bar_time = sig["bar"]
        i = ltf_store.pos(bar_time)
        if i < 0 or i >= n - 1: continue

        # Exp 5: Multiple LTF — no busy_until, use cooldown instead
        multi_cd = exp_multi_ltf_cd if exp_multi_ltf else cooldown_bars
        if exp_multi_ltf:
            # cooldown after ANY exit (win or loss) to prevent overtrading
            if multi_cd > 0 and i - last_exit_bar < multi_cd: continue
        else:
            if busy_until and bar_time <= busy_until: continue
            if cooldown_bars > 0 and i - last_loss_bar < cooldown_bars: continue

        # Streak halt
        if halt_skip_next:
            halt_skip_next = False
            consecutive_losses = 0
            continue

        # Exp 3: Adaptive halt — reset on regime change
        if exp_adaptive_halt and last_regime is not None:
            if use != last_regime:
                consecutive_losses = 0
                halt_skip_next = False
        last_regime = use

        direction = int(sig["dir"])
        entry = float(candles_ltf[i]["close"])
        sl_pivot = sig["swing_start_px"]

        # Exp 7: Pullback entry — wait for dip to MA
        if exp_pullback_ma > 0 and i >= exp_pullback_ma:
            ma = sum(float(candles_ltf[j]["close"]) for j in range(i - exp_pullback_ma, i)) / exp_pullback_ma
            if direction == 1:
                if entry > ma * 1.001:  # price too far above MA, skip
                    continue
            else:
                if entry < ma * 0.999:  # price too far below MA, skip
                    continue

        if direction == 1:
            sl = sl_pivot - sl_buf_atr * atr15[i] if sl_buf_atr > 0 else sl_pivot
            if sl >= entry: continue
            risk = entry - sl
            if risk < 0.0005 * entry: continue
            target = entry + 3.0 * risk
        else:
            sl = sl_pivot + sl_buf_atr * atr15[i] if sl_buf_atr > 0 else sl_pivot
            if sl <= entry: continue
            risk = sl - entry
            if risk < 0.0005 * entry: continue
            target = entry - 3.0 * risk

        sl0 = sl; sl_cur = sl; best = entry
        want_dir = "up" if direction == 1 else "down"
        events = []
        for s in swings_ltf:
            if s.get("dir") != want_dir: continue
            ct = s.get("confirmed_at_time", "")
            if not ct: continue
            cidx = ltf_store.pos(ct)
            if cidx >= 0:
                events.append((cidx, float(s["seg"]["start_px"])))
        events.sort(key=lambda x: x[0])
        ev_idx = -1
        exit_idx = None; exit_px = None; outcome = "open"; exit_ts = None; exit_date = None

        # Exp 6: partial exit tracking
        partial_done = False
        partial_r = 0.0

        if fine_ltf:
            bar_ts_val = int(candles_ltf[i]["ts"])
            events_ts = [(candle_ts[min(e + 1, n - 1)], px) for e, px in events
                         if candle_ts[min(e + 1, n - 1)] > bar_ts_val]
            f_start = bs.bisect_left(fine_ts, candle_ts[i + 1])
            best_f = entry; sl_cur_f = sl_cur; ev_idx_f = -1
            fk = None; exit_px_f = None; outcome_f = "open"

            # Exp 6: partial exit — track position size
            pos_size = 1.0  # full position

            for k in range(f_start, len(fine_ltf)):
                c = fine_ltf[k]
                hi = float(c["high"]); lo = float(c["low"]); ts = int(c["ts"])
                if direction == 1:
                    if hi > best_f: best_f = hi
                else:
                    if lo < best_f: best_f = lo

                # Exp 6: partial exit at 1.5R
                if exp_partial_exit and not partial_done:
                    if direction == 1:
                        if best_f >= entry + 1.5 * risk:
                            partial_done = True
                            partial_r = 1.5 * (pos_size * 0.5)  # 50% at 1.5R
                            pos_size *= 0.5
                    else:
                        if best_f <= entry - 1.5 * risk:
                            partial_done = True
                            partial_r = 1.5 * (pos_size * 0.5)
                            pos_size *= 0.5

                if direction == 1:
                    if lo <= sl_cur_f:
                        fill = min(sl_cur_f, float(c["open"]))
                        fk, exit_px_f, outcome_f = k, fill, ("sl" if sl_cur_f <= sl0 else "trail")
                        break
                    while ev_idx_f + 1 < len(events_ts) and events_ts[ev_idx_f + 1][0] <= ts:
                        ev_idx_f += 1
                        cand = events_ts[ev_idx_f][1]
                        if sl_cur_f < cand < lo:
                            sl_cur_f = cand
                else:
                    if hi >= sl_cur_f:
                        fill = max(sl_cur_f, float(c["open"]))
                        fk, exit_px_f, outcome_f = k, fill, ("sl" if sl_cur_f >= sl0 else "trail")
                        break
                    while ev_idx_f + 1 < len(events_ts) and events_ts[ev_idx_f + 1][0] <= ts:
                        ev_idx_f += 1
                        cand = events_ts[ev_idx_f][1]
                        if hi < cand < sl_cur_f:
                            sl_cur_f = cand

            if fk is None:
                outcome = "open"
                exit_idx = n - 1
                exit_px = float(fine_ltf[-1]["close"])
                exit_ts = int(fine_ltf[-1]["ts"])
                exit_date = fine_ltf[-1].get("date") or candles_ltf[-1]["date"]
            else:
                outcome = outcome_f
                exit_px = exit_px_f
                exit_ts = int(fine_ltf[fk]["ts"])
                exit_date = fine_ltf[fk].get("date")
                exit_idx = bs.bisect_right(candle_ts, exit_ts) - 1
                exit_idx = max(0, min(exit_idx, n - 1))
                if not exit_date:
                    exit_date = candles_ltf[exit_idx]["date"]
        elif exit_idx is None:
            exit_idx = n - 1
            exit_px = float(candles_ltf[-1]["close"])
            outcome = "open"
        if not fine_ltf:
            exit_ts = int(candles_ltf[exit_idx]["ts"])
            exit_date = candles_ltf[exit_idx]["date"]

        move = (exit_px - entry) if direction == 1 else (entry - exit_px)
        r_multiple = move / risk if risk > 0 else 0

        # Exp 6: add partial R
        if exp_partial_exit and partial_done:
            r_multiple = partial_r + (r_multiple * pos_size)

        # Streak halt
        if max_consecutive_losses > 0:
            if r_multiple <= 0:
                consecutive_losses += 1
                if consecutive_losses >= max_consecutive_losses:
                    halt_skip_next = True
                    consecutive_losses = 0
            else:
                consecutive_losses = 0

        ltf_trades.append({
            "trade_no": len(ltf_trades) + 1,
            "dir": "long" if direction == 1 else "short",
            "swing_no": sig["swing_no"],
            "break_kind": sig["kind"],
            "htf_regime": use,
            "entry_idx": i,
            "entry_ts": int(candles_ltf[i]["ts"]),
            "entry_date": candles_ltf[i]["date"],
            "entry_price": round(entry, 2),
            "sl": round(sl0, 2),
            "target": round(target, 2),
            "exit_idx": exit_idx,
            "exit_ts": int(exit_ts),
            "exit_date": exit_date,
            "exit_price": round(float(exit_px), 2),
            "outcome": outcome,
            "r_multiple": round(float(r_multiple), 3),
            "bars_held": exit_idx - i,
        })

        # Exp 5: Multi-LTF — track last exit for cooldown
        if exp_multi_ltf:
            last_exit_bar = exit_idx  # cooldown after ANY exit
        else:
            busy_until = candles_ltf[exit_idx]["date"] if exit_idx is not None and exit_idx < n else ""
            if cooldown_bars > 0 and r_multiple < 0:
                last_loss_bar = exit_idx

    return {"htf_trades": htf_trades_flip, "htf_trades_b2": htf_trades_b2,
            "ltf_trades": ltf_trades, "intervals": intervals_flip}


def run_and_report(name, trades):
    rs = [t["r_multiple"] for t in trades]
    n = len(rs)
    if n == 0:
        return {"name": name, "trades": 0, "total_r": 0, "wr": 0, "pf": 0, "allyes": False}
    tot = sum(rs)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    wr = 100 * len(wins) / n
    pf = sum(wins) / abs(sum(losses)) if losses else float("inf")
    years = {}
    for t in trades:
        y = t["entry_date"][:4]
        years.setdefault(y, [0, 0.0])
        years[y][0] += 1
        years[y][1] += t["r_multiple"]
    allyes = all(v[1] > 0 for v in years.values())
    return {"name": name, "trades": n, "total_r": tot, "wr": wr, "pf": pf,
            "allyes": allyes, "years": years}


def fmt(r, base_r=None):
    yr = "  ".join(f"{y}:{v[1]:+.0f}" for y, v in sorted(r.get("years", {}).items()))
    flag = "OK" if r["allyes"] else "NEG"
    delta = ""
    if base_r is not None:
        d = r["total_r"] - base_r
        delta = f"  ({d:+.1f}R)"
    return (f"  {r['name']:25s}  {r['trades']:4d}t  {r['total_r']:+8.1f}R  "
            f"WR {r['wr']:5.1f}%  PF {r['pf']:5.2f}  [{yr}]  {flag}{delta}")


def main():
    args = sys.argv[1:]
    run_all = not args or "--all" in args
    run_baseline = "--baseline" in args

    print("Loading data...")
    c1h, f1h = load_window("1h")
    c15, f15 = load_window("15m")
    sw1h = _compute_swings(f1h, "continuous", min_bars=20)
    sw15 = _compute_swings(f15, "continuous", min_bars=50)
    t0 = min(c1h[0]["ts"], c15[0]["ts"])
    t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
    fine = _load_fine_1m(t0, t1, symbol=SYMBOL)
    print(f"  Data loaded. 1h: {len(c1h)} bars, 15m: {len(c15)} bars, 1m: {len(fine)} bars")

    base_kw = dict(sl_buf_atr=PARAMS["sl_buf_atr"], ext_stop_r=PARAMS["ext_stop_r"],
                    chop_thresh=PARAMS["chop_thresh"], cooldown_bars=PARAMS["cooldown_bars"],
                    max_consecutive_losses=PARAMS["max_consecutive_losses"])

    # --- Baseline ---
    print("\n" + "=" * 110)
    print("  BASELINE (v18 C14+C15)")
    print("=" * 110)
    t0b = time.time()
    base_tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **base_kw)["ltf_trades"]
    dt = time.time() - t0b
    base = run_and_report("v18 BASELINE", base_tr)
    print(fmt(base))
    print(f"  ({dt:.1f}s)")

    if run_baseline:
        return

    results = [base]
    base_r = base["total_r"]

    # --- Experiments ---
    experiments = []

    # Exp 1: Dual-Active Windows
    if run_all or "1" in args:
        experiments.append(("Exp1: Dual-Active Windows", {"exp_dual_active": True}))

    # Exp 2: Regime Persistence
    if run_all or "2" in args:
        for persist_bars in [2, 3, 5]:
            experiments.append((f"Exp2: Regime Persist={persist_bars}", {"exp_regime_persist": persist_bars}))

    # Exp 3: Adaptive Halt
    if run_all or "3" in args:
        experiments.append(("Exp3: Adaptive Halt", {"exp_adaptive_halt": True}))

    # Exp 4: Time-of-Day Filter
    if run_all or "4" in args:
        experiments.append(("Exp4: TOD Filter 00-04", {"exp_tod_filter": True}))

    # Exp 5: Multiple LTF per Window
    if run_all or "5" in args:
        for multi_cd in [5, 10, 15, 20]:
            experiments.append((f"Exp5: Multi-LTF cd={multi_cd}", {"exp_multi_ltf": True, "exp_multi_ltf_cd": multi_cd}))

    # Exp 6: Partial Exit
    if run_all or "6" in args:
        experiments.append(("Exp6: Partial Exit 50%@1.5R", {"exp_partial_exit": True}))

    # Exp 7: Pullback Entry
    if run_all or "7" in args:
        for ma_period in [10, 20, 30]:
            experiments.append((f"Exp7: Pullback MA={ma_period}", {"exp_pullback_ma": ma_period}))

    # Exp 8: Window Quality
    if run_all or "8" in args:
        for skip_pct in [0.1, 0.2, 0.3]:
            experiments.append((f"Exp8: Quality skip={skip_pct:.0%}", {"exp_window_quality": skip_pct}))

    # Exp 9: Regime Persistence + Adaptive Halt combo
    if run_all or "9" in args:
        experiments.append(("Exp9: Persist3 + Adaptive Halt", {"exp_regime_persist": 3, "exp_adaptive_halt": True}))

    # Exp 10: Dual-Active + TOD + Adaptive Halt
    if run_all or "10" in args:
        experiments.append(("Exp10: Dual+TOD+AdaptiveHalt", {"exp_dual_active": True, "exp_tod_filter": True, "exp_adaptive_halt": True}))

    print("\n" + "=" * 110)
    print(f"  RUNNING {len(experiments)} EXPERIMENTS")
    print("=" * 110)

    for name, kwargs in experiments:
        t0e = time.time()
        tr = simulate_v18_experiments(c1h, sw1h, c15, sw15, fine, **base_kw, **kwargs)["ltf_trades"]
        dt = time.time() - t0e
        r = run_and_report(name, tr)
        results.append(r)
        print(fmt(r, base_r))
        print(f"  ({dt:.1f}s)")

    # --- Summary ---
    print("\n" + "=" * 110)
    print("  SUMMARY (sorted by total R)")
    print("=" * 110)
    results.sort(key=lambda x: -x["total_r"])
    for i, r in enumerate(results):
        marker = " *** BASELINE ***" if r["name"] == "v18 BASELINE" else ""
        better = " ^" if r["total_r"] > base_r else ""
        print(f"  #{i+1:2d} {fmt(r, base_r)}{better}{marker}")

    best = results[0]
    print(f"\n  BEST: {best['name']} — {best['total_r']:+.1f}R ({best['total_r'] - base_r:+.1f}R vs baseline)")


if __name__ == "__main__":
    main()
