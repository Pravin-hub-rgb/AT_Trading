# P104 - LIVE PARITY. Same engine, different parameters.

Branch: agents/champion-reality-audit
Date: 2026-09-30.

## THE ANSWER

`live_stuff/live_loop.py:35` imports `simulate_htf_ltf_streak_halt` from
`backend/src/btc/engines/htf_ltf/v18_streak_halt.py`. That is the same
function the backtester runs. There is no second engine, no live variant
of the entry logic, no divergence in the trade loop.

The parity gap is parameters, not code.

## PARAMETERS DIFFER IN SIX PLACES

| param | live (v18_params.py) | champion |
|---|---|---|
| `mode` | `b2_vs_flip_chop` | `atr_high` |
| `ext_stop_r` | 1.5 | 3.0 |
| `sl_buf_atr` | 0.25 | 0.01 |
| `chop_thresh` | 61.8 | 58.0 |
| `cooldown_bars` | 20 | 8 |
| `max_consecutive_losses` | 5 | 3 |

Six of the shared parameters disagree. The live bot has never run the
champion configuration.

## FOUR LIVE PARAMS ARE SILENTLY IGNORED

`get_v18_params("BTCUSDT")` returns 13 keys. The engine accepts 9.

    fee_pct = 0.05, entry_slip_pct = 0.005, exit_slip_pct = 0.010,
    rr_target = 3.0

None of these is an engine input. They are applied by the backtest cost
model in `run_experiment.net_r`, outside the simulator. So the engine
never sees them, and neither does the live loop. `rr_target=3.0` happens
to match the engine's hardcoded `target=entry+3.0*risk`, which is why the
mismatch is invisible.

This is correct as written, but it means "the live params" and "the
engine params" are two different vocabularies over the same engine. Any
future change to cost assumptions touches the harness, not the engine,
and the live bot does not inherit it.

## WHY THIS IS NOT A DEFECT YET

The live bot was never pointed at the champion. It is on an older
configuration from `v18_params.py`, and the user has said the live bot
will be rewritten once a strategy is chosen. Nothing here says the live
bot is broken; it says the champion has never been run in it.

The champion needs three things before it can be: v19 (multi-position
and hysteresis) as the engine, the champion param set in
`v18_params.py`, and a decision on capital allocation across concurrent
positions. The last is a design question, not an audit finding.

## ONE THING THAT IS A REAL BUG

`new bugs.md` C8 records that live attaches a 3R take-profit to every LTF
order while the backtest rides winners to +5.02R on the trail. If v19 is
ever pointed at the live loop without fixing that, the backtest and the
bot diverge on every winner. That fix belongs with the port.