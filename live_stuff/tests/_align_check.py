import sys
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading')
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff')
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests')
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\backend')
import bisect
from exp_thesis_htf_deep_atlas import load_scope, build_windows
for scope in ('is','oos'):
    d=load_scope(scope)
    fine=d['fine']; fts=[int(c['ts']) for c in fine]
    w=build_windows(d,3.0,16)['flip']
    ok=bad=0
    for t in w[:60]:
        ets=int(t['entry_ts']); ep=float(t['entry_price'])
        i=bisect.bisect_left(fts, ets+900)
        if i>=len(fine): bad+=1; continue
        lo=min(float(fine[k]['low']) for k in range(i,min(i+30,len(fine))))
        hi=max(float(fine[k]['high']) for k in range(i,min(i+30,len(fine))))
        if lo<=ep<=hi: ok+=1
        else: bad+=1
    print(scope,'fine0',fine[0]['date'],'c15_0',d['c15'][0]['date'],'ok',ok,'bad',bad, flush=True)
