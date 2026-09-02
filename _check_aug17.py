import pandas as pd

df = pd.read_csv('data/nifty_1min.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
df['time'] = df['timestamp'].dt.strftime('%H:%M')

print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print()

# Check 17 Aug
aug17 = df[df['date'] == '2026-08-17']
print(f"Aug 17 rows: {len(aug17)}")
print()

# Show 10:10 to 10:20
sub = aug17[(aug17['time'] >= '10:10') & (aug17['time'] <= '10:20')]
print("10:10 to 10:20:")
for _, r in sub.iterrows():
    print(f"  {r['time']}  O:{r['open']:.2f}  H:{r['high']:.2f}  L:{r['low']:.2f}  C:{r['close']:.2f}")
