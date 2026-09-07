"""Refresh BTC data: fetch new Binance candles and APPEND them to the main CSVs.

One dataset, one CSV per timeframe (data/btc/BTCUSDT_{tf}.csv). The original
in-sample window (2025-01-01 -> 2025-10-01) is preserved in
data/btc/backup_insample/ for research reproducibility.

Usage:
    python debug/_btc_fetch_update.py --tf 5m --skip-sweep   # refresh CSV only
    python debug/_btc_fetch_update.py --tf 15m               # refresh + 15m sweep grid

Behaviour:
    - reads the last timestamp of the existing CSV
    - fetches Binance klines from there to now (IST wall-clock, same format)
    - appends only NEW timestamps (never overwrites history)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]  # backend/
DATA_DIR = ROOT.parent / "data" / "btc"
IST = timedelta(hours=5, minutes=30)
SYMBOL = "BTCUSDT"
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
         "1h": 3_600_000, "4h": 14_400_000}
# first in-sample bar of the repo CSVs (2025-01-01 00:00 UTC = 05:30 IST)
SEED_IST = "2025-01-01 05:30:00"


def _fetch_json(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def last_ts(tf: str) -> str | None:
    path = DATA_DIR / f"BTCUSDT_{tf}.csv"
    if not path.exists():
        return None
    last = ""
    with open(path, encoding="utf-8") as f:
        f.readline()  # header
        for line in f:
            if line.strip():
                last = line.split(",", 1)[0]
    return last or None


def ts_to_ms(ist_wall: str) -> int:
    """IST wall-clock string -> UTC epoch ms."""
    dt = datetime.strptime(ist_wall, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def fetch_tf(tf: str, since_ms: int) -> dict[str, tuple[float, float, float, float]]:
    """{ist_wall: (o, h, l, c)} for all Binance candles from since_ms to now."""
    step_ms = TF_MS[tf]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    out: dict[str, tuple[float, float, float, float]] = {}
    cur = since_ms + step_ms  # start AFTER the last stored candle
    while cur < now_ms:
        url = (
            f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}"
            f"&interval={tf}&limit=1000&startTime={cur}"
        )
        rows = _fetch_json(url)
        if not rows:
            break
        for k in rows:
            utc = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist = (utc + IST).strftime("%Y-%m-%d %H:%M:%S")
            out[ist] = (float(k[1]), float(k[2]), float(k[3]), float(k[4]))
        nxt = rows[-1][0] + step_ms
        if nxt <= cur:
            break
        cur = nxt
    return out


def merge_csv(tf: str, new_rows: dict[str, tuple[float, float, float, float]],
              seed: bool = False) -> int:
    """Append new timestamps to the main CSV; returns rows written."""
    path = DATA_DIR / f"BTCUSDT_{tf}.csv"
    existing: dict[str, str] = {}
    header = "timestamp,open,high,low,close,x,y\n"
    if path.exists() and not seed:
        with open(path, encoding="utf-8") as f:
            header = f.readline()
            for line in f:
                if line.strip():
                    existing[line.split(",", 1)[0]] = line
    added = 0
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for t in sorted(existing):
            f.write(existing[t])
        for t, (o, h, lo, c) in sorted(new_rows.items()):
            if t in existing:
                continue  # never overwrite history
            f.write(f"{t},{o:.2f},{h:.2f},{lo:.2f},{c:.2f},0,0\n")
            added += 1
    return added

def sweep_15m() -> None:
    """15m parameter grid over the full merged series (net R after costs)."""
    sys.path.insert(0, str(ROOT))
    from src.btc.btc_config import load_btc_df
    from src.btc.btc_engine import simulate_btc_trades
    from src.btc.btc_swing import compute_btc_swings
    from src.walker import FlowCandle

    df = load_btc_df("15m")
    candles = [
        FlowCandle(date=r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                   open=float(r.open), high=float(r.high),
                   low=float(r.low), close=float(r.close))
        for r in df.itertuples()
    ]
    fee_pct, slip_pts = 0.05, 2.0
    res = []
    for eb in ("decisive", "flip"):
        for mb in (20, 30, 50):
            swings = compute_btc_swings(candles, opts={"minBars": mb},
                                        max_swings=len(candles) // 2)
            for trail in ("off", "swing"):
                for be in (0.0, 1.0):
                    tr = simulate_btc_trades(candles, swings, entry_break=eb,
                                             sl_mode="swing", rr_target=3.0,
                                             trailing=trail, breakeven_r=be)
                    closed = [t for t in tr if t["outcome"] != "open"]
                    base = sum(t["r_multiple"] for t in closed)
                    wins = sum(1 for t in closed if t["r_multiple"] > 0)
                    fees = 0.0
                    for t in closed:
                        risk = abs(t["entry_price"] - t["sl"])
                        if risk <= 0:
                            continue
                        fees += (2.0 * fee_pct * abs(t["entry_price"]) / 100.0 + slip_pts) / risk
                    res.append({
                        "entry_break": eb, "min_bars": mb, "trailing": trail,
                        "breakeven_r": be, "trades": len(closed),
                        "win_rate": round(100.0 * wins / max(1, len(closed)), 1),
                        "base_r": round(base, 1), "net_r": round(base - fees, 1),
                    })
    res.sort(key=lambda r: -r["net_r"])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ROOT / f"sweep_15m_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"rows": len(candles), "fee_pct": fee_pct,
                   "slippage_pts": slip_pts, "results": res}, f, indent=2)
    print("saved:", out_path)
    print("\n15m grid on full merged data (net after 0.05%+2pt):")
    for r in res[:12]:
        print("  %-8s mb=%2d tr=%-5s be=%g n=%4d win%%=%5.1f base=%+7.1f net=%+7.1f"
              % (r["entry_break"], r["min_bars"], r["trailing"], r["breakeven_r"],
                 r["trades"], r["win_rate"], r["base_r"], r["net_r"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="15m", choices=sorted(TF_MS))
    ap.add_argument("--skip-sweep", action="store_true")
    args = ap.parse_args()
    tf = args.tf

    last = last_ts(tf)
    seeding = last is None
    if seeding:
        # new timeframe — seed the full period so it matches the other CSVs
        since_ms = ts_to_ms(SEED_IST)
        print(f"no existing CSV for {tf} — seeding from {SEED_IST} ...")
        start_ms = since_ms
    else:
        since_ms = ts_to_ms(last)
        print(f"fetching Binance {tf} candles after {last} ...")
        start_ms = since_ms + TF_MS[tf]  # start AFTER the last stored candle
    new_rows = fetch_tf(tf, start_ms)
    print(f"fetched {len(new_rows)} candidate rows")
    added = merge_csv(tf, new_rows, seed=seeding)
    print(f"wrote {added} rows -> data/btc/BTCUSDT_{tf}.csv")
    if args.skip_sweep or tf != "15m":
        return 0
    sweep_15m()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
