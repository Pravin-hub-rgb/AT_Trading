"""Check why 1-min FS isn't being computed for 28 Aug."""
import requests, json

# Test with 1min execution + opposite_swing_needed (this is where 1-min FS is computed)
r = requests.get('http://localhost:8003/api/intraday/backtest', params={
    'swing_mode': 'opposite_swing_needed',
    'bias': 'combined',
    'execution': '1min',
    'entry_method': 'pivot_break',
    'start': '2026-08-28',
    'end': '2026-08-28'
}, timeout=120)
data = r.json()
for d in data.get('days', []):
    if d.get('date') == '2026-08-28':
        print(f"=== 28 Aug (pivot_break + 1min + opposite_swing_needed) ===")
        print(f"All keys: {sorted(d.keys())}")
        print(f"swing_direction: {d.get('swing_direction')}")
        print(f"first_swing_confirmed_idx: {d.get('first_swing_confirmed_idx')}")
        print(f"first_swing_end_time: {d.get('first_swing_end_time')}")
        print(f"fs1_1min_confirmed_idx_5min: {d.get('fs1_1min_confirmed_idx_5min')}")
        print(f"fs1_1min_confirmed_time: {d.get('fs1_1min_confirmed_time')}")
        print(f"swing2_direction: {d.get('swing2_direction')}")
        print(f"swing2_confirmed_idx: {d.get('swing2_confirmed_idx')}")
        print(f"Trades: {len(d.get('trades', []))}")
        for t in d.get('trades', []):
            print(f"  {t.get('entry_time')} | {t.get('dir')} | {t.get('r_multiple',0):.2f}R | pace={t.get('pace_break_type','N/A')} | level={t.get('level','N/A')}")
        
        print(f"\n=== All events ===")
        for e in d.get('events', []):
            print(f"  {e.get('time')} | {e.get('type')} | bar={e.get('bar','N/A')} | conf_idx={e.get('confirmed_at_idx','N/A')} | dir={e.get('dir','N/A')} | level={e.get('level','N/A')} | break={e.get('break_type','N/A')}")
