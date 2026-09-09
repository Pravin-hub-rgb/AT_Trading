"""Sweep v5 buffer 0.15-0.35 and hhll N 20-50 on 4yr FULL + focus 2023 chop.
Compares each buf/hhll against baseline v3 ext-stop 1.5 on live 2023-2026 1.93M data."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_engine import trade_stats
from src.btc.btc_config import load_btc_df
from src.btc.engines.htf_ltf.v1_15m import simulate_htf_ltf_15m
from src.btc.engines.htf_ltf.v3_ext_stop import simulate_htf_ltf_ext_stop
from src.btc.engines.htf_ltf.v5_sl_buffer import simulate_htf_ltf_sl_buffer
from src.btc.engines.htf_ltf.v6_sl_hhll import simulate_htf_ltf_sl_hhll
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
    return c,f,df

c1h,f1h,_=load_window("1h")
c15,f15,_=load_window("15m")
sw1h=_compute_swings(f1h,"continuous",min_bars=20)
sw15=_compute_swings(f15,"continuous",min_bars=50)
t0=min(c1h[0]["ts"],c15[0]["ts"]); t1=max(c1h[-1]["ts"],c15[-1]["ts"])
fine=_load_fine_1m(t0,t1)
print(f"ready: 1h {len(c1h)} 15m {len(c15)} fine {len(fine)} swings 1h{len(sw1h)} 15m{len(sw15)}")

def eval_nested(nested):
    ltf=nested["ltf_trades"]; htf=nested["htf_trades"]
    _trade_costs(ltf,FEE,SLIP); _trade_costs(htf,FEE,SLIP)
    s=trade_stats(ltf)
    net=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open")
    base=s["total_r"]
    # per-year net
    yearly=defaultdict(float)
    for t in ltf:
        if t["outcome"]=="open": continue
        yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
    return {"tr":s["closed"],"win":s["win_rate"],"base":base,"net":net,"pf":s["profit_factor"],"dd":s["max_drawdown_r"],"maxL":s["max_consecutive_losses"],"yearly":dict(yearly)}

baseline=eval_nested(simulate_htf_ltf_ext_stop(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5))
print(f"\nBaseline v3 ext-stop 1.5R: {baseline}")

print("\n=== Buffer sweep 0.15-0.35 ATR (ext-stop 1.5R held) ===")
print("buf | tr | win% | base | net | PF | DD | maxL | 2023 net | 2024 net | 2025 net | 2026 net")
for buf in [0.0, 0.10, 0.15, 0.20, 0.22, 0.25, 0.27, 0.30, 0.35, 0.50]:
    nested=simulate_htf_ltf_sl_buffer(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=buf)
    r=eval_nested(nested)
    y=r["yearly"]
    print(f"{buf:4.2f} | {r['tr']:3d} | {r['win']:4.1f} | {r['base']:6.1f} | {r['net']:6.1f} | {r['pf']:4.2f} | {r['dd']:5.1f} | {r['maxL']:2d} | {y.get('2023',0):6.1f} | {y.get('2024',0):6.1f} | {y.get('2025',0):6.1f} | {y.get('2026',0):6.1f}")

print("\n=== HHLL sweep N=10..60 (ext-stop 1.5R held, buf 0) ===")
print("N  | tr | win% | base | net | PF | DD | maxL | 2023 | 2024 | 2025 | 2026")
for n in [10,15,20,25,30,35,40,50,60]:
    nested=simulate_htf_ltf_sl_hhll(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_hhll_n=n)
    r=eval_nested(nested)
    y=r["yearly"]
    print(f"{n:2d} | {r['tr']:3d} | {r['win']:4.1f} | {r['base']:6.1f} | {r['net']:6.1f} | {r['pf']:4.2f} | {r['dd']:5.1f} | {r['maxL']:2d} | {y.get('2023',0):6.1f} | {y.get('2024',0):6.1f} | {y.get('2025',0):6.1f} | {y.get('2026',0):6.1f}")

print("\n=== Buf 0.25 vs HHLL-30 head-to-head on 2023 OOS only (full engine but filtered by exit year) ===")
for label, fn in [
    ("v3 ext-stop", lambda: simulate_htf_ltf_ext_stop(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5)),
    ("v5 buf0.25", lambda: simulate_htf_ltf_sl_buffer(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)),
    ("v6 hhll30", lambda: simulate_htf_ltf_sl_hhll(c1h,sw1h,c15,sw15,fine, htf_entry_break="flip", ltf_entry_break="decisive", sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_hhll_n=30)),
]:
    nested=fn()
    ltf=nested["ltf_trades"]
    _trade_costs(ltf,FEE,SLIP)
    # 2023 only
    tr23=[t for t in ltf if t["exit_date"][:4]=="2023" and t["outcome"]!="open"]
    wins=sum(1 for t in tr23 if float(t["r_multiple"])-float(t.get("cost_r",0))>0)
    net23=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in tr23)
    base23=sum(float(t["r_multiple"]) for t in tr23)
    print(f"{label}: 2023 {len(tr23)}tr {wins}/{len(tr23)} win base {base23:.1f} net {net23:.1f}")
