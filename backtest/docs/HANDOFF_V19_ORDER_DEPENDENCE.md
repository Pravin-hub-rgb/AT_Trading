# HANDOFF — v19 backtest: origin-rule result depends on call order inside one process

## The bug, stated precisely

`simulate_htf_ltf_streak_halt` gives a different result for the SAME input data
depending on what ran earlier in the same Python process. It is deterministic
(identical across runs of the same sequence) but not order-independent.

Minimal repro. One process, one data load, params fixed:

    V19(leg)    ; V19(origin)   ->  origin = 499 trades / 358.98R
    V19(origin) alone            ->  origin = 500 trades / 445.22R
    V19(leg)    alone            ->  leg    = 499 trades / 355.72R
    V19(origin) ; V19(leg)       ->  leg    = 500 trades / 433.47R
    origin ; origin              ->  500 / 445.22 then 500 / 445.22   (stable)
    leg    ; leg                 ->  499 / 355.72 then 499 / 355.72   (stable)

Same rule twice is stable. Switching the rule mid-process changes the SECOND
result. The first run's identity decides the trade COUNT of the second run.

Only the ORIGIN path is affected. The LEG path returns 499 / 355.72 whether it
runs first or second.

## Why it matters

The live route shows the order-dependent value. With a fresh backend, request 1
for `version=v19_champion` already returns 499 / 358.98 gross / 242.28 net —
matching the "leg then origin" sequence above, not "origin alone".

So the pre-C16 retro book in the UI does NOT measure what the offline harness
measures for the same rule:

    harness, origin, fresh process : 500 / 445.22 gross / 325.78 net
    route, origin, any request     : 499 / 358.98 gross / 242.28 net
    registry pin champion_multi_sw10: n 500, net 325.78   (matches the harness)

C16 leg rule agrees everywhere: harness 499 / 355.72 / 239.12 == route 499 /
355.72 / 239.12.

## What has been ruled out

Data is identical. The route's own arguments were dumped mid-request (env
`BTC_DUMP_V19_INPUTS`, a temporary hook in the `v19_champion` branch of
`btc_routes.py`, since removed) and compared against `%TEMP%\at_datacache.pkl`:

    c1h   32434 candles   identical list  True
    c15  129736 candles   identical list  True
    fine 1946026 candles  identical list  True
    sw10    1601 swings    identical list  True
    sw15    2900 swings    identical list  True

Also checked and negative:

- input list lengths before/after a run: unchanged
- sha256 over every candle and swing dict, including `fine`: unchanged
- module-level mutable state diffed across all of `sys.modules`: nothing changes
- no `lru_cache` / `functools` memoization anywhere in the engine
- no duplicate `btc_engine` module objects
- constructing `CandleStore` beforehand: no effect
- calling `_collect_signals` beforehand: no effect
- positional vs keyword call to the simulator: no effect

## Where to look

- `backend/src/btc/btc_engine.py:205` and `:282` — the two `pivot_rule == "leg"`
  branches. In the leg branch `_lo_leg` / `_hi_leg` are built from
  `candles[_sw_idx : _br_idx + 1]`, using `_sw_idx = start_idx_fb if >= 0 else 0`
  and `_br_idx = store.pos(b_time)`. When empty, `sl = seg_start`.
- `backend/src/btc/engines/htf_ltf/v19_champion.py:255` — the
  `from src.btc.btc_engine import _collect_signals` sits inside the function body,
  which is why rebinding the module attribute reaches the engine.
- `backend/src/btc/engines/htf_ltf/v19_champion.py:678` and `:680` —
  `sl_pivot = _csl[i] if direction==1 else _csh[i]` versus
  `sl_pivot = sig["swing_start_px"]`. The origin path reads `swing_start_px`
  straight out of the signal dict; the leg path uses the separately built `_csl`
  / `_csh` arrays.
- `backend/src/btc/btc_routes.py:1316` (`v19_champion`, with the `pivot_rule`
  monkeypatch), `:1354` (`v19_causal`), `:1378` (`v19_c16`). All three call
  `simulate_htf_ltf_v19_champion` exactly once per request, so the route does not
  run it twice. Something earlier in the request must be producing the
  "leg-first" state.

The asymmetry is the clue: the leg path does not consult `swing_start_px`, the
origin path does. Something is changing the signal dicts, the swing objects, or
the values derived from `seg_start`, in a way that survives without altering any
of the objects that were hashed.

## Repro harness

`backtest/tests/exp_v19_arm.py` — one arm per process, this is reliable:

    python exp_v19_arm.py origin arm_origin.json
    python exp_v19_arm.py leg    arm_leg.json
    python exp_v19_arm.py leg    arm_causal.json 1

To reproduce the order dependence, run both arms inside a single process, in both
orders.

## Known-bad claims in the prior notes, do not trust these

Three earlier conclusions were wrong and have been retracted:

- "C16 removes 7 trades and costs -86.66R" — true only for the harness data. On
  the route, origin and leg are 499 trades each and differ by 3.16R net.
- "0 trades added, 0 removed, -3.16R" — true for the route, false for the
  harness-first-origin case. Both were presented as universal.
- "the registry pin belongs to a different engine" — wrong. The origin arm does
  reproduce `n 500 / net 325.78`. The mismatch is this ordering bug, not a
  config difference.

The first error was reading a `r` key that does not exist; the field is
`r_multiple`. Costs are computed per trade by `_trade_costs` in
`backend/src/btc/btc_routes.py:225`.

## Also outstanding, separate from the bug

`v19_causal` (`exp_causal_sl=1`) and `v19_c16` (default leg rule) return
byte-identical results: 499 / 355.72 / 239.12. Two dropdown books are computing
the same thing.

## Intended direction

The user wants the origin rule retired so every book uses the honest leg rule.
The plan was to delete `pivot_rule` from `_collect_signals`, delete
`exp_causal_sl` from the v19 simulator, and drop the monkeypatch in favour of
explicit parameter propagation. That work is not started. Fixing the ordering bug
first would make the measurements trustworthy enough to decide whether the two
arms are really as close as they look.