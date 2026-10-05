"""1-MINUTE SCALPING ENGINE - a SEPARATE book that lives inside the HTF window.

WHAT THE USER ASKED FOR (and what this is)
=========================================
  1h  -> opens the BIAS WINDOW              (unchanged, shipped)
  15m -> opens the NORMAL trade             (unchanged, shipped)
  1m  -> SCALPS inside that same window     (THIS FILE - new, parallel)

The 15m book is NOT replaced and NOT modified. This is a second book of
1m trades, run on its own engine, gated by the same HTF windows the
champion already uses. The champion's 15m ledger must come out bit-identical
or the run aborts - that is the control gate.

This is deliberately NOT the "Phase 1" patch described in
method/PHASE0_1M_SWING_BLOCKER.md. That one swapped `swings_ltf` for 1m swings
inside the shipped engine, which is index-coupled to `candles_ltf` and
silently drops 91% of signals. A SEPARATE book has no such coupling: it
carries its own candles, its own swings, its own ATR, its own slots. So the
re-parameterisation trap that blocks Phase 1 does not apply here - the 15m
book's bar-counted params (cooldown_bars=8, minBars, atr_high) are never
reinterpreted, because they keep governing 15m and only 15m.

THE 1m MECHANICS (mirroring the 15m engine's proven semantics)
==============================================================
  entry      : close of the 1m signal bar
  SL         : the 1m swing's own start pivot, +/- sl_buf_atr * atr1m
  target     : FIXED 2R (the user's "1:2 fixed wager")
  trail      : 1m swing confirmations ratchet the SL, same D3 ordering as
               the 15m engine (ratchet BEFORE the SL check, so the stop is
               armed the instant the swing confirms)
  exit       : walked on 1m bars - native resolution, no sub-1m data needed

WINDOW GATE (causal, pre-registered)
====================================
The window tuple is [start_ts, end_ts, dir, entry_px, sl] from the HTF
trade. A 1m signal may scalp only when:
    s + 3600  <  entry_inst  <=  e + 60
  * s + 3600 : the governing 1h bar CLOSES then, so before that the bias
               is not knowable (this is the shipped C14 rule)
  * entry_inst = bar_ts + 60 : the 1m bar's CLOSE
  * e + 60    : the window's own 1m-resolution edge
and the signal direction must equal the window direction. This mirrors the
15m engine's `s + 2700 < bar_ts <= e + 2700` with the correct per-tf
offsets (3600 = 1h bar, 60 = 1m bar).

MARK KINDS
==========
`decisive` = B2 + FLIP (the shipped default, first rung).
`b2` / `flip` isolate one kind. `b1` requires adding a `"b1": ("B1",)`
key to `_collect_signals`, which the shipped engine does NOT have - done
here by rebuilding btc_engine in memory, never editing the shared file
(same pattern as exp_b1_entry.py). B1 on 1m is a genuinely new trigger:
on 15m it failed hard (method/B1_ENTRY.md), but 1m has 15x the bars and a much
finer swing structure, so it is worth one honest test rather than an
assumption.

NO PRODUCTION FILE IS EDITED. Everything here is additive and default-off.
"""
from __future__ import annotations

import bisect as _bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))


# ------------------------------------------------------------------ windows
def htf_windows(candles_htf, swings_htf, *, htf_rr=3.0, cap_days=16,
                fine_ltf=None):
    """The HTF bias windows, built exactly as v18_streak_halt builds them.

    Replicated (not imported) so this file can be read on its own; the
    identity gate in the experiment proves the replication is exact.
    Returns a sorted list of (start_ts, end_ts, dir, entry_px, sl).
    """
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
    trades = simulate_btc_trades_v7(
        candles_htf, swings_htf, entry_break="decisive", sl_mode="swing",
        rr_target=htf_rr, trailing="off", breakeven_r=0.0, skip_first=True,
        fine=fine_ltf, cap_days=cap_days)
    last = int(candles_htf[-1]["ts"]) + 3600 if candles_htf else 0
    iv = []
    for t in trades:
        if t["outcome"] == "open":
            iv.append([int(t["entry_ts"]), last,
                       1 if t["dir"] == "long" else -1,
                       float(t["entry_price"]), float(t["sl"])])
        else:
            iv.append([int(t["entry_ts"]), int(t["exit_ts"]),
                       1 if t["dir"] == "long" else -1,
                       float(t["entry_price"]), float(t["sl"])])
    iv.sort(key=lambda x: x[0])
    return [tuple(w) for w in iv]


