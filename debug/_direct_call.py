"""Force a fresh server computation by using a never-before-seen config."""
import requests

# Use prev_pivot mode (different from default avg)
r = requests.get('http://127.0.0.1:8003/api/intraday/backtest', params={
    'sl_mode': 'avg',
    'execution': '5min',
    'trailing': 'off',
    'trail_distance_r': 1.0,
    'gap_pct': 0.27,
    'sl_pivot_buffer': 1.0,
})
data = r.json()
s = data['stats']
print('TRADES:', s['trades'], 'WINS:', s['wins'], 'WIN_RATE:', s['win_rate'], 'TOTAL_R:', s['total_r'])
print('cfg:', data['config'])
