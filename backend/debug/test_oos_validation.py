import sys, statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))
from src.btc.btc_config import load_btc_df
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.btc.engines.htf_ltf.v11_conditional_htf import simulate_htf_ltf_conditional
from src.walker import FlowCandle

def load_window(tf, start_year=None, end_year=None):
    df = load_btc_df(tf)
    candles, flow = [], []
    for row in df.itertuples():
        date = row.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        if start_year and row.timestamp.year < start_year:
            continue
        if end_year and row.timestamp.year > end_year:
            continue
        candles.append({'date': date, 'ts': int(row.ts), 'open': float(row.open), 'high': float(row.high), 'low': float(row.low), 'close': float(row.close), 'volume': 0, 'oi': 0})
        flow.append(FlowCandle(date=date, open=float(row.open), high=float(row.high), low=float(row.low), close=float(row.close)))
    return candles, flow

print('OOS VALIDATION')
print()

c1h_is, f1h_is = load_window('1h', 2023, 2024)
c15_is, f15_is = load_window('15m', 2023, 2024)
sw1h_is = _compute_swings(f1h_is, 'continuous', min_bars=20)
sw15_is = _compute_swings(f15_is, 'continuous', min_bars=50)
t0_is = min(c1h_is[0]['ts'], c15_is[0]['ts'])
t1_is = max(c1h_is[-1]['ts'], c15_is[-1]['ts'])
fine_is = _load_fine_1m(t0_is, t1_is)

c1h_oos, f1h_oos = load_window('1h', 2025, 2026)
c15_oos, f15_oos = load_window('15m', 2025, 2026)
sw1h_oos = _compute_swings(f1h_oos, 'continuous', min_bars=20)
sw15_oos = _compute_swings(f15_oos, 'continuous', min_bars=50)
t0_oos = min(c1h_oos[0]['ts'], c15_oos[0]['ts'])
t1_oos = max(c1h_oos[-1]['ts'], c15_oos[-1]['ts'])
fine_oos = _load_fine_1m(t0_oos, t1_oos)

print('IS window (2023-2024):', len(c15_is), '15m bars,', len(sw15_is), 'swings')
print('OOS window (2025-2026):', len(c15_oos), '15m bars,', len(sw15_oos), 'swings')
print()

v12_is = simulate_htf_ltf_conditional(c15_is, sw15_is, c1h_is, sw1h_is, fine_is, cooldown_bars=20)
v12_oos = simulate_htf_ltf_conditional(c15_oos, sw15_oos, c1h_oos, sw1h_oos, fine_oos, cooldown_bars=20)

v18_is = simulate_htf_ltf_streak_halt(c15_is, sw15_is, c1h_is, sw1h_is, fine_is, cooldown_bars=20, max_consecutive_losses=5)
v18_oos = simulate_htf_ltf_streak_halt(c15_oos, sw15_oos, c1h_oos, sw1h_oos, fine_oos, cooldown_bars=20, max_consecutive_losses=5)

print('IS (2023-2024):')
print('  v12+cd20:', len(v12_is), 'trades, net=', round(sum(t['r_multiple'] for t in v12_is), 2))
print('  v18 halt5L:', len(v18_is), 'trades, net=', round(sum(t['r_multiple'] for t in v18_is), 2))
print()
print('OOS (2025-2026):')
print('  v12+cd20:', len(v12_oos), 'trades, net=', round(sum(t['r_multiple'] for t in v12_oos), 2))
print('  v18 halt5L:', len(v18_oos), 'trades, net=', round(sum(t['r_multiple'] for t in v18_oos), 2))
print()

print('STREAK ANALYSIS (IS 2023-2024):')
streaks = []
cur = 0
for t in v12_is:
    if t['r_multiple'] <= 0:
        cur += 1
    else:
        if cur > 0:
            streaks.append(cur)
        cur = 0
if cur > 0:
    streaks.append(cur)
print('  Total streaks:', len(streaks))
print('  Max streak:', max(streaks) if streaks else 0)
if streaks:
    print('  Avg streak:', round(statistics.mean(streaks), 1))
print()

print('RECOVERY AFTER STREAK (IS):')
for streak_len in [1, 2, 3, 4, 5, 6, 7]:
    next_trades = []
    cur = 0
    for i, t in enumerate(v12_is):
        if t['r_multiple'] <= 0:
            cur += 1
        else:
            if cur == streak_len and i + 1 < len(v12_is):
                next_trades.append(v12_is[i + 1]['r_multiple'])
            cur = 0
    if next_trades:
        wins = sum(1 for r in next_trades if r > 0)
        print('  After', streak_len, 'L: n=', len(next_trades), ', avg=', round(statistics.mean(next_trades), 3), ', win=', wins, '/', len(next_trades), sep='')
print()

print('WHAT v18 SKIPS IN OOS:')
skipped_oos = []
cur_losses = 0
for t in v12_oos:
    if t['r_multiple'] <= 0:
        cur_losses += 1
        if cur_losses >= 5:
            skipped_oos.append(t)
    else:
        cur_losses = 0
print('  Skipped trades:', len(skipped_oos))
if skipped_oos:
    print('  Skipped avg R:', round(statistics.mean(t['r_multiple'] for t in skipped_oos), 3))
    print('  Skipped winners:', sum(1 for t in skipped_oos if t['r_multiple'] > 0))
    print('  Skipped losers:', sum(1 for t in skipped_oos if t['r_multiple'] <= 0))
print()

print('OOS PER-YEAR:')
for year in [2025, 2026]:
    v12_y = [t for t in v12_oos if int(t['date'][:4]) == year]
    v18_y = [t for t in v18_oos if int(t['date'][:4]) == year]
    v12_net = sum(t['r_multiple'] for t in v12_y)
    v18_net = sum(t['r_multiple'] for t in v18_y)
    print(' ', year, ': v12=', len(v12_y), 'tr ', round(v12_net, 1), 'R | v18=', len(v18_y), 'tr ', round(v18_net, 1), 'R', sep='')