# ------------------------------------------------------------------ helpers
def atr_series(candles, lb=14):
    """ATR (absolute price units) per bar - same shape as the engine's atr15."""
    n = len(candles)
    tr = [0.0] * n
    for i in range(n):
        hi, lo = float(candles[i]["high"]), float(candles[i]["low"])
        pc = float(candles[i - 1]["close"]) if i else hi
        tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    out = [0.0] * n
    for i in range(n):
        lo_i = max(0, i - lb + 1)
        out[i] = sum(tr[lo_i:i + 1]) / (i - lo_i + 1)
    return out


def simulate_1m_scalp(
    candles_1m, swings_1m, windows, *,
    entry_break="decisive",
    target_r=2.0,            # the user's fixed 1:2
    sl_buf_atr=0.01,         # SAME constant as the 15m champion
    atr_lb=14,
    max_concurrent=1,        # scalps stacking on top of each other
    cooldown_min=0.0,        # minutes, not bars - 1m has no "bar" meaning
    max_hold_min=240.0,
    trail=True,
    take_partial=False,
    exit_mode="trail",     # "target" | "trail" | "half_be"
    be_r=1.0,              # for exit_mode="half_be": move SL to BE at +be_r
    min_risk_atr=0.25,     # HANDOVER 5.1: a stop inside 0.25x ATR is noise
    stats=None,
):
    """The 1m scalping book. Returns a list of trade dicts.

    Deliberately self-contained: it never touches the 15m book's state, so
    it cannot inherit the slot/cascade confound that killed
    exp_mltf_green_r. This is a genuinely separate book of trades.
    """
    from src.btc.btc_engine import _collect_signals

    n = len(candles_1m)
    if n == 0 or not windows:
        return []

    ts = [int(c["ts"]) for c in candles_1m]
    store = {c["date"]: i for i, c in enumerate(candles_1m)}
    atr = atr_series(candles_1m, atr_lb) if sl_buf_atr > 0 else [0.0] * n

    sigs = _collect_signals(swings_1m, entry_break, skip_first=True,
                            selection="stream", candles=candles_1m)

    # --- window lookup: bisect on window starts -------------------------
    w_starts = [w[0] for w in windows]
    hit_win = miss_dir = miss_time = 0

    # --- trail events from 1m swing confirmations -----------------------
    ev_by_dir = {1: [], -1: []}
    if trail:
        for s in swings_1m:
            ct = s.get("confirmed_at_time", "")
            if not ct:
                continue
            ci = store.get(ct)
            if ci is None or ci < 0:
                continue
            d = 1 if s.get("dir") == "up" else -1
            ev_by_dir[d].append((ci, float(s["seg"]["start_px"])))
        for d in ev_by_dir:
            ev_by_dir[d].sort(key=lambda x: x[0])
    ev_pos = {1: [e[0] for e in ev_by_dir[1]],
              -1: [e[0] for e in ev_by_dir[-1]]}

    trades = []
    open_pos = []
    cooldown_until = -1
    ex_sl = ex_degen = ex_open = ex_tgt = ex_noise = 0

    for sg in sigs:
        i = store.get(sg["bar"], -1)
        if i < 0 or i >= n - 1:
            continue
        entry_inst = ts[i] + 60          # the 1m bar's CLOSE
        d = 1 if sg["dir"] == 1 else -1

        # ---- WINDOW GATE (causal) ----
        w = _bs.bisect_right(w_starts, entry_inst) - 1
        if w < 0:
            miss_time += 1
            continue
        ws, we, wd, _wpx, _wsl = windows[w]
        if not (ws + 3600 < entry_inst <= we + 60):
            miss_time += 1
            continue
        if wd != d:
            miss_dir += 1
            continue
        hit_win += 1

        # ---- book state ----
        open_pos = [p for p in open_pos if p[0] > i]
        if len(open_pos) >= max_concurrent:
            continue
        if cooldown_min > 0 and entry_inst < cooldown_until:
            continue

        # ---- stop + target (FIXED 1:2) ----
        entry = float(candles_1m[i]["close"])
        sl_pivot = float(sg["swing_start_px"])
        if d == 1:
            sl = sl_pivot - sl_buf_atr * atr[i] if sl_buf_atr > 0 else sl_pivot
            if sl >= entry:
                ex_sl += 1
                continue
            risk = entry - sl
            target = entry + target_r * risk
        else:
            sl = sl_pivot + sl_buf_atr * atr[i] if sl_buf_atr > 0 else sl_pivot
            if sl <= entry:
                ex_sl += 1
                continue
            risk = sl - entry
            target = entry - target_r * risk
        if risk < 0.0005 * entry:      # degenerate-stop guard (HANDOVER 5.1)
            ex_degen += 1
            continue
        # HANDOVER 5.1: a stop tighter than ~0.25x ATR sits inside the noise,
        # so R explodes on arithmetic rather than on the move. Exclude and
        # COUNT these - never average them in.
        if min_risk_atr > 0 and atr[i] > 0 and risk < min_risk_atr * atr[i]:
            ex_noise += 1
            continue

        # ---- walk forward on 1m bars ----
        sl_cur = sl
        exit_i = exit_px = None
        outcome = "open"
        # exit_mode decides whether the swing trail may move the stop at all:
        #   "target"  - fixed target only, the stop never moves (pure wager)
        #   "trail"   - stop ratchets to each confirmed 1m swing pivot
        #   "half_be" - stop to breakeven at +be_r, then trails like "trail"
        use_trail = exit_mode in ("trail", "half_be")
        # `bars_held` is exit_i - i, so lim must be i + cap for the cap to
        # bind exactly. i + cap + 1 overshoots by one bar and trips the guard.
        lim = min(n - 1, i + int(max_hold_min))
        ev = ev_by_dir[d]
        ev_i = _bs.bisect_right(ev_pos[d], i)
        be_done = False
        for j in range(i + 1, lim + 1):
            hi = float(candles_1m[j]["high"])
            lo = float(candles_1m[j]["low"])
            # D3 ordering: ratchet BEFORE the stop check, so the stop is
            # armed the instant the 1m swing confirms.
            if use_trail:
                while ev_i < len(ev) and ev[ev_i][0] <= j:
                    cand = ev[ev_i][1]
                    if d == 1 and sl_cur < cand:
                        sl_cur = cand
                    elif d == -1 and sl_cur > cand:
                        sl_cur = cand
                    ev_i += 1
            if exit_mode == "half_be" and not be_done:
                if (d == 1 and hi >= entry + be_r * risk) or \
                   (d == -1 and lo <= entry - be_r * risk):
                    be_done = True
                    sl_cur = entry

            if d == 1:
                if lo <= sl_cur:
                    exit_i = j
                    exit_px = min(sl_cur, float(candles_1m[j]["open"]))
                    if use_trail and sl_cur > sl:
                        outcome = "trail"
                    elif exit_mode == "half_be" and be_done and sl_cur >= sl:
                        outcome = "be"
                    else:
                        outcome = "sl"
                    break
                if hi >= target:
                    exit_i = j
                    exit_px = max(target, float(candles_1m[j]["open"]))
                    outcome = "target"
                    break
            else:
                if hi >= sl_cur:
                    exit_i = j
                    exit_px = max(sl_cur, float(candles_1m[j]["open"]))
                    if use_trail and sl_cur < sl:
                        outcome = "trail"
                    elif exit_mode == "half_be" and be_done and sl_cur <= sl:
                        outcome = "be"
                    else:
                        outcome = "sl"
                    break
                if lo <= target:
                    exit_i = j
                    exit_px = min(target, float(candles_1m[j]["open"]))
                    outcome = "target"
                    break


        if exit_i is None:
            # The hold cap is a REAL exit, not a fallback. The first version
            # of this engine fell through to `candles_1m[-1]` here, which
            # exited at the LAST bar of the dataset - a Jan-2023 entry was
            # marked out at the Sep-2026 price and booked +2942.7R. That is
            # the HANDOVER section 5 trap-1 signature, and it was mine.
            # An un-resolved trade is now closed AT THE CAP, on the last bar
            # the walk actually looked at.
            exit_i = lim
            exit_px = float(candles_1m[exit_i]["close"])
            outcome = "time_stop"
            ex_open += 1


        move = (exit_px - entry) if d == 1 else (entry - exit_px)
        r = move / risk if risk > 0 else 0.0
        trades.append({
            "dir": "long" if d == 1 else "short",
            "entry_ts": ts[i], "entry_date": candles_1m[i]["date"],
            "entry_price": round(entry, 2), "sl": round(sl, 2),
            "risk": round(risk, 2), "target": round(target, 2),
            "exit_ts": ts[exit_i], "exit_date": candles_1m[exit_i]["date"],
            "exit_price": round(float(exit_px), 2),
            "r_multiple": round(float(r), 3), "outcome": outcome,
            "bars_held": exit_i - i, "kind": sg.get("kind", ""),
            "swing_no": sg.get("swing_no"),
        })
        open_pos.append((exit_i, d))
        ex_tgt += 1 if outcome == "target" else 0
        if cooldown_min > 0:
            cooldown_until = ts[exit_i] + int(cooldown_min * 60)

    if stats is not None:
        stats.update({
            "signals": len(sigs), "window_hits": hit_win,
            "miss_time": miss_time, "miss_dir": miss_dir,
            "excluded_sl_geometry": ex_sl, "excluded_degenerate": ex_degen,
            "excluded_noise_risk": ex_noise,
            "trades": len(trades), "targets": ex_tgt, "still_open": ex_open,
            "windows": len(windows),
        })
    return trades


