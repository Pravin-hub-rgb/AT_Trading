"""BTC position engine — entries on swing breaks, SL/trailing/breakeven.

Continuous-market adaptation of the intraday position-management core
(entry -> protective SL -> target/trail -> exit). No session logic.

Signal model (matches the swing chain from btc_swing):
    - each swing carries its B1/B2/FLIP break marks with a direction
    - a swing's decisive break points in the swing's own direction, so
      a break with dir="up"   -> LONG signal  (up-break of an up-swing)
      a break with dir="down" -> SHORT signal (down-break of a down-swing)
    - entry price = close of the break bar (break confirmed on bar close)

Risk model:
    - sl_mode="swing": SL at the triggering swing's START extreme (the origin
      of the leg: down-swing's start high for shorts, up-swing's start low
      for longs). sl_mode="pct": fixed percent beyond entry.
    - rr_target: fixed R target (used when trailing="off")
    - breakeven_r: once price travels breakeven_r * risk in favor, SL moves
      to entry (0 = off)
    - trailing: "off" | "r" (SL trails the favorable extreme at
      trail_distance_r * risk) | "swing" (SL trails to confirmed swing
      pivots in the trade's favor)
    - one position at a time; signals during an open position are ignored
    - conservative fills: SL checked before target on the same bar; exits
      use the SL as of the PREVIOUS bar (updates apply after exit checks)
"""
from __future__ import annotations

import bisect
from typing import Optional


