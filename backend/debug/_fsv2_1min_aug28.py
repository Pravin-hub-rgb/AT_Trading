"""POST 1-min 28 Aug bars to /api/firstswing/compute to find first swing."""
import sys, csv, json, os
import urllib.request

# Read 1-min CSV
bars = []
with open(r'C:\Users\Pravin\Desktop\main\AT_Trading\data\nifty_1min.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts = row.get('timestamp', '') or row.get('date', '')
        if not ts:
            continue
        if '2026-08-28' in ts:
            bars.append({
                "date": ts,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
            })

out = []
out.append(f"28 Aug 1-min bars: {len(bars)}")
if not bars:
    out.append("NO BARS!")
    with open(r'C:\Users\Pravin\Desktop\main\AT_Trading\backend\debug\_fsv2_1min_result.txt', 'w') as f:
        f.write('\n'.join(out))
    sys.exit(1)

# Show first and last bars
out.append(f"First bar: {bars[0]['date']}")
out.append(f"Last bar: {bars[-1]['date']}")

# POST to /api/firstswing/compute on both ports
for port in [8003, 8004]:
    url = f'http://localhost:{port}/api/firstswing/compute'
    data = json.dumps(bars).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            results = json.loads(r.read())
            out.append(f'\nPort {port}: {len(results)} results')
            for res in results:
                out.append(json.dumps(res, indent=2))
    except Exception as e:
        out.append(f'Port {port}: Error - {e}')

# Write output
output_path = r'C:\Users\Pravin\Desktop\main\AT_Trading\backend\debug\_fsv2_1min_result.txt'
with open(output_path, 'w') as f:
    f.write('\n'.join(out))
print(f"Written to {output_path}")
