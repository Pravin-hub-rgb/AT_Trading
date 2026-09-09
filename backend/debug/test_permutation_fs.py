"""Permutation with FS — HTF fs/fs_opposite × LTF fs/fs_opposite/flip/b2/decisive
FULL 1.93M, 0.05%+2pt, 15m mb50 and 5m mb14, 1h HTF cap16 or FS intervals.
Focus: FS opposite (trade opposite to swing, FS chop is opposite) — buying swing FS -> short on LTF.
"""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _trade_costs
from src.btc.btc_config import load_btc_df
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
c5,f5 = load_window("5m")
sw1h = _compute_swings(f1h,"continuous",min_bars=20)
sw15 = _compute_swings(f15,"continuous",min_bars=50)
sw5 = _compute_swings(f5,"continuous",min_bars=14)
t0=min(c1h[0]["ts"], min(c15[0]["ts"], c5[0]["ts"])); t1=max(c1h[-1]["ts"], max(c15[-1]["ts"], c5[-1]["ts"]))
fine=_load_fine_1m(t0,t1)
print(f"ready 1h {len(c1h)} 15m {len(c15)} 5m {len(c5)} fine {len(fine)}")

def eval_combo(htf_br, ltf_br, ltf_tf, sw_ltf, c_ltf):
    try:
        nested=simulate_htf_ltf_15m(c1h, sw1h, c_ltf, sw_ltf, fine, htf_entry_break=htf_br, ltf_entry_break=ltf_br, sl_mode="swing", rr_target=3.0, ltf_trailing="swing", htf_breakeven=0, ltf_breakeven=0, htf_cap_days=16, ext_stop_r=1.5, sl_buf_atr=0.25)
        ltf=nested["ltf_trades"]
        _trade_costs(ltf,FEE,SLIP)
        stats=trade_stats(ltf)
        net=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in ltf if t["outcome"]!="open")
        yearly=defaultdict(float)
        for t in ltf:
            if t["outcome"]=="open": continue
            yearly[t["exit_date"][:4]] += float(t["r_multiple"])-float(t.get("cost_r",0))
        return {"tr":stats["closed"],"net":net,"pf":stats["profit_factor"],"dd":stats["max_drawdown_r"],"win":stats["win_rate"],"y2023":yearly.get("2023",0),"y2025":yearly.get("2025",0)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"tr":0,"net":0,"pf":0,"dd":0,"win":0,"y2023":0,"y2025":0,"err":str(e)}

print("\n=== 15m LTF fs permutations — HTF fs/fs_opposite/flip/b2/decisive x LTF fs/fs_opposite/flip/b2/decisive ===")
for h in ["flip","b2","decisive","fs","fs_opposite"]:
    for l in ["fs","fs_opposite","flip","b2","decisive"]:
        r=eval_combo(h,l,"15m",sw15,c15)
        print(f"HTF {h:11s} x LTF {l:11s} | tr {r['tr']:3d} | net {r['net']:6.1f} | PF {r['pf']:4.2f} | DD {r['dd']:5.1f} | 2023 {r['y2023']:6.1f} | 2025 {r['y2025']:6.1f} | win {r['win']:4.1f}%")

print("\n=== 5m LTF fs permutations (same) ===")
for h in ["flip","fs_opposite"]:
    for l in ["fs_opposite","decisive"]:
        r=eval_combo(h,l,"5m",sw5,c5)
        print(f"HTF {h:11s} x LTF {l:11s} (5m) | tr {r['tr']:3d} | net {r['net']:6.1f} | 2023 {r['y2023']:6.1f}")

# Specifically test the combo you asked: fs of buying swing -> trade short on ltf
# That is HTF fs_opposite (buying swing up -> short) + LTF decisive (or fs_opposite?)
print("\n=== Specific: HTF fs_opposite (buying FS -> short) x LTF decisive/fs_opposite on 15m ===")
for l in ["decisive","fs_opposite","flip"]:
    r=eval_combo("fs_opposite", l, "15m", sw15, c15)
    print(f"HTF fs_opposite x LTF {l:11s} | tr {r['tr']:3d} net {r['net']:6.1f} 2023 {r['y2023']:6.1f} PF {r['pf']:4.2f}")

print("\nDone FS permutation.")
