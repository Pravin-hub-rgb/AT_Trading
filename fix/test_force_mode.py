import pandas as pd, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from src import bias as b, config
from src.intraday_1m_standalone import run_backtest_1min

p1=config.DATA_DIR/'nifty_1min.csv'
p5=config.DATA_DIR/'nifty_5min.csv'
pdaily=config.DATA_DIR/'nifty_daily.csv'
df1=pd.read_csv(p1)
df5=pd.read_csv(p5)
daily=pd.read_csv(pdaily) if pdaily.exists() else None
labels=b.compute_bias_with_mode(df5, daily, df1, mode='daily_swing')

base_cfg = {"execution":"1min","sl_mode":"prev_pivot","rr_target":4.0,"min_sl_pts":13,"breakeven_r":1.0,"gap_pct":0.0027,"ft_fail_enabled":True,"max_entries":2,"entry_cutoff":"15:15","second_trade_after":"always","swing_traverse":True,"need_opp_swing":True,"bias_mode":"daily_swing"}

for force in [None, "aggressive", "conservative"]:
    cfg=dict(base_cfg)
    if force:
        cfg["force_trade_mode"]=force
    else:
        cfg.pop("force_trade_mode", None)
    res=run_backtest_1min(df1, labels, cfg=cfg)
    s=res['stats']
    print(f"\n=== Force {force} ===")
    print(f"Trades {s['trades']} Wins {s['wins']} Win% {s['win_rate']} TotalR {s['total_r']} Avg {s['avg_r']} PF {round(sum(t['r_multiple'] for d in res['days'] for t in d['trades'] if t['r_multiple']>0)/max(1, -sum(t['r_multiple'] for d in res['days'] for t in d['trades'] if t['r_multiple']<0)),2) if s['trades'] else 0} Days {s['days_traded']}/{s['days_total']} L/S {s['longs']}/{s['shorts']} Outcomes {s['outcomes']}")
    # Also check per trade_mode distribution
    from collections import Counter
    modes=Counter(d['trade_mode'] for d in res['days'])
    print(f"trade_mode dist: {dict(modes)}")
    # Show first few days where forced made difference
    if force:
        # Compare to baseline
        pass
