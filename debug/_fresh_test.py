import requests

# Use unique buffer to force fresh computation
r = requests.get('http://127.0.0.1:8003/api/intraday/backtest', params={
    'sl_mode': 'avg',
    'sl_pivot_buffer': 9.9,
})
s = r.json()['stats']
print('trades', s['trades'], 'wins', s['wins'], 'win_rate', s['win_rate'], 'total_r', s['total_r'])
