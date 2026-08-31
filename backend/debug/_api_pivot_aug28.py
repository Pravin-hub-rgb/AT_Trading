"""Hit the LIVE server endpoint with user's settings to see if trade is returned."""
import json
import urllib.request
import urllib.parse

# User's exact settings
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
qs = urllib.parse.urlencode(params)
url = f"http://127.0.0.1:8003/api/intraday/backtest?{qs}"
print("GET", url)

try:
    with urllib.request.urlopen(url, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))
except Exception as e:
    print("ERR:", e)
    raise SystemExit(1)

stats = data.get("stats", {})
print("\n=== STATS ===")
print("  total_trades:", stats.get("total_trades"))
print("  net_r       :", stats.get("net_r"))

print("\n=== 2026-08-28 day ===")
target = None
for d in data.get("days", []):
    if d["date"] == "2026-08-28":
        target = d
        break

if target is None:
    print("  day not found")
else:
    print("  bias     :", target.get("bias"))
    print("  case     :", target.get("case"))
    print("  swing_dir:", target.get("swing_direction"))
    print("  n_trades :", target.get("n_trades"))
    print("  outcomes :", target.get("outcomes"))
    print("\n  --- trades ---")
    for i, t in enumerate(target.get("trades", [])):
        print(f"    [{i}] dir={t.get('dir')} entry_ts={t.get('entry_ts')} "
              f"entry_px={t.get('entry_price')} exit_ts={t.get('exit_ts')} "
              f"outcome={t.get('outcome')} R={t.get('r_multiple'):.3f}")