def assert_hold_cap(trades, max_hold_min, label=""):
    """REGRESSION GUARD - no trade may live longer than the hold cap.

    This exists because the first version of this engine exited unresolved
    trades at the LAST bar of the dataset, turning a Jan-2023 entry into a
    Sep-2026 exit worth +2942.7R. The number looked spectacular and was
    entirely one bug. Any harness that books an unbounded hold must be
    assumed capable of this until it proves otherwise.
    """
    cap = int(max_hold_min)
    bad = [t for t in trades if int(t.get("bars_held", 0)) > cap]
    if bad:
        worst = max(bad, key=lambda t: int(t["bars_held"]))
        raise AssertionError(
            f"{label}: {len(bad)} trade(s) exceeded the {cap}-bar hold cap; "
            f"worst bars_held={worst['bars_held']} R={worst['r_multiple']} "
            f"{worst['entry_date']}->{worst['exit_date']}")
    return True


# ------------------------------------------------------------------ B1 key
def install_b1_key():
    """Rebuild btc_engine in memory with a `"b1": ("B1",)` mark kind.

    The shipped `_collect_signals` has NO b1 key, so B1 is unreachable
    without this. Same pattern as exp_b1_entry.py: types.ModuleType +
    exec, installed into sys.modules, shared file NEVER edited.
    """
    import types
    src_path = ROOT / "backend/src/btc/btc_engine.py"
    src = src_path.read_text(encoding="utf-8")
    if '"b1": ("B1",)' in src:
        return
    anchor = '        "b2": ("B2",),'
    assert src.count(anchor) == 1, f"b2 anchor count {src.count(anchor)}"
    src = src.replace(anchor, anchor + '\n        "b1": ("B1",),')
    mod = types.ModuleType("src.btc.btc_engine")
    mod.__file__ = str(src_path)
    mod.__package__ = "src.btc"
    exec(compile(src, str(src_path), "exec"), mod.__dict__)
    sys.modules["src.btc.btc_engine"] = mod


