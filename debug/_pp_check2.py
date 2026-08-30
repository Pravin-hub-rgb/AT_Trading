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
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2, default=str)[:2000])
