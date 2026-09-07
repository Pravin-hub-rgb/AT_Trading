"""Per-bias smart sweep - finds best logical (min>=13) per master bias mode"""
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
    # Precompute groups etc for speed (like previous)
    from src.intraday import EOD_EXIT
    dates = df1["timestamp"].dt.strftime("%Y-%m-%d")
    groups = {d: g for d,g in df1.groupby(dates, sort=True)}
    ordered = sorted(groups)
    prev_close = {ordered[i]: float(groups[ordered[i-1]]["close"].iloc[-1]) for i in range(1,len(ordered))}
    # For zone etc we need labels per mode later, but we can compute bias_map per mode inside worker per task
    # So store these for reuse
    GLOBAL_DATA["groups"] = groups
    GLOBAL_DATA["ordered"] = ordered
    GLOBAL_DATA["prev_close"] = prev_close

def run_one(args):
    # args = (cfg_dict, bias_mode)
    cfg_dict, bias_mode = args
    global GLOBAL_DATA
    from src import bias as bias_svc
    from src.intraday_1m_standalone import simulate_day_1min
    from src.intraday import resolve_cfg
    import pandas as pd
    df1 = GLOBAL_DATA["df1"]
    df5 = GLOBAL_DATA["df5"]
    daily = GLOBAL_DATA["daily"]
    groups = GLOBAL_DATA["groups"]
    ordered = GLOBAL_DATA["ordered"]
    prev_close = GLOBAL_DATA["prev_close"]
    # Compute bias labels for this mode
    labels = bias_svc.compute_bias_with_mode(df5, daily, df1, mode=bias_mode)
    bias_map = {l["date"]: l["bias"] for l in labels}
    zone_map = {l["date"]: (l.get("overview") or {}).get("zone") for l in labels}
    def _ext(z): return "highs" if z in ("new_high","highs_extreme") else "lows" if z in ("new_low","lows_extreme") else None
    # avg_by_date needs day_ranges - compute quickly per task (could be cached per mode but okay)
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
    # Ensure bias_mode in cfg for later
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

    # Smart grid per bias - logical min>=13 only
    grid = {
        "sl_mode": ["avg", "prev_pivot", "swing_end"],
        "rr_target": [2.0, 3.0, 4.0],
        "min_sl_pts": [13, 15, 20],
        "breakeven_r": [0, 1.0],
        "gap_pct": [0.0027, 0.0035],
        "ft_fail_enabled": [True],
        "max_entries": [2],
        "entry_cutoff": ["15:15"],
        "second_trade_after": ["always"],
    }
    bias_modes = ["daily_swing", "ema_daily_10", "ema_5min_20_50", "opposite_first", "streak_3_1_1", "ema_daily_5"]
    # For daily_swing we also want to test sl_only vs always? But we fixed to always for now as it was best. Keep always for per-bias best.
    # To keep total reasonable, we keep second always only. If you want sl_only too, double.

    keys=list(grid.keys())
    combos=list(itertools.product(*grid.values()))
    # Build task list: for each bias_mode, for each combo
    tasks=[]
    for bm in bias_modes:
        for c in combos:
            d=dict(zip(keys,c))
            d["execution"]="1min"
            d["swing_traverse"]=True
            d["need_opp_swing"]=True
            tasks.append((d, bm))
    total=len(tasks)
    print(f"[{datetime.now()}] Per-bias smart grid: {len(combos)} combos per bias × {len(bias_modes)} biases = {total} total")
    print(f"Grid: {grid}")
    print(f"Bias modes: {bias_modes}")
    print(f"Estimated with 8 workers @0.8s/cfg: {total*0.8/60/8:.1f} min wall (4 workers ~{total*0.8/60/4:.1f} min)")
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
                print(f"[{datetime.now()}] {done}/{total} elapsed {elapsed:.1f}s avg {elapsed/done:.2f}s wall {elapsed/60:.1f}min", flush=True)
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

    # Group by bias_mode and rank
    from collections import defaultdict
    by_bias=defaultdict(list)
    for r in results:
        if "error" in r:
            continue
        by_bias[r["bias_mode"]].append(r)

    # Find best per bias
    best_per_bias={}
    for bm, lst in by_bias.items():
        ranked=sorted(lst, key=lambda x: (x["total_r"], x["win_rate"], x["pf"]), reverse=True)
        best= ranked[0]
        best_per_bias[bm]=best
        print(f"\n=== Best for {bm} ===")
        # Top 5 for this bias
        for i,r in enumerate(ranked[:5]):
            cfg=r["cfg"]
            print(f"#{i+1} R{r['total_r']:+7.2f} WR{r['win_rate']:4.1f}% PF{r['pf']:4.2f} trades{r['trades']:3d} | sl:{cfg['sl_mode']:10s} rr:{cfg['rr_target']} min{cfg['min_sl_pts']:2.0f} BE{cfg['breakeven_r']} gap{cfg['gap_pct']*100:.2f}%")
        # Save per bias top 20
        out = Path(__file__).parent / f"sweep_per_bias_{bm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(out,"w") as f:
            import json
            json.dump(ranked[:20], f, indent=2, default=str)
        print(f"Saved {out}")

    # Save combined best
    out_all = Path(__file__).parent / f"sweep_per_bias_best_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_all,"w") as f:
        json.dump(best_per_bias, f, indent=2, default=str)
    print(f"\nSaved best per bias to {out_all}")

    # Also create frontend presets TS file
    presets_path = Path(__file__).parent.parent / "frontend" / "src" / "lib" / "biasPresets.ts"
    # Build TS content
    ts_lines = ["// Auto-generated per-bias best presets - do not edit manually, run sweep_per_bias.py",
                "import type { BacktestParams } from \"./api\";",
                "export const BIAS_PRESETS: Record<string, Partial<BacktestParams>> = {"]
    for bm, best in best_per_bias.items():
        cfg=best["cfg"]
        # Convert gap_pct fraction to string percent for UI
        gap_pct_str = f"{cfg['gap_pct']*100:.2f}".rstrip("0").rstrip(".")
        # Need to ensure we have all fields for BacktestParams
        ts_lines.append(f"  \"{bm}\": {{")
        ts_lines.append(f"    sl_mode: \"{cfg['sl_mode']}\",")
        ts_lines.append(f"    execution: \"1min\",")
        ts_lines.append(f"    rr_target: {cfg['rr_target']},")
        ts_lines.append(f"    min_sl_pts: {cfg['min_sl_pts']},")
        ts_lines.append(f"    breakeven_r: {cfg['breakeven_r']},")
        ts_lines.append(f"    gap_pct: \"{gap_pct_str}\",")
        ts_lines.append(f"    ft_fail_enabled: {str(cfg['ft_fail_enabled']).lower()},")
        ts_lines.append(f"    max_entries: {cfg['max_entries']},")
        ts_lines.append(f"    entry_cutoff: \"{cfg['entry_cutoff']}\",")
        ts_lines.append(f"    second_trade_after: \"{cfg['second_trade_after']}\",")
        ts_lines.append(f"    swing_traverse: true,")
        ts_lines.append(f"    need_opp_swing: true,")
        ts_lines.append(f"    trailing: \"off\",")
        ts_lines.append(f"    entry_method: \"pivot_break\",")
        ts_lines.append(f"  }}, // R{best['total_r']:+.2f} WR{best['win_rate']}% PF{best['pf']} trades{best['trades']}")
    ts_lines.append("};")
    ts_lines.append("")
    ts_lines.append("export const BIAS_PRESETS_META: Record<string, {total_R:number, win_rate:number, pf:number, trades:number}> = {")
    for bm, best in best_per_bias.items():
        ts_lines.append(f"  \"{bm}\": {{ total_R: {best['total_r']}, win_rate: {best['win_rate']}, pf: {best['pf']}, trades: {best['trades']} }},")
    ts_lines.append("};")
    presets_path.write_text("\n".join(ts_lines))
    print(f"Wrote presets to {presets_path}")
    print("\nDone per-bias sweep")
