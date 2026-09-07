"""Sweep for far-from-EMA + force_trade_mode"""
import itertools, json, time, sys, os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

GLOBAL_DATA = {}

def init_worker():
    global GLOBAL_DATA
    from src import bias as bias_svc, config
    p1 = config.DATA_DIR / "nifty_1min.csv"
    p5 = config.DATA_DIR / "nifty_5min.csv"
    pdaily = config.DATA_DIR / "nifty_daily.csv"
    import pandas as pd
    df1 = pd.read_csv(p1)
    df5 = pd.read_csv(p5)
    daily = pd.read_csv(pdaily) if pdaily.exists() else None
    df1["timestamp"] = pd.to_datetime(df1["timestamp"])
    df1["ts"] = (df1["timestamp"].astype("int64")//1_000_000_000).astype("int64")
    df1 = df1.sort_values("timestamp").drop_duplicates(subset="ts", keep="last")
    GLOBAL_DATA["df1"] = df1
    GLOBAL_DATA["df5"] = df5
    GLOBAL_DATA["daily"] = daily
    from src.intraday import EOD_EXIT
    dates = df1["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d,g in df1.groupby(dates, sort=True)}
    ordered = sorted(groups)
    prev_close = {ordered[i]: float(groups[ordered[i-1]]["close"].iloc[-1]) for i in range(1,len(ordered))}
    GLOBAL_DATA["groups"] = groups
    GLOBAL_DATA["ordered"] = ordered
    GLOBAL_DATA["prev_close"] = prev_close

def run_one(args):
    cfg_dict, bias_mode = args
    global GLOBAL_DATA
    from src import bias as bias_svc
    from src.intraday_1m_standalone import simulate_day_1min
    from src.intraday import resolve_cfg
    df1 = GLOBAL_DATA["df1"]
    df5 = GLOBAL_DATA["df5"]
    daily = GLOBAL_DATA["daily"]
    groups = GLOBAL_DATA["groups"]
    ordered = GLOBAL_DATA["ordered"]
    prev_close = GLOBAL_DATA["prev_close"]
    labels = bias_svc.compute_bias_with_mode(df5, daily, df1, mode=bias_mode)
    bias_map = {l["date"]: l["bias"] for l in labels}
    zone_map = {l["date"]: (l.get("overview") or {}).get("zone") for l in labels}
    def _ext(z): return "highs" if z in ("new_high","highs_extreme") else "lows" if z in ("new_low","lows_extreme") else None
    # avg_by_date
    from src.intraday import EOD_EXIT
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
    cfg = resolve_cfg(cfg_dict)
    cfg["bias_mode"] = bias_mode
    traded = set(groups) & set(bias_map.keys())
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
    return {
        "bias_mode": bias_mode,
        "cfg": cfg_dict,
        "stats": {"days_total":len(days),"days_traded":sum(1 for dy in days if dy["trades"]),"trades":len(all_trades),"wins":len(wins),"win_rate":win_rate,"total_r":total_r,"avg_r":avg_r,"outcomes":dict(outcomes)},
        "pf": pf,
        "trades": len(all_trades),
        "win_rate": win_rate,
        "total_r": total_r,
        "avg_r": avg_r,
    }

if __name__ == "__main__":
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import itertools

    # Grid for far sweep - include force_trade_mode and lower EMA
    grid = {
        "sl_mode": ["prev_pivot", "avg"],
        "rr_target": [2.0, 3.0, 4.0],
        "min_sl_pts": [13, 15],
        "breakeven_r": [0, 1.0],
        "gap_pct": [0.0027],
        "ft_fail_enabled": [True],
        "max_entries": [2],
        "entry_cutoff": ["15:15"],
        "second_trade_after": ["always"],
        "force_trade_mode": [None, "aggressive", "conservative"],
    }
    bias_modes = ["ema_daily_10_far_50", "ema_daily_5_far_50", "ema_5min_20_50_far_30", "ema_1min_5_far_20", "ema_1min_10_far_30", "ema_daily_10", "ema_5min_20_50"]
    # For non-far modes, we still test force, but far modes are the focus
    keys=list(grid.keys())
    combos=list(itertools.product(*grid.values()))
    tasks=[]
    for bm in bias_modes:
        for c in combos:
            d=dict(zip(keys,c))
            d["execution"]="1min"
            d["swing_traverse"]=True
            d["need_opp_swing"]=True
            # Convert None force to not set? Keep as None to test case-driven
            tasks.append((d, bm))
    total=len(tasks)
    print(f"[{datetime.now()}] Far+Force sweep: {len(combos)} combos per bias × {len(bias_modes)} biases = {total} total")
    print(f"Grid: {grid}")
    print(f"Bias modes: {bias_modes}")
    start=time.time()
    workers = min(8, os.cpu_count() or 4)
    print(f"[{datetime.now()}] Starting MP with {workers} workers")
    results=[]
    with ProcessPoolExecutor(max_workers=workers, initializer=init_worker) as ex:
        futures={ex.submit(run_one, t): t for t in tasks}
        done=0
        for fut in as_completed(futures):
            done+=1
            if done%50==0 or done==total:
                elapsed=time.time()-start
                print(f"[{datetime.now()}] {done}/{total} elapsed {elapsed:.1f}s avg {elapsed/done:.2f}s", flush=True)
            try:
                res=fut.result()
                results.append(res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                cfg,bm = futures[fut]
                results.append({"bias_mode":bm,"cfg":cfg,"error":str(e),"total_r":-9999})
    elapsed=time.time()-start
    print(f"Done {total} in {elapsed:.1f}s")

    from collections import defaultdict
    by_bias=defaultdict(list)
    for r in results:
        if "error" in r:
            continue
        by_bias[r["bias_mode"]].append(r)

    for bm, lst in by_bias.items():
        ranked=sorted(lst, key=lambda x: (x["total_r"], x["win_rate"], x["pf"]), reverse=True)
        print(f"\n=== Best for {bm} ===")
        for i,r in enumerate(ranked[:5]):
            cfg=r["cfg"]
            print(f"#{i+1} R{r['total_r']:+7.2f} WR{r['win_rate']:4.1f}% PF{r['pf']:4.2f} trades{r['trades']:3d} | sl:{cfg['sl_mode']:10s} rr:{cfg['rr_target']} min{cfg['min_sl_pts']:2.0f} BE{cfg['breakeven_r']} force:{cfg['force_trade_mode']}")
        out = Path(__file__).parent / f"sweep_far_{bm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(out,"w") as f:
            json.dump(ranked[:20], f, indent=2, default=str)
        print(f"Saved {out}")

    # Overall best
    all_valid=[r for r in results if "error" not in r]
    ranked_all=sorted(all_valid, key=lambda x: (x["total_r"], x["win_rate"], x["pf"]), reverse=True)
    print(f"\n=== Overall Top 10 ===")
    for i,r in enumerate(ranked_all[:10]):
        cfg=r["cfg"]
        print(f"#{i+1} {r['bias_mode']:20s} R{r['total_r']:+7.2f} WR{r['win_rate']:4.1f}% PF{r['pf']:4.2f} trades{r['trades']:3d} | sl:{cfg['sl_mode']} rr:{cfg['rr_target']} force:{cfg['force_trade_mode']}")

    out_all = Path(__file__).parent / f"sweep_far_best_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(out_all,"w") as f:
        json.dump(ranked_all[:50], f, indent=2, default=str)
    print(f"\nSaved overall {out_all}")
