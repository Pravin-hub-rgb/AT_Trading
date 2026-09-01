"""RR target sweep — which fixed target (1:1 .. 1:4) performs best?

Runs the full backtest per rr_target for one execution mode and prints a
comparison table. Usage (from backend/):
    python debug/_rr_sweep.py 5min
    python debug/_rr_sweep.py 1min
"""
import sys
sys.path.insert(0, '.')
sys.path = [p for p in sys.path if 'src' not in p]
sys.path.insert(0, '.')
import pandas as pd
from src.intraday import run_backtest, DEFAULT_CFG, resolve_cfg
from src.bias import compute_bias
from src.config import DATA_DIR

assert resolve_cfg({})["rr_target"] == 3.0, "resolve_cfg must default rr_target to 3.0"

execution = sys.argv[1] if len(sys.argv) > 1 else "5min"
RR_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

df5 = pd.read_csv(DATA_DIR / 'nifty_5min.csv')
df5['timestamp'] = pd.to_datetime(df5['timestamp'])
daily_df = pd.read_csv(DATA_DIR / 'nifty_daily.csv') if (DATA_DIR / 'nifty_daily.csv').exists() else None
labels = [lb for lb in compute_bias(df5, daily_df)
          if lb['date'] in set(df5['timestamp'].astype(str).str[:10])]

df1 = pd.read_csv(DATA_DIR / 'nifty_1min.csv') if (DATA_DIR / 'nifty_1min.csv').exists() else None

results = []
for rr in RR_VALUES:
    cfg = dict(DEFAULT_CFG, execution=execution, rr_target=rr)
    if execution == "1min":
        import src.intraday_1m_standalone as m1
        bt = m1.run_backtest_1min(df1, labels, cfg=cfg)
    else:
        bt = run_backtest(df5, labels, cfg=cfg, df_1min=df1)
    s = bt["stats"]
    oc = s.get("outcomes", {})
    oc_str = " ".join(f"{k}:{v}" for k, v in sorted(oc.items()))
    cases = s.get("cases") or {}
    case_str = " ".join(
        f"{c}:{v['total_r']:+.1f}" for c, v in sorted(cases.items()) if v.get("trades")
    )
    print(
        f"RR 1:{rr:<4} | trades={s['trades']:<4} wins={s['wins']:<4} "
        f"wr={s['win_rate']:<6} total_r={s['total_r']:<8} avg_r={s['avg_r']:<6} "
        f"longs={s.get('longs','-')} shorts={s.get('shorts','-')}",
        flush=True,
    )
    print(f"          outcomes: {oc_str}", flush=True)
    print(f"          cases R : {case_str}", flush=True)
    results.append((rr, s))

print(f"\n=== SUMMARY ({execution}) ===", flush=True)
best = max(results, key=lambda t: t[1]["total_r"])
best_avg = max(results, key=lambda t: t[1]["avg_r"])
print(f"best total_r : RR 1:{best[0]}  ({best[1]['total_r']}R over {best[1]['trades']} trades)", flush=True)
print(f"best avg_r   : RR 1:{best_avg[0]}  ({best_avg[1]['avg_r']}R/trade)", flush=True)
