# HANDOFF — v19 origin rule only ever reaches half the engine

## The mechanism, confirmed

`pivot_rule` is applied through a monkeypatch of `btc_engine._collect_signals`
(`btc_routes.py:1327-1352`). That patch reaches ONE of the FOUR places
`_collect_signals` is called per v19 run. The other three keep the default.

    _collect_signals is called FOUR times per simulate_htf_ltf_streak_halt call:

      HTF  x3   v19_champion.py:258,259,260 -> simulate_btc_trades_v7
                -> v7_timecap.py:29 -> _collect_signals(..., candles=candles)
                v7_timecap.py:5 binds it at MODULE IMPORT time:
                    from src.btc.btc_engine import _collect_signals
                A later rebind of btc_engine._collect_signals does NOT reach it.

      LTF  x1   v19_champion.py:439
                v19_champion.py:255 binds it inside the FUNCTION BODY, so it
                re-reads the module attribute on every call and DOES see the patch.

So the origin book has never been an origin book. It is leg on the HTF window and
origin on the LTF entries, always, on every request, single-threaded or not.

## Proof

`backtest/tests/exp_v19_order.py` prints what each of the two bindings actually is,
before and after each run. `HTF(v7:29)` is the stale module-level binding;
`LTF(:439)` is the live one.

    $ python exp_v19_order.py leg,origin
    leg     csl=0  LTF(:439)=TRUE     HTF(v7:29)=TRUE     -> 499 trades / 355.72R
    origin  csl=0  LTF(:439)=WRAPPER  HTF(v7:29)=TRUE     -> 499 trades / 358.98R

    $ python exp_v19_order.py origin,leg
    origin  csl=0  LTF(:439)=WRAPPER  HTF(v7:29)=WRAPPER  -> 500 trades / 445.22R
    leg     csl=0  LTF(:439)=TRUE     HTF(v7:29)=WRAPPER  -> 500 trades / 433.47R

The HTF binding is frozen at first import and never moves again. The LTF binding is
whatever the caller set for that run. That is the whole bug.

## Why the numbers look the way they do

The trade COUNT follows the HTF rule, because the HTF windows decide which LTF
signals fall inside a window (`window_end="exit"`). The R value follows the LTF
rule, because the LTF signal's SL is what sets risk. So a mixed run reports the
HTF run's count with the LTF run's R, which is why hybrids are not either arm.

    sequence     HTF rule   LTF rule    result
    origin       origin     origin      500 / 445.22R   clean origin
    leg          leg        leg         499 / 355.72R   clean leg
    origin,leg   origin     leg         500 / 433.47R   hybrid
    leg,origin   leg        origin      499 / 358.98R   hybrid

`origin,origin` and `leg,leg` look "stable" only because both runs happen to share
the same frozen HTF binding. That is not stability, it is coincidence.

## Which numbers are real

    clean origin, both paths    500 / 445.22R gross / 325.78R net
    clean leg, both paths       499 / 355.72R gross / 239.12R net

`exp_v19_arm.py` happens to produce a clean origin: it imports `btc_engine`, then
installs the wrapper, and only THEN calls `V19` for the first time. `v7_timecap` is
first imported inside that call, at which moment the wrapper is live, so its binding
freezes onto the wrapper. Both paths end up origin. That is luck, not design.

The registry pin `champion_multi_sw10 = {n: 500, net: 325.78}` matches the clean
origin run, so the pin is a genuine clean-origin measurement and is correct.

The route cannot produce that number. `btc_routes.py:41` imports `v7_timecap` at
module load, long before any wrapper exists, so its binding freezes onto the true
function and stays there for the life of the process. Every `v19_champion` request
therefore runs leg-on-HTF, origin-on-LTF and returns 499 / 358.98 gross /
242.28 net, including the very first request after a fresh boot.

The comment at `btc_routes.py:1319-1322` ("Measured IS 500t / +325.78R") is not
merely stale. No route invocation has ever measured it.

## Retraction

The previous version of this document claimed `_collect_signals` is called exactly
once per v19 run and that `v7_timecap` never touches it. Both claims were false and
checkable in two greps. Everything the old document built on top of that — the
"symmetric count inheritance" framing, the module-global state hunt, the
`_collect_signals` probes, the mutation checks — was chasing the wrong thing. There
is no leaked state and no cross-run contamination. The pickle-reload and
wrapper-uninstall controls were sound; they simply proved the bug was not where the
old document said it was.

## The fix

Thread `pivot_rule` explicitly instead of patching a module attribute:

1. add `pivot_rule: str = "leg"` to `simulate_btc_trades_v7`
   (`v7_timecap.py:7`) and forward it at `v7_timecap.py:29`
2. add `pivot_rule: str = "leg"` to `simulate_htf_ltf_streak_halt`, forward it to
   the LTF call at `v19_champion.py:439`, and forward it to all three HTF calls at
   `v19_champion.py:258-260`
3. delete the monkeypatch at `btc_routes.py:1327-1352` and pass `pivot_rule="origin"`
   as a normal argument at `btc_routes.py:1336`

Step 3 also removes a genuine production race. FastAPI serves sync endpoints from a
threadpool, so two concurrent `v19_champion` and `v19_c16` requests share one module
global and can read each other's wrapper mid-flight.

Keep both rules available. The origin arm is the pre-C16 baseline; retiring it would
make the cost of C16 unprovable, since the pre-C16 figure could no longer be
reproduced for comparison.

## Re-measure everything after the fix

Every v19 figure quoted anywhere predates the fix and must be re-measured, because
none of them is currently trustworthy:

- `btc_routes.py:1319-1322` — 500t / +325.78R
- `btc_routes.py:1357-1360` — 494t / +247.96R
- `btc_routes.py:1379-1382` — 499t / +239.12R
- `backtest/docs/C16_C18_SL_PIVOT_AUDIT.md:129` — 500t / +314.52R

The three different `v19_causal` figures are explained by the same mechanism: they
were taken when the frozen HTF binding was origin, then when it was leg, then in the
current configuration. They are not a documentation conflict to be settled by
picking a winner; they are three different HTF/LTF combinations.

## Also outstanding

`v19_causal` (`exp_causal_sl=1`, `btc_routes.py:1354`) and `v19_c16`
(`exp_causal_sl=0`, `:1378`) both return 499 / 355.72 / 239.12, byte-identical. Two
dropdown books compute the same thing. Consolidate or differentiate them.

`exp_v19_arm.py:12-16` installs the origin wrapper and never restores it. Harmless
while it stays one arm per process, but it is the same class of mistake that caused
this bug.

Costs are computed per trade by `_trade_costs` in `btc_routes.py:225`. The result
field is `r_multiple`, not `r`.

## Intended direction

Retire the origin rule so every book uses the honest leg rule — but only after the
fix above has landed and the figures have been re-measured. Until the fix lands,
no v19 number is trustworthy, including the ones that look clean.