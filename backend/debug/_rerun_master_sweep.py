"""Rerun master preset sweep with CURRENT engine (stream+1m fine+0.05%+2pt).

Loads same windows as /api/btc/summary — FULL Jan25→Sep26 per TF, continuous, stream entries incl pre-start churn, 1m-precise fills.

Outputs ranked table + JSON for btcMaster regeneration.
"""
import sys
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")

from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.btc.btc_routes import _MASTER_PRESETS, _compute_swings, _load_fine_1m
from src.btc.btc_engine import simulate_btc_trades
from src.btc.btc_routes import _trade_costs

def load_window(tf):
    df = load_btc_df(tf)
    candles=[]
    flow=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({'date':date,'ts':int(row.ts),'open':float(row.open),'high':float(row.high),'low':float(row.low),'close':float(row.close),'volume':0,'oi':0})
        flow.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return candles, flow, df

fee_pct=0.05
slip=2.0

# group by TF like summary
by_tf={}
for p in _MASTER_PRESETS:
    by_tf.setdefault(p['bestTf'], []).append(p)

rows=[]
for tf, presets in by_tf.items():
    candles, flow, df = load_window(tf)
    # fine for this TF
    fine = _load_fine_1m(candles[0]['ts'], candles[-1]['ts']) if tf!='1m' else None
    # bias timeline only for sniper etc needs 15m — but we handle per preset below
    # load 15m for bias if needed
    bias_timeline_global=None
    if tf in ('1m','5m'):
        from src.btc.btc_routes import _compute_swings as cs
        c15,f15,_=load_window('15m')
        s15 = cs(f15,'continuous', min_bars=14)
        # build timeline like routes does (confirmed_at_idx -> ts,dir)
        bias_timeline_global = sorted(
            (int(c15[s['confirmed_at_idx']]['ts']), s['dir'])
            for s in s15 if 0 <= int(s.get('confirmed_at_idx',-1)) < len(c15)
        )
    # day gate for streak_311
    from src.btc.btc_routes import _streak_regime_gate
    day_gate_global = _streak_regime_gate(candles) if any(p.get('regime')=='streak_311' for p in presets) else None

    for p in presets:
        sw = _compute_swings(flow,'continuous', min_bars=p['min_bars'])
        # per preset gates
        bias_tl = bias_timeline_global if p.get('bias')=='15m' else None
        # if bias requested but tf==15m, routes would ignore — we do same
        if p.get('bias')=='15m' and tf=='15m':
            bias_tl=None
            # need to actually compute bias gate correctly: for 15m presets with bias, they need 15m bias on 15m chart? routes ignores because tf in (1m,5m) only
            # So sniper is 15m with bias 15m — routes logic: ptf==15m -> bias_timeline stays None, so _run_preset passes None for 15m even if p bias==15m (see line 559)
            # Let's mimic: only pass bias if ptf in 1m/5m — else None
            bias_tl=None
        day_gate = day_gate_global if p.get('regime')=='streak_311' else None

        # Correct sniper handling: routes for summary groups by ptf, and for ptf==15m bias stays None, so sniper's 15m bias gate is actually IGNORED in summary!
        # Let's check routes: for ptf 15m, bias_timeline = None initially, only set if ptf in 1m/5m. Then row = _run_preset(..., bias_timeline if p bias==15m else None) -> None
        # So sniper in summary has NO bias gate — weird. Let's replicate that bug for parity.
        # For fair sweep we also compute WITH bias using 15m timeline built from 15m swings.

        # For visibility, compute both
        tr = simulate_btc_trades(candles, sw, entry_break=p['entry_break'], sl_mode=p['sl_mode'], rr_target=p['rr_target'], trailing=p['trailing'], breakeven_r=p['breakeven_r'], bias_timeline=bias_tl, day_gate=day_gate, fine=fine, entry_selection='stream')
        closed=[t for t in tr if t['outcome']!='open']
        base=sum(t['r_multiple'] for t in closed)
        wins=sum(1 for t in closed if t['r_multiple']>0)
        win_rate=100*wins/max(1,len(closed))
        _trade_costs(tr, fee_pct, slip)
        costs=sum(float(t.get('cost_r',0)) for t in closed)
        net=base-costs
        rows.append({
            'key':p['key'],'label':p['label'],'tf':tf,'entry_break':p['entry_break'],'min_bars':p['min_bars'],'trailing':p['trailing'],'breakeven_r':p['breakeven_r'],'bias':p['bias'],'regime':p['regime'],
            'trades':len(closed),'wins':wins,'win_rate':round(win_rate,1),'base_r':round(base,2),'costs_r':round(costs,2),'net_r':round(net,2),
            'swings':len(sw)
        })

# sort by net_r desc
rows.sort(key=lambda r: r['net_r'], reverse=True)
for i,r in enumerate(rows,1):
    r['rank']=i

print(f"{'Rank':<4} {'Key':<15} {'Label':<32} {'TF':<4} {'Tr':>4} {'Win%':>5} {'Base':>7} {'Costs':>7} {'Net':>7} {'Bias':<6} {'Regime'}")
print("-"*110)
for r in rows:
    print(f"{r['rank']:<4} {r['key']:<15} {r['label']:<32} {r['tf']:<4} {r['trades']:>4} {r['win_rate']:>5.1f} {r['base_r']:>7.1f} {r['costs_r']:>7.1f} {r['net_r']:>7.1f} {r['bias']:<6} {r['regime']}")

# also print JSON
import json, pathlib
out_path = pathlib.Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\backend\debug\_rerun_master_out.json")
out_path.write_text(json.dumps({'rows':rows,'fee_pct':fee_pct,'slippage_pts':slip}, indent=2))
print(f"\nWritten {out_path}")

# Compare claimed 325 table
claimed={
    'decisive50':325,
    'flip50':284,
    'flip30':278,
    'decisive30':343, # claimed but our label is decisive30? actually claimed Decisive Trail 30 (15m) 343 — but our presets have flip30 etc
}
print("\nClaimed vs actual for key presets:")
for k,v in claimed.items():
    actual=next((r for r in rows if r['key']==k), None)
    if actual:
        print(f"{k}: claimed {v} vs actual {actual['trades']} (base claimed ? vs actual {actual['base_r']})")

# Also recompute with BIAS correctly for sniper (using 15m bias timeline even on 15m)
print("\n--- Sniper WITH correct 15m bias (1m/5m vs 15m handling fix) ---")
for tf in ['15m']:
    candles, flow, _ = load_window(tf)
    fine = _load_fine_1m(candles[0]['ts'], candles[-1]['ts'])
    sw = _compute_swings(flow,'continuous', min_bars=20)
    # build bias timeline from 15m itself (as if we allow 15m bias on 15m)
    c15,f15,_=load_window('15m')
    s15 = _compute_swings(f15,'continuous', min_bars=14)
    bias_tl = sorted((int(c15[s['confirmed_at_idx']]['ts']), s['dir']) for s in s15 if 0 <= int(s.get('confirmed_at_idx',-1)) < len(c15))
    from src.btc.btc_routes import _streak_regime_gate
    day_gate = _streak_regime_gate(candles)
    tr_sniper = simulate_btc_trades(candles, sw, entry_break='flip', sl_mode='swing', rr_target=3.0, trailing='off', breakeven_r=1.0, bias_timeline=bias_tl, day_gate=day_gate, fine=fine, entry_selection='stream')
    closed=[t for t in tr_sniper if t['outcome']!='open']
    base=sum(t['r_multiple'] for t in closed)
    _trade_costs(tr_sniper, fee_pct, slip)
    costs=sum(float(t.get('cost_r',0)) for t in closed)
    print(f"sniper WITH bias+regime: tr {len(closed)} base {round(base,2)} costs {round(costs,2)} net {round(base-costs,2)}")
    # without bias
    tr2 = simulate_btc_trades(candles, sw, entry_break='flip', sl_mode='swing', rr_target=3.0, trailing='off', breakeven_r=1.0, bias_timeline=None, day_gate=day_gate, fine=fine, entry_selection='stream')
    closed2=[t for t in tr2 if t['outcome']!='open']
    base2=sum(t['r_multiple'] for t in closed2)
    _trade_costs(tr2, fee_pct, slip)
    costs2=sum(float(t.get('cost_r',0)) for t in closed2)
    print(f"sniper bias OFF, regime ON: tr {len(closed2)} base {round(base2,2)} net {round(base2-costs2,2)}")
