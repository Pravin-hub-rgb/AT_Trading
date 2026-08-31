"""Check full API response for pivot_break settings."""
import json, urllib.request, urllib.parse

params = {
    "sl_mode": "avg",
    "execution": "1min",
    "trailing": "off",
    "trail_distance_r": "1.0",
    "gap_pct": "0.27",
    "sl_pivot_buffer": "1.0",
    "ft_fail_enabled": "true",
    "entry_method": "pivot_break",
    "swing_mode": "opposite_swing_needed",
}
url = f"http://127.0.0.1:8003/api/intraday/backtest?" + urllib.parse.urlencode(params)
try:
    with urllib.request.urlopen(url, timeout=120) as r:
        raw = r.read().decode("utf-8")
        data = json.loads(raw)
except Exception as e:
    print("ERR:", e)
    raise SystemExit(1)

print("Keys in response:", list(data.keys()))
print("\nStats keys:", list(data.get("stats", {}).keys()) if isinstance(data.get("stats"), dict) else data.get("stats"))
print("Total days:", len(data.get("days", [])))
print("\nAll days with trades:")
for d in data.get("days", []):
    nt = d.get("n_trades", 0)
    if nt > 0:
        print(f"  {d['date']}: {nt} trades, case={d.get('case')}, outcomes={d.get('outcomes')}")
