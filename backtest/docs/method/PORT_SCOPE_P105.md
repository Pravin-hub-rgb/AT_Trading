# P105 - WHAT PORTING v19 TO LIVE ACTUALLY REQUIRES

Branch: agents/champion-reality-audit
Date: 2026-09-30. This is a scoping note, not a decision. The live loop
is the user''s to rewrite when a strategy is chosen.

## THREE THINGS, ONLY ONE IS A DECISION

### 1. Point live at v19 instead of v18 - mechanical

`live_loop.py:35` imports `simulate_htf_ltf_streak_halt` from v18.
v19 exports the same function name. Change the import path. No
signature change, no behavioural plumbing. The engine already runs on
rolling windows in live exactly as it does in backtest.

### 2. Move the champion params into v18_params.py - mechanical

`v18_params.py` currently carries a different configuration from the
champion in six places (see method/LIVE_PARITY_P104.md). Porting means setting
V18 / SYMBOL_PARAMS to the champion's values:

    mode="atr_high"            (live has b2_vs_flip_chop)
    ext_stop_r=3.0             (live has 1.5)
    sl_buf_atr=0.01            (live has 0.25)
    chop_thresh=58.0           (live has 61.8)
    cooldown_bars=8            (live has 20)
    max_consecutive_losses=3   (live has 5)

Two of these are large. `sl_buf_atr` moves from 0.25 to 0.01, which makes
stops sit almost exactly on the swing pivot instead of a quarter-ATR
buffered beyond it. That changes the risk denominator on every trade and
therefore every R figure. `ext_stop_r` 1.5 to 3.0 admits signals that the
live config currently rejects. Neither is a bug fix; both are part of what
was tuned. They need to be adopted as a set.

### 3. Capital allocation across concurrent positions - THE DECISION

This is the only part that is not mechanical, and it is the reason P99
listed it as open. The champion runs up to 6 simultaneous positions (max
conc 6 IS, 5 OOS). v19 removes the position limit entirely, so the
engine will open as many as the signal stream produces.

The engine sizes every trade from its own SL distance. It has no concept
of a total risk budget, so six concurrent trades each sized at "one
position" is six times the intended exposure. That is a live-execution
question - how much risk to allocate across an overlapping book - and the
answer belongs to whoever owns the account, not to the backtest.

Until that is decided, the champion can be ported and backtested but not
funded.

## WHAT IS ALREADY SAFE

- The engine is the same code in both places. No live-specific entry logic.
- Fillability verified: all 500 entries have close[i] == open[i+1].
- C8 is fixed. No exchange TP; LTF exits are trail-only, matching the
  simulator (0 target exits, 313 trail / 187 sl).
- Lookahead clean in the HTF gate path.

## WHAT REMAINS UNVALIDATED

Live restart, reconnection, incremental state, and fine-data replay were
never exercised against this engine. Forward data holds 2 champion trades
over 12.5 days.