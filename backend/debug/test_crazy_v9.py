import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v9_mean_rev_exit import simulate_htf_ltf_rchb_exit
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.walker import FlowCandle
from collections import defaultdict

def load_window(tf):
    df = load_btc_df(tf)
    c=[]; f=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        c.append({"date":date,"ts":int(row.ts),"open":float(row.open),"high":float(row.high),"low":float(row.low),"close":float(row.close),"volume":0,"oi":0})
        f.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return c,f

c1h,f1h = load_window("1h")
c15,f15 = load_window("15m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
print(f"ready {len(c1h)} {len(c15)} {len(fine)}")

from src.btc.btc_engine import trade_stats

def eval_nested(nested, name):
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,0.05,2.0)
    stats=trade_stats(ltf)
    net=stats.get("net_total_r", sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open"))
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    print(f"{name:30s} | tr {stats['closed']:3d} | net {net:6.1f} | PF {stats['profit_factor']:4.2f} DD {stats['max_drawdown_r']:5.1f} | 2023 {yearly.get('2023',0):6.1f} 2024 {yearly.get('2024',0):6.1f} 2025 {yearly.get('2025',0):6.1f} 2026 {yearly.get('2026',0):6.1f}")

baseline=simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
eval_nested(baseline, "V5.0 MB50 baseline")

try:
    rchb=simulate_htf_ltf_rchb_exit(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=1.5)
    eval_nested(rchb, "Crazy2 v5 entry + RCHB exit")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"RCHB failed: {e}")