# ------------------------------------------------------------------ metrics
def net_r_series(trades):
    """Per-trade NET R for the 1m book: gross minus fees, slippage, funding.

    CRITICAL GAP THIS FIXES
    ======================
    Every 1m result so far was GROSS. The 15m book is scored on net R
    (`run_experiment.net_r`, and the reference ledgers +325.8 / +358.9 are
    net), so a gross 1m number is not comparable to the baseline it is
    being added to.

    This matters MORE for 1m than for 15m, not less, because cost is a
    function of round trips, not time:

        cost_R ~= (fee% * (entry+exit) + slip) / risk

    A scalping book with 1,000-10,000 round trips pays this 50-100x more
    often than a 500-trade swing book. The retest work already recorded the
    mechanism once - "fee-in-R inflation (costs are % of notional; smaller
    risk = bigger R cost)" - and it is exactly what a fine-grained book
    walks into.

    Funding is charged per 1m bar held (`bars_held`), matching `fund()`,
    which uses the 15m convention `0.25/8` per 8h bar; here it is applied
    per minute as `rate_per_min * bars_held` on the same notional/risk
    basis, so the units are honest for a 1m hold.
    """
    from run_experiment import _trade_costs, _g
    fee_pct = _g["fee_pct"]
    e_slip = _g["entry_slip_pct"]
    x_slip = _g["exit_slip_pct"]
    fund_rate_pm = 0.0001 * 0.25 / 8.0 / 60.0   # 0.25%/8h, per 1m bar
    out = []
    for t in trades:
        e = float(t["entry_price"])
        sl = float(t["sl"])
        rk = abs(e - sl)
        gross = float(t["r_multiple"])
        if rk <= 0 or e <= 0:
            out.append((gross, 0.0, gross))
            continue
        cost = 0.0
        fee = fee_pct / 100.0
        exit_px = float(t.get("exit_price", e))
        cost += (e * fee + exit_px * fee) / rk
        if e_slip > 0 or x_slip > 0:
            cost += (e * e_slip / 100.0 + exit_px * x_slip / 100.0) / rk
        cost += fund_rate_pm * int(t.get("bars_held") or 0) * (e / rk)
        out.append((gross, cost, gross - cost))
    return out


