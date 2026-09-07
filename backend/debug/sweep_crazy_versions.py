"""Sweep all crazy versions v1..v6 across NetR/win%/PF/maxDD, TF, bias, costs.
Honest FULL window Jan-25→Sep-26, stream+touchable+one-swing-one-trade+1m fills.
Logs to fix/btc_15m_trail_decisive_crazy_ideas.md and JSON.
"""
import sys, json, pathlib
sys.path.insert(0, r"C:\Users\Pravin\Desktop\main\AT_Trading\backend")
from src.btc.btc_config import load_btc_df
from src.walker import FlowCandle
from src.btc.btc_routes import _compute_swings, _load_fine_1m, _streak_regime_gate, _trade_costs
from src.btc.btc_engine import trade_stats

def load_window(tf):
    df=load_btc_df(tf)
    candles=[]
    flow=[]
    for row in df.itertuples():
        date=row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        candles.append({'date':date,'ts':int(row.ts),'open':float(row.open),'high':float(row.high),'low':float(row.low),'close':float(row.close),'volume':0,'oi':0})
        flow.append(FlowCandle(date=date,open=float(row.open),high=float(row.high),low=float(row.low),close=float(row.close)))
    return candles, flow

def run_version(version: str, tf: str, fee_pct: float, bias: str, regime: str):
    # version dispatch
    candles, flow = load_window(tf)
    fine = _load_fine_1m(candles[0]['ts'], candles[-1]['ts']) if tf!='1m' else None
    sw = _compute_swings(flow,'continuous', min_bars=50)
    # bias timeline
    bias_tl=None
    if bias=="15m" and tf in ("1m","5m"):
        # for 15m decisive we want bias test even though api blocks, we test here
        c15,f15 = load_window('15m')
        sw15=_compute_swings(f15,'continuous',min_bars=14)
        bias_tl= sorted((int(c15[s["confirmed_at_idx"]]["ts"]), s["dir"]) for s in sw15 if 0 <= int(s.get("confirmed_at_idx",-1)) < len(c15))
        # only apply if version wants it
    day_gate=_streak_regime_gate(candles) if regime=="streak_311" else None
    # choose engine
    if version=="v1":
        from src.btc.btc_engine import simulate_btc_trades
        tr=simulate_btc_trades(candles, sw, entry_break="decisive", trailing="swing", breakeven_r=0.0, sl_mode="swing", bias_timeline=bias_tl if bias=="15m" else None, day_gate=day_gate, fine=fine, entry_selection="stream")
    elif version=="v2":
        from src.btc.engines.v2_chandelier import simulate_btc_trades_v2
        tr=simulate_btc_trades_v2(candles, sw, entry_break="decisive", trailing="chandelier", trail_k=3.0, breakeven_r=0.0, bias_timeline=bias_tl if bias=="15m" else None, day_gate=day_gate, fine=fine, entry_selection="stream")
    elif version=="v3":
        from src.btc.engines.v3_htf_trail import simulate_btc_trades_v3
        c1h,f1h = load_window('1h')
        sw1h=_compute_swings(f1h,'continuous',min_bars=50)
        ts1h=[int(c["ts"]) for c in c1h]
        tr=simulate_btc_trades_v3(candles, sw, swings_htf=sw1h, candle_ts_htf=ts1h, entry_break="decisive", trailing="swing", breakeven_r=0.0, bias_timeline=bias_tl if bias=="15m" else None, day_gate=day_gate, fine=fine, entry_selection="stream")
    elif version=="v4":
        from src.btc.engines.v4_partial import simulate_btc_trades_v4
        tr=simulate_btc_trades_v4(candles, sw, entry_break="decisive", trailing="swing", breakeven_r=0.0, bias_timeline=bias_tl if bias=="15m" else None, day_gate=day_gate, fine=fine, entry_selection="stream")
    elif version=="v5":
        from src.btc.engines.v5_be1 import simulate_btc_trades_v5
        tr=simulate_btc_trades_v5(candles, sw, entry_break="decisive", trailing="swing", breakeven_r=1.0, bias_timeline=bias_tl if bias=="15m" else None, day_gate=day_gate, fine=fine, entry_selection="stream")
    elif version=="v6":
        from src.btc.engines.v6_adx import simulate_btc_trades_v6
        tr=simulate_btc_trades_v6(candles, sw, entry_break="decisive", trailing="swing", breakeven_r=0.0, adx_threshold=25.0, bias_timeline=bias_tl if bias=="15m" else None, day_gate=day_gate, fine=fine, entry_selection="stream")
    else:
        raise ValueError(version)
    stats=trade_stats(tr)
    # costs
    from copy import deepcopy
    tr2=[dict(t) for t in tr]
    _trade_costs(tr2, fee_pct, 2.0)
    net=sum(float(t["r_multiple"])-float(t.get("cost_r",0)) for t in tr2 if t["outcome"]!="open")
    # PF
    wins=sum(1 for t in tr if t["r_multiple"]>0)
    losses=sum(1 for t in tr if t["r_multiple"]<=0 and t["outcome"]!="open")
    total_r=stats["total_r"]
    # PF calc
    wins_r=sum(t["r_multiple"] for t in tr if t["r_multiple"]>0)
    losses_r=abs(sum(t["r_multiple"] for t in tr if t["r_multiple"]<0))
    pf= round(wins_r/losses_r,2) if losses_r>0 else 0
    return {
        "version": version, "tf": tf, "fee_pct": fee_pct, "bias": bias, "regime": regime,
        "trades": stats["closed"], "win_rate": stats["win_rate"], "total_r": stats["total_r"], "net_r": round(net,2),
        "pf": pf, "maxDD": stats["max_drawdown_r"], "avg_r": stats["avg_r"], "longs": stats["longs"], "shorts": stats["shorts"],
    }

