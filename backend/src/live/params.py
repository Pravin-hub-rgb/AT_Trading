"""FROZEN v18 production parameters — the exact configuration validated as
best (330 trades, +331.1R gross / ~+200R net, PF 2.81, 4/4 years positive).

Do not edit without re-running: 33-test checklist + full backtest + A/B.
Sourced from btc_routes.py v18 wiring + simulate_htf_ltf_streak_halt defaults.
"""

# Strategy selection
STRATEGY_NAME = "Backbencher"   # codename: low win rate (36.4%), tops the life game
STRATEGY = "v18_streak_halt"
MODE = "b2_vs_flip_chop"        # HTF B2 windows when chop>61.8, else FLIP windows
WINDOW_END = "exit"             # window = HTF trade lifetime (r_touch/bias_flip REJECTED)

# Swing chains
HTF_TF = "1h"
HTF_MIN_BARS = 20               # 1h chain (v7 flip windows)
LTF_TF = "15m"
LTF_MIN_BARS = 50               # 15m chain (MB50)
FILL_TF = "1m"                  # fine fills

# Regime gate
CHOP_LOOKBACK = 14              # 1h Choppiness Index lookback
CHOP_THRESHOLD = 61.8           # golden ratio, plateau-proven (sweep 55-70 all +305..338R)

# Risk / execution
SL_BUF_ATR = 0.25               # SL = swing extreme ± 0.25*ATR(15m,14)
EXT_STOP_R = 1.5                # extended stop
RR_TARGET = 3.0                 # HTF window target
CAP_DAYS = 16                   # HTF trade time cap
COOLDOWN_BARS = 20              # 15m bars after a loss
MAX_CONSECUTIVE_LOSSES = 5      # streak halt

# Costs (per side, % of notional + points)
FEE_PCT = 0.05
SLIPPAGE_PTS = 2.0

# Data schema (identical to btc_config.load_btc_df output)
CANDLE_KEYS = ("date", "ts", "open", "high", "low", "close")
