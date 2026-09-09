import sys, urllib.request, urllib.error
sys.path.insert(0, "backend")
from src.live.boot_data import fetch_klines
try:
    c = fetch_klines("BTCUSDT", "15m", 10)
    print("OK", len(c), c[-1])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:300])
    print("url:", e.url)
