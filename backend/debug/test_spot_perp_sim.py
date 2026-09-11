"""TEST ONLY: Spot signals → Perp execution simulation.

Fetches BTC SPOT candles for swing detection (same as backtest),
then simulates execution on BTCUSDT PERP (different fill prices).

This tests: 'what if we use spot data for signals but trade on perp?'
NO live code is modified. Pure comparison.
"""
import sys, json, time
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

IST = timedelta(hours=5, minutes=30)
IST_OFFSET_SEC = 19800
SPOT_URL = "https://api.binance.com/api/v3/klines"
PERP_URL = "https://fapi.binance.com/fapi/v1/klines"


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def download_candles(symbol, tf, url_base):
    start_ms = int((datetime(2023, 1, 1, tzinfo=timezone.utc)).timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    step_ms = {"15m": 900000, "1h": 3600000}[tf]
    rows, cur = [], start_ms
    while cur < now_ms:
        url = f"{url_base}?symbol={symbol}&interval={tf}&startTime={cur}&limit=1000"
        try:
            data = _fetch(url)
        except:
            time.sleep(1)
            continue
        if not data:
            break
        for k in data:
            utc_dt = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            ist_str = (utc_dt + IST).strftime("%Y-%m-%d %H:%M:%S")
            rows.append({
                "date": ist_str,
                "open": float(k[1]), "high": float(k[2]),
                "low": float(k[3]), "close": float(k[4]),
                "ts": int(k[6]) // 1000,
            })
        nxt = data[-1][0] + step_ms
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.1)
    return rows


def to_flow(candles):
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                        low=c["low"], close=c["close"]) for c in candles]


def to_dicts(candles):
    return [{"date": c["date"], "ts": c["ts"], "open": c["open"],
             "high": c["high"], "low": c["low"], "close": c["close"],
             "volume": 0, "oi": 0} for c in candles]


print("=" * 72)
print("TEST: Spot Signals -> Perp Execution Simulation")
print("=" * 72)

print("\n1. Downloading BTC SPOT 1h...")
spot_1h = download_candles("BTCUSDT", "1h", SPOT_URL)
print(f"   {len(spot_1h)} candles")

print("2. Downloading BTC SPOT 15m...")
spot_15m = download_candles("BTCUSDT", "15m", SPOT_URL)
print(f"   {len(spot_15m)} candles")

print("3. Downloading BTC PERP 1h...")
perp_1h = download_candles("BTCUSDT", "1h", PERP_URL)
print(f"   {len(perp_1h)} candles")

print("4. Downloading BTC PERP 15m...")
perp_15m = download_candles("BTCUSDT", "15m", PERP_URL)
print(f"   {len(perp_15m)} candles")

# Build price lookup: date → perp close
perp_1h_close = {c["date"]: c["close"] for c in perp_1h}
perp_15m_close = {c["date"]: c["close"] for c in perp_15m}

# === RUN 1: Pure spot (baseline) ===
print("\n5. Running v18 on SPOT (baseline)...")
sw1h_s = _compute_swings(to_flow(spot_1h), "continuous", min_bars=20)
sw15m_s = _compute_swings(to_flow(spot_15m), "continuous", min_bars=50)
c15_dicts = to_dicts(spot_15m)
c1h_dicts = to_dicts(spot_1h)
t0 = min(c1h_dicts[0]["ts"], c15_dicts[0]["ts"])
t1 = max(c1h_dicts[-1]["ts"], c15_dicts[-1]["ts"])
fine = _load_fine_1m(t0, t1)

spot_trades = simulate_htf_ltf_streak_halt(
    c1h_dicts, sw1h_s, c15_dicts, sw15m_s, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5
)["ltf_trades"]

spot_rs = [t["r_multiple"] for t in spot_trades]
print(f"   Spot: {len(spot_trades)} trades, {sum(spot_rs):+.1f}R")

# === RUN 2: Same signals, perp fill prices ===
print("\n6. Simulating perp execution (same signals, perp prices)...")
perp_trades = []
for t in spot_trades:
    entry_date = t["entry_date"]
    exit_date = t.get("exit_date", entry_date)

    # Get perp close prices at entry/exit
    perp_entry = perp_15m_close.get(entry_date)
    perp_exit = perp_15m_close.get(exit_date)

    if perp_entry and perp_exit and perp_entry > 0:
        entry_px = perp_entry
        exit_px = perp_exit
        sl_px = t["sl"]
        risk = abs(entry_px - sl_px)
        if risk > 0:
            if t["dir"] == "long":
                perp_r = (exit_px - entry_px) / risk
            else:
                perp_r = (entry_px - exit_px) / risk
            new_t = dict(t)
            new_t["r_multiple"] = perp_r
            new_t["entry_price"] = entry_px
            new_t["exit_price"] = exit_px
            perp_trades.append(new_t)
        else:
            perp_trades.append(t)
    else:
        perp_trades.append(t)

perp_rs = [t["r_multiple"] for t in perp_trades]
print(f"   Perp: {len(perp_trades)} trades, {sum(perp_rs):+.1f}R")

# === RUN 3: Pure perp (different swings entirely) ===
print("\n7. Running v18 on pure PERP (different data)...")
sw1h_p = _compute_swings(to_flow(perp_1h), "continuous", min_bars=20)
sw15m_p = _compute_swings(to_flow(perp_15m), "continuous", min_bars=50)
perp_c15 = to_dicts(perp_15m)
perp_c1h = to_dicts(perp_1h)

pure_perp_trades = simulate_htf_ltf_streak_halt(
    perp_c1h, sw1h_p, perp_c15, sw15m_p, fine_ltf=[],
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, max_consecutive_losses=5
)["ltf_trades"]

pure_rs = [t["r_multiple"] for t in pure_perp_trades]
print(f"   Pure perp: {len(pure_perp_trades)} trades, {sum(pure_rs):+.1f}R")


def stats(rs):
    n = len(rs)
    tot = sum(rs)
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    wr = 100 * len(w) / n if n else 0
    pf = sum(w) / abs(sum(l)) if l else 0
    eq = peak = dd = 0.0
    for r in rs:
        eq += r; peak = max(peak, eq); dd = max(dd, peak - eq)
    return n, tot, wr, pf, dd


print("\n" + "=" * 72)
print("COMPARISON")
print("=" * 72)
print(f"{'Method':<30} {'Trades':>6} {'Total R':>9} {'WR%':>6} {'PF':>6} {'MaxDD':>7}")
print("-" * 72)

for label, rs in [("Spot (baseline)", spot_rs),
                   ("Spot signals -> Perp fills", perp_rs),
                   ("Pure perp (different data)", pure_rs)]:
    n, tot, wr, pf, dd = stats(rs)
    print(f"{label:<30} {n:>6} {tot:>+9.1f} {wr:>5.1f}% {pf:>6.2f} {dd:>6.1f}R")

print("\n" + "=" * 72)
print("VERDICT")
print("=" * 72)
n_s, tot_s, _, _, _ = stats(spot_rs)
n_p, tot_p, _, _, _ = stats(perp_rs)
diff = abs(tot_s - tot_p)
pct = 100 * tot_p / tot_s if tot_s else 0
print(f"  Spot->Perp retains {pct:.1f}% of spot returns")
print(f"  Difference: {diff:.1f}R out of {tot_s:.1f}R")
print(f"  Conclusion: {'EXCELLENT - use spot signals + perp execution' if pct > 95 else 'GOOD - acceptable slippage' if pct > 85 else 'FAIR - consider pure perp data'}")
