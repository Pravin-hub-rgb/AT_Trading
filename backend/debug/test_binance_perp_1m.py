"""Binance Perp v18 backtest with 1m fills — default + sweep."""
import sys; sys.path.insert(0, '.')
from src.btc.btc_routes import _load_window, _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.btc.btc_engine import trade_stats

htf_win, _ = _load_window("1h", None, "BTCUSDT_PERP")
ltf_win, _ = _load_window("15m", None, "BTCUSDT_PERP")
htf_candles, htf_flow = htf_win
ltf_candles, ltf_flow = ltf_win
htf_swings = _compute_swings(htf_flow, "continuous", min_bars=20)
ltf_swings = _compute_swings(ltf_flow, "continuous", min_bars=50)
ltf_fine = _load_fine_1m(ltf_candles[0]["ts"], ltf_candles[-1]["ts"], "BTCUSDT_PERP")
print(f"1h: {len(htf_candles)} candles, {len(htf_swings)} swings")
print(f"15m: {len(ltf_candles)} candles, {len(ltf_swings)} swings")
print(f"1m fine: {len(ltf_fine)} candles")

def run(label, **kwargs):
    r = simulate_htf_ltf_streak_halt(
        htf_candles, htf_swings, ltf_candles, ltf_swings,
        fine_ltf=ltf_fine, **kwargs
    )
    s = trade_stats(r.get("ltf_trades", []))
    net = s.get("total_r", 0)
    dd = s.get("max_drawdown_r", 0)
    n = s.get("trades", 0)
    print(f"  {label}: {n}t net={net:.1f}R wr={s.get('win_rate',0):.1f}% dd={dd:.1f}R pf={s.get('profit_factor',0)}")
    return s

print("\n--- Default spot params ---")
run("Default (chop=61.8 cd=20 slbuf=0.25)",
    sl_buf_atr=0.25, ext_stop_r=1.5, mode="b2_vs_flip_chop",
    chop_thresh=61.8, cooldown_bars=20, max_consecutive_losses=5)

print("\n--- Sweep ---")
best = None
for chop in [56, 58, 60, 61.8]:
    for cd in [0, 5, 10, 20]:
        for slbuf in [0.15, 0.20, 0.25, 0.30]:
            r = simulate_htf_ltf_streak_halt(
                htf_candles, htf_swings, ltf_candles, ltf_swings,
                fine_ltf=ltf_fine,
                sl_buf_atr=slbuf, ext_stop_r=1.5,
                mode="b2_vs_flip_chop", chop_thresh=chop,
                cooldown_bars=cd, max_consecutive_losses=5
            )
            s = trade_stats(r.get("ltf_trades", []))
            net = s.get("total_r", 0)
            dd = s.get("max_drawdown_r", 0)
            n = s.get("trades", 0)
            key = (net, -dd, -n)
            if best is None or key > best[0]:
                best = (key, chop, cd, slbuf, net, dd, n, s)
                print(f"  BEST: chop={chop} cd={cd} slbuf={slbuf} -> {n}t net={net:.1f}R wr={s.get('win_rate',0):.1f}% dd={dd:.1f}R")

k, chop, cd, slbuf, net, dd, n, s = best
print(f"\nFINAL BEST: chop={chop} cd={cd} slbuf={slbuf}")
print(f"  {n}t net={net:.1f}R wr={s.get('win_rate',0):.1f}% dd={dd:.1f}R pf={s.get('profit_factor',0)}")
print(f"  Yearly: {s.get('yearly_r', {})}")
