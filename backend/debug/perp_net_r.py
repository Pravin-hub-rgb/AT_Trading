import sys; sys.path.insert(0, r'backend')
import pandas as pd
from pathlib import Path
from src.btc.btc_routes import _compute_swings
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.walker import FlowCandle

IST_OFF = 19800
DATA_DIR = Path(r'data/btc-fut')
FEE_PCT = 0.05   # 0.05% per side
SLIP_PTS = 2.0   # 2 points slippage per trade

def load_fut(tf):
    path = DATA_DIR / f'BTCUSDT_{tf}.csv'
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').drop_duplicates(subset='timestamp', keep='last').reset_index(drop=True)
    df['ts'] = (df['timestamp'].astype('int64') // 10**9) - IST_OFF
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        candles.append({'date': date, 'ts': int(row.ts), 'open': float(row.open), 'high': float(row.high),
                        'low': float(row.low), 'close': float(row.close), 'volume': 0, 'oi': 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high),
                               low=float(row.low), close=float(row.close)))
    return candles, flow

c1h, f1h = load_fut('1h')
c15, f15 = load_fut('15m')
sw1h = _compute_swings(f1h, 'continuous', min_bars=20)
sw15 = _compute_swings(f15, 'continuous', min_bars=50)

tr = simulate_htf_ltf_streak_halt(
    c1h, sw1h, c15, sw15, fine_ltf=[],
    sl_buf_atr=0.25, ext_stop_r=1.5, mode='b2_vs_flip_chop',
    cooldown_bars=20, max_consecutive_losses=5
)['ltf_trades']

# Calculate net R per trade
print("BTCUSDT PERP - v18 Net R Breakdown (after costs)")
print("=" * 70)
header = "{:<6} {:>6} {:>9} {:>7} {:>9} {:>7} {:>9}".format(
    "Year", "Trades", "Gross R", "Costs R", "Net R", "Win%", "Avg Net")
print(header)
print("-" * 70)

years = {}
for t in tr:
    y = t['entry_date'][:4]
    years.setdefault(y, {'n': 0, 'gross': 0.0, 'costs': 0.0, 'wins': 0})
    years[y]['n'] += 1
    years[y]['gross'] += t['r_multiple']
    if t['r_multiple'] > 0:
        years[y]['wins'] += 1

    # Cost calculation
    entry = abs(t['entry_price'])
    sl = abs(t['sl'])
    risk = abs(entry - sl)
    if risk < 0.01:
        risk = 1.0
    round_trip_fee = 2.0 * (FEE_PCT / 100.0) * entry
    cost_pts = round_trip_fee + SLIP_PTS
    cost_r = cost_pts / risk
    years[y]['costs'] += cost_r

total_gross = 0.0
total_costs = 0.0
total_n = 0
total_wins = 0

for y in sorted(years):
    d = years[y]
    net = d['gross'] - d['costs']
    wr = 100 * d['wins'] / d['n'] if d['n'] else 0
    avg_net = net / d['n'] if d['n'] else 0
    print("{:<6} {:>6} {:>+9.1f} {:>7.1f} {:>+9.1f} {:>6.1f}% {:>+7.2f}".format(
        y, d['n'], d['gross'], d['costs'], net, wr, avg_net))
    total_gross += d['gross']
    total_costs += d['costs']
    total_n += d['n']
    total_wins += d['wins']

total_net = total_gross - total_costs
print("-" * 70)
print("{:<6} {:>6} {:>+9.1f} {:>7.1f} {:>+9.1f} {:>6.1f}% {:>+7.2f}".format(
    "TOTAL", total_n, total_gross, total_costs, total_net,
    100 * total_wins / total_n if total_n else 0,
    total_net / total_n if total_n else 0))

print()
print("Cost assumptions: {}% fee per side, {} pts slippage".format(FEE_PCT, SLIP_PTS))
print("Spot baseline: 331.1R gross, ~286R net (from earlier)")
print("Perp vs Spot net: {:.1f}R vs ~286R".format(total_net))
