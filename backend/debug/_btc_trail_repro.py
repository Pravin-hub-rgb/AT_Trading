"""Repro: what does 'Trailing Max R' (trail_max_r preset) actually return per tf/window?"""
import sys

sys.path.insert(0, ".")

from src.btc.btc_routes import btc_backtest  # noqa: E402

PRESET = dict(
    entry_break="decisive",
    sl_mode="swing",
    rr_target=3.0,
    trailing="swing",
    breakeven_r=1.0,
    min_bars=20,
    regime="off",
    bias="off",
)

configs = []
for tf in ("5m", "15m", "1m"):
    for limit in (2000, 5000, None):
        configs.append((tf, limit))

for tf, limit in configs:
    try:
        r = btc_backtest(tf=tf, mode="continuous", limit=limit, **PRESET)
        if not isinstance(r, dict):
            print(tf, limit, "ERROR", getattr(r, "status_code", "?"))
            continue
        s = r["stats"]
        p = r["params"]
        days = (r["count"] / {"1m": 1440, "5m": 288, "15m": 96}[tf])
        tag = ""
        if s["trades"] in (489,) or abs(s["total_r"] - 126.91) < 3:
            tag = "   <-- MATCHES user"
        print(
            f"tf={tf:<3} limit={str(limit):<6} count={r['count']:<7} (~{days:.1f}d) "
            f"swings={r['swings_used']:<5} trades={s['trades']:<5} win%={s['win_rate']:<5.1f} "
            f"total_r={s['total_r']:<+8.2f} avg={s['avg_r']:<+6.3f} min_bars={p['min_bars']}{tag}"
        )
    except Exception as e:  # noqa: BLE001
        print(tf, limit, "EXC", repr(e))