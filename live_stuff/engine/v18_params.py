"""v18_streak_halt parameters — per-instrument tuned.

Each value is lifted directly from the backtester source. DO NOT edit by hand
without updating the corresponding backtester code AND the golden test.

Sources:
  backend/src/btc/btc_routes.py:869-906 (v18 branch with per-symbol routing)
  backend/debug/bybit_default_params.py (golden test: 331R spot, 308R Bybit)
  backend/src/btc/engines/htf_ltf/v18_streak_halt.py (engine defaults)
"""

# Default v18 params (Binance Spot)
V18 = {
    "sl_buf_atr": 0.25,            # SL = extreme +/- 0.25*ATR(14) on 15m
    "ext_stop_r": 1.5,             # ENTRY GATE: pause new LTF entries when 1h leg >1.5R unrealized
    "mode": "b2_vs_flip_chop",    # chop>61.8 -> B2 windows; else FLIP windows
    "cooldown_bars": 20,           # 15m bars to skip after a loss
    "max_consecutive_losses": 5,   # halt after 5L, resume on next winner
}

# Per-instrument overrides (from btc_routes.py:878-889)
# Peer model: asymmetric % slippage (entry orderly, exit adverse during fast move)
# Very conservative: 0.005%/0.010% — honest when we have no fill data
SYMBOL_PARAMS = {
    "BTCUSDT": {
        "chop_thresh": 61.8,
        "cooldown_bars": 20,
        "sl_buf_atr": 0.25,
        "fee_pct": 0.05,              # Binance taker 0.05%/side
        "entry_slip_pct": 0.005,      # 5bp entry slip (very conservative)
        "exit_slip_pct": 0.010,       # 10bp exit slip (very conservative)
    },
    "BTCUSDT_PERP": {
        "chop_thresh": 61.8,
        "cooldown_bars": 5,
        "sl_buf_atr": 0.15,
        "fee_pct": 0.05,              # Binance taker 0.05%/side
        "entry_slip_pct": 0.005,
        "exit_slip_pct": 0.010,
    },
    "BTCUSDT_BYBIT": {
        "chop_thresh": 58.0,
        "cooldown_bars": 10,
        "sl_buf_atr": 0.10,
        "max_consecutive_losses": 3,
        "fee_pct": 0.055,             # Bybit taker 0.055%/side
        "entry_slip_pct": 0.005,      # 5bp entry slip (very conservative)
        "exit_slip_pct": 0.010,       # 10bp exit slip (very conservative)
    },
}


def get_v18_params(symbol: str = "BTCUSDT") -> dict:
    """Get v18 params for a specific instrument."""
    base = dict(V18)
    overrides = SYMBOL_PARAMS.get(symbol, SYMBOL_PARAMS["BTCUSDT"])
    base.update(overrides)
    return base


# Engine internal defaults (v18_streak_halt.py:78-87)
V18_ENGINE = {
    "chop_thresh": 61.8,           # 1h chop threshold (log Dreiss, 14-bar) — overridden per symbol
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

