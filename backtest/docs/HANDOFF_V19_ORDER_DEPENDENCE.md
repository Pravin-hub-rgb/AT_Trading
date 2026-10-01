# HANDOFF — v19 backtest: second run in a process inherits the first run's trade count

## The bug, stated precisely

Running `simulate_htf_ltf_streak_halt` twice inside one Python process makes the
SECOND result depend on the FIRST. It is deterministic: the same sequence always
gives the same numbers. It is not order-dependence of the monkeypatch.

Repro: `backtest/tests/exp_v19_order.py`, which installs and uninstalls the
origin wrapper explicitly around every single run, and reloads the pickle fresh
each time. No wrapper is ever left installed between runs.

    $ python exp_v19_order.py origin
    origin  csl=0 active=origin-wrapper  -> 500 trades / 445.22R

    $ python exp_v19_order.py leg
    leg     csl=0 active=TRUE             -> 499 trades / 355.72R

    $ python exp_v19_order.py origin,origin
    origin  csl=0 -> 500 trades / 445.22R
    origin  csl=0 -> 500 trades / 445.22R        stable

    $ python exp_v19_order.py leg,leg
    leg     csl=0 -> 499 trades / 355.72R
    leg     csl=0 -> 499 trades / 355.72R        stable

    $ python exp_v19_order.py origin,leg
    origin  csl=0 -> 500 trades / 445.22R
    leg     csl=0 -> 500 trades / 433.47R        <- count inherited, R not

    $ python exp_v19_order.py leg,origin
    leg     csl=0 -> 499 trades / 355.72R
    origin  csl=0 -> 499 trades / 358.98R        <- count inherited, R not

## The signature: count inheritance is symmetric

Same rule twice is stable. Mixed rules are not. The second run's TRADE COUNT is
always the first run's count, in both directions:

    origin -> leg   : 500, 500     (first run had 500)
    leg    -> origin: 499, 499     (first run had 499)

