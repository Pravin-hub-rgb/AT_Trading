"""HTF experiments: 1h / 4h strategy sweeps + 15m with 1h-bias gate.

Data: data/btc/BTCUSDT_{1h,4h}.csv (seeded 2025-01-01 -> now, same window as
the 5m/15m CSVs). Costs: 0.05%/side taker + 2pt slippage (net R reported).

Run:  python debug/_btc_htf_sweep.py
Out:  backend/sweep_htf_<ts>.json
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_config import load_btc_df  # noqa: E402
from src.btc.btc_engine import simulate_btc_trades  # noqa: E402
from src.btc.btc_swing import compute_btc_swings  # noqa: E402
from src.walker import FlowCandle  # noqa: E402

FEE_PCT, SLIP_PTS = 0.05, 2.0


def load_candles(tf: str) -> tuple[list[FlowCandle], list[dict]]:
    df = load_btc_df(tf)
    flow: list[FlowCandle] = []
    candles: list[dict] = []
    for r in df.itertuples():
        date = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        o, h, lo, c = float(r.open), float(r.high), float(r.low), float(r.close)
        flow.append(FlowCandle(date=date, open=o, high=h, low=lo, close=c))
        candles.append({"date": date, "ts": int(r.ts), "open": o, "high": h,
                        "low": lo, "close": c, "volume": 0, "oi": 0})
    return flow, candles


def score(candles, tr) -> dict:
    """Aggregate closed trades -> trades/win%/base R/net R (after costs)."""
    closed = [t for t in tr if t["outcome"] != "open"]
    base = sum(t["r_multiple"] for t in closed)
    wins = sum(1 for t in closed if t["r_multiple"] > 0)
    fees = 0.0
    for t in closed:
        risk = abs(t["entry_price"] - t["sl"])
        if risk <= 0:
            continue
        fees += (2.0 * FEE_PCT * abs(t["entry_price"]) / 100.0 + SLIP_PTS) / risk
    return {
        "trades": len(closed),
        "win_rate": round(100.0 * wins / max(1, len(closed)), 1),
        "base_r": round(base, 1), "net_r": round(base - fees, 1),
    }


def main() -> int:
    results: list[dict] = []

    # --- 1h / 4h grids ---
    for tf, mbs in (("1h", (5, 10, 20, 30, 50)), ("4h", (3, 5, 10, 20, 30))):
        flow, candles = load_candles(tf)
        print(f"{tf}: {len(candles)} candles "
              f"({candles[0]['date']} -> {candles[-1]['date']})")
        for mb in mbs:
            sw = compute_btc_swings(flow, opts={"minBars": mb},
                                    max_swings=len(flow) // 2)
            for eb in ("decisive", "flip"):
                for trail in ("off", "swing"):
                    for be in (0.0, 1.0):
                        tr = simulate_btc_trades(candles, sw, entry_break=eb,
                                                 sl_mode="swing", rr_target=3.0,
                                                 trailing=trail, breakeven_r=be)
                        results.append({"tf": tf, "entry_break": eb,
                                        "min_bars": mb, "trailing": trail,
                                        "breakeven_r": be, **score(candles, tr)})

    # --- 15m with 1h bias gate (higher-TF bias) ---
    flow15, candles15 = load_candles("15m")
    flow1h, _ = load_candles("1h")
    df1h = load_btc_df("1h")
    ts_map = {r.timestamp.strftime("%Y-%m-%d %H:%M:%S"): int(r.ts)
              for r in df1h.itertuples()}
    htf_sw = compute_btc_swings(flow1h, opts={"minBars": 5},
                                max_swings=len(flow1h) // 2)
    bias_timeline = sorted(
        (ts_map[flow1h[s["confirmed_at_idx"]].date], s["dir"])
        for s in htf_sw
        if 0 <= int(s.get("confirmed_at_idx", -1)) < len(flow1h)
        and flow1h[s["confirmed_at_idx"]].date in ts_map
    )
    print(f"15m: {len(candles15)} candles, 1h bias points: {len(bias_timeline)}")
    for eb in ("decisive", "flip"):
        for mb in (20, 30, 50):
            sw = compute_btc_swings(flow15, opts={"minBars": mb},
                                    max_swings=len(flow15) // 2)
            for trail in ("off", "swing"):
                for be in (0.0, 1.0):
                    tr = simulate_btc_trades(candles15, sw, entry_break=eb,
                                             sl_mode="swing", rr_target=3.0,
                                             trailing=trail, breakeven_r=be,
                                             bias_timeline=bias_timeline)
                    results.append({"tf": "15m+1h-bias", "entry_break": eb,
                                    "min_bars": mb, "trailing": trail,
                                    "breakeven_r": be, **score(candles15, tr)})

    results.sort(key=lambda r: -r["net_r"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"sweep_htf_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"fee_pct": FEE_PCT, "slippage_pts": SLIP_PTS,
                   "results": results}, f, indent=2)
    print("\nsaved:", out)
    print("\nTOP 25 (net R after 0.05%/side + 2pt):")
    for r in results[:25]:
        print("  %-12s %-8s mb=%2d tr=%-5s be=%g n=%4d win%%=%5.1f base=%+7.1f net=%+7.1f"
              % (r["tf"], r["entry_break"], r["min_bars"], r["trailing"],
                 r["breakeven_r"], r["trades"], r["win_rate"],
                 r["base_r"], r["net_r"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
