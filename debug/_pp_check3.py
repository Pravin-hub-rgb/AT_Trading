"""Check if prev_pivot mode actually uses pivots or falls back to avg."""
import requests
import json

url = "http://127.0.0.1:8003/api/intraday/backtest"

def get_data(params):
    r = requests.get(url, params=params, timeout=120)
    data = r.json()
    stats = data.get("stats", {})
    days = data.get("days", [])
    trades_data = []
    for d in days:
        for t in d.get("trades", []):
            trades_data.append(t)
    return stats, trades_data

# Test prev_pivot mode
print("=== sl_mode=prev_pivot ===")
params1 = {"sl_mode": "prev_pivot", "sl_pivot_buffer": 1.0}
stats1, trades1 = get_data(params1)
print(f"trades={stats1['trades']}, win_rate={stats1['win_rate']:.1f}%, total_r={stats1['total_r']:.2f}")

# sl_mode_used breakdown
sl_modes_used = {}
sl_px_values = []
for t in trades1:
    key = t.get("sl_mode_used", "MISSING")
    sl_modes_used[key] = sl_modes_used.get(key, 0) + 1
    sl_px_values.append({
        "date": t.get("date", "?")[:10],
        "entry_bar": t.get("entry_bar"),
        "sl_mode_used": key,
        "sl": t.get("sl"),
        "entry": t.get("entry"),
    })
print(f"sl_mode_used breakdown: {sl_modes_used}")

# Show first 5 trades with details
print("\n=== First 5 trades (prev_pivot) ===")
for t in trades1[:5]:
    print(json.dumps(t, indent=2, default=str))

# Test avg mode
print("\n\n=== sl_mode=avg ===")
params2 = {"sl_mode": "avg"}
stats2, trades2 = get_data(params2)
print(f"trades={stats2['trades']}, win_rate={stats2['win_rate']:.1f}%, total_r={stats2['total_r']:.2f}")

# Comparison
print(f"\n=== Comparison ===")
print(f"Same trade count? {stats1['trades'] == stats2['trades']}")
print(f"Same total_r?    {stats1['total_r'] == stats2['total_r']}")
print(f"Same win_rate?   {stats1['win_rate'] == stats2['win_rate']}")
print(f"Same outcomes?   {stats1['outcomes'] == stats2['outcomes']}")

# SL values comparison for first 5 trades
print("\n=== SL comparison (first 5 trades) ===")
print(f"{'idx':<4} {'entry':>8} {'avg_sl':>8} {'pp_sl':>8} {'same?':>6}")
for i in range(min(5, len(trades1), len(trades2))):
    t1 = trades1[i]
    t2 = trades2[i]
    avg_sl = t2.get("sl")
    pp_sl = t1.get("sl")
    same = "YES" if abs((avg_sl or 0) - (pp_sl or 0)) < 0.001 else "NO"
    print(f"{i:<4} {t1.get('entry', 0):>8.2f} {(avg_sl or 0):>8.2f} {(pp_sl or 0):>8.2f} {same:>6}")