def _collect_signals(
    swings: list[dict],
    entry_break: str,
    skip_first: bool = True,
    selection: str = "stream",
    candles: Optional[list[dict]] = None,
) -> list[dict]:
    """Entry signals from swing break marks.

    selection="stream" (default, LIVE-FAITHFUL): every B2/FLIP mark is an
        entry signal in the mark's OWN direction, in chronological order.
        This mirrors live trading: at any bar you only know the marks that
        have FIRED so far - never the swing's final break_kind.
        SL = the origin pivot of the leg the mark confirmed:
          - mark dir == swing dir  -> this swing's start pivot
          - opposite-dir mark (state churn) -> the previous swing's end
            pivot (the opposite extreme where that leg began)
        Marks that fire BEFORE their swing's declared start are NOT skipped
        when `candles` is supplied: a same-direction B2/FLIP that fires in
        the pre-start churn is a REAL live signal (it breaks the PREVIOUS
        leg's extreme), so its SL is the touchable extreme since that leg's
        end — the low since prev_end for a LONG, the high since prev_end for
        a SHORT. (This is exactly what a live engine at that bar would see.)

    selection="final" (legacy, research only): one entry per swing at the
        last mark matching the swing's FINAL break_kind. Retrospective
        selection (the final kind depends on later marks) - kept solely to
        reproduce the old sweep numbers.

    skip_first=True: the first swing of the chain only establishes structure.
    """
    tradeable = {
        "decisive": ("B2", "FLIP"),
        "b2": ("B2",),
        "flip": ("FLIP",),
    }.get(entry_break, ("B2", "FLIP"))
    out: list[dict] = []
    seen: set = set()
    for si, s in enumerate(swings):
        if skip_first and int(s.get("swing_index", 0)) < 1:
            continue
        brks = s.get("breaks") or []
        if not brks:
            continue
        sdir = 1 if s.get("dir") == "up" else -1
        seg_start = float(s["seg"]["start_px"])
        seg_end = float(s["seg"]["end_px"])
        prev_start = (
            float(swings[si - 1]["seg"]["start_px"]) if si > 0 else None
        )
        prev_end = (
            float(swings[si - 1]["seg"]["end_px"]) if si > 0 else None
        )
        start_idx = int(s["seg"]["start_idx"])
        prev_start_idx = (
            int(swings[si - 1]["seg"]["start_idx"]) if si > 0 else -1
        )
        prev_end_idx = (
            int(swings[si - 1]["seg"]["end_idx"]) if si > 0 else -1
        )
        # ONE SWING ONE TRADE (14 Jan 21:30 fix): we already took B2 at 17:30 from this swing,
        # so 19:00 FLIP + 21:30 FLIP from SAME swing must be ignored — otherwise same swing gives 3 trades.
        # Keep only the earliest chronological tradeable mark per swing (live: you trade the first B2/FLIP you see).
        first_added_for_this_swing = False
        for b in brks:
            if first_added_for_this_swing:
                break  # one swing one trade — ignore later marks from same swing
            if b["kind"] not in tradeable:
                continue
            bdir = 1 if b["dir"] == "up" else -1
            bidx = int(b["idx"])
            if selection == "final":
                # legacy: only the mark matching the swing's FINAL break_kind
                if b["kind"] != s.get("break_kind"):
                    continue
                sl = seg_start
            else:
                # live-faithful: trade the mark in its own direction
                if bdir == sdir:
                    if bidx < start_idx:
                        # pre-start churn mark. The mark is a REAL live signal
                        # only when we can pin its stop to the leg it broke:
                        # the LOW since the previous swing's end (LONG) or the
                        # HIGH since the previous swing's end (SHORT).
                        if candles is None or si == 0 or prev_end_idx < 0:
                            continue
                        lo_seg = [float(c["low"]) for c in candles[prev_end_idx + 1 : bidx + 1]]
                        hi_seg = [float(c["high"]) for c in candles[prev_end_idx + 1 : bidx + 1]]
                        if not lo_seg or not hi_seg:
                            continue
                        entry_px = float(candles[bidx]["close"])
                        if bdir == 1:  # LONG: SL = lowest low since prev end
                            sl = min(lo_seg)
                            if sl >= entry_px:
                                continue  # degenerate — can't stop below entry
                        else:  # SHORT: SL = highest high since prev end
                            sl = max(hi_seg)
                            if sl <= entry_px:
                                continue  # degenerate — can't stop above entry
                    else:
                        sl = seg_start
                else:
                    # opposite-direction break: we are fading the PREVIOUS leg.
                    # User's live logic: SL = highest high / lowest low SINCE the
                    # leg started (e.g. 14 Jan 11:30 short: from 08:00 to 11:30 the
                    # highest is 10:30 high 95465, not 07:45 high 95281). So we use
                    # touchable extreme since prev_end (max high for SHORT / min low
                    # for LONG) — same as pre-start churn. This fixes both 13 Jan
                    # 20:00 repaint and 14 Jan 11:30 SL.
                    if prev_end is None or bidx < prev_end_idx:
                        continue  # churn before the opposite leg's end pivot
                    sl = prev_end
                    if candles is not None and prev_end_idx >= 0:
                        try:
                            entry_px_chk = float(candles[bidx]["close"])
                            lo_seg = [float(c["low"]) for c in candles[prev_end_idx + 1 : bidx + 1]]
                            hi_seg = [float(c["high"]) for c in candles[prev_end_idx + 1 : bidx + 1]]
                            if lo_seg and hi_seg:
                                if bdir == 1:  # LONG needs sl < entry
                                    cand = min(lo_seg)
                                    if cand < entry_px_chk:
                                        sl = cand  # touchable low since prev_end (live)
                                else:  # SHORT needs sl > entry
                                    cand = max(hi_seg)
                                    if cand > entry_px_chk:
                                        sl = cand  # highest high since prev_end (e.g. 10:30 high for 11:30)
                        except Exception:
                            pass
            key = (bidx, b["kind"], b["dir"], round(float(b["px"]), 6))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "bar": int(b["idx"]),
                    "dir": bdir,
                    "swing_start_px": sl,
                    "swing_no": int(s.get("swing_index", si)),
                    "kind": b["kind"],
                }
            )
            first_added_for_this_swing = True
    out.sort(key=lambda x: x["bar"])
    return out


def _trail_events(swings: list[dict], direction: int) -> list[tuple[int, float]]:
    """(confirmed_at_idx, pivot_px) events for swing-trailing.

    LONG  trails to UP-swing START lows (pivot lows, ratchet up)
    SHORT trails to DOWN-swing START highs (pivot highs, ratchet down)
    """
    want_dir = "up" if direction == 1 else "down"
    ev = [
        (int(s["confirmed_at_idx"]), float(s["seg"]["start_px"]))
        for s in swings
        if s.get("dir") == want_dir and int(s.get("confirmed_at_idx", -1)) >= 0
    ]
    ev.sort(key=lambda x: x[0])
    return ev


