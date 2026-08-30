"""Check if prev_pivot mode actually uses pivots or falls back to avg."""
import requests
import json

url = "http://127.0.0.1:8003/api/intraday/backtest"

# Test prev_pivot mode
params = {
    "sl_mode": "prev_pivot",
    "sl_pivot_buffer": 1.0,
}
r = requests.get(url, params=params, timeout=120)
data = r.json()
print(f"=== sl_mode=prev_pivot ===")
print(f"trades={data.get('trades')}, win_rate={data.get('win_rate'):.1f}, total_r={data.get('total_r'):.2f}")
print(f"days={data.get('days')}, long={data.get('long_count')}, short={data.get('short_count')}")

# Inspect the days for sl_mode_used if present
days = data.get("days", [])
sl_modes_used = {}
for d in days:
    for t in d.get("trades", []):
        key = t.get("sl_mode_used", t.get("sl_mode", "unknown"))
        sl_modes_used[key] = sl_modes_used.get(key, 0) + 1
print(f"sl_modes_used breakdown: {sl_modes_used}")

# Show first 3 trades
print("\n=== First 3 trades ===")
shown = 0
for d in days:
    for t in d.get("trades", []):
        if shown >= 3:
            break
        print(json.dumps(t, indent=2, default=str))
        shown += 1
    if shown >= 3:
        break

# Now test avg mode for comparison
print("\n\n=== sl_mode=avg ===")
params2 = {"sl_mode": "avg"}
r2 = requests.get(url, params=params2, timeout=120)
data2 = r2.json()
print(f"trades={data2.get('trades')}, win_rate={data2.get('win_rate'):.1f}, total_r={data2.get('total_r'):.2f}")
print(f"days={data2.get('days')}, long={data2.get('long_count')}, short={data2.get('short_count')}")

days2 = data2.get("days", [])
sl_modes_used2 = {}
for d in days2:
    for t in d.get("trades", []):
        key = t.get("sl_mode_used", t.get("sl_mode", "unknown"))
        sl_modes_used2[key] = sl_modes_used2.get(key, 0) + 1
print(f"sl_modes_used breakdown: {sl_modes_used2}")

# Are the trade counts and totals identical?
print("\n=== Comparison ===")
print(f"Same trade count? {data.get('trades') == data2.get('trades')}")
print(f"Same total_r?     {data.get('total_r') == data2.get('total_r')}")
print(f"Same win_rate?    {data.get('win_rate') == data2.get('win_rate')}")
