"""Bybit v18 with EXACT same params as Binance spot default."""
import sys; sys.path.insert(0, '.')
from src.btc.btc_routes import _load_window, _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.btc.btc_engine import trade_stats

htf_win, _ = _load_window("1h", None, "BTCUSDT_BYBIT")
ltf_win, _ = _load_window("15m", None, "BTCUSDT_BYBIT")
htf_candles, htf_flow = htf_win
ltf_candles, ltf_flow = ltf_win
htf_swings = _compute_swings(htf_flow, "continuous", min_bars=20)
ltf_swings = _compute_swings(ltf_flow, "continuous", min_bars=50)
ltf_fine = _load_fine_1m(ltf_candles[0]["ts"], ltf_candles[-1]["ts"], "BTCUSDT_BYBIT")

# EXACT same params as spot default
r = simulate_htf_ltf_streak_halt(
    htf_candles, htf_swings, ltf_candles, ltf_swings,
    fine_ltf=ltf_fine, sl_buf_atr=0.25, ext_stop_r=1.5,
    mode="b2_vs_flip_chop", cooldown_bars=20, max_consecutive_losses=5
)
s = trade_stats(r.get("ltf_trades", []))

print("=== Bybit v18 — SAME params as Binance Spot ===")
print(f"chop=61.8 cooldown=20 slbuf=0.25 ext=1.5 mcl=5 mode=b2_vs_flip_chop")
print(f"Trades: {s['trades']}")
print(f"Net R:  {s['total_r']:.1f}")
print(f"Win%:   {s['win_rate']:.1f}%")
print(f"DD:     {s['max_drawdown_r']:.1f}R")
print(f"PF:     {s['profit_factor']}")
print(f"Payoff: {s['payoff']}")
print(f"Avg R:  {s['avg_r']:.3f}")
print(f"Max consec losses: {s['max_consecutive_losses']}")
print(f"Longs: {s['longs']}  Shorts: {s['shorts']}")
print(f"Outcomes: {s['outcomes']}")
print()
print("Yearly breakdown:")
for yr, r_val in s.get("yearly_r", {}).items():
    print(f"  {yr}: {r_val:+.1f}R")
print()
print("Monthly (last 12):")
monthly = s.get("monthly_r", {})
months = sorted(monthly.keys())[-12:]
for m in months:
    print(f"  {m}: {monthly[m]:+.1f}R")