results=[]
for version in ["v1","v2","v3","v4","v5","v6"]:
    for tf in ["15m","1h","4h"]:
        for fee in [0.05, 0.02]:
            for bias,regime in [("off","off"), ("15m","off"), ("off","streak_311"), ("15m","streak_311")]:
                # for 15m decisive, bias only matters on 1m/5m but we test anyway
                # skip 1h bias on 1h/4h (no HTF above)
                if tf in ("1h","4h") and bias!="off":
                    continue
                try:
                    r=run_version(version, tf, fee, bias, regime)
                    results.append(r)
                    print(f"{version} {tf} fee{fee} bias{bias} regime{regime} -> net {r['net_r']} win {r['win_rate']}% PF {r['pf']} maxDD {r['maxDD']} tr {r['trades']}")
                except Exception as e:
                    print(f"ERR {version} {tf} {e}")
                    import traceback; traceback.print_exc()

# save
out_path=pathlib.Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\backend\debug\sweep_crazy_versions_out.json")
out_path.write_text(json.dumps(results, indent=2))
print(f"\nWrote {out_path} {len(results)} rows")

# also update md log
md_path=pathlib.Path(r"C:\Users\Pravin\Desktop\main\AT_Trading\fix\btc_15m_trail_decisive_crazy_ideas.md")
# append sweep log
with open(md_path, "a", encoding="utf-8") as f:
    f.write("\n\n## Sweep 2026-09-06 — All versions honest\n\n")
    f.write("| Ver | TF | Fee%/side | Bias | Regime | Tr | Win% | BaseR | NetR | PF | maxDD | Notes |\n")
    f.write("|-----|----|-----------|------|--------|----|------|-------|------|----|-------|-------|\n")
    for r in sorted(results, key=lambda x: x["net_r"], reverse=True)[:30]:
        f.write(f"| {r['version']} | {r['tf']} | {r['fee_pct']} | {r['bias']} | {r['regime']} | {r['trades']} | {r['win_rate']}% | {r['total_r']} | {r['net_r']} | {r['pf']} | {r['maxDD']} | |\n")
    f.write("\n_full sweep logged to `backend/debug/sweep_crazy_versions_out.json`_\n")
print("Logged to md")
