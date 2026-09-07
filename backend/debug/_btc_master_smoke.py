"""Smoke test: LIVE server /api/btc/backtest with min_bars + regime params."""
import json
import urllib.request

url = (
    "http://127.0.0.1:8003/api/btc/backtest"
    "?tf=5m&mode=continuous&limit=3000&entry_break=flip"
    "&min_bars=20&regime=streak_311&bias=15m"
)
with urllib.request.urlopen(url, timeout=60) as resp:
    r = json.loads(resp.read())

p, s = r["params"], r["stats"]
print("params:", {k: p.get(k, "<MISSING>") for k in ("min_bars", "regime", "bias", "bias_applied")})
print("swings:", r["swings_used"])
print("trades:", s["trades"], "win_rate:", s["win_rate"], "total_r:", s["total_r"], "avg_r:", s["avg_r"])
