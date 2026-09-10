"""v18_streak_halt parameters - the verified parameter matrix.

Each value is lifted directly from the backtester source. DO NOT edit by hand
without updating the corresponding backtester code AND the golden test.

Sources:
  backend/src/btc/btc_routes.py:834-853 (v18 branch call)
  backend/debug/test_cat_f.py (golden test: 330 trades, +331.1R)
  backend/src/btc/engines/htf_ltf/v18_streak_halt.py (engine defaults)
"""

# v18 call signature (btc_routes.py:834-853)
V18 = {
    "sl_buf_atr": 0.25,            # SL = extreme +/- 0.25*ATR(14) on 15m
    "ext_stop_r": 1.5,             # ENTRY GATE: pause new LTF entries when 1h leg >1.5R unrealized
    "mode": "b2_vs_flip_chop",    # chop>61.8 -> Decisive (B2|FLIP); else FLIP windows
    "cooldown_bars": 20,           # 15m bars to skip after a loss
    "max_consecutive_losses": 5,   # halt after 5L, resume on next winner
}

# engine internal defaults (v18_streak_halt.py:78-87)
V18_ENGINE = {
    "chop_thresh": 61.8,           # 1h chop threshold (log Dreiss, 14-bar)
    "atr_low_thresh": 0.35,        # 15m ATR% < 0.35 also routes to Decisive
    "atr_high_thresh": 0.65,       # (unused in b2_vs_flip_chop, kept for sweep parity)
    "rr_target": 3.0,              # fixed 3R target on BOTH 1h window and 15m LTF trades
    "window_end": "exit",          # HTF window lives until its trade exits (SL/3R/16d)
}

# swing chain params (test_cat_f.py:20-21)
SWING = {
    "min_bars_1h": 20,             # SwingEngine minBars for 1h
    "min_bars_15m": 50,            # SwingEngine minBars for 15m
}

# chop formula constants (v18_streak_halt.py:12-37)
CHOP = {
    "lookback": 14,                # TR/ range lookback
    "formula": "100*log10(STR/range) / log10(14)",
}

# ATR formula (v18_streak_halt.py:39-54)
ATR = {
    "lookback": 14,                # rolling TR mean window
    "pct_scale": 100,              # ATR% = ATR/close * 100
}

