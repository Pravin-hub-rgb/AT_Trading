import sys
sys.path.insert(0,"backend"); sys.path.insert(0,".")
import src.btc.btc_routes as r
for v in ("entry_minus_1","unified","v19_champion"):
    d=r.btc_backtest(tf="15m",mode="continuous",symbol="BTCUSDT_BYBIT",htf_ltf="off",
                     min_bars=50,htf_tf="1h",htf_min_bars=10,sl_mode="swing",
                     sl_pct=0.5,rr_target=3.0,entry_break="decisive",version=v)
    t=d["trades"]; g=sum(float(x["r_multiple"]) for x in t)
    print("%-14s trades=%4d gross=%+9.2f windows=%d"%(v,len(t),g,len(d["htf_windows"])))