def _exit_on_fine(
    fine: list[dict],
    start: int,
    direction: int,
    entry: float,
    sl0: float,
    sl_cur: float,
    target: float,
    risk: float,
    trailing: str,
    trail_distance_r: float,
    breakeven_r: float,
    events: list[tuple[int, float]],
) -> tuple[Optional[int], Optional[float], str]:
    """1m-precise exit resolution for ONE trade.

    Walks the fine (1m) candles from index `start` with the same conservative
    rules as the signal-TF walk:
      - exit checks use the SL as of the PREVIOUS bar (updates apply after)
      - SL checked before the target inside a bar (worst-case intrabar order)
      - gap realism: fill at the bar open when it opens beyond the stop
      - swing-trail pivots ratchet only when they sit beyond the current bar
        extreme (below-market for longs, above-market for shorts)

    events: (active_from_ts, pivot_px) — a pivot level arms for exits from the
    fine bar at/after its activation ts (the HTF bar AFTER its confirmation).

    Returns (exit_fine_idx, exit_px, outcome); (None, None, "open") when the
    fine data ends before an exit triggers.
    """
    best = entry
    ev_idx = -1
    for k in range(start, len(fine)):
        c = fine[k]
        hi, lo = float(c["high"]), float(c["low"])
        ts = int(c["ts"])
        if direction == 1:
            if lo <= sl_cur:
                fill = min(sl_cur, float(c["open"]))
                outcome = ("sl" if sl_cur <= sl0
                           else "be" if abs(sl_cur - entry) <= 1e-9 else "trail")
                return k, fill, outcome
            if trailing == "off" and hi >= target:
                return k, target, "target"
            if breakeven_r > 0 and hi >= entry + breakeven_r * risk and sl_cur < entry:
                sl_cur = entry
            if trailing == "r":
                best = max(best, hi)
                sl_cur = max(sl_cur, best - trail_distance_r * risk)
            elif trailing == "swing":
                while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= ts:
                    ev_idx += 1
                    cand = events[ev_idx][1]
                    if sl_cur < cand < lo:
                        sl_cur = cand
        else:
            if hi >= sl_cur:
                fill = max(sl_cur, float(c["open"]))
                outcome = ("sl" if sl_cur >= sl0
                           else "be" if abs(sl_cur - entry) <= 1e-9 else "trail")
                return k, fill, outcome
            if trailing == "off" and lo <= target:
                return k, target, "target"
            if breakeven_r > 0 and lo <= entry - breakeven_r * risk and sl_cur > entry:
                sl_cur = entry
            if trailing == "r":
                best = min(best, lo)
                sl_cur = min(sl_cur, best + trail_distance_r * risk)
            elif trailing == "swing":
                while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= ts:
                    ev_idx += 1
                    cand = events[ev_idx][1]
                    if hi < cand < sl_cur:
                        sl_cur = cand
    return None, None, "open"


