"""Exp7 V5.1 — ATR trail vs Structure (MB50) inside v5.
Sweep K=1.5/2.0/2.5/3.0 coarse for plateau. Same entries/SL/costs/data."""
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
print(f"ready: 1h {len(c1h)} 15m {len(c15)} fine {len(fine)} swings {len(sw1h)}/{len(sw15)}")

def eval_nested(nested):
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,FEE,SLIP)
    stats=trade_stats(ltf)
    net=stats.get("net_total_r", sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open"))
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    # runners and avg runner, mfe capture approx via net vs mfe not available here, but runner count
    runners=[t for t in ltf if float(t["r_multiple"])-float(t.get("cost_r",0)) >=3]
    avg_runner=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in runners)/len(runners) if runners else 0
    return {"tr":stats["closed"],"win":stats["win_rate"],"net":net,"pf":stats["profit_factor"],"dd":stats["max_drawdown_r"],"yearly":dict(yearly),"runners":len(runners),"avg_runner":avg_runner,"stats":stats,"ltf":ltf}

# Baseline V5.0 MB50 immediate
baseline=eval_nested(simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25, atr_trail_k=0.0))
print(f"\nV5.0 MB50 immediate: tr {baseline['tr']} net {baseline['net']:.1f} PF {baseline['pf']} DD {baseline['dd']} runners {baseline['runners']} avg {baseline['avg_runner']:.1f} 2023 {baseline['yearly'].get('2023',0):.1f}")

for k in [1.5,2.0,2.5,3.0]:
    nested=simulate_htf_ltf_15m(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="atr", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25, atr_trail_k=k)
    r=eval_nested(nested)
    print(f"V5.1 ATR k={k}    | tr {r['tr']:3d} | net {r['net']:6.1f} | PF {r['pf']:4.2f} | DD {r['dd']:5.1f} | runners {r['runners']:2d} avg {r['avg_runner']:4.1f} | 2023 {r['yearly'].get('2023',0):6.1f} | 2024 {r['yearly'].get('2024',0):6.1f} | 2025 {r['yearly'].get('2025',0):6.1f} | 2026 {r['yearly'].get('2026',0):6.1f}")

# V5.2 Structure: same as V5.0 but structure trail is MB50 already, so baseline is structure. To differentiate, we could test MB50 vs prev swing (hhll) — but that's v6. For now just note structure IS MB50.
print("\nV5.2 Structure trail IS MB50 (v5.0) — same as baseline, not separate. For reference, v6 hhll-30 is 417tr +139.5 net vs 442 +168 MB50, so MB50 beats hhll.")

# Quick conditional sweep: V5.3 conditional MB50 after +1R/+2R already tested in Exp2 B delay +1R/+2R (423tr +159, 372tr +141) — MB50 delayed activation.

# V5.4 Partial exit: test 20%/30% at +2R close then trail rest — quick approximate by reducing net of runners
# For doc, we note partial table will be computed via post-hoc runner split, not engine change, to estimate.
