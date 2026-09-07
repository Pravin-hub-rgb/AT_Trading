"""Multiprocess sweep for 1-min - optimized precompute"""
import itertools, json, time, sys, os
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

# Precompute globally in main, then share via initializer
GLOBAL_DATA = {}

def init_worker():
    global GLOBAL_DATA
    from src import bias as bias_svc, config
    from src.intraday_1m_standalone import simulate_day_1min
    from src.intraday import EOD_EXIT
    import pandas as pd
    p1 = config.DATA_DIR / "nifty_1min.csv"
    p5 = config.DATA_DIR / "nifty_5min.csv"
    pdaily = config.DATA_DIR / "nifty_daily.csv"
    df1 = pd.read_csv(p1)
    df5 = pd.read_csv(p5)
    daily = pd.read_csv(pdaily) if pdaily.exists() else None
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])
    df1["ts"] = (df1["timestamp"].astype("int64")//1_000_000_000).astype("int64")
    df1 = df1.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
    labels = bias_svc.compute_bias(df5, daily)
    # Precompute groups etc like run_backtest does but once
    dates = df1["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d,g in df1.groupby(dates, sort=True)}
    ordered = sorted(groups)
    prev_close = {ordered[i]: float(groups[ordered[i-1]]["close"].iloc[-1]) for i in range(1,len(ordered))}
    bias_map = {l["date"]: l["bias"] for l in labels}
    zone_map = {l["date"]: (l.get("overview") or {}).get("zone") for l in labels}
    def _ext(z): return "highs" if z in ("new_high","highs_extreme") else "lows" if z in ("new_low","lows_extreme") else None
    def _q(g):
        rows=g.reset_index(drop=True)
        return [float(r["high"])-float(r["low"]) for _,r in rows.iloc[1:].iterrows() if r["timestamp"].strftime("%H:%M") < EOD_EXIT]
    day_ranges = {d: _q(groups[d]) for d in ordered}
    avg_by_date = {}
    for idx,d in enumerate(ordered):
        flat=[]
        for j in range(max(0, idx-10), idx):
            flat.extend(day_ranges[ordered[j]])
        avg_by_date[d]= sum(flat)/len(flat) if flat else None
    GLOBAL_DATA["groups"] = groups
    GLOBAL_DATA["ordered"] = ordered
    GLOBAL_DATA["prev_close"] = prev_close
    GLOBAL_DATA["bias_map"] = bias_map
    GLOBAL_DATA["zone_map"] = zone_map
    GLOBAL_DATA["avg_by_date"] = avg_by_date
    GLOBAL_DATA["labels"] = labels
    # store EOD for later
    GLOBAL_DATA["EOD"] = EOD_EXIT

def run_one_cfg(cfg_dict):
    global GLOBAL_DATA
    from src.intraday_1m_standalone import simulate_day_1min
    from src.intraday import resolve_cfg
    import pandas as pd
    cfg = resolve_cfg(cfg_dict)
    groups = GLOBAL_DATA["groups"]
    ordered = GLOBAL_DATA["ordered"]
    prev_close = GLOBAL_DATA["prev_close"]
    bias_map = GLOBAL_DATA["bias_map"]
    zone_map = GLOBAL_DATA["zone_map"]
    avg_by_date = GLOBAL_DATA["avg_by_date"]
    def _ext(z): return "highs" if z in ("new_high","highs_extreme") else "lows" if z in ("new_low","lows_extreme") else None
    traded = set(groups) & set(bias_map)
    days=[]
    for d in sorted(traded):
        g = groups[d]
        gap_val = float(g["open"].iloc[0])
        pc = prev_close.get(d)
        gap="flat"
        if pc:
            frac=abs(gap_val-pc)/pc
            gap="flat" if frac<=cfg["gap_pct"] else "gap-up" if gap_val>pc else "gap-down"
        ctx={"gap":gap,"extreme":_ext(zone_map.get(d)),"avg_range":avg_by_date.get(d)}
        days.append(simulate_day_1min(g, bias_map[d], cfg=cfg, ctx=ctx))
    all_trades=[t for dy in days for t in dy["trades"]]
    wins=[t for t in all_trades if t["r_multiple"]>0]
    from collections import Counter
    outcomes=Counter(t["outcome"] for t in all_trades)
    total_r = round(sum(t["r_multiple"] for t in all_trades),2)
    avg_r = round(total_r/len(all_trades),2) if all_trades else 0
    win_rate = round(len(wins)/len(all_trades)*100,1) if all_trades else 0
    gross_win = sum(r for r in [t["r_multiple"] for t in all_trades] if r>0)
    gross_loss = sum(-r for r in [t["r_multiple"] for t in all_trades] if r<0)
    pf = gross_win/gross_loss if gross_loss>0 else 999 if gross_win>0 else 0
    pf=round(pf,2)
    # per sl mode best etc not needed
    return {
        "cfg": cfg_dict,
        "stats": {"days_total":len(days),"days_traded":sum(1 for dy in days if dy["trades"]),"trades":len(all_trades),"wins":len(wins),"win_rate":win_rate,"total_r":total_r,"avg_r":avg_r,"outcomes":dict(outcomes)},
        "pf": pf,
        "trades": len(all_trades),
        "win_rate": win_rate,
        "total_r": total_r,
        "avg_r": avg_r,
    }

if __name__ == "__main__":
    import itertools, json, time, sys
    from concurrent.futures import ProcessPoolExecutor, as_completed

    # choose grid
    default_grid = {
        "sl_mode": ["avg", "avg075", "prev_pivot", "swing_end"],
        "rr_target": [2.0, 3.0, 4.0],
        "min_sl_pts": [0, 13, 20],
        "breakeven_r": [0, 1.0, 1.5],
        "gap_pct": [0.0027, 0.0035],
        "ft_fail_enabled": [True, False],
        "max_entries": [1, 2],
        "entry_cutoff": ["15:15", "12:00"],
        "second_trade_after": ["sl_only", "always"],
    }
    quick_grid = {
        "sl_mode": ["avg", "prev_pivot"],
        "rr_target": [2.0, 3.0],
        "min_sl_pts": [0, 13],
        "breakeven_r": [0, 1.0],
        "gap_pct": [0.0027],
        "ft_fail_enabled": [True],
        "max_entries": [1, 2],
        "entry_cutoff": ["15:15", "12:00"],
        "second_trade_after": ["sl_only", "always"],
    }
    arg = sys.argv[1] if len(sys.argv)>1 else "--default"
    grid = quick_grid if arg=="--quick" else default_grid
    if arg=="--full":
        grid = {
            "sl_mode": ["avg", "avg075", "avg05", "prev_pivot", "swing_end", "fixed8"],
            "rr_target": [1.5, 2.0, 3.0, 4.0],
            "min_sl_pts": [0, 8, 13, 20],
            "breakeven_r": [0, 1.0, 1.5, 2.0],
            "gap_pct": [0.0015, 0.0027, 0.0035],
            "ft_fail_enabled": [True, False],
            "max_entries": [1, 2],
            "entry_cutoff": ["15:15", "14:00", "12:00", "11:30"],
            "second_trade_after": ["sl_only", "loss", "always"],
        }
    keys=list(grid.keys())
    combos=list(itertools.product(*grid.values()))
    total=len(combos)
    print(f"[{datetime.now()}] Grid {arg} total {total} combos", flush=True)
    for k,v in grid.items():
        print(f"  {k}: {v}")

    # Build cfg dicts
    cfg_list=[]
    for c in combos:
        d=dict(zip(keys,c))
        d["execution"]="1min"
        d["swing_traverse"]=True
        d["need_opp_swing"]=True
        # ensure gap_pct is float
        cfg_list.append(d)

    start=time.time()
    results=[]
    # Use 4 workers (adjust to cpu count)
    workers = min(4, os.cpu_count() or 4)
    print(f"[{datetime.now()}] Starting MP with {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker) as ex:
        futures={ex.submit(run_one_cfg, cfg): cfg for cfg in cfg_list}
        done=0
        for fut in as_completed(futures):
            done+=1
            if done%20==0 or done==total:
                elapsed=time.time()-start
                print(f"[{datetime.now()}] {done}/{total} elapsed {elapsed:.1f}s avg {elapsed/done:.2f}s per cfg", flush=True)
            try:
                res=fut.result()
                results.append(res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                results.append({"cfg":futures[fut],"error":str(e),"total_r":-9999})

    elapsed=time.time()-start
    print(f"Done {total} in {elapsed:.1f}s", flush=True)
    # Rank
    valid=[r for r in results if "error" not in r]
    ranked=sorted(valid, key=lambda x: (x["total_r"], x["win_rate"], x["pf"]), reverse=True)
    print("\nTOP 20 by total_R")
    for i,r in enumerate(ranked[:20]):
        cfg=r["cfg"]
        print(f"#{i+1:2d} R{r['total_r']:+7.2f} WR{r['win_rate']:4.1f}% PF{r['pf']:4.2f} trades{r['trades']:3d} avg{r['avg_r']:+5.2f} | sl:{cfg['sl_mode']:10s} rr:{cfg['rr_target']} min{cfg['min_sl_pts']:2.0f} BE{cfg['breakeven_r']} gap{cfg['gap_pct']*100:.2f}% ft{cfg['ft_fail_enabled']} max{cfg['max_entries']} cut{cfg['entry_cutoff']} 2nd{cfg['second_trade_after']}")

    print("\nTOP 20 by win_rate (trades>=50)")
    ranked_wr=sorted([r for r in valid if r["trades"]>=50], key=lambda x: (x["win_rate"], x["total_r"]), reverse=True)
    for i,r in enumerate(ranked_wr[:20]):
        cfg=r["cfg"]
        print(f"#{i+1:2d} WR{r['win_rate']:4.1f}% R{r['total_r']:+7.2f} PF{r['pf']:4.2f} trades{r['trades']:3d} | sl:{cfg['sl_mode']:10s} rr{cfg['rr_target']} min{cfg['min_sl_pts']} BE{cfg['breakeven_r']} cut{cfg['entry_cutoff']} 2nd{cfg['second_trade_after']}")

    # Save
    out=Path(__file__).parent / f"sweep_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out,"w") as f:
        json.dump(ranked[:100], f, indent=2, default=str)
    print(f"Saved {out}")
    csv_path=out.with_suffix(".csv")
    import csv
    with open(csv_path,"w",newline="") as cf:
        w=csv.writer(cf)
        w.writerow(["rank","total_R","win_rate","pf","trades","avg_R","sl_mode","rr","min_sl","be","gap","ft","max","cutoff","second"])
        for i,r in enumerate(ranked[:100]):
            cfg=r["cfg"]
            w.writerow([i+1, r["total_r"], r["win_rate"], r["pf"], r["trades"], r["avg_r"], cfg["sl_mode"], cfg["rr_target"], cfg["min_sl_pts"], cfg["breakeven_r"], cfg["gap_pct"], cfg["ft_fail_enabled"], cfg["max_entries"], cfg["entry_cutoff"], cfg["second_trade_after"]])
    print(f"Saved {csv_path}")

    print("\nBEST per sl_mode")
    for sl in sorted(set(r["cfg"]["sl_mode"] for r in valid)):
        best=max([r for r in valid if r["cfg"]["sl_mode"]==sl], key=lambda x: x["total_r"])
        cfg=best["cfg"]
        print(f"{sl:12s} R{best['total_r']:+7.2f} WR{best['win_rate']:4.1f}% PF{best['pf']:4.2f} trades{best['trades']:3d} | rr{cfg['rr_target']} min{cfg['min_sl_pts']} BE{cfg['breakeven_r']} gap{cfg['gap_pct']*100:.2f}% ft{cfg['ft_fail_enabled']} max{cfg['max_entries']} cut{cfg['entry_cutoff']} 2nd{cfg['second_trade_after']}")
