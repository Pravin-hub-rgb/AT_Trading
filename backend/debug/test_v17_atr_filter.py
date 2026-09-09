"""v17 ATR filter: build, validate, and prove noise removal."""
import sys, statistics, math
from pathlib import Path
from collections import Counter
from datetime import datetime
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v17_atr_filter import simulate_htf_ltf_atr_filter
from src.btc.engines.htf_ltf.v16_entry_dist import simulate_htf_ltf_entry_dist
from src.walker import FlowCandle

def load_window(tf):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({"date": date, "ts": int(row.ts), "open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close), "volume": 0, "oi": 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_window("1h")
c15, f15 = load_window("15m")
sw1h = _compute_swings(f1h, "continuous", min_bars=20)
sw15 = _compute_swings(f15, "continuous", min_bars=50)
t0 = min(c1h[0]["ts"], c15[0]["ts"])
t1 = max(c1h[-1]["ts"], c15[-1]["ts"])
fine = _load_fine_1m(t0, t1)

# v12+cd20 baseline (no ATR filter)
v12 = simulate_htf_ltf_entry_dist(
    candles_htf=c1h, swings_htf=sw1h, candles_ltf=c15, swings_ltf=sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, entry_dist_max=0.0,
)

# v17: ATR<0.5% filter
v17 = simulate_htf_ltf_atr_filter(
    candles_htf=c1h, swings_htf=sw1h, candles_ltf=c15, swings_ltf=sw15, fine_ltf=fine,
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    cooldown_bars=20, atr_max_pct=0.5,
)

v12_trades = v12["ltf_trades"]
v17_trades = v17["ltf_trades"]

# Find excluded trades (in v12 but not in v17)
v17_keys = set()
for t in v17_trades:
    v17_keys.add((t["entry_ts"], t["dir"]))

excluded = []
for t in v12_trades:
    key = (t["entry_ts"], t["dir"])
    if key not in v17_keys:
        excluded.append(t)

print("=" * 72)
print("v17 ATR FILTER VALIDATION")
print("=" * 72)
print(f"v12+cd20 (baseline): {len(v12_trades)} trades, net={sum(t['r_multiple'] for t in v12_trades):+.2f}")
print(f"v17 (ATR<0.5%):      {len(v17_trades)} trades, net={sum(t['r_multiple'] for t in v17_trades):+.2f}")
print(f"Excluded:            {len(excluded)} trades, net={sum(t['r_multiple'] for t in excluded):+.2f}")
print(f"v17 avg R/trade:     {statistics.mean(t['r_multiple'] for t in v17_trades):+.3f}")
# --- Analyze excluded trades ---
print("\n" + "=" * 72)
print("EXCLUDED TRADE ANALYSIS")
print("=" * 72)

exc_r = [t["r_multiple"] for t in excluded]
exc_winners = [r for r in exc_r if r > 0]
exc_losers = [r for r in exc_r if r <= 0]
exc_big_winners = [r for r in exc_r if r > 2]
exc_big_losers = [r for r in exc_r if r < -0.8]

print(f"Winners:       {len(exc_winners)} ({len(exc_winners)/len(excluded)*100:.0f}%)")
print(f"Losers:        {len(exc_losers)} ({len(exc_losers)/len(excluded)*100:.0f}%)")
print(f"Big winners (>2R): {len(exc_big_winners)}")
print(f"Big losers (<-0.8R): {len(exc_big_losers)}")
print(f"Net R:         {sum(exc_r):+.2f}")
print(f"Mean R:        {statistics.mean(exc_r):+.3f}")
print(f"Median R:      {statistics.median(exc_r):+.3f}")
print(f"Max R:         {max(exc_r):+.3f}")
print(f"Min R:         {min(exc_r):+.3f}")

if exc_big_winners:
    print(f"\nBig winner details:")
    for t in excluded:
        if t["r_multiple"] > 2:
            print(f"  {t['entry_date'][:10]} {t['dir']} entry={t['entry_price']:.0f} r={t['r_multiple']:+.2f}")
if exc_big_losers:
    print(f"\nBig loser details:")
    for t in excluded:
        if t["r_multiple"] < -0.8:
            print(f"  {t['entry_date'][:10]} {t['dir']} entry={t['entry_price']:.0f} r={t['r_multiple']:+.2f}")

# --- Session/timing cross-check ---
print("\n" + "=" * 72)
print("SESSION/TIMING CROSS-CHECK")
print("=" * 72)

def get_hour(date_str):
    return int(date_str[11:13])

v17_hours = Counter()
for t in v17_trades:
    h = get_hour(t["entry_date"])
    v17_hours[h] += 1

exc_hours = Counter()
for t in excluded:
    h = get_hour(t["entry_date"])
    exc_hours[h] += 1

print(f"\nHour  v17  excluded")
print("-" * 24)
for h in range(24):
    v = v17_hours.get(h, 0)
    e = exc_hours.get(h, 0)
    total = v + e
    if total > 0:
        print(f"  {h:02d}   {v:>3}   {e:>3}   ({v/total*100:.0f}% kept)")

# Asia session: 00-07 UTC, London: 08-15 UTC, NY: 13-21 UTC
sessions = {
    "Asia (00-07)": range(0, 8),
    "London (08-15)": range(8, 16),
    "NY (13-21)": range(13, 22),
}

print(f"\nSession breakdown:")
print(f"{'Session':>15} {'v17':>5} {'excl':>5} {'kept%':>8}")
print("-" * 35)
for sname, hrs in sessions.items():
    v = sum(v17_hours.get(h, 0) for h in hrs)
    e = sum(exc_hours.get(h, 0) for h in hrs)
    total = v + e
    kept_pct = v / total * 100 if total > 0 else 0
    print(f"  {sname:>13}  {v:>5}  {e:>5}  {kept_pct:>7.0f}%")

# --- Conclusion ---
print("\n" + "=" * 72)
print("CONCLUSION")
print("=" * 72)

net_excluded = sum(exc_r)
pct_losers = len(exc_losers) / len(excluded) * 100

if net_excluded < -10 and pct_losers > 55:
    print("ATR filter removes NET-NEGATIVE trades with HIGH loser rate.")
    print("Evidence: filter removes noise, not signal.")
elif net_excluded < 0:
    print("ATR filter removes slightly negative trades.")
    print("Evidence: filter removes some noise, marginal improvement.")
else:
    print("ATR filter removes net-POSITIVE trades.")
    print("Warning: filter may be removing signal, not noise.")

# Per-year
print(f"\nPer-year breakdown:")
for year in ["2023", "2024", "2025", "2026"]:
    v17_y = [t for t in v17_trades if t["entry_date"][:4] == year]
    v12_y = [t for t in v12_trades if t["entry_date"][:4] == year]
    exc_y = [t for t in excluded if t["entry_date"][:4] == year]
    v17_net = sum(t["r_multiple"] for t in v17_y)
    v12_net = sum(t["r_multiple"] for t in v12_y)
    exc_net = sum(t["r_multiple"] for t in exc_y)
    print(f"  {year}: v12={len(v12_y)}tr/{v12_net:+.1f}R  v17={len(v17_y)}tr/{v17_net:+.1f}R  excl={len(exc_y)}tr/{exc_net:+.1f}R")

print(f"Excluded avg R/trade:{statistics.mean(t['r_multiple'] for t in excluded):+.3f}")
