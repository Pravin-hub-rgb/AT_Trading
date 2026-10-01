import sys, bisect
sys.path.insert(0, r"backend")
sys.path.insert(0, r"backend/debug")
from test_experiments import simulate_v18_experiments as sim
from src.btc.btc_routes import _compute_swings, _load_fine_1m
from src.btc.btc_config import load_btc_df

df = load_btc_df("15m", "BTCUSDT_BYBIT")
c15=[{"date":r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),"ts":int(r.ts),"open":float(r.open),"high":float(r.high),"low":float(r.low),"close":float(r.close),"volume":0,"oi":0} for r in df.itertuples()]
df2 = load_btc_df("1h", "BTCUSDT_BYBIT")
c1h=[{"date":r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),"ts":int(r.ts),"open":float(r.open),"high":float(r.high),"low":float(r.low),"close":float(r.close),"volume":0,"oi":0} for r in df2.itertuples()]
fine=_load_fine_1m(min(c1h[0]["ts"],c15[0]["ts"]),max(c1h[-1]["ts"],c15[-1]["ts"]),symbol="BTCUSDT_BYBIT")
sw20=_compute_swings([type("F",(),{"date":c["date"],"open":c["open"],"high":c["high"],"low":c["low"],"close":c["close"]})() for c in c1h],"continuous",min_bars=20)
sw15=_compute_swings([type("F",(),{"date":c["date"],"open":c["open"],"high":c["high"],"low":c["low"],"close":c["close"]})() for c in c15],"continuous",min_bars=50)
BP=dict(sl_buf_atr=0.01,chop_thresh=58.0,cooldown_bars=10,max_consecutive_losses=3)
bases={"lb30":(dict(exp31_lb=30),275,224.5),"lb14":(dict(),281,201.9),
       "A4":(dict(exp31_lb=30,chop_thresh=55.0,exp_persist=2),266,228.6)}
from src.btc.btc_routes import _trade_costs
_g={"fee_pct":0.055,"entry_slip_pct":0.01,"exit_slip_pct":0.01}
def fund(tr):
    f=0.0
    for t in tr:
        e,sl=float(t["entry_price"]),float(t["sl"]);rk=abs(e-sl)
        if rk>0 and e>0:f+=(int(t.get("bars_held")or 0)*0.25/8.0)*0.0001*(e/rk)
    return f
for b,(kw,en,eg) in bases.items():
    for w in (0,24):
        wage={"exp_wage_h":w} if w else {}
        r=sim(c1h,sw20,c15,sw15,fine_ltf=fine,**{**BP,**kw,**wage,"ext_stop_r":1.5})
        tr=r["ltf_trades"]
        rs=[float(t["r_multiple"]) for t in tr]
        c2,_=_trade_costs(tr,_g["fee_pct"],0.0,_g["entry_slip_pct"],_g["exit_slip_pct"])
        net=sum(rs)-c2-fund(tr)
        print(b,("w0" if not w else "w24"),"fine n=%d NET=%+.1f (doc %d,%+.1f)"%(len(tr),net,en,eg),flush=True)
