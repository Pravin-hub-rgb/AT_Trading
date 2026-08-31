import requests, json
r = requests.get('http://localhost:8003/api/intraday/backtest', params={
    'swing_mode': 'pivot_break',
    'bias': 'combined',
    'entry': '1min',
    'start': '2026-08-28',
    'end': '2026-08-28'
}, timeout=120)
print(f'Status: {r.status_code}', flush=True)
data = r.json()
print(f'Keys: {list(data.keys())}', flush=True)
days = data.get('days', [])
print(f'Days: {len(days)}', flush=True)
for d in days:
    print(f'  {d.get("date")}: trades={len(d.get("trades",[]))}, fs1_conf={d.get("fs1_confirmed_time","N/A")}, fs1_end={d.get("fs1_end_time","N/A")}, fs2={d.get("fs2_confirmed_time","N/A")}', flush=True)
    for t in d.get('trades', []):
        print(f'    Trade: entry={t.get("entry_time","")} | dir={t.get("direction","")} | pnl={t.get("pnl_r",0):.2f}R | gate_ts={t.get("gate_open_ts","")} | pivot_break_ts={t.get("pivot_break_ts","")} | type={t.get("entry_kind","")}', flush=True)
print('--- full day ---', flush=True)
for d in days:
    print(json.dumps(d, indent=2, default=str)[:3000], flush=True)
