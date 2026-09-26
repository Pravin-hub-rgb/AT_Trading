import sys, bisect
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading')
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff')
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests')
sys.path.insert(0, r'C:\Users\Pravin\Desktop\main\AT_Trading\backend')
from exp_thesis_htf_deep_atlas import load_scope, build_windows
for scope in ('is','oos'):
    d=load_scope(scope); fine=d['fine']; fts=[int(c['ts']) for c in fine]
    ok=bad=0
    for lane in ('flip','b2'):
        for t in build_windows(d,3.0,16)[lane]:
            ets=int(t['entry_ts']); ep=float(t['entry_price'])
            i=bisect.bisect_left(fts, ets+3600)
            if i>=len(fine): bad+=1; continue
            seg=range(i,min(i+60,len(fine)))
            lo=min(float(fine[k]['low']) for k in seg); hi=max(float(fine[k]['high']) for k in seg)
            if lo<=ep<=hi: ok+=1
            else: bad+=1
    print(scope,'entry_in_fine ok',ok,'bad',bad, flush=True)
