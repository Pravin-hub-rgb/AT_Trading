"""BTC sweep harness — core grid + crazy-idea filters over the real engine.

Data:    data/btc/BTCUSDT_5m.csv (full series, continuous 24/7) + 15m for bias
Engine:  backend/src/btc/btc_swing.compute_btc_swings (parity-tested SwingEngine)
Sim:     mirrors backend/src/btc/btc_engine.simulate_btc_trades + filter gates:
             - leg-size filter (swing leg in ATR multiples)
             - EMA regime gate (long above / short below)
             - 15m higher-TF bias gate (last confirmed 15m swing dir)
             - daily-color streak regime gate (3-1-1: fade break, pause, flip)
             - session-hour windows (BTC 24/7 — does hour matter?)
             - decisive-break distance (close beyond pivot by >= k*ATR)

Run:  backend/venv/Scripts/python.exe fix/btc_sweep.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd  # noqa: E402

from src.btc.btc_config import load_btc_df  # noqa: E402
from src.btc.btc_swing import compute_btc_swings  # noqa: E402
from src.walker import FlowCandle  # noqa: E402

# ── data ─────────────────────────────────────────────────────────────────────


def build(df: pd.DataFrame):
    candles: list[dict] = []
    flow: list[FlowCandle] = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        candles.append({"date": date, "ts": int(row.ts), "open": o, "high": h, "low": l, "close": c})
        flow.append(FlowCandle(date=date, open=o, high=h, low=l, close=c))
    return candles, flow


def atr_series(df: pd.DataFrame, n: int = 14) -> list[float]:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().bfill().tolist()


def ema_series(df: pd.DataFrame, span: int) -> list[float]:
    return df["close"].ewm(span=span, adjust=False).mean().tolist()


def daily_colors(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    d = df.copy()
    d["day"] = d["timestamp"].dt.strftime("%Y-%m-%d")
    g = d.groupby("day", sort=True).agg(open=("open", "first"), close=("close", "last"))
    days = list(g.index)
    colors = ["g" if float(r.close) >= float(r.open) else "r" for r in g.itertuples()]
    return days, colors


def streak_regime_gate(days: list[str], colors: list[str]) -> dict[str, Optional[str]]:
    """3-1-1 streak regime (ideas.md §7): trade regime; on color-break day keep
    old regime; next day PAUSE (no trades) and flip regime to pause-day color."""
    gate: dict[str, Optional[str]] = {}
    if not days:
        return gate
    regime = "long" if colors[0] == "g" else "short"
    pause = False
    for day, c in zip(days, colors):
        col = "long" if c == "g" else "short"
        if pause:
            gate[day] = None
            regime = col
            pause = False
            continue
        gate[day] = regime
        if col != regime:
            pause = True
    return gate


# ── signals ──────────────────────────────────────────────────────────────────


def collect_signals(swings: list[dict], entry_break: str, skip_first: bool = True) -> list[dict]:
    out: list[dict] = []
    for s in swings:
        if skip_first and int(s.get("swing_index", 0)) < 1:
            continue
        brks = s.get("breaks") or []
        if not brks:
            continue
        trig: Optional[dict] = None
        if entry_break == "decisive":
            bk = s.get("break_kind")
            if bk:
                for b in brks:
                    if b["kind"] == bk:
                        trig = b
        elif entry_break == "b2":
            trig = next((b for b in brks if b["kind"] == "B2"), None)
        elif entry_break == "flip":
            trig = next((b for b in brks if b["kind"] == "FLIP"), None)
        if trig is None:
            continue
        out.append(
            {
                "bar": int(trig["idx"]),
                "dir": 1 if trig["dir"] == "up" else -1,
                "start_px": float(s["seg"]["start_px"]),
                "end_px": float(s["seg"]["end_px"]),
                "swing_no": int(s["swing_index"]),
                "kind": trig["kind"],
            }
        )
    out.sort(key=lambda x: x["bar"])
    return out


def trail_events(swings: list[dict], direction: int) -> list[tuple[int, float]]:
    want = "up" if direction == 1 else "down"
    ev = [
        (int(s["confirmed_at_idx"]), float(s["seg"]["start_px"]))
        for s in swings
        if s.get("dir") == want and int(s.get("confirmed_at_idx", -1)) >= 0
    ]
    ev.sort(key=lambda x: x[0])
    return ev


# ── simulator (engine core + filter gates) ──────────────────────────────────


def sim(
    candles: list[dict],
    swings: list[dict],
    signals: list[dict],
    *,
    sl_mode: str = "swing",
    sl_pct: float = 0.5,
    rr: float = 3.0,
    trailing: str = "off",
    trail_r: float = 1.0,
    be: float = 1.0,
    atr: Optional[list[float]] = None,
    min_leg_atr: float = 0.0,
    max_leg_atr: Optional[float] = None,
    ema: Optional[list[float]] = None,
    min_break_atr: float = 0.0,
    hour_win: Optional[tuple[str, str]] = None,
    bias15: Optional[list[tuple[int, str]]] = None,
    day_gate: Optional[dict[str, Optional[str]]] = None,
) -> list[dict]:
    n = len(candles)
    trades: list[dict] = []
    busy_until = -1
    bias_ptr = -1
    bias_now: Optional[str] = None

    for sig in signals:
        i = sig["bar"]
        if i <= busy_until or i >= n - 1:
            continue
        direction: int = sig["dir"]

        # ── filter gates ──
        if atr is not None and (min_leg_atr > 0 or max_leg_atr is not None):
            a = atr[i]
            if a and a > 0:
                leg = abs(sig["end_px"] - sig["start_px"]) / a
                if leg < min_leg_atr:
                    continue
                if max_leg_atr is not None and leg > max_leg_atr:
                    continue
        if ema is not None:
            c0 = candles[i]["close"]
            if direction == 1 and not c0 > ema[i]:
                continue
            if direction == -1 and not c0 < ema[i]:
                continue
        if min_break_atr > 0 and atr is not None and atr[i] > 0:
            excess = (candles[i]["close"] - sig["start_px"]) * direction
            if excess < min_break_atr * atr[i]:
                continue
        if hour_win is not None:
            t = candles[i]["date"][11:16]
            a, b = hour_win
            ok = (t >= a and t < b) if a <= b else (t >= a or t < b)
            if not ok:
                continue
        if day_gate is not None:
            g = day_gate.get(candles[i]["date"][:10])
            if g != ("long" if direction == 1 else "short"):
                continue
        if bias15 is not None:
            bar_ts = int(candles[i]["ts"])
            while bias_ptr + 1 < len(bias15) and bias15[bias_ptr + 1][0] <= bar_ts:
                bias_ptr += 1
                bias_now = bias15[bias_ptr][1]
            if bias_now != ("up" if direction == 1 else "down"):
                continue

        # ── risk ──
        entry = float(candles[i]["close"])
        if direction == 1:
            sl = sig["start_px"] if sl_mode == "swing" else entry * (1.0 - sl_pct / 100.0)
            if sl >= entry:
                continue
            risk = entry - sl
            target = entry + rr * risk
        else:
            sl = sig["start_px"] if sl_mode == "swing" else entry * (1.0 + sl_pct / 100.0)
            if sl <= entry:
                continue
            risk = sl - entry
            target = entry - rr * risk

        sl0 = sl_cur = sl
        best = entry
        ev_idx = -1
        events = trail_events(swings, direction) if trailing == "swing" else []
        exit_idx: Optional[int] = None
        exit_px: Optional[float] = None
        outcome = "open"

        for j in range(i + 1, n):
            c = candles[j]
            hi, lo = float(c["high"]), float(c["low"])
            if direction == 1:
                if lo <= sl_cur:
                    exit_idx, exit_px = j, min(sl_cur, float(c["open"]))
                    outcome = "sl" if sl_cur <= sl0 else ("be" if abs(sl_cur - entry) <= 1e-9 else "trail")
                    break
                if trailing == "off" and hi >= target:
                    exit_idx, exit_px, outcome = j, target, "target"
                    break
                if be > 0 and hi >= entry + be * risk and sl_cur < entry:
                    sl_cur = entry
                if trailing == "r":
                    best = max(best, hi)
                    sl_cur = max(sl_cur, best - trail_r * risk)
                elif trailing == "swing":
                    while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                        ev_idx += 1
                        cand = events[ev_idx][1]
                        if sl_cur < cand < lo:
                            sl_cur = cand
            else:
                if hi >= sl_cur:
                    exit_idx, exit_px = j, max(sl_cur, float(c["open"]))
                    outcome = "sl" if sl_cur >= sl0 else ("be" if abs(sl_cur - entry) <= 1e-9 else "trail")
                    break
                if trailing == "off" and lo <= target:
                    exit_idx, exit_px, outcome = j, target, "target"
                    break
                if be > 0 and lo <= entry - be * risk and sl_cur > entry:
                    sl_cur = entry
                if trailing == "r":
                    best = min(best, lo)
                    sl_cur = min(sl_cur, best + trail_r * risk)
                elif trailing == "swing":
                    while ev_idx + 1 < len(events) and events[ev_idx + 1][0] <= j:
                        ev_idx += 1
                        cand = events[ev_idx][1]
                        if hi < cand < sl_cur:
                            sl_cur = cand

        if exit_idx is None:
            exit_idx = n - 1
            exit_px = float(candles[-1]["close"])
            outcome = "open"

        move = (exit_px - entry) if direction == 1 else (entry - exit_px)
        trades.append(
            {
                "dir": "long" if direction == 1 else "short",
                "kind": sig["kind"],
                "outcome": outcome,
                "r": move / risk if risk > 0 else 0.0,
            }
        )
        busy_until = exit_idx
    return trades


def stats(trades: list[dict]) -> dict:
    closed = [t for t in trades if t["outcome"] != "open"]
    rs = [t["r"] for t in closed]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gross_w = sum(wins)
    gross_l = abs(sum(losses))
    counts: dict[str, int] = {}
    for t in trades:
        counts[t["outcome"]] = counts.get(t["outcome"], 0) + 1
    oc = " ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    return {
        "trades": len(trades),
        "winrate": 100.0 * len(wins) / len(closed) if closed else 0.0,
        "total_r": sum(rs),
        "avg_r": sum(rs) / len(rs) if rs else 0.0,
        "pf": gross_w / gross_l if gross_l > 0 else float("inf"),
        "ls": (sum(1 for t in trades if t["dir"] == "long"), sum(1 for t in trades if t["dir"] == "short")),
        "oc": oc,
    }


def fmt(name: str, s: dict) -> str:
    return (
        f"{name:<44} Trades {s['trades']:<5} Win% {s['winrate']:<5.1f} "
        f"TotalR {s['total_r']:+8.2f} Avg {s['avg_r']:+6.3f} PF {s['pf']:<5.2f} "
        f"L/S {s['ls'][0]}/{s['ls'][1]}  [{s['oc']}]"
    )


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    t0 = time.time()
    df5 = load_btc_df("5m")
    candles, flow = build(df5)
    n = len(flow)
    print(f"5m candles: {n}  {candles[0]['date']} -> {candles[-1]['date']}")

    atr = atr_series(df5, 14)
    ema20 = ema_series(df5, 20)
    ema50 = ema_series(df5, 50)
    days, colors = daily_colors(df5)
    gate31 = streak_regime_gate(days, colors)

    # 15m bias timeline (last confirmed 15m swing dir)
    df15 = load_btc_df("15m")
    c15, f15 = build(df15)
    sw15 = compute_btc_swings(f15, max_swings=len(f15) // 2)
    bias15 = sorted(
        (int(c15[s["confirmed_at_idx"]]["ts"]), s["dir"])
        for s in sw15
        if 0 <= int(s.get("confirmed_at_idx", -1)) < len(c15)
    )
    print(f"15m swings: {len(sw15)}  bias timeline events: {len(bias15)}")

    t1 = time.time()
    swings = compute_btc_swings(flow, max_swings=n // 2)
    print(f"5m swings: {len(swings)}  ({time.time() - t1:.1f}s)\n")

    # ── S1: swing structure stats ────────────────────────────────────────────
    print("=" * 110)
    print("S1. SWING STRUCTURE STATS (whole series, continuous chain)")
    print("=" * 110)
    ups = sum(1 for s in swings if s["dir"] == "up")
    print(f"total swings {len(swings)}  up {ups} ({100.0 * ups / len(swings):.1f}%)  down {len(swings) - ups}")
    legs = [abs(s["seg"]["end_px"] - s["seg"]["start_px"]) for s in swings]
    legs_atr = [
        legs[i] / atr[swings[i]["seg"]["end_idx"]] if atr[swings[i]["seg"]["end_idx"]] > 0 else 0.0
        for i in range(len(swings))
    ]
    ls = pd.Series(legs)
    la = pd.Series(legs_atr)
    print(f"leg pts : mean {ls.mean():.0f} median {ls.median():.0f} p25 {ls.quantile(0.25):.0f} p75 {ls.quantile(0.75):.0f} p90 {ls.quantile(0.90):.0f}")
    print(f"leg/ATR : mean {la.mean():.2f} median {la.median():.2f} p25 {la.quantile(0.25):.2f} p75 {la.quantile(0.75):.2f} p90 {la.quantile(0.90):.2f}")
    kinds: dict[str, int] = {}
    for s in swings:
        k = s.get("break_kind") or "none"
        kinds[k] = kinds.get(k, 0) + 1
    print(f"break kinds: {kinds}")
    srcs: dict[str, int] = {}
    for s in swings:
        srcs[s.get("kind", "?")] = srcs.get(s.get("kind", "?"), 0) + 1
    print(f"confirm source: {srcs}")
    same2 = same3 = tot = 0
    for i in range(1, len(swings)):
        tot += 1
        if swings[i]["dir"] == swings[i - 1]["dir"]:
            same2 += 1
    for i in range(2, len(swings)):
        if swings[i]["dir"] == swings[i - 1]["dir"] == swings[i - 2]["dir"]:
            same3 += 1
    print(f"next swing SAME dir as prev: {same2}/{tot} ({100.0 * same2 / tot:.1f}%)  3-in-a-row same: {same3} ({100.0 * same3 / tot:.1f}%)")
    fs = swings[0]
    print(f"first swing: dir {fs['dir']} kind {fs['kind']} leg {abs(fs['seg']['end_px'] - fs['seg']['start_px']):.0f} pts")
    dc_g = sum(1 for c in colors if c == "g")
    print(f"daily candles: {len(days)}  green {dc_g} ({100.0 * dc_g / len(days):.1f}%)  red {len(days) - dc_g}")
    st = 1
    streaks: list[int] = []
    for i in range(1, len(colors)):
        if colors[i] == colors[i - 1]:
            st += 1
        else:
            streaks.append(st)
            st = 1
    streaks.append(st)
    print(f"daily color streaks: mean {sum(streaks) / len(streaks):.2f} max {max(streaks)}  >=3: {sum(1 for x in streaks if x >= 3)}")
    print()

    # ── S2: core param grid ──────────────────────────────────────────────────
    print("=" * 110)
    print("S2. CORE GRID SWEEP — entry_break x sl_mode x rr x trailing x breakeven  (skip_first=True, no filters)")
    print("=" * 110)
    sig_cache: dict[str, list[dict]] = {}
    for eb in ("decisive", "b2", "flip"):
        sig_cache[eb] = collect_signals(swings, eb, skip_first=True)
    results: list[tuple[str, dict]] = []
    for eb in ("decisive", "b2", "flip"):
        for slm, slm_name in (("swing", "slSwing"), ("pct", "sl0.5%")):
            for rr in (2.0, 3.0, 4.0):
                for tr_name, tr_kwargs in (("off", {}), ("r1", {"trailing": "r", "trail_r": 1.0}), ("swing", {"trailing": "swing"})):
                    for be in (0.0, 1.0):
                        tr = sim(candles, swings, sig_cache[eb], sl_mode=slm, rr=rr, be=be, **tr_kwargs)
                        name = f"{eb} {slm_name} rr{rr:.0f} {tr_name} be{be:.0f}"
                        results.append((name, stats(tr)))
    results.sort(key=lambda kv: -kv[1]["total_r"])
    for name, s in results[:20]:
        print(fmt(name, s))
    print("...")
    base = next(s for n2, s in results if n2 == "decisive slSwing rr3 off be1")
    print(fmt("BASELINE (decisive slSwing rr3 off be1)", base))
    print()

    # ── S3: engine params ────────────────────────────────────────────────────
    print("=" * 110)
    print("S3. ENGINE PARAMS — minBars x sustainBars  (core = decisive slSwing rr3 off be1)")
    print("=" * 110)
    for mb in (7, 14, 20):
        for sb in (3, 7, 10):
            sw2 = compute_btc_swings(flow, opts={"minBars": mb, "sustainBars": sb}, max_swings=n // 2)
            sg = collect_signals(sw2, "decisive", skip_first=True)
            s = stats(sim(candles, sw2, sg, sl_mode="swing", rr=3.0, be=1.0))
            tag = "  <-default" if (mb, sb) == (14, 7) else ""
            print(fmt(f"minBars{mb} sustain{sb} (swings {len(sw2)})", s) + tag)
    print()

    # ── S4: crazy filters (fixed baseline core) ──────────────────────────────
    print("=" * 110)
    print("S4. CRAZY FILTERS — fixed core decisive/slSwing/rr3/off/be1, one filter at a time")
    print("=" * 110)
    base_sig = sig_cache["decisive"]
    tests: list[tuple[str, dict]] = [
        ("BASELINE (no filter)", {}),
        ("skip_first=False (trade 1st swing too)", {"_skip_first": False}),
        ("leg >= 1.0 ATR (strong swings only)", {"min_leg_atr": 1.0}),
        ("leg >= 1.5 ATR", {"min_leg_atr": 1.5}),
        ("leg <= 0.5 ATR (weak fade)", {"max_leg_atr": 0.5}),
        ("EMA20 gate (long>/short<)", {"ema": ema20}),
        ("EMA50 gate", {"ema": ema50}),
        ("15m bias gate", {"bias15": bias15}),
        ("daily streak regime 3-1-1", {"day_gate": gate31}),
        ("hours 09:15-15:30 IST only", {"hour_win": ("09:15", "15:30")}),
        ("hours 19:00-01:30 IST (US) only", {"hour_win": ("19:00", "01:30")}),
        ("hours 13:30-01:30 IST (EU+US)", {"hour_win": ("13:30", "01:30")}),
        ("break close >= 0.25 ATR past pivot", {"min_break_atr": 0.25}),
        ("break close >= 0.50 ATR past pivot", {"min_break_atr": 0.50}),
        ("trail r1 (instead of fixed rr3)", {"trailing": "r", "trail_r": 1.0}),
        ("trail r2", {"trailing": "r", "trail_r": 2.0}),
        ("swing trailing", {"trailing": "swing"}),
    ]
    for name, kwargs in tests:
        sf = kwargs.pop("_skip_first", True)
        sg = collect_signals(swings, "decisive", skip_first=sf)
        s = stats(sim(candles, swings, sg, sl_mode="swing", rr=3.0, be=1.0, atr=atr, **kwargs))
        print(fmt(name, s))
    print()

    # ── S5: per-break-kind edge ──────────────────────────────────────────────
    print("=" * 110)
    print("S5. WHICH BREAK KIND PAYS — per-kind trade stats (decisive core, no filters)")
    print("=" * 110)
    all_tr = sim(candles, swings, base_sig, sl_mode="swing", rr=3.0, be=1.0, atr=atr)
    for k in ("B1", "B2", "FLIP"):
        kt = [t for t in all_tr if t["kind"] == k]
        if kt:
            print(fmt(f"entry kind {k}", stats(kt)))
    print()

    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