def simulate_btc_trades(
    candles: list[dict],
    swings: list[dict],
    *,
    entry_break: str = "decisive",
    sl_mode: str = "swing",
    sl_pct: float = 0.5,
    rr_target: float = 3.0,
    trailing: str = "off",
    trail_distance_r: float = 1.0,
    breakeven_r: float = 1.0,
    skip_first: bool = True,
    bias_timeline: Optional[list[tuple[int, str]]] = None,
    day_gate: Optional[dict[str, Optional[str]]] = None,
    fine: Optional[list[dict]] = None,
    entry_selection: str = "stream",
) -> list[dict]:
    """Run the position engine over a candle window + its swing chain.

    candles: chart-window candle dicts (date/ts/open/high/low/close) —
             indices are window positions, matching swing/break idx values.
    skip_first: first swing of the chain establishes structure only (FS/bias
             role) — entries start from swing #2 onward.
    bias_timeline: optional higher-TF bias [(confirmed_ts, "up"|"down")]
             sorted ascending (e.g. 15m swings for 1m/5m trading). LONGs
             need the last confirmed bias "up", SHORTs need "down" — the
             BTC analog of Nifty's pre-open bias gate. None = no bias gate.
    day_gate: optional per-calendar-day regime gate {date: "long"|"short"}
             (e.g. the 3-1-1 daily-color streak regime). A signal whose day
             gate disagrees with its direction is skipped. Missing date or
             None value = no trade that day (pause). None = no gate.
    fine: optional 1m candles (same keys as `candles`) covering the window.
             When given, EXITS resolve minute-by-minute (SL/target/trail/BE
             checked on 1m bars — no hidden intrabar stops), while entries
             stay at the signal bar's close (already 1m-precise). None =
             exit resolution on the signal TF itself.

    Returns a list of trade dicts (chronological).
    """
    n = len(candles)
    if n == 0:
        return []
    signals = _collect_signals(
        swings, entry_break, skip_first=skip_first, selection=entry_selection,
        candles=candles if entry_selection == "stream" else None,
    )

    candle_ts = [int(c["ts"]) for c in candles]
    fine_ts = [int(c["ts"]) for c in fine] if fine else []

    # advance-on-demand pointer into the bias timeline
    bias_ptr = -1
    bias_now: Optional[str] = None

    trades: list[dict] = []
    busy_until = -1  # a signal at bar <= busy_until lands inside an open trade

    for sig in signals:
        i = sig["bar"]
        if i <= busy_until or i >= n - 1:
            continue  # in-position signal, or no forward bars to manage

        direction: int = sig["dir"]
        if day_gate is not None:
            g = day_gate.get(candles[i]["date"][:10])
            if g != ("long" if direction == 1 else "short"):
                continue  # regime gate disagrees (or pause day) — no trade
        bar_ts = int(candles[i]["ts"])
        while bias_ptr + 1 < len(bias_timeline or []) and bias_timeline[bias_ptr + 1][0] <= bar_ts:
            bias_ptr += 1
            bias_now = bias_timeline[bias_ptr][1]
        if bias_timeline is not None:
            want = "up" if direction == 1 else "down"
            if bias_now != want:
                continue  # trade direction not aligned with higher-TF bias

        entry = float(candles[i]["close"])

        if direction == 1:
            sl = (
                sig["swing_start_px"] if sl_mode == "swing"
                else entry * (1.0 - sl_pct / 100.0)
            )
            if sl >= entry:
                continue  # degenerate risk
            risk = entry - sl
            # rounding-artifact floor: CSVs round prices to 2dp, so a swing
            # start_px and the entry close can collide to the same number and
            # yield a 0.0x-point stop. That is not a tradeable stop — skip.
            if risk < 0.0005 * entry:
                continue
            target = entry + rr_target * risk
        else:
            sl = (
                sig["swing_start_px"] if sl_mode == "swing"
                else entry * (1.0 + sl_pct / 100.0)
            )
            if sl <= entry:
                continue
            risk = sl - entry
            if risk < 0.0005 * entry:
                continue
            target = entry - rr_target * risk

        sl0 = sl
        sl_cur = sl
        best = entry  # favorable extreme since entry
        ev_idx = -1  # pointer into trail events
        events = _trail_events(swings, direction) if trailing == "swing" else []
        exit_idx: Optional[int] = None
        exit_px: Optional[float] = None
        outcome = "open"
        exit_ts: Optional[int] = None
        exit_date: Optional[str] = None

        # When fine (1m) candles are supplied the HTF walk below is skipped
        # (zero-length range) and exits resolve minute-by-minute instead.
        for j in range(i + 1, n if not fine else i + 1):
            c = candles[j]
            hi, lo = float(c["high"]), float(c["low"])

            if direction == 1:
                # exits first (SL as of previous bar), conservative.
                # Gap realism: if the bar opens beyond the stop, fill at the
                # open (worse), never at an untraded stop level.
                if lo <= sl_cur:
                    fill = min(sl_cur, float(c["open"]))
                    exit_idx, exit_px = j, fill
                    if sl_cur <= sl0:
                        outcome = "sl"
                    elif abs(sl_cur - entry) <= 1e-9:
                        outcome = "be"
                    else:
                        outcome = "trail"
                    break
                if trailing == "off" and hi >= target:
                    exit_idx, exit_px, outcome = j, target, "target"
                    break
                # updates apply after exit checks
                if breakeven_r > 0 and hi >= entry + breakeven_r * risk and sl_cur < entry:
                    sl_cur = entry
                if trailing == "r":
                    best = max(best, hi)
                    sl_cur = max(sl_cur, best - trail_distance_r * risk)
                elif trailing == "swing":
                    while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                        ev_idx += 1
                        # skip trail events that confirmed BEFORE the entry —
                        # those pivots pre-date the trade and must not ratchet
                        # the SL (bug: 10 Jan 2025 23:15 LONG was exiting at
                        # -0.39R via a pre-entry pivot instead of holding to
                        # the real SL at -1.0R).
                        if events[ev_idx][0] < i:
                            continue
                        cand = events[ev_idx][1]
                        # ratchet up, BELOW-market pivots only — a stale pivot
                        # above price is not a stop, it's a phantom fill
                        if sl_cur < cand < lo:
                            sl_cur = cand
            else:
                if hi >= sl_cur:
                    fill = max(sl_cur, float(c["open"]))
                    exit_idx, exit_px = j, fill
                    if sl_cur >= sl0:
                        outcome = "sl"
                    elif abs(sl_cur - entry) <= 1e-9:
                        outcome = "be"
                    else:
                        outcome = "trail"
                    break
                if trailing == "off" and lo <= target:
                    exit_idx, exit_px, outcome = j, target, "target"
                    break
                if breakeven_r > 0 and lo <= entry - breakeven_r * risk and sl_cur > entry:
                    sl_cur = entry
                if trailing == "r":
                    best = min(best, lo)
                    sl_cur = min(sl_cur, best + trail_distance_r * risk)
                elif trailing == "swing":
                    while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                        ev_idx += 1
                        # skip trail events that confirmed BEFORE the entry —
                        # those pivots pre-date the trade and must not ratchet
                        # the SL (bug: 10 Jan 2025 23:15 LONG was exiting at
                        # -0.39R via a pre-entry pivot instead of holding to
                        # the real SL at -1.0R).
                        if events[ev_idx][0] < i:
                            continue
                        cand = events[ev_idx][1]
                        # ratchet down, ABOVE-market pivots only
                        if hi < cand < sl_cur:
                            sl_cur = cand