def book_metrics(trades, years, net=True):
    """Shape stats for the 1m book. `net=True` scores NET R (comparable to
    the 15m baseline); `net=False` keeps the gross series for the audit.
    """
    n = len(trades)
    if n == 0:
        return {"n": 0, "net": 0.0, "gross": 0.0}
    if net:
        series = net_r_series(trades)
    else:
        series = [(float(t["r_multiple"]), 0.0, float(t["r_multiple"]))
                  for t in trades]
    rs = [x[2] for x in series]
    cost_tot = sum(x[1] for x in series)
    gross_tot = sum(float(t["r_multiple"]) for t in trades)
    wins = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    # Walk the curve in TIME order (HANDOVER 5.3: sorting by R silently
    # reports max_dd 1.0).
    peak = cum = dd = 0.0
    for r, _t in sorted(zip(rs, trades), key=lambda z: int(z[1]["exit_ts"])):
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    k = int(n * 0.05)
    tr = sorted(rs)[k:n - k] if n - 2 * k > 0 else rs
    return {
        "n": n, "net": round(sum(rs), 1), "gross": round(gross_tot, 1),
        "cost_r": round(cost_tot, 1),
        "cost_per_trade": round(cost_tot / n, 4) if n else None,
        "wr": round(100.0 * len(wins) / n, 1),
        "pf": round(sum(wins) / loss, 3) if loss > 1e-9 else None,
        "avg_r": round(sum(rs) / n, 3),
        "trimmed_mean": round(sum(tr) / len(tr), 3),
        "max_dd": round(dd, 1),
        "calmar": round(sum(rs) / dd, 3) if dd > 1e-9 else None,
        "ex_best3": round(sum(sorted(rs, reverse=True)[3:]), 1),
        "ex_best5": round(sum(sorted(rs, reverse=True)[5:]), 1),
        "top5_share_pct": (round(100.0 * sum(sorted(rs, reverse=True)[:max(1, n // 20)])
                                   / max(sum(rs), 1e-9), 1) if sum(rs) > 0 else None),
        "yrs": years,
    }



