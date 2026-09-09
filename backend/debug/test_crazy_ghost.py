"""Crazy Ghost Mix — HTF ghost streak bias + LTF B2/FLIP same dir
Run vs v5 baseline 442 +168 on FULL 1.93M."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.btc.engines.htf_ltf.v8_ghost_htf_bias import simulate_htf_ltf_ghost
from src.walker import FlowCandle
from collections import defaultdict

FEE=0.05
SLIP=2.0

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
print(f"ready: 1h {len(c1h)} 15m {len(c15)} fine {len(fine)} swings {len(sw1h)}/{len(sw15)}")

from src.btc.btc_engine import trade_stats

def eval_nested(nested, name):
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,FEE,SLIP)
    stats=trade_stats(ltf)
    net=stats.get("net_total_r", sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open"))
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    print(f"{name:35s} | tr {stats['closed']:3d} | win {stats['win_rate']:4.1f}% | base {stats['total_r']:6.1f} | net {net:6.1f} | PF {stats['profit_factor']:4.2f} | DD {stats['max_drawdown_r']:5.1f} | 2023 {yearly.get('2023',0):6.1f} 2024 {yearly.get('2024',0):6.1f} 2025 {yearly.get('2025',0):6.1f} 2026 {yearly.get('2026',0):6.1f} | intervals {len(nested.get('intervals',[]))}")

# Baseline v5
baseline=simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
eval_nested(baseline, "V5.0 MB50 baseline")

# Crazy1 ghost HTF + LTF B2/FLIP same dir (window 4h, also try 8h)
for wh in [4,8,12]:
    nested=simulate_htf_ltf_ghost(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=1.5, window_hours=wh)
    eval_nested(nested, f"Crazy1 ghostHTF B2/FLIP wh{wh}h")

# Crazy1 variant: ghost HTF but LTF FLIP only (not decisive)
# For FLIP only, need to change ltf_entry_break to flip — ghost engine currently hardcodes decisive, but we can test by modifying call to use flip via manual filtered? For now just note.

# Crazy with ext_stop disabled
nested=simulate_htf_ltf_ghost(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=0.0, window_hours=4)
eval_nested(nested, "Crazy1 ghost wh4 no ext-stop")

print("\nCrazy Ghost Mix done — compare vs v5 442 +168 net, ghost windows are mean-reversion opposite streak.")
