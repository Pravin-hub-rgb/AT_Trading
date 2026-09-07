import io
import re

p = "backend/src/btc/btc_routes.py"
s = io.open(p, encoding="utf-8").read()

# 1. add bestTf to each preset in _MASTER_PRESETS
tf_map = {
    "decisive50": "15m", "flip50": "15m", "flip30": "15m",
    "sniper": "15m", "flip_bias": "15m", "baseline": "15m",
    "trail_max_r": "15m", "flip_quality": "15m",
    "flip1h20": "1h", "decisive1h30": "1h", "flip1h30": "1h", "flip1h20t": "1h",
}
for key, tf in tf_map.items():
    marker = f'{{"key": "{key}",'
    if marker in s:
        s = s.replace(marker, f'{{"key": "{key}", "bestTf": "{tf}",', 1)

# 2. fix the summary function - use p["bestTf"] directly (no fallback to tf)
s = s.replace('ptf = p.get("bestTf", tf)', 'ptf = p.get("bestTf", "15m")')

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("bestTf added to presets, summary fixed")
