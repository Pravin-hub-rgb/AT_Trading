import requests, json

# Test server health
try:
    r = requests.get('http://localhost:8003/api/swings?limit=1', timeout=5)
    print(f"Server health: {r.status_code}")
except Exception as e:
    print(f"Server not reachable: {e}")

# Test the day endpoint
try:
    r2 = requests.get('http://localhost:8003/api/intraday/2026-08-28', timeout=30)
    print(f"Day endpoint: {r2.status_code}")
    if r2.status_code == 200:
        d = r2.json()
        print(f"  Swing direction: {d.get('swing_direction')}")
        print(f"  First swing: conf_idx={d.get('first_swing_confirmed_idx')} time={d.get('first_swing_end_time')}")
        print(f"  1-min FS 5min idx: {d.get('fs1_1min_confirmed_idx_5min')}")
        print(f"  1-min FS time: {d.get('fs1_1min_confirmed_time')}")
        print(f"  Trades: {len(d.get('trades', []))}")
        for t in d.get('trades', []):
            print(f"    {t.get('entry_time')} | {t.get('dir')} | {t.get('r_multiple',0):.2f}R")
        print(f"\n  Events (first 20):")
        for e in d.get('events', [])[:20]:
            print(f"    {e.get('time')} | {e.get('type')} | bar={e.get('bar','N/A')}")
except Exception as e:
    print(f"Day endpoint error: {e}")
