"""BTC API routes — chart swings + position-engine backtest (24/7 continuous).

Mounted from server.py via a single app.include_router() call.
BTC-only: no Nifty imports, no session logic, no Upstox dependency.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.btc.btc_config import BTC_TFS, btc_csv_path, load_btc_df
from src.btc.btc_engine import simulate_btc_trades, trade_stats
from src.btc.btc_swing import compute_btc_flow, compute_btc_swings
from src.walker import FlowCandle

# Versioned engines — each isolated, v1 is the default (above)
try:
    from src.btc.engines.v2_chandelier import simulate_btc_trades_v2
except Exception:
    simulate_btc_trades_v2 = None  # type: ignore
try:
    from src.btc.engines.v3_htf_trail import simulate_btc_trades_v3
except Exception:
    simulate_btc_trades_v3 = None  # type: ignore
try:
    from src.btc.engines.v4_partial import simulate_btc_trades_v4
except Exception:
    simulate_btc_trades_v4 = None  # type: ignore
try:
    from src.btc.engines.v5_be1 import simulate_btc_trades_v5
except Exception:
    simulate_btc_trades_v5 = None  # type: ignore
try:
    from src.btc.engines.v6_adx import simulate_btc_trades_v6
except Exception:
    simulate_btc_trades_v6 = None  # type: ignore
try:
    from src.btc.engines.v7_timecap import simulate_btc_trades_v7
except Exception:
    simulate_btc_trades_v7 = None  # type: ignore
try:
    from src.btc.engines.v8_break_entry import simulate_btc_trades_v8
except Exception:
    simulate_btc_trades_v8 = None  # type: ignore
try:
    from src.btc.engines.v9_conditional_cap import simulate_btc_trades_v9
except Exception:
    simulate_btc_trades_v9 = None  # type: ignore
try:
    from src.btc.engines.v10_strength import simulate_btc_trades_v10
except Exception:
    simulate_btc_trades_v10 = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
except Exception:
    simulate_htf_ltf_15m = None  # type: ignore
try:
    from src.btc.engines.htf_ltf.v3_ext_stop import simulate_htf_ltf_ext_stop
except Exception:
    simulate_htf_ltf_ext_stop = None  # type: ignore

BTC_VERSIONS = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10"]
VERSION_LABELS = {
    "v1": "v1 Honest (touchable + one-swing-one-trade) — cap 16d for 1h Flip",
    "v2": "v2 Chandelier ATR k=3.0",
    "v3": "v3 HTF 1h Trail",
    "v4": "v4 Partial 50/50",
    "v5": "v5 BE1 (breakeven 1R)",
    "v6": "v6 ADX>25",
    "v7": "v7 TimeCap 16d (1h Flip)",
    "v8": "v8 Break High/Low + Opposite Cancel",
    "v9": "v9 Conditional Cap 2R→30d",
    "v10": "v10 Flip Strength Body/ATR",
}

router = APIRouter(prefix="/api/btc")

# Top-level index fields that need window-offsetting in daily mode.
# seg.start_idx/seg.end_idx are nested inside `seg` and offset separately.
_IDX_FIELDS = ("confirmed_at_idx", "fs_at_idx")


def _load_window(tf: str, limit: int | None):
    """Validated load of one timeframe window. Returns (candles, flow) or
    (None, JSONResponse-error)."""
    try:
        df = load_btc_df(tf)
    except FileNotFoundError:
        return None, JSONResponse(
            status_code=404,
            content={"detail": f"BTC {tf} data missing in data/btc/ — copy the CSV first."},
        )
    except ValueError as e:
        return None, JSONResponse(status_code=400, content={"detail": str(e)})
    if limit and limit > 0:
        df = df.tail(int(limit)).reset_index(drop=True)

    candles: list[dict] = []
    flow: list[FlowCandle] = []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(row.open), float(row.high), float(row.low), float(row.close)
        candles.append(
            {
                "date": date,
                "ts": int(row.ts),
                "open": o,
                "high": h,
                "low": lo,
                "close": c,
                # BTC CSV has no volume/oi — zero-filled for frontend shape compat
                "volume": 0,
                "oi": 0,
            }
        )
        flow.append(FlowCandle(date=date, open=o, high=h, low=lo, close=c))
    return (candles, flow), None


def _compute_swings(flow: list[FlowCandle], mode: str, min_bars: int = 14) -> list[dict]:
    """Swing chain for a window.

    continuous: ONE 24/7 chain, swing_index never resets
    daily:      per-calendar-day chains (NSE-style); slice idx values are
                offset back to window positions
    min_bars:   SwingEngine minBars (sweep winner: 20 > 14 > 7 on BTC)
    """
    opts = {"minBars": max(2, int(min_bars))}
    cap = max(1, len(flow) // 2)  # no 1000-swing cap — full chain like the sweep
    if mode == "continuous":
        return compute_btc_swings(flow, opts=opts, max_swings=cap)

    swings: list[dict] = []
    slice_start = 0
    n = len(flow)
    for i in range(1, n + 1):
        if i == n or flow[i].date[:10] != flow[slice_start].date[:10]:
            chunk = flow[slice_start:i]
            day_swings = compute_btc_swings(
                chunk, opts={"minBars": max(2, int(min_bars))}, max_swings=max(1, len(chunk) // 2)
            )
            for s in day_swings:
                for f in _IDX_FIELDS:
                    if s.get(f, -1) >= 0:
                        s[f] += slice_start
                # seg.start_idx/end_idx are nested — offset them the same way
                # so the zigzag draws at the correct window positions.
                seg = s.get("seg") or {}
                if seg.get("start_idx", -1) >= 0:
                    seg["start_idx"] += slice_start
                if seg.get("end_idx", -1) >= 0:
                    seg["end_idx"] += slice_start
                for b in s["breaks"]:
                    b["idx"] += slice_start
            swings.extend(day_swings)
            slice_start = i
    return swings


def _validate_tf_mode(tf: str, mode: str):
    if tf not in BTC_TFS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"tf must be one of {sorted(BTC_TFS)}"},
        )
    if mode not in ("continuous", "daily"):
        return JSONResponse(status_code=400, content={"detail": "mode must be continuous | daily"})
    return None


def _trade_costs(trades: list[dict], fee_pct: float, slip_pts: float) -> tuple[float, float]:
    """Per-trade cost (in R) of round-trip fees + slippage, and total.

    fee_pct: % of notional per side (e.g. 0.05 = Binance taker).
    slip_pts: adverse price points on the exit (beyond the bar-gap fill).
    Fee model: 2 * fee_pct% * price / risk  +  slip_pts / risk per trade.
    """
    total = 0.0
    count = 0
    for t in trades:
        risk = abs(float(t["entry_price"]) - float(t["sl"]))
        if risk <= 0:
            continue
        cost_r = (2.0 * max(0.0, float(fee_pct)) * abs(float(t["entry_price"])) / 100.0
                  + max(0.0, float(slip_pts))) / risk
        t["cost_r"] = round(cost_r, 4)
        total += cost_r
        count += 1
    return round(total, 4), count


def _net_stats(stats: dict, trades: list[dict]) -> dict:
    """Extend a stats dict with cost-adjusted net-R aggregates."""
    out = dict(stats)
    closed = [t for t in trades if t["outcome"] != "open"]
    net_r = 0.0
    for t in closed:
        cost = float(t.get("cost_r", 0.0))
        net_r += float(t["r_multiple"]) - cost
    out["net_total_r"] = round(net_r, 2)
    out["net_avg_r"] = round(net_r / len(closed), 3) if closed else 0.0
    out["total_costs_r"] = round(sum(float(t.get("cost_r", 0.0)) for t in closed), 2)
    return out


# Master presets — ONE SWING ONE TRADE + 11:30 fix 2026-09-06 via _rerun_master_sweep.py
# Fix: one swing one trade (first B2/FLIP per swing only) + opposite-dir touchable SL (max high since prev_end).
# 14 Jan 21:30 FLIP from same swing as 17:30 B2 now ignored; 11:30 SL 95465 not 95281; 20:00 SL 91780.
# Method: stream incl churn + touchable + one-trade-per-swing + 1m fills + 0.05%+2pt FULL window, OWN TF, net desc.
_MASTER_PRESETS: list[dict] = [
    {"key": "flip1h20", "bestTf": "1h",
     "label": "#1 Flip Fixed 3R (1h)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 0.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
    {"key": "flip1h30", "bestTf": "1h",
     "label": "#2 Flip Trail 30 (1h)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "decisive1h30", "bestTf": "1h",
     "label": "#3 Decisive Trail 30 (1h)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "flip1h20t", "bestTf": "1h",
     "label": "#4 Flip Trail 20 (1h)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
    {"key": "flip50", "bestTf": "15m",
     "label": "#5 Flip Trail 50 (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 50, "bias": "off", "regime": "off"},
    {"key": "decisive50", "bestTf": "15m",
     "label": "#6 Decisive Trail 50 (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 50, "bias": "off", "regime": "off"},
    {"key": "sniper", "bestTf": "15m",
     "label": "#7 Sniper 3R (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 1.0,
     "min_bars": 20, "bias": "15m", "regime": "streak_311"},
    {"key": "decisive30", "bestTf": "15m",
     "label": "#8 Decisive Trail 30 (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "flip30", "bestTf": "15m",
     "label": "#9 Flip Trail 30 (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 0.0,
     "min_bars": 30, "bias": "off", "regime": "off"},
    {"key": "baseline", "bestTf": "15m",
     "label": "#10 Baseline (ship) (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 1.0,
     "min_bars": 14, "bias": "off", "regime": "off"},
    {"key": "trail_max_r", "bestTf": "15m",
     "label": "#11 Trailing Max R (15m)", "entry_break": "decisive", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 1.0,
     "min_bars": 20, "bias": "off", "regime": "off"},
    {"key": "flip_bias", "bestTf": "15m",
     "label": "#12 FLIP + 15m Bias (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "off", "breakeven_r": 1.0,
     "min_bars": 14, "bias": "15m", "regime": "off"},
    {"key": "flip_quality", "bestTf": "15m",
     "label": "#13 FLIP Quality (15m)", "entry_break": "flip", "sl_mode": "swing",
     "rr_target": 3.0, "trailing": "swing", "breakeven_r": 1.0,
     "min_bars": 14, "bias": "off", "regime": "off"},
]


def _run_preset(candles: list[dict], swings: list[dict], p: dict,
                fee_pct: float, slip_pts: float,
                bias_timeline=None, day_gate=None, fine=None,
                entry_selection: str = "stream", version: str = "v1") -> dict:
    """Run one master preset and return a summary row. Versioned — v1 default never disturbed."""
    # v1 flip1h20 is now cap 16d default (old cap 0 removed) — use v7 engine for this preset when version v1
    if p.get("key") == "flip1h20" and version == "v1" and simulate_btc_trades_v7 is not None:
        tr = simulate_btc_trades_v7(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
            cap_days=16,
        )
        closed = [t for t in tr if t["outcome"] != "open"]
        base = sum(t["r_multiple"] for t in closed)
        wins = sum(1 for t in closed if t["r_multiple"] > 0)
        _trade_costs(tr, fee_pct, slip_pts)
        costs = sum(float(t.get("cost_r", 0.0)) for t in closed)
        return {
            "key": p["key"], "label": p["label"],
            "entry_break": p["entry_break"], "min_bars": p["min_bars"],
            "trailing": p["trailing"], "breakeven_r": p["breakeven_r"],
            "bias": p["bias"], "regime": p["regime"],
            "trades": len(closed),
            "win_rate": round(100.0 * wins / max(1, len(closed)), 1),
            "base_r": round(base, 2),
            "net_r": round(base - costs, 2),
            "costs_r": round(costs, 2),
        }
    # version dispatch
    if version == "v2" and simulate_btc_trades_v2 is not None:
        tr = simulate_btc_trades_v2(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
        # for v2 we ignore p trailing and force chandelier if needed — but keep as is
    elif version == "v3" and simulate_btc_trades_v3 is not None:
        # v3 needs HTF swings — caller should have built them; fallback to v1
        tr = simulate_btc_trades(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    elif version == "v4" and simulate_btc_trades_v4 is not None:
        tr = simulate_btc_trades_v4(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    elif version == "v5" and simulate_btc_trades_v5 is not None:
        tr = simulate_btc_trades_v5(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    elif version == "v6" and simulate_btc_trades_v6 is not None:
        tr = simulate_btc_trades_v6(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
            sl_pct=0.5, rr_target=float(p["rr_target"]),
            trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
            bias_timeline=bias_timeline, day_gate=day_gate, fine=fine, entry_selection=entry_selection,
        )
    else:
        tr = simulate_btc_trades(
            candles, swings,
            entry_break=p["entry_break"], sl_mode=p["sl_mode"],
        sl_pct=0.5, rr_target=float(p["rr_target"]),
        trailing=p["trailing"], breakeven_r=float(p["breakeven_r"]),
        bias_timeline=bias_timeline, day_gate=day_gate,
        fine=fine, entry_selection=entry_selection,
    )
    closed = [t for t in tr if t["outcome"] != "open"]
    base = sum(t["r_multiple"] for t in closed)
    wins = sum(1 for t in closed if t["r_multiple"] > 0)
    _trade_costs(tr, fee_pct, slip_pts)
    costs = sum(float(t.get("cost_r", 0.0)) for t in closed)
    return {
        "key": p["key"], "label": p["label"],
        "entry_break": p["entry_break"], "min_bars": p["min_bars"],
        "trailing": p["trailing"], "breakeven_r": p["breakeven_r"],
        "bias": p["bias"], "regime": p["regime"],
        "trades": len(closed),
        "win_rate": round(100.0 * wins / max(1, len(closed)), 1),
        "base_r": round(base, 2),
        "net_r": round(base - costs, 2),
        "costs_r": round(costs, 2),
    }


def _load_fine_1m(t0: int, t1: int) -> list[dict]:
    """1m candles for [t0, t1] from the 1m CSV — for 1m-precise exit fills.

    Returns [] when the 1m CSV is missing. Filters the frame BEFORE building
    dicts so a full-window backtest still only materialises the needed rows.
    """
    try:
        df = load_btc_df("1m")
    except FileNotFoundError:
        return []
    df = df[(df["ts"] >= t0) & (df["ts"] <= t1)]
    out: list[dict] = []
    for row in df.itertuples():
        out.append(
            {
                "date": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "ts": int(row.ts),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
            }
        )
    return out


def _streak_regime_gate(candles: list[dict]) -> dict[str, Optional[str]]:
    """3-1-1 daily-color streak regime gate (fix/btc_sweep2.py D4 winner).

    Trade the regime; on a color-break day keep the old regime; the NEXT day
    is a PAUSE (no trades) and the regime flips to the pause day's color.
    Returns {date: "long"|"short"|None} — None = pause day.
    """
    per_day: dict[str, list[dict]] = {}
    for c in candles:
        per_day.setdefault(c["date"][:10], []).append(c)

    days = sorted(per_day)
    gate: dict[str, Optional[str]] = {}
    if not days:
        return gate

    def _color(day: str) -> str:
        cs = per_day[day]
        return "long" if float(cs[-1]["close"]) >= float(cs[0]["open"]) else "short"

    regime = _color(days[0])
    pause = False
    for day in days:
        col = _color(day)
        if pause:
            gate[day] = None
            regime = col
            pause = False
            continue
        gate[day] = regime
        if col != regime:
            pause = True
    return gate


@router.get("/status")
def btc_status():
    """Data presence per timeframe (rows + coverage)."""
    out: dict = {}
    for tf in BTC_TFS:
        path = btc_csv_path(tf)
        if not path.exists():
            out[tf] = {"exists": False, "rows": 0, "first_ts": None, "last_ts": None}
            continue
        try:
            df = load_btc_df(tf)
        except Exception:  # malformed CSV etc.
            out[tf] = {"exists": False, "rows": 0, "first_ts": None, "last_ts": None}
            continue
        out[tf] = {
            "exists": True,
            "rows": int(len(df)),
            "first_ts": df["timestamp"].iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
            "last_ts": df["timestamp"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S"),
        }
    return {"tfs": out}


@router.get("/chart")
def btc_chart(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    min_bars: int = 14,
):
    """Candles + REAL swing chain (B1/B2/FLIP/FS-SUS) for ONE window.

    Swings are computed on exactly the candle window returned - the chart's
    OWN timeframe (15m chart -> 15m swings; never a lower-TF projection) -
    so swing idx values equal array positions in `candles`.
    """
    err = _validate_tf_mode(tf, mode)
    if err:
        return err
    win, err = _load_window(tf, limit)
    if err:
        return err
    candles, flow = win

    return {
        "tf": tf,
        "mode": mode,
        "count": len(candles),
        "first_ts": candles[0]["date"] if candles else None,
        "last_ts": candles[-1]["date"] if candles else None,
        "candles": candles,
        "swings": _compute_swings(flow, mode, min_bars=min_bars),
        # white walker path — continuous chains across midnight (24/7),
        # daily re-seeds per calendar day
        "flow": compute_btc_flow(flow, mode),
    }


@router.get("/backtest")
def btc_backtest(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    fee_pct: float = 0.0,
    slippage_pts: float = 0.0,
    entry_break: str = "decisive",
    sl_mode: str = "swing",
    sl_pct: float = 0.5,
    rr_target: float = 3.0,
    trailing: str = "off",
    trail_distance_r: float = 1.0,
    breakeven_r: float = 1.0,
    skip_first: bool = True,
    bias: str = "off",
    min_bars: int = 14,
    regime: str = "off",
    fill_tf: str = "1m",
    entry_selection: str = "stream",
    version: str = "v1",
    htf_ltf: str = "off",
    htf_ltf_ver: str = "v1",
):
    """Position engine over the swing chain: entries on swing breaks,
    swing/pct SL, fixed R target, breakeven-R and trailing.

    Args:
        entry_break: decisive (default: the swing's B2/FLIP flip break) | b2 | flip
        sl_mode:     swing (broken pivot extreme) | pct (sl_pct% beyond entry)
        rr_target:   fixed R target — used when trailing=off
        trailing:    off | r (trail trail_distance_r behind favorable extreme)
                     | swing (trail to confirmed swing pivots)
        breakeven_r: SL moves to entry after breakeven_r * risk traveled (0 = off)
        skip_first:  first swing of the chain establishes structure only (FS/bias
                     role) — entries start from swing #2 onward (default true)
        bias:        off | 15m — gate entries by the last CONFIRMED 15m swing
                     direction (longs need "up", shorts need "down"). The BTC
                     analog of Nifty's pre-open bias. Ignored when tf=15m
                     (no higher TF available).
        min_bars:    SwingEngine minBars (sweep winner: 20 > 14 > 7 on BTC).
        regime:      off | streak_311 — daily-color streak regime gate
                     (trade regime, fade the break day, pause, flip).

    Returns:
        {params, stats, trades: [...]} — trades carry entry/exit ts + date so
        the frontend draws PositionPrimitive boxes and a trade table.
    """
    err = _validate_tf_mode(tf, mode)
    if err:
        return err
    if entry_break not in ("decisive", "b2", "flip"):
        return JSONResponse(status_code=400, content={"detail": "entry_break must be decisive | b2 | flip"})
    if sl_mode not in ("swing", "pct"):
        return JSONResponse(status_code=400, content={"detail": "sl_mode must be swing | pct"})
    if trailing not in ("off", "r", "swing"):
        return JSONResponse(status_code=400, content={"detail": "trailing must be off | r | swing"})
    if bias not in ("off", "15m"):
        return JSONResponse(status_code=400, content={"detail": "bias must be off | 15m"})
    if regime not in ("off", "streak_311"):
        return JSONResponse(status_code=400, content={"detail": "regime must be off | streak_311"})
    if not (2 <= int(min_bars) <= 200):
        return JSONResponse(status_code=400, content={"detail": "min_bars must be 2..200"})
    if not (0 <= float(fee_pct) <= 0.5):
        return JSONResponse(status_code=400, content={"detail": "fee_pct must be 0..0.5 (% per side)"})
    if not (0 <= float(slippage_pts) <= 1000):
        return JSONResponse(status_code=400, content={"detail": "slippage_pts must be 0..1000"})
    if fill_tf not in ("signal", "1m"):
        return JSONResponse(status_code=400, content={"detail": "fill_tf must be signal | 1m"})
    if entry_selection not in ("stream", "final"):
        return JSONResponse(status_code=400, content={"detail": "entry_selection must be stream | final"})
    if version not in BTC_VERSIONS:
        return JSONResponse(status_code=400, content={"detail": f"version must be one of {BTC_VERSIONS}"})
    if htf_ltf not in ("off", "5m", "15m"):
        return JSONResponse(status_code=400, content={"detail": "htf_ltf must be off | 5m | 15m"})
    if htf_ltf_ver not in ("v1", "v3"):
        return JSONResponse(status_code=400, content={"detail": "htf_ltf_ver must be v1 | v3"})

    win, err = _load_window(tf, limit)
    if err:
        return err
    candles, flow = win

    swings = _compute_swings(flow, mode, min_bars=min_bars)

    # 1m-precise exit fills: walk 1m candles for SL/target/trail/BE instead of
    # the signal TF's bars (no hidden intrabar stops). tf=1m already exact.
    fine: Optional[list[dict]] = None
    if fill_tf == "1m" and tf != "1m":
        fine = _load_fine_1m(candles[0]["ts"], candles[-1]["ts"])
        if not fine:
            return JSONResponse(
                status_code=400,
                content={"detail": "fill_tf=1m needs data/btc/BTCUSDT_1m.csv — missing or empty for this window."},
            )

    # Daily-color streak regime gate (3-1-1) over the trade window's days.
    day_gate: dict[str, Optional[str]] | None = None
    if regime == "streak_311":
        day_gate = _streak_regime_gate(candles)

    # Higher-TF bias timeline (15m swings over the FULL 15m series so the
    # gate is warm even at the very start of the trade window).
    bias_applied = False
    bias_timeline: list[tuple[int, str]] | None = None
    if bias == "15m" and tf in ("1m", "5m"):
        htf, htf_err = _load_window("15m", None)
        if htf_err is None:
            htf_candles, htf_flow = htf
            htf_swings = _compute_swings(htf_flow, mode)
            bias_timeline = sorted(
                (
                    int(htf_candles[s["confirmed_at_idx"]]["ts"]),
                    s["dir"],
                )
                for s in htf_swings
                if 0 <= int(s.get("confirmed_at_idx", -1)) < len(htf_candles)
            )
            bias_applied = True

    params = {
        "tf": tf,
        "mode": mode,
        "limit": limit,
        "fee_pct": float(fee_pct),
        "slippage_pts": float(slippage_pts),
        "entry_break": entry_break,
        "sl_mode": sl_mode,
        "sl_pct": float(sl_pct),
        "rr_target": float(rr_target),
        "trailing": trailing,
        "trail_distance_r": float(trail_distance_r),
        "breakeven_r": float(breakeven_r),
        "skip_first": bool(skip_first),
        "bias": bias,
        "bias_applied": bias_applied,
        "min_bars": int(min_bars),
        "regime": regime,
        "fill_tf": fill_tf if tf != "1m" else "signal",
        "entry_selection": entry_selection,
        "version": version,
        "htf_ltf": htf_ltf,
        "htf_ltf_ver": htf_ltf_ver,
    }
    # HTF-LTF nested execution: 1h Flip cap16 + 15m/5m Decisive inside HTF window
    if htf_ltf != "off" and simulate_htf_ltf_15m is not None:
        # HTF is always 1h Flip cap16, LTF is htf_ltf (15m or 5m) Decisive
        htf_tf = "1h"
        ltf_tf = htf_ltf
        # Load HTF window (full)
        htf_win, htf_err = _load_window(htf_tf, None)
        ltf_win, ltf_err = _load_window(ltf_tf, limit)  # use same limit as chart window for LTF
        if htf_err is None and ltf_err is None and htf_win is not None and ltf_win is not None:
            htf_candles, htf_flow = htf_win  # type: ignore
            ltf_candles, ltf_flow = ltf_win  # type: ignore
            # HTF swings
            htf_swings = _compute_swings(htf_flow, mode, min_bars=20)
            # LTF swings
            ltf_min = 50 if ltf_tf == "15m" else 14
            ltf_swings = _compute_swings(ltf_flow, mode, min_bars=ltf_min)
            # HTF fine for 1h
            htf_fine = _load_fine_1m(htf_candles[0]["ts"], htf_candles[-1]["ts"])
            ltf_fine = _load_fine_1m(ltf_candles[0]["ts"], ltf_candles[-1]["ts"])
            # Use HTF-LTF engine
            if htf_ltf_ver == "v3" and simulate_htf_ltf_ext_stop is not None:
                # v3 Extension Stop: block fresh same-dir LTF entries once the
                # 1h leg is beyond 1.5R unrealized (see v3_ext_stop docstring).
                nested = simulate_htf_ltf_ext_stop(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                    ext_stop_r=1.5,
                )
                params["ext_stop_r"] = 1.5
            else:
                nested = simulate_htf_ltf_15m(
                    htf_candles, htf_swings, ltf_candles, ltf_swings, ltf_fine,
                    htf_entry_break="flip", ltf_entry_break="decisive",
                    sl_mode=sl_mode, rr_target=rr_target, ltf_trailing="swing",
                    htf_breakeven=0.0, ltf_breakeven=0.0, htf_cap_days=16,
                )
            # For chart, we show LTF trades (inside HTF) as main trades, plus HTF trades as context
            # Combine for stats: LTF trades are the execution, HTF trades are regime
            ltf_trades = nested.get("ltf_trades", [])
            htf_trades = nested.get("htf_trades", [])
            # Use LTF trades for main chart, but also include HTF for stats
            # For now, return LTF trades as primary, with HTF count in params
            _trade_costs(ltf_trades, fee_pct, slippage_pts)
            _trade_costs(htf_trades, fee_pct, slippage_pts)
            stats_ltf = trade_stats(ltf_trades)
            stats_ltf = _net_stats(stats_ltf, ltf_trades)
            # Also compute HTF stats for reference
            stats_htf = trade_stats(htf_trades)
            stats_htf = _net_stats(stats_htf, htf_trades)
            # Combined net
            combined_net = float(stats_ltf.get("net_total_r", 0)) + float(stats_htf.get("net_total_r", 0))
            # Return LTF trades as main, but include htf info in params
            params["htf_trades"] = len(htf_trades)
            params["htf_net"] = stats_htf.get("net_total_r")
            params["ltf_trades"] = len(ltf_trades)
            return {
                "params": params,
                "count": len(ltf_candles) if ltf_candles else len(candles),
                "swings_used": len(ltf_swings) if ltf_swings else len(swings),
                "trades": ltf_trades,
                "stats": stats_ltf,
                "htf_trades": htf_trades,
                "htf_stats": stats_htf,
                "combined_net": combined_net,
            }
    # versioned dispatch — v1 is default honest baseline, v2..v7 are isolated crazy ideas
    # v1 flip1h20 is now cap 16d default (old cap 0 removed) — use v7 engine for that preset
    if version == "v1" and tf == "1h" and entry_break == "flip" and int(min_bars) == 20 and trailing == "off" and float(breakeven_r) == 0.0 and simulate_btc_trades_v7 is not None:
        trades = simulate_btc_trades_v7(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
        )
    elif version == "v1":
        trades = simulate_btc_trades(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            trail_distance_r=float(trail_distance_r),
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v2":
        if simulate_btc_trades_v2 is None:
            return JSONResponse(status_code=500, content={"detail": "v2 engine not loaded"})
        trades = simulate_btc_trades_v2(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            trail_k=3.0,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v3":
        if simulate_btc_trades_v3 is None:
            return JSONResponse(status_code=500, content={"detail": "v3 engine not loaded"})
        # load HTF 1h swings for HTF trail
        htf_swings = None
        htf_ts = None
        try:
            htf_win, htf_err = _load_window("1h", None)
            if htf_err is None and htf_win is not None:
                htf_candles, htf_flow = htf_win  # type: ignore
                htf_swings = _compute_swings(htf_flow, mode, min_bars=min_bars)
                htf_ts = [int(c["ts"]) for c in htf_candles]
        except Exception:
            htf_swings = None
            htf_ts = None
        trades = simulate_btc_trades_v3(
            candles,
            swings,
            swings_htf=htf_swings,
            candle_ts_htf=htf_ts,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v4":
        if simulate_btc_trades_v4 is None:
            return JSONResponse(status_code=500, content={"detail": "v4 engine not loaded"})
        trades = simulate_btc_trades_v4(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v5":
        if simulate_btc_trades_v5 is None:
            return JSONResponse(status_code=500, content={"detail": "v5 engine not loaded"})
        # v5 forces BE1
        trades = simulate_btc_trades_v5(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=1.0,
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v6":
        if simulate_btc_trades_v6 is None:
            return JSONResponse(status_code=500, content={"detail": "v6 engine not loaded"})
        trades = simulate_btc_trades_v6(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )
    elif version == "v7":
        if simulate_btc_trades_v7 is None:
            return JSONResponse(status_code=500, content={"detail": "v7 engine not loaded"})
        trades = simulate_btc_trades_v7(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
        )
    elif version == "v8":
        if simulate_btc_trades_v8 is None:
            return JSONResponse(status_code=500, content={"detail": "v8 engine not loaded"})
        trades = simulate_btc_trades_v8(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
            confirm_bars=3,
        )
    elif version == "v9":
        if simulate_btc_trades_v9 is None:
            return JSONResponse(status_code=500, content={"detail": "v9 engine not loaded"})
        trades = simulate_btc_trades_v9(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
            extend_threshold_r=2.5,
            extend_cap_days=30,
        )
    elif version == "v10":
        if simulate_btc_trades_v10 is None:
            return JSONResponse(status_code=500, content={"detail": "v10 engine not loaded"})
        trades = simulate_btc_trades_v10(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
            cap_days=16,
            min_body_atr=0.5,
            max_wick_atr=1.0,
        )
    else:
        trades = simulate_btc_trades(
            candles,
            swings,
            entry_break=entry_break,
            sl_mode=sl_mode,
            sl_pct=float(sl_pct),
            rr_target=float(rr_target),
            trailing=trailing,
            trail_distance_r=float(trail_distance_r),
            breakeven_r=float(breakeven_r),
            skip_first=bool(skip_first),
            bias_timeline=bias_timeline,
            day_gate=day_gate,
            fine=fine,
            entry_selection=entry_selection,
        )

    # cost model: round-trip fees (% notional, both sides) + slippage points,
    # expressed in R against each trade's own risk -> honest NET R stats.
    _trade_costs(trades, fee_pct, slippage_pts)
    stats = _net_stats(trade_stats(trades), trades)

    return {
        "params": params,
        "count": len(candles),
        "swings_used": len(swings),
        "trades": trades,
        "stats": stats,
    }


@router.get("/versions")
def btc_versions():
    """List available crazy-idea versions (v1 locked, v2..v6 isolated)."""
    return {"versions": BTC_VERSIONS, "labels": VERSION_LABELS, "default": "v1"}

@router.get("/summary")
def btc_summary(
    tf: str = "5m",
    mode: str = "continuous",
    limit: int | None = None,
    fee_pct: float = 0.05,
    slippage_pts: float = 2.0,
    entry_selection: str = "stream",
    version: str = "v1",
):
    """\'Konsi best hai\' table - every master preset on its OWN reference TF.

    Each preset is evaluated on the timeframe it was designed for (bestTf),
    with its own minBars/swing config, then reports base R (zero cost) AND
    net R after fee_pct %/side + slippage_pts. `best` = highest net_r row.
    """
    if entry_selection not in ("stream", "final"):
        return JSONResponse(status_code=400, content={"detail": "entry_selection must be stream | final"})
    if not (0 <= float(fee_pct) <= 0.5):
        return JSONResponse(status_code=400, content={"detail": "fee_pct must be 0..0.5 (% per side)"})
    if not (0 <= float(slippage_pts) <= 1000):
        return JSONResponse(status_code=400, content={"detail": "slippage_pts must be 0..1000"})
    if version not in BTC_VERSIONS:
        return JSONResponse(status_code=400, content={"detail": f"version must be one of {BTC_VERSIONS}"})

    # group presets by their reference TF, load each TF\'s data once
    by_tf: dict = {}
    for p in _MASTER_PRESETS:
        ptf = p.get("bestTf", "15m")
        by_tf.setdefault(ptf, []).append(p)

    rows = []
    for ptf, presets in by_tf.items():
        win_p, err_p = _load_window(ptf, None)
        if err_p:
            continue
        candles_p, flow_p = win_p

        # 15m bias timeline (only for presets on lower TFs)
        bias_timeline = None
        if ptf in ("1m", "5m"):
            htf, htf_err = _load_window("15m", None)
            if htf_err is None:
                htf_candles, htf_flow = htf
                htf_swings = _compute_swings(htf_flow, mode)
                bias_timeline = sorted(
                    (
                        int(htf_candles[s["confirmed_at_idx"]]["ts"]),
                        s["dir"],
                    )
                    for s in htf_swings
                    if 0 <= int(s.get("confirmed_at_idx", -1)) < len(htf_candles)
                )

        # 1m-precise exit fills
        fine = None
        if ptf != "1m":
            fine = _load_fine_1m(candles_p[0]["ts"], candles_p[-1]["ts"]) or None

        for p in presets:
            sw_p = _compute_swings(flow_p, mode, min_bars=p["min_bars"])
            row = _run_preset(
                candles_p, sw_p, p, fee_pct, slippage_pts,
                bias_timeline=bias_timeline if p["bias"] == "15m" else None,
                day_gate=_streak_regime_gate(candles_p) if p["regime"] == "streak_311" else None,
                fine=fine,
                entry_selection=entry_selection,
                version=version,
            )
            row["tf"] = ptf
            rows.append(row)

    rows.sort(key=lambda r: r["net_r"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    return {
        "fee_pct": float(fee_pct),
        "slippage_pts": float(slippage_pts),
        "entry_selection": entry_selection,
        "version": version,
        "rows": rows,
        "best": rows[0]["key"] if rows else None,
    }
