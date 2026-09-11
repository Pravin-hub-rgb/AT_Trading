"""Quick v18 scan on major Binance futures — find the best instruments."""
import json
import time
import urllib.request
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pandas as pd
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

IST = timedelta(hours=5, minutes=30)
IST_OFFSET_SEC = 19800
FAPI_URL = "https://fapi.binance.com/fapi/v1/klines"
START_IST = "2023-01-01 05:30:00"
TF_MS = {"15m": 900_000, "1h": 3_600_000}

# Top candidates — high volume, good trend, diverse sectors
SYMBOLS = [
    "WIFUSDT", "PEPEUSDT", "FILUSDT", "ATOMUSDT", "UNIUSDT",
]

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "scan-fut"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def ist_to_ms(s):
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S") - IST
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def download_tf(symbol, tf):
    path = DATA_DIR / f"{symbol}_{tf}.csv"
    if path.exists():
        df = pd.read_csv(path)
        if len(df) > 1000:
            return path
    step_ms = TF_MS[tf]
    start_ms = ist_to_ms(START_IST)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    header = "timestamp,open,high,low,close,x,y\n"
    rows, cur, total = [], start_ms, 0
    while cur < now_ms:
        url = f"{FAPI_URL}?symbol={symbol}&interval={tf}&startTime={cur}&limit=1000"
        try:
            data = _fetch_json(url)
        except:
            time.sleep(1)
            continue
        if not data:
            break
        for k in data:
            utc_dt = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist_str = (utc_dt + IST).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(f"{ist_str},{float(k[1]):.2f},{float(k[2]):.2f},{float(k[3]):.2f},{float(k[4]):.2f},0,0\n")
            total += 1
        nxt = data[-1][0] + step_ms
        if nxt <= cur:
            break
        cur = nxt
    unique = {}
    for line in rows:
        unique[line.split(",")[0]] = line
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header)
        for ts in sorted(unique):
            f.write(unique[ts])
    return path


def load_and_run(symbol):
    try:
        for tf in ["15m", "1h"]:
            download_tf(symbol, tf)

        def load_fut(tf):
            path = DATA_DIR / f"{symbol}_{tf}.csv"
            df = pd.read_csv(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last").reset_index(drop=True)
            df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC
            candles, flow = [], []
            for row in df.itertuples():
                date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                candles.append({"date": date, "ts": int(row.ts), "open": float(row.open),
                                "high": float(row.high), "low": float(row.low), "close": float(row.close),
                                "volume": 0, "oi": 0})
                flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                                       low=float(row.low), close=float(row.close)))
            return candles, flow

        c1h, f1h = load_fut("1h")
        c15, f15 = load_fut("15m")
        if len(c15) < 5000:
            return None
        sw1h = _compute_swings(f1h, "continuous", min_bars=20)
        sw15 = _compute_swings(f15, "continuous", min_bars=50)
        tr = simulate_htf_ltf_streak_halt(
            c1h, sw1h, c15, sw15, fine_ltf=[],
            sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
            cooldown_bars=20, max_consecutive_losses=5
        )["ltf_trades"]
        rs = [t["r_multiple"] for t in tr]
        n = len(rs)
        tot = sum(rs)
        wins = [r for r in rs if r > 0]
        losses = [r for r in rs if r <= 0]
        wr = 100 * len(wins) / n if n else 0
        pf = sum(wins) / abs(sum(losses)) if losses else 0
        eq = peak = dd = 0.0
        for r in rs:
            eq += r; peak = max(peak, eq); dd = max(dd, peak - eq)
        return {"symbol": symbol, "trades": n, "total_r": round(tot, 1),
                "win_rate": round(wr, 1), "pf": round(pf, 2), "max_dd": round(dd, 1)}
    except Exception as e:
        return {"symbol": symbol, "error": str(e)[:80]}


print(f"Scanning {len(SYMBOLS)} symbols...\n")
results = []
for i, sym in enumerate(SYMBOLS):
    print(f"  [{i+1}/{len(SYMBOLS)}] {sym}...", end=" ", flush=True)
    r = load_and_run(sym)
    if r and "error" not in r:
        print(f"{r['trades']}t {r['total_r']:+.1f}R WR={r['win_rate']}% DD={r['max_dd']}R PF={r['pf']}")
        results.append(r)
    elif r:
        print(f"ERROR: {r['error']}")
    else:
        print("SKIP")
    time.sleep(0.3)

results.sort(key=lambda x: -x["total_r"])
print("\n" + "=" * 80)
print(f"{'Symbol':<14} {'Trades':>6} {'Total R':>9} {'WR%':>6} {'PF':>6} {'MaxDD':>7}")
print("-" * 80)
for r in results:
    print(f"{r['symbol']:<14} {r['trades']:>6} {r['total_r']:>+9.1f} {r['win_rate']:>5.1f}% {r['pf']:>6.2f} {r['max_dd']:>6.1f}R")
