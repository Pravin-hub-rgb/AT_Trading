import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v11_conditional_htf import simulate_htf_ltf_conditional
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.walker import FlowCandle
from collections import defaultdict
from src.btc.btc_engine import trade_stats

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
print(f"ready 1h {len(c1h)} 15m {len(c15)} fine {len(fine)}")

def eval_nested(nested, name):
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,FEE,SLIP)
    stats=trade_stats(ltf)
    net=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open")
    # also stats net
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    print(f"{name:35s} | tr {stats['closed']:3d} net {net:6.1f} PF {stats['profit_factor']:4.2f} DD {stats['max_drawdown_r']:5.1f} win {stats['win_rate']:4.1f}% | 2023 {yearly.get('2023',0):6.1f} 2024 {yearly.get('2024',0):6.1f} 2025 {yearly.get('2025',0):6.1f} 2026 {yearly.get('2026',0):6.1f}")

# Baselines
eval_nested(simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25), "V5.0 flip x decisive (baseline)")
eval_nested(simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="decisive", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25), "HTF decisive x decisive")

# Conditional
for mode in ["chop","atr_low","chop_or_atr_low","chop_and_atr_low","b2_vs_flip_chop","decisive_vs_flip_chop"]:
    nested=simulate_htf_ltf_conditional(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=61.8, atr_low_thresh=0.35, mode=mode)
    eval_nested(nested, f"Conditional {mode}")

# Try different chop thresholds
for thresh in [50.0, 61.8, 70.0]:
    nested=simulate_htf_ltf_conditional(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=1.5, chop_thresh=thresh, mode="chop")
    eval_nested(nested, f"Conditional chop>{thresh}")

# ATR low thresh sweep
for thr in [0.30,0.35,0.40]:
    nested=simulate_htf_ltf_conditional(c1h,sw1h,c15,sw15,fine, sl_buf_atr=0.25, ext_stop_r=1.5, atr_low_thresh=thr, mode="atr_low")
    eval_nested(nested, f"Conditional atr<{thr}")

print("\nGame changer test done — looking for net >168 and 2023 >37.7 simultaneously.")
