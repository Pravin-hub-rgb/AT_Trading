"""Compare Bybit vs Spot v18 with 1m fills — same params."""
import sys; sys.path.insert(0, '.')
from src.btc.btc_routes import _load_window, _compute_swings, _load_fine_1m
from src.btc.engines.htf_ltf.v18_streak_halt import simulate_htf_ltf_streak_halt
from src.btc.btc_engine import trade_stats

for label, sym in [("BTC Spot", "BTCUSDT"), ("BTC Bybit", "BTCUSDT_BYBIT")]:
    htf_win, _ = _load_window("1h", None, sym)
    ltf_win, _ = _load_window("15m", None, sym)
    htf_candles, htf_flow = htf_win
    ltf_candles, ltf_flow = ltf_win
    htf_swings = _compute_swings(htf_flow, "continuous", min_bars=20)
    ltf_swings = _compute_swings(ltf_flow, "continuous", min_bars=50)
    ltf_fine = _load_fine_1m(ltf_candles[0]["ts"], ltf_candles[-1]["ts"], sym)

    # Default v18
    r = simulate_htf_ltf_streak_halt(
        htf_candles, htf_swings, ltf_candles, ltf_swings,
        fine_ltf=ltf_fine, sl_buf_atr=0.25, ext_stop_r=1.5,
        mode="b2_vs_flip_chop", cooldown_bars=20, max_consecutive_losses=5
    )
    s = trade_stats(r.get("ltf_trades", []))
    net = s.get("total_r", 0)
    print(f"[{label}] Default v18: {len(r['ltf_trades'])}t net={net:.1f}R wr={s.get('win_rate',0):.1f}% dd={s.get('max_drawdown_r',0):.1f}R pf={s.get('profit_factor',0)}")

    # Bybit-optimized (same params for spot comparison)
    r2 = simulate_htf_ltf_streak_halt(
        htf_candles, htf_swings, ltf_candles, ltf_swings,
        fine_ltf=ltf_fine, sl_buf_atr=0.20, ext_stop_r=1.5,
        mode="b2_vs_flip_chop", cooldown_bars=0, max_consecutive_losses=5
    )
    s2 = trade_stats(r2.get("ltf_trades", []))
    net2 = s2.get("total_r", 0)
    print(f"[{label}] cd=0 slbuf=0.20: {len(r2['ltf_trades'])}t net={net2:.1f}R wr={s2.get('win_rate',0):.1f}% dd={s2.get('max_drawdown_r',0):.1f}R pf={s2.get('profit_factor',0)}")
    print()
