import requests

# Use a unique buffer to force fresh computation
r = requests.get('http://127.0.0.1:8003/api/intraday/backtest?sl_mode=avg&sl_pivot_buffer=2.5')
s = r.json()['stats']
print('trades', s['trades'], 'wins', s['wins'], 'win_rate', s['win_rate'], 'total_r', s['total_r'])
