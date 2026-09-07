"""Reproduce the IN-SAMPLE-ONLY headline numbers against the pristine backup CSV
(data/btc/backup_insample/) — proves the merge didn't distort history."""
import csv, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

from src.btc.btc_engine import compute_btc_swings, simulate_btc_trades, trade_stats

FAIL = 0

def check(name, cond, extra=""):
    global FAIL
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond:
        FAIL += 1

def load_backup(tf):
    p = "data/btc/backup_insample/BTCUSDT_%s.csv" % tf
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "date": r["timestamp"],
            "ts": int(__import__("datetime").datetime.strptime(
                r["timestamp"], "%Y-%m-%d %H:%M:%S").timestamp()),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
        }
        for r in rows
    ]

# 5m Trailing Max R: decisive/swing-trail/BE1/mb20 -> 1720 tr, +392.95R
candles = load_backup("5m")
swings = compute_btc_swings(candles, min_bars=20)
trades = simulate_btc_trades(candles, swings, entry_break="decisive",
                             sl_mode="swing", rr_target=3.0, trailing="swing",
                             breakeven_r=1.0, skip_first=True)
st = trade_stats(trades)
check("in-sample 5m trail repro", st["trades"] == 1720 and abs(st["total_r"] - 392.95) < 0.5,
      f"tr={st['trades']} R={st['total_r']}")

# 5m baseline: decisive/fixed-3R/mb14 -> 557 tr, +67.89R
candles14 = load_backup("5m")
swings14 = compute_btc_swings(candles14, min_bars=14)
trades14 = simulate_btc_trades(candles14, swings14, entry_break="decisive",
                               sl_mode="swing", rr_target=3.0, trailing="off",
                               breakeven_r=1.0, skip_first=True)
st14 = trade_stats(trades14)
check("in-sample 5m baseline repro", st14["trades"] == 557 and abs(st14["total_r"] - 67.89) < 0.5,
      f"tr={st14['trades']} R={st14['total_r']}")

# 15m decisive swing-trail mb20 -> 489 tr, +126.91R
candles15 = load_backup("15m")
swings15 = compute_btc_swings(candles15, min_bars=20)
trades15 = simulate_btc_trades(candles15, swings15, entry_break="decisive",
                               sl_mode="swing", rr_target=3.0, trailing="swing",
                               breakeven_r=1.0, skip_first=True)
st15 = trade_stats(trades15)
check("in-sample 15m trail repro", st15["trades"] == 489 and abs(st15["total_r"] - 126.91) < 0.5,
      f"tr={st15['trades']} R={st15['total_r']}")

print()
print("FAILURES:", FAIL)
sys.exit(1 if FAIL else 0)