The R value does NOT follow this rule. The second run computes its own R, but the
count is wrong, so the R total is computed over the wrong trade set. `origin ->
leg` yields 500 / 433.47R, which is neither arm's standalone number. `leg ->
origin` yields 499 / 358.98R, which is also neither.

Because the count is frozen, the mixed numbers are not "the second rule" at all.
They are hybrids and must not be quoted as anything.

## Why it matters

The live route returns 499 / 358.98 gross / 242.28 net for `version=v19_champion`,
on the very first request after a fresh boot. That is the `leg -> origin` hybrid,
not a clean origin measurement.

A clean origin measurement is 500 / 445.22 gross / 325.78 net, which is exactly
what `backtest/tests/experiment_registry.py` pins for `champion_multi_sw10`
(`{n: 500, net: 325.78}`). The pin is correct. The route is not reproducing it.

So the pre-C16 retro book in the UI has never shown the number its label claims.
The route comment at `btc_routes.py:1319-1322` reads "Measured IS 500t / +325.78R",
which is the harness number, not what that route branch returns. That comment is
stale and should not be trusted.

The leg rule is unaffected: route and harness both give 499 / 355.72 / 239.12.

## The route's monkeypatch is not the cause

Two independent reasons.

First, the repro above uninstalls the wrapper after every run and still
reproduces it. `origin,origin` is stable with the wrapper installed both times.

Second, `_collect_signals` is called EXACTLY ONCE per v19 run, at
`v19_champion.py:439`. The HTF window at `v19_champion.py:258-260` goes through
`simulate_btc_trades_v7`, which never touches `_collect_signals`. The `finally` at
`btc_routes.py:1352` restores `_be._collect_signals` correctly, and the restore
target is the true function, not a wrapper.

A related but separate defect does exist there: `exp_v19_arm.py:12-16` installs the
origin wrapper and never restores it. In that script the leak is harmless because
it is one arm per process, but if anyone drives two arms through it in one
process, the second arm silently runs origin. Worth fixing regardless.

## What has been ruled out

Input data is identical. The route's own arguments were dumped mid-request and
compared against `%TEMP%\at_datacache.pkl`:

    c1h   32434 candles   identical list  True
    c15  129736 candles   identical list  True
    fine 1946026 candles  identical list  True
    sw10    1601 swings    identical list  True
    sw15    2900 swings    identical list  True

Also negative:

- input list lengths before and after a run: unchanged
- sha256 over every candle and swing dict, `fine` included: unchanged
- the repro reloads the pickle between runs, so input objects cannot carry over
- module-level state diffed across all of `sys.modules`: nothing changes
- no `global` declarations anywhere under `backend/src/btc/`
- no `id()`-keyed caches anywhere under `backend/src/btc/`
- `CandleStore` holds only instance attributes; no class-level cache
- `lru_cache` / `functools.cache`: absent
- no duplicate `btc_engine` module objects
- no module shadowing: `backtest/` contains no `src/` and no second copy of
  `btc_engine.py`, `btc_routes.py` or `v19_champion.py`
- `v7_timecap.py` does not mutate `fine`; its only append is the trade list
- positional vs keyword call: no effect

The carrier is not in the data, not in the inputs, not in any module global, and
not in the monkeypatch. It has not been located.

## Where to look next

- `v19_champion.py:439` is the single `_collect_signals` call site. The signal
  list it returns is the only thing downstream that differs between arms.
- `_collect_signals` (`btc_engine.py:136-339`) writes only to local `out` and
  `seen`, then sorts `out` at line 338. `btc_engine.py:205` and `:282` are the two
  `pivot_rule == "leg"` branches, and both silently fall back to
  `sl = seg_start` at `:215` and `:292` whenever the leg slice comes back empty.
  If a signal's SL falls back to `seg_start` in one run and not the other, the
  gate results diverge while `pivot_rule` looks identical. Log how many times each
  of those two fallbacks fires, per run.
- `v19_champion.py:678` and `:680` select between `_csl`/`_csh` and
  `sig["swing_start_px"]` on `exp_causal_sl`. With `exp_causal_sl=0` every arm
  takes `:680`, so the divergence is upstream of this line, in the signal dicts.
  Do not start here.
- `btc_engine.py:100-106`: `pivot_rule` defaults to `"leg"` and the leg branch is
  additionally gated on `candles is not None`. A silent fall-through to
  `seg_start` looks exactly like an origin result while reporting `"leg"`.

Suggested next probes, in order of cost:

1. Dump `len(ltf_sigs)` and the sorted `entry_ts` set from `exp_v19_order.py` for
   all six sequences. If run 2's signal key set equals run 1's, the carryover is
   in signal collection. If the signals are identical, the carryover is in the
   trade walk.
2. Count the `:215` and `:292` fallbacks per run. If they differ, that is the
   mechanism.
3. Bisect with `V19` called on truncated `candles_htf` / `candles_ltf` to find
   the smallest dataset that still reproduces it, which usually localises the state
   quickly.

## The real fix, independent of the hunt

`pivot_rule` should be an explicit parameter on `simulate_htf_ltf_streak_halt`,
passed straight through to `_collect_signals` at `v19_champion.py:439`, and the
monkeypatch at `btc_routes.py:1327-1352` deleted. That removes the module-global
write, which is a genuine production defect: FastAPI serves sync endpoints from a
threadpool, so a concurrent `v19_champion` request and `v19_c16` request share one
module global and can read each other's wrapper mid-flight. Do this whether or not
the count-inheritance hunt lands.

Keep both rules available. The origin arm is the pre-C16 baseline; retiring it
would make the cost of C16 permanently unprovable, since the pre-C16 number could
no longer be reproduced for comparison.

## Also outstanding, separate from the bug

`v19_causal` (`exp_causal_sl=1`, `btc_routes.py:1354`) and `v19_c16`
(`exp_causal_sl=0`, `:1378`) both return 499 / 355.72 / 239.12, byte-identical.
Two dropdown books are computing the same thing. Consolidate or differentiate them.

Three conflicting sets of numbers exist for `v19_causal`:

- `backtest/docs/C16_C18_SL_PIVOT_AUDIT.md:129` — 500t / +314.52R
- `btc_routes.py:1357-1360` comment — 494t / +247.96R
- measured, harness and route agree — 499 / 355.72 gross / 239.12 net

247.96 is the audit's C17-only figure, per `C16_C18_SL_PIVOT_AUDIT.md:132`. None of
the three should be quoted until the count-inheritance bug is fixed, since a
measured figure is only trustworthy from a run that was first in its process.

Costs are computed per trade by `_trade_costs` in `btc_routes.py:225`. The result
field is `r_multiple`, not `r`.

## Intended direction

Retire the origin rule so every book uses the honest leg rule, once the numbers can
be trusted. `pivot_rule` should then be deleted from `_collect_signals`,
`exp_causal_sl` deleted from the v19 simulator, and the remaining books
differentiated rather than duplicated.