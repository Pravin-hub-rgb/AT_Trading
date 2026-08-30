import requests
r = requests.get('http://127.0.0.1:8003/api/intraday/backtest?sl_mode=avg')
s = r.json()['stats']
print('Server avg: trades={} wins={} win_rate={}% total_r={}'.format(
    s['trades'], s['wins'], s['win_rate'], s['total_r']))
