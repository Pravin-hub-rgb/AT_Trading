"""Full HTF sweep — find TRUE best configs with current engine (stream+1m fine).

Mimics _btc_htf_sweep.py but FULL window continuous, correct trail fix.
Prints Top 25 by net_r.
"""
import sys
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")
from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs, _streak_regime_gate
from src.btc.btc_engine import simulate_btc_trades

fee_pct=0.05
slip=2.0

def load_window(tf):
    df=load_btc_df(tf)
    candles=[]
    flow=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({'date':date,'ts':int(row.ts),'open':float(row.open),'high':float(row.high),'low':float(row.low),'close':float(row.close),'volume':0,'oi':0})
        flow.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return candles,flow

results=[]
for tf in ['15m','1h','4h']:
    candles,flow = load_window(tf)
    fine = _load_fine_1m(candles[0]['ts'], candles[-1]['ts']) if tf!='1m' else None
    print(f"\n=== TF {tf} candles {len(candles)} swings? fine {len(fine) if fine else 0}")
    for entry_break in ['decisive','flip']:
        for min_bars in [14,20,30,50]:
            for trailing in ['off','swing']:
                for be in [0.0,1.0]:
                    sw=_compute_swings(flow,'continuous', min_bars=min_bars)
                    tr=simulate_btc_trades(candles, sw, entry_break=entry_break, sl_mode='swing', rr_target=3.0, trailing=trailing, breakeven_r=be, fine=fine, entry_selection='stream')
                    closed=[t for t in tr if t['outcome']!='open']
                    if not closed: continue
                    base=sum(t['r_multiple'] for t in closed)
                    wins=sum(1 for t in closed if t['r_multiple']>0)
                    _trade_costs(tr, fee_pct, slip)
                    costs=sum(float(t.get('cost_r',0)) for t in closed)
                    net=base-costs
                    win_rate=100*wins/len(closed)
                    results.append({
                        'tf':tf,'entry_break':entry_break,'min_bars':min_bars,'trailing':trailing,'be':be,
                        'trades':len(closed),'win_rate':round(win_rate,1),'base':round(base,1),'net':round(net,1),'costs':round(costs,1)
                    })
                    # also with bias+regime for 15m? skip for now

results_sorted=sorted(results, key=lambda x: x['net'], reverse=True)
print("\n===== TOP 25 by NET R (stream+1m fine+0.05%+2pt FULL window) =====")
for i,r in enumerate(results_sorted[:25],1):
    print(f"{i:2} {r['tf']:4} {r['entry_break']:8} mb{r['min_bars']:2} {r['trailing']:5} BE{r['be']:.0f} | tr {r['trades']:4} win {r['win_rate']:4.1f}% base {r['base']:7.1f} net {r['net']:7.1f} costs {r['costs']:6.1f}")

# Also check with bias+streak for 15m flip20 etc
print("\n===== 15m WITH bias 15m + streak_311 (sniper style) =====")
candles,flow=load_window('15m')
fine=_load_fine_1m(candles[0]['ts'], candles[-1]['ts'])
# build bias timeline
c15,f15=load_window('15m')
s15=_compute_swings(f15,'continuous', min_bars=14)
bias_tl=sorted((int(c15[s['confirmed_at_idx']]['ts']), s['dir']) for s in s15 if 0 <= int(s.get('confirmed_at_idx',-1)) < len(c15))
day_gate=_streak_regime_gate(candles)
for entry_break in ['flip','decisive']:
    for mb in [14,20,30]:
        for trail in ['off','swing']:
            for be in [0.0,1.0]:
                sw=_compute_swings(flow,'continuous', min_bars=mb)
                tr=simulate_btc_trades(candles, sw, entry_break=entry_break, trailing=trail, breakeven_r=be, sl_mode='swing', bias_timeline=bias_tl, day_gate=day_gate, fine=fine, entry_selection='stream')
                closed=[t for t in tr if t['outcome']!='open']
                if not closed: continue
                base=sum(t['r_multiple'] for t in closed)
                _trade_costs(tr, fee_pct, slip)
                costs=sum(float(t.get('cost_r',0)) for t in closed)
                net=base-costs
                print(f"15m {entry_break:8} mb{mb:2} {trail:5} BE{be:.0f} +bias+streak | tr {len(closed):3} base {base:6.1f} net {net:6.1f}")

import json, pathlib
pathlib.Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\backend\debug\_btc_full_sweep_out.json").write_text(json.dumps(results_sorted, indent=2))
print("\nWrote _btc_full_sweep_out.json")