# CONTINUE_MARKER
        if fine:
            # 1m-precise exits: signals remain on the chart TF, but SL /
            # target / trail / breakeven fills are checked minute by minute.
            # Filter out trail events that confirmed BEFORE the entry — those
            # pivots pre-date the trade and must not ratchet the SL (bug:
            # 10 Jan 2025 23:15 LONG was exiting at -0.39R via a pre-entry
            # pivot instead of holding to the real SL at -1.0R).
            events_ts = (
                [(candle_ts[min(e + 1, n - 1)], px) for e, px in events
                 if candle_ts[min(e + 1, n - 1)] > bar_ts]
                if trailing == "swing" else []
            )
            f_start = bisect.bisect_left(fine_ts, candle_ts[i + 1])
            fk, exit_px_f, outcome_f = _exit_on_fine(
                fine, f_start, direction, entry, sl0, sl_cur, target, risk,
                trailing, trail_distance_r, breakeven_r, events_ts,
            )
            if fk is None:
                # fine data ended before an exit — mark to last fine close
                outcome = "open"
                exit_idx = n - 1
                exit_px = float(fine[-1]["close"])
                exit_ts = int(fine[-1]["ts"])
                exit_date = fine[-1].get("date") or candles[-1]["date"]
            else:
                outcome = outcome_f
                exit_px = exit_px_f
                exit_ts = int(fine[fk]["ts"])
                exit_date = fine[fk].get("date")
                exit_idx = bisect.bisect_right(candle_ts, exit_ts) - 1
                exit_idx = max(0, min(exit_idx, n - 1))
                if not exit_date:
                    exit_date = candles[exit_idx]["date"]
        elif exit_idx is None:
            # still open at window end — mark to last close
            exit_idx = n - 1
            exit_px = float(candles[-1]["close"])
            outcome = "open"

        if not fine:
            exit_ts = int(candles[exit_idx]["ts"])
            exit_date = candles[exit_idx]["date"]

        move = (exit_px - entry) if direction == 1 else (entry - exit_px)
        r_multiple = move / risk if risk > 0 else 0.0

        trades.append(
            {
                "trade_no": len(trades) + 1,
                "dir": "long" if direction == 1 else "short",
                "swing_no": sig["swing_no"],
                "break_kind": sig["kind"],
                "entry_idx": i,
                "entry_ts": int(candles[i]["ts"]),
                "entry_date": candles[i]["date"],
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
            }
        )
        busy_until = exit_idx

    return trades


