import requests
import json

URL = 'http://127.0.0.1:8003/api/intraday/2026-08-27'
PARAMS = '?execution=1min&sl_mode=prev_pivot&entry_method=pivot_break&swing_mode=opposite_swing_needed'

for url in [URL, URL + PARAMS]:
    print(f'\n=== GET {url.split("/api")[-1]} ===')
    try:
        r = requests.get(url, timeout=30)
        print('STATUS:', r.status_code)
        print('LEN:', len(r.text))
        if r.status_code == 200:
            d = r.json()
            print('trades count:', len(d.get('trades', [])))
            for t in d.get('trades', []):
                print('  TRADE:', t)
            print('case:', d.get('case'))
            print('trade_mode:', d.get('trade_mode'))
            # Also show key events
            events = d.get('events', [])
            for e in events:
                et = e.get('type', '')
                if et in ('fs_segment','fs2_segment','second_swing_armed','pace_break','entry','exit'):
                    print('  EV:', et, e.get('time',''), e)
    except Exception as e:
        print('ERROR:', e)