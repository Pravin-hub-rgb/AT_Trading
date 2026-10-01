import sys; sys.path.insert(0, '.')
from test_experiments import simulate_v18_experiments
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.walker import FlowCandle
from src.btc.btc_config import load_btc_df
import statistics

df = load_btc_df("15m", "BTCUSDT_BYBIT")
c15, f15 = [], []
for row in df.itertuples():
    d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    c15.append({"date":d,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
    f15.append(FlowCandle(date=d,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
df2 = load_btc_df("1h", "BTCUSDT_BYBIT")
c1h, f1h = [], []
for row in df2.itertuples():
    d = row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    c1h.append({"date":d,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
    f1h.append(FlowCandle(date=d,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
fine = _load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol="BTCUSDT_BYBIT")

def costs(trades):
    fee_rate = 0.055/100; eslip = 0.005/100; eslipx = 0.010/100
    fnd_per = 0.01/100/32
    tf,tsl,tfund,tbars = 0,0,0,0
    n=0
    for t in trades:
        risk = abs(t["entry_price"]-t["sl"])
        if risk<=0: continue
        ep = abs(t["entry_price"]); xp = abs(t.get("exit_price",ep))
        b = int(t.get("bars_held",0))
        tf += (ep*fee_rate+xp*fee_rate)/risk
        tsl += (ep*eslip+xp*eslipx)/risk
        tfund += (ep*fnd_per*b)/risk
        tbars += b
        n += 1
    avg_b = tbars/n if n else 0
    return tf, tsl, tfund, n, avg_b

configs = [
    ("BASELINE", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3), 20, 50),
    ("Multi-LTF cd=5", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_multi_ltf=True,exp_multi_ltf_cd=5), 20, 50),
    ("Persist=5", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_regime_persist=5), 20, 50),
    ("MLTF+Persist5", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_multi_ltf=True,exp_multi_ltf_cd=10,exp_regime_persist=5), 20, 50),
    ("MLTF cd=0", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_multi_ltf=True,exp_multi_ltf_cd=0), 20, 50),
    ("mb1h10+chop55", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=55.0,cooldown_bars=10,max_consecutive_losses=3), 10, 50),
    ("SAFE combo", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=55.0,cooldown_bars=10,max_consecutive_losses=3,exp_regime_persist=2), 10, 50),
    ("MIDDLE cd=5", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=55.0,cooldown_bars=5,max_consecutive_losses=3,exp_multi_ltf=True,exp_multi_ltf_cd=5,exp_regime_persist=2), 10, 50),
    ("OPTIMAL cd=0", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=55.0,cooldown_bars=0,max_consecutive_losses=3,exp_multi_ltf=True,exp_multi_ltf_cd=0,exp_regime_persist=2), 10, 50),
    ("Dual-active", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_dual_active=True), 20, 50),
    ("Adaptive halt", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_adaptive_halt=True), 20, 50),
    ("TOD filter", dict(sl_buf_atr=0.01,ext_stop_r=1.5,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3,exp_tod_filter=True), 20, 50),
]

hdr = "{:<18} {:>5} {:>7} {:>6} {:>6} {:>6} {:>9} {:>8} {:>7} {:>6}".format("Config","T","Gross","Fees","Slip","Fund","Cost","NET R","NetDD","AvBar")
print("Cost model: Bybit 0.055%/side, entry slip 0.005%, exit slip 0.01%, funding 0.01%/8h")
print("="*100)
print(hdr)
print("-"*100)

results = []
for name,p,mb1h,mb15 in configs:
    sw1h=_compute_swings(f1h,"continuous",min_bars=mb1h)
    sw15=_compute_swings(f15,"continuous",min_bars=mb15)
    tr=simulate_v18_experiments(c1h,sw1h,c15,sw15,fine,**p)["ltf_trades"]
    gross=sum(t["r_multiple"] for t in tr)
    fee,slip,fund,n,avg_b=costs(tr)
    tc=fee+slip+fund
    net=gross-tc
    ac=tc/n if n else 0
    r_vals=[t["r_multiple"] for t in tr]
    cum,peak,dd=0,0,0
    for r in r_vals:
        cum+=r-ac; peak=max(peak,cum); dd=max(dd,peak-cum)
    results.append((name,n,gross,fee,slip,fund,tc,net,dd,avg_b))
    row = "{:<18} {:>5} {:>+7.1f} {:>6.1f} {:>6.1f} {:>6.1f} {:>9.1f} {:>+8.1f} {:>6.1f}R {:>5.0f}".format(name,n,gross,fee,slip,fund,tc,net,dd,avg_b)
    print(row)

bl_net = next(r[7] for r in results if "BASELINE" in r[0])
print()
print("RANKED BY NET R:")
print("-"*100)
for i,(name,n,gross,fee,slip,fund,tc,net,dd,avg_b) in enumerate(sorted(results,key=lambda x:-x[7]),1):
    delta=net-bl_net
    marker = " <-- BASELINE" if "BASELINE" in name else ""
    print("  {:>2}. {:<18} Net {:>+7.1f}R  (delta {:>+7.1f}R)  Cost {:>5.1f}R  DD {:>5.1f}R  AvgBars {:>4.0f}{}".format(i,name,net,delta,tc,dd,avg_b,marker))
