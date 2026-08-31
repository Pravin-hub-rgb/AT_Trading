"""Check what pivot exists at 10:21 on 28 Aug 1-min data."""
import sys, csv, json

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
                'ts': ts,
                'o': float(row['open']),
                'h': float(row['high']),
                'l': float(row['low']),
                'c': float(row['close']),
            })

print(f"28 Aug 1-min bars: {len(bars)}", file=sys.stderr)
if not bars:
    print("NO BARS FOUND for 28 Aug!", file=sys.stderr)
    sys.exit(1)

print(f"First bar: {bars[0]['ts']}", file=sys.stderr)
print(f"Last bar: {bars[-1]['ts']}", file=sys.stderr)

# Find bars around 10:20-10:25
print("\n=== Bars 10:20-10:25 ===", file=sys.stderr)
for b in bars:
    t = b['ts']
    if '10:2' in t or ('10:1' in t and '10:15' <= t.split(' ')[1] <= '10:25'):
        print(f"{t} O={b['o']:.2f} H={b['h']:.2f} L={b['l']:.2f} C={b['c']:.2f}", file=sys.stderr)

# Find pivot lows in this range
print("\n=== Pivot LOWS in 10:15-10:30 ===", file=sys.stderr)
for i, b in enumerate(bars):
    t = b['ts']
    time_part = t.split(' ')[1] if ' ' in t else t
    if '10:15' <= time_part <= '10:30':
        # A pivot low: current low < prev low AND current low < next low
        if i > 0 and i < len(bars)-1:
            if b['l'] < bars[i-1]['l'] and b['l'] < bars[i+1]['l']:
                print(f"PIVOT LOW at {t}: {b['l']:.2f} (surround: {bars[i-1]['l']:.2f} / {bars[i+1]['l']:.2f})", file=sys.stderr)

# Find pivot highs in this range
print("\n=== Pivot HIGHS in 10:15-10:30 ===", file=sys.stderr)
for i, b in enumerate(bars):
    t = b['ts']
    time_part = t.split(' ')[1] if ' ' in t else t
    if '10:15' <= time_part <= '10:30':
        if i > 0 and i < len(bars)-1:
            if b['h'] > bars[i-1]['h'] and b['h'] > bars[i+1]['h']:
                print(f"PIVOT HIGH at {t}: {b['h']:.2f} (surround: {bars[i-1]['h']:.2f} / {bars[i+1]['h']:.2f})", file=sys.stderr)
