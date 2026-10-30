"""Book 107 - the single strategy this deployment runs.

Book: fsent_champ_long_mcloff_htf15 (code 107)
Source: backtest/tests/registry, measured 2026-10-22 (repin_all, net lens,
        wait-for-FS gate).
Pins:  IS 2026: 520t / +508.37R / DD 27.23R / WR 40.0%
       OOS 2021-22: 290t / +220.71R / DD 9.61R / WR 41.0%

The wait-for-FS gate is in the engine, not here: an entry on a mark may only be
taken once the PREVIOUS swing has printed its FS. Entering at this swing's own
FS print is a different thing and is unchanged. The gate cost this book
30.03R in sample and 52.21R out of sample - it removed 51 in-sample and 48
out-of-sample entries that were taken before the previous swing was declared,
and the chain that replaced them was worth less than what it removed.

These 15 values are the merged engine signature: registry BP + the book's
own params. Everything else is unified.py's default, which is part of the
tested configuration - do not add knobs here that the book did not pin.
"""

BOOK_NAME = "fsent_champ_long_mcloff_htf15"
BOOK_CODE = "107"

BOOK_PARAMS = {
    "atr_high_thresh": 0.65,
    "atr_low_thresh": 0.35,
    "chop_thresh": 58.0,
    "cooldown_bars": 8,
    "exp_fs_entry_side": "long",
    "exp_partial_r": 0.0,
    "exp_persist": 7,
    "ext_stop_r": 3.0,
    "htf_rr": 3.0,
    "max_consecutive_losses": 0,
    "max_positions": 0,
    "mode": "atr_high",
    "pivot_rule": "leg",
    "sl_buf_atr": 0.01,
    "window_end": "exit",
}

# Book 107 ships on the htf15 swing series:
#   15m: continuous chain, minBars=50 (engine MB50)
#   1h : continuous chain, minBars=15 (the HTF plane at a longer leg)
SWING = {"min_bars_15m": 50, "min_bars_1h": 15}

# Distinct persisted-chain label so the old sw20 state (swing_state_1h) is
# never re-used by the minBars=15 chain.
SWING_1H_LABEL = "1h_htf15"


def get_book_params(instrument=None):
    """Return the active book's engine params. Instrument is accepted for
    backwards compatibility with the old get_v18_params() call sites."""
    return dict(BOOK_PARAMS)
