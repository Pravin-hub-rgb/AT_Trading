"""Exp2 — Delayed trail family sweep on v5 FULL (docs only, no UI).
Uses patched v1_15m with trail_delay_bars / trail_delay_r support."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
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
print(f"ready: 1h {len(c1h)} 15m {len(c15)} fine {len(fine)}")

def eval_nested(nested):
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,FEE,SLIP)
    stats=trade_stats(ltf)
    net=stats.get("net_total_r", sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open"))
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    return {"tr":stats["closed"],"win":stats["win_rate"],"base":stats["total_r"],"net":net,"pf":stats["profit_factor"],"dd":stats["max_drawdown_r"],"maxL":stats["max_consecutive_losses"],"yearly":dict(yearly),"stats":stats,"ltf":ltf}

configs=[
    ("A current MB50 immediate", 0, 0.0),
    ("B delay 4 bars", 4, 0.0),
    ("B delay 8 bars", 8, 0.0),
    ("B delay 16 bars", 16, 0.0),
    ("B delay 32 bars", 32, 0.0),
    ("B delay +1R", 0, 1.0),
    ("B delay +2R", 0, 2.0),
    ("B delay 8b +1R", 8, 1.0),
    ("B delay 16b +1R", 16, 1.0),
]

print("\n=== Exp2 Delayed trail family (v5: ext-stop1.5 + buf0.25) FULL 442tr ===")
# baseline check: delay 0 should match v5 442 +168
baseline=eval_nested(simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25, sl_hhll_n=0, trail_delay_bars=0, trail_delay_r=0.0))
print(f"BASELINE check (should be 442 +168): tr {baseline['tr']} net {baseline['net']:.1f} PF {baseline['pf']} DD {baseline['dd']} 2023 {baseline['yearly'].get('2023',0):.1f}")

for label, db, dr in configs:
    nested=simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25, sl_hhll_n=0, trail_delay_bars=db, trail_delay_r=dr)
    r=eval_nested(nested)
    yearly=r["yearly"]
    print(f"{label:22s} | tr {r['tr']:3d} | win {r['win']:4.1f}% | net {r['net']:6.1f} | PF {r['pf']:4.2f} | DD {r['dd']:5.1f} | maxL {r['maxL']:2d} | 2023 {yearly.get('2023',0):6.1f} | 2024 {yearly.get('2024',0):6.1f} | 2025 {yearly.get('2025',0):6.1f} | 2026 {yearly.get('2026',0):6.1f} | runners>=3R {len([t for t in r['ltf'] if float(t['r_multiple'])-float(t.get('cost_r',0))>=3])}")