def trade_stats(trades: list[dict]) -> dict:
    """Summary stats + R equity curve over CLOSED trades — now with streaks, PF, DD duration."""
    closed = [t for t in trades if t["outcome"] != "open"]
    rs = [t["r_multiple"] for t in closed]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]

    equity: list[dict] = []
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    peak_idx = 0
    max_dd_start = 0
    max_dd_end = 0
    max_dd_duration_bars = 0
    # For DD duration: track peak cum and when maxDD occurred
    cum_history: list[float] = []
    for k, r in enumerate(rs, start=1):
        cum += r
        cum_history.append(cum)
        if cum > peak:
            peak = cum
            peak_idx = k
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
            max_dd_start = peak_idx
            max_dd_end = k
            max_dd_duration_bars = k - peak_idx
        equity.append({"trade_no": k, "cum_r": round(cum, 3)})

    # Streaks
    max_consec_losses = 0
    max_consec_wins = 0
    cur_losses = 0
    cur_wins = 0
    for r in rs:
        if r <= 0:
            cur_losses += 1
            cur_wins = 0
            max_consec_losses = max(max_consec_losses, cur_losses)
        else:
            cur_wins += 1
            cur_losses = 0
            max_consec_wins = max(max_consec_wins, cur_wins)

    # Profit factor and payoff
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else 0.0
    payoff = round((gross_win / len(wins)) / (gross_loss / len(losses)) if wins and losses else 0.0, 2)
    expectancy = round(sum(rs) / len(rs), 3) if rs else 0.0

    # Cost-aware (net) extended stats: median, top-N contributions, time
    # buckets, rolling windows. cost_r is set by _trade_costs before this call
    # in the routes flow; when absent, net == gross (engines' internal calls).
    net_rs = [float(t["r_multiple"]) - float(t.get("cost_r", 0.0)) for t in closed]
    net_total = round(sum(net_rs), 2)

    _srt = sorted(net_rs)
    median_r = round((_srt[len(_srt) // 2] if len(_srt) % 2 == 1
                      else (_srt[len(_srt) // 2 - 1] + _srt[len(_srt) // 2]) / 2.0), 3) if _srt else 0.0

    _top_sorted = sorted(net_rs, reverse=True)
    tops: dict = {}
    for _k in (1, 5, 10):
        _top = round(sum(_top_sorted[:_k]), 2)
        tops[f"top{_k}_contribution_r"] = _top
        tops[f"top{_k}_contribution_pct"] = (round(100.0 * _top / net_total, 1) if net_total > 0 else None)

    # Time buckets by EXIT month/year (net R, costs included)
    monthly: dict[str, float] = {}
    yearly: dict[str, float] = {}
    for _t, _nr in zip(closed, net_rs):
        _ed = str(_t.get("exit_date", "") or "")
        if len(_ed) >= 7:
            monthly[_ed[:7]] = round(monthly.get(_ed[:7], 0.0) + _nr, 2)
        if len(_ed) >= 4:
            yearly[_ed[:4]] = round(yearly.get(_ed[:4], 0.0) + _nr, 2)
    monthly = dict(sorted(monthly.items()))
    yearly = dict(sorted(yearly.items()))

    monthly_equity: list[dict] = []
    _cum_m = 0.0
    for _m, _nr in monthly.items():
        _cum_m += _nr
        monthly_equity.append({"month": _m, "net_r": _nr, "cum_r": round(_cum_m, 2)})

    def _rolling(w: int) -> tuple[list[dict], float, float, float]:
        roll = []
        for _k in range(1, len(net_rs) + 1):
            roll.append({"trade_no": _k, "net_r": round(sum(net_rs[max(0, _k - w):_k]), 2)})
        _vals = [x["net_r"] for x in roll]
        return (roll, min(_vals) if _vals else 0.0, max(_vals) if _vals else 0.0,
                _vals[-1] if _vals else 0.0)

    roll20, r20_min, r20_max, r20_last = _rolling(20)
    roll50, r50_min, r50_max, r50_last = _rolling(50)

    # Avg bars held
    bars_held = [int(t.get("bars_held", 0)) for t in closed]
    avg_bars = round(sum(bars_held) / len(bars_held), 1) if bars_held else 0.0
    max_bars = max(bars_held) if bars_held else 0

    # DD duration in trades and estimated days (for 1h TF, 24 bars =1 day; for 15m 96 bars =1 day)
    # We report DD duration as number of trades in drawdown, and also bars
    # For time-based DD duration, we can estimate via bars_held sum? Simpler: use max_dd_duration_bars as trade count in DD
    # Also compute max losing streak duration in R
    return {
        "trades": len(trades),
        "closed": len(closed),
        "open": len(trades) - len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(100.0 * len(wins) / len(closed), 1) if closed else 0.0,
        "total_r": round(sum(rs), 2),
        "avg_r": round(sum(rs) / len(rs), 3) if rs else 0.0,
        "avg_win_r": round(sum(wins) / len(wins), 3) if wins else 0.0,
        "avg_loss_r": round(sum(losses) / len(losses), 3) if losses else 0.0,
        "profit_factor": profit_factor,
        "payoff": payoff,
        "expectancy": expectancy,
        "max_drawdown_r": round(max_dd, 2),
        "max_drawdown_duration_trades": max_dd_duration_bars,
        "max_drawdown_start": max_dd_start,
        "max_drawdown_end": max_dd_end,
        "max_consecutive_losses": max_consec_losses,
        "max_consecutive_wins": max_consec_wins,
        "avg_bars_held": avg_bars,
        "max_bars_held": max_bars,
        "longs": sum(1 for t in trades if t["dir"] == "long"),
        "shorts": sum(1 for t in trades if t["dir"] == "short"),
        "outcomes": _outcome_counts(trades),
        "equity": equity,
        # cost-aware extended stats (net = r_multiple - cost_r when present)
        "median_r": median_r,
        "top1_contribution_r": tops["top1_contribution_r"],
        "top5_contribution_r": tops["top5_contribution_r"],
        "top10_contribution_r": tops["top10_contribution_r"],
        "top1_contribution_pct": tops["top1_contribution_pct"],
        "top5_contribution_pct": tops["top5_contribution_pct"],
        "top10_contribution_pct": tops["top10_contribution_pct"],
        "monthly_r": monthly,
        "yearly_r": yearly,
        "monthly_equity": monthly_equity,
        "rolling_20": roll20,
        "rolling_20_min": r20_min,
        "rolling_20_max": r20_max,
        "rolling_20_last": r20_last,
        "rolling_50": roll50,
        "rolling_50_min": r50_min,
        "rolling_50_max": r50_max,
        "rolling_50_last": r50_last,
    }


def _outcome_counts(trades: list[dict]) -> dict[str, int]:
    """Outcome histogram (all trades, incl. open) sorted by count desc."""
    counts: dict[str, int] = {}
    for t in trades:
        o = t["outcome"]
        counts[o] = counts.get(o, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

