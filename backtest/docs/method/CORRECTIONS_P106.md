# P106 - CORRECTIONS TO P104. I compared the wrong parameter set.

Branch: agents/champion-reality-audit
Date: 2026-09-30. Supersedes method/LIVE_PARITY_P104.md.

## WHAT P104 GOT WRONG

P104 compared the champion against a dict I built by hand:

    {**V18, **SYMBOL_PARAMS[symbol], **V18_ENGINE}

That is not what the live bot runs. `get_v18_params()` is:

    base = dict(V18)
    base.update(SYMBOL_PARAMS.get(symbol, SYMBOL_PARAMS["BTCUSDT"]))
    return base

It never merges V18_ENGINE. My merge pushed `V18_ENGINE["chop_thresh"]=61.8`
over the real Bybit value of 58.0, which made all six parameters look
different. It also compared against the Binance Spot row when every
backtest dataset here is Bybit.

## THE REAL COMPARISON

`get_v18_params("BTCUSDT_BYBIT")` against champion_multi_sw10:

| param | live (Bybit) | champion | |
|---|---|---|---|
| sl_buf_atr | 0.01 | 0.01 | same |
| chop_thresh | 58.0 | 58.0 | same |
| max_consecutive_losses | 3 | 3 | same |
| mode | b2_vs_flip_chop | atr_high | differs |
| cooldown_bars | 10 | 8 | differs |
| ext_stop_r | 1.5 | 3.0 | differs |

Three of six already match. The research basis IS the live config on the
three that matter most for risk geometry, which is not a coincidence -
chop 58 and sl_buf 0.01 both trace to the Bybit sweeps.

So PORT_SCOPE_P105's claim that all six must move is wrong. Three move.

## THE LIVE NUMBER IS ALSO WRONG IN BOTH DIRECTIONS

`method/new bugs.md:642-653` and `method/reality of champion followup.md` both report
the live configuration as pinned at 351t / +137.33R / PF 1.907 via
`test_v18_causal_integrity.py::test_baseline`.

Running the live configuration now, through the shipped v18 engine with
`get_v18_params("BTCUSDT_BYBIT")`:

    n=369  net=+78.50R  PF=1.675

Neither the 351 count nor the +137.33R figure reproduces. The golden
test threshold was itself re-anchored twice (`method/new bugs.md`: the
2026-09-21 trail-ordering fix, then a fresh baseline note), and nobody has
reconciled it against a live run since. Until someone does, the live
configuration's net figure is unsettled, not pinned at +137.33R.

## THE CAPITAL CONCERN WAS OVERSTATED

P105 said six concurrent positions at one position each is 6x exposure
and needs a capital model. That is wrong. R is move over risk, where risk
is the SL distance. It is scale-free. Six concurrent trades at 1% per
trade is 6% margin, which Bybit accepts for BTCUSDT perp.

The real concern is different and nobody has measured it: exp_mltf opens
its positions inside a single 1h window, and they are same-direction by
construction. That is 6x concentration, not 6x risk. One adverse 1h move
takes all six together. This is the correlated-cluster question and it
needs measuring before the champion is funded.

## THE TWO-ENGINE RISK

P105's step 1 was to leave v18 in place and repoint live_loop.py later.
`method/reality of champion followup.md` is right that this leaves two engines in
the tree. live_loop.py:35 still imports v18. v19 reproduces the pin under
a real import and py_compile, but nothing routes production to it yet, and
a wrong import silently ships v18's single-position behaviour.

## NET POSITION

Correct as of now: champion = v19, IS 500t/+325.78R, OOS 279t/+70.15R,
verified by importing the committed file. Three of six champion params
already match the live config. The live config's own net figure is
unreconciled at +78.50R measured against +137.33R claimed. The capital
question is concentration, not exposure.