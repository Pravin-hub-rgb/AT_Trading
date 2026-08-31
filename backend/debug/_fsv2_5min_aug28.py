"""Build 5-min payload for 28 Aug and POST to /api/firstswing/compute."""
import json
import sys
import os
import urllib.request
import urllib.error

# Read 5-min data
import csv
bars = []
with open(r'C:\Users\Pravin\Desktop\main\AT_Trading\data\nifty_5min.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['timestamp'].startswith('2026-08-28'):
            bars.append({
                'date': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
            })

print(f'5-min bars: {len(bars)}')
for i, b in enumerate(bars):
    print(f'  idx {i}: {b["date"]} O={b["open"]} H={b["high"]} L={b["low"]} C={b["close"]}')

# POST to server
url = 'http://localhost:8003/api/firstswing/compute'
req = urllib.request.Request(
    url,
    data=json.dumps(bars).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    print(f'\n=== FsV2 results: {len(data)} entries ===')
    for entry in data:
        seg = entry.get('seg')
        if seg:
            print(f'  confIdx={entry.get("confIdx")}, confTime={entry.get("confTime")}, dir={entry.get("dir")}, source={entry.get("source")}')
            print(f'  seg: {json.dumps(seg)}')
            breaks = entry.get('breaks', [])
            if breaks:
                print(f'  breaks: {breaks}')
        else:
            print(f'  [no seg] confIdx={entry.get("confIdx")}, dir={entry.get("dir")}')
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()[:500]}')
except Exception as e:
    print(f'Error: {e}')
