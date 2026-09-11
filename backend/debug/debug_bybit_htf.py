import sys; sys.path.insert(0, '.')
from src.btc.btc_routes import _load_window, _compute_swings
from src.btc.engines.v7_timecap import simulate_btc_trades_v7

htf_win, _ = _load_window('1h', None, 'BTCUSDT_BYBIT')
htf_candles, htf_flow = htf_win
htf_swings = _compute_swings(htf_flow, 'b2_vs_flip_chop', min_bars=20)

print(f'HTF candles: {len(htf_candles)}, swings: {len(htf_swings)}')
for i, s in enumerate(htf_swings[:5]):
    idx = s.get("confirmed_at_idx")
    d = s.get("dir")
    print(f'  swing[{i}] dir={d} confirmed_at_idx={idx}')

# Compare with spot
htf_win2, _ = _load_window('1h', None, 'BTCUSDT')
htf_candles2, htf_flow2 = htf_win2
htf_swings2 = _compute_swings(htf_flow2, 'b2_vs_flip_chop', min_bars=20)
print(f'\nSpot HTF candles: {len(htf_candles2)}, swings: {len(htf_swings2)}')
htf_b2_spot = simulate_btc_trades_v7(htf_candles2, htf_swings2, entry_break='b2', sl_mode='swing', rr_target=3.0, trailing='off', breakeven_r=0.0, skip_first=True, cap_days=16)
print(f'Spot HTF b2 trades: {len(htf_b2_spot)}')

# Try no fine on bybit
htf_b2 = simulate_btc_trades_v7(htf_candles, htf_swings, entry_break='b2', sl_mode='swing', rr_target=3.0, trailing='off', breakeven_r=0.0, skip_first=True, cap_days=16)
print(f'Bybit HTF b2 (no fine): {len(htf_b2)} trades')
htf_flip = simulate_btc_trades_v7(htf_candles, htf_swings, entry_break='flip', sl_mode='swing', rr_target=3.0, trailing='off', breakeven_r=0.0, skip_first=True, cap_days=16)
print(f'Bybit HTF flip (no fine): {len(htf_flip)} trades')
