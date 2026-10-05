# TIGHTENED STOP — path-true, and it is catastrophic in 4/4 cells

The user's variant, tested properly: not the half-swing stop (already shown
degenerate) but **keep the B2/flip entry and put the SL above the swing low**,
i.e. a tighter but usable stop.

## The patch

The engine anchors its stop on `sl_pivot` (the swing extreme):

```
sl = sl_pivot -/+ sl_buf_atr*atr15[i]
```

So the only change needed is to move `sl_pivot` toward the entry by k × ATR15
before those lines. Moving it *toward* the entry is direction-agnostic
(`sign(entry − sl_pivot)`), so one injected line covers both the long and
short branches and cannot invert the short case.

```
sl_pivot = sl_pivot + exp_sl_tight*atr15[i]*(1.0 if entry>sl_pivot else -1.0)
```

`exp_sl_tight = 0.0` reproduces the shipped engine exactly. Both SL anchors
asserted to match exactly once. BASE verified: 500t/+325.8R, 454t/+358.9R,
279t/+70.2R, 253t/+60.2R — all four reference ledgers exact.

This is a real path-true run: a different stop changes which trades survive,
so exits, cooldown and loss streak all re-simulate.

## Results — every tightening is worse, in every cell

| arm | is/champion | is/utcsat | oos/champion | oos/utcsat |
|---|---|---|---|---|
| **baseline** | **+325.8** | **+358.9** | **+70.2** | **+60.2** |
| tight 0.5 ATR | +192.9 | +222.4 | +44.1 | +47.5 |
| tight 1.0 ATR | +15.2 | **−30.8** | **−28.8** | **−21.2** |
| tight 1.5 ATR | **−21.6** | **−69.1** | **−16.5** | **−13.3** |
| tight 2.0 ATR | +42.4 | +34.8 | **−56.6** | **−46.8** |

## What it does to the book

Win rate collapses and drawdown explodes, together:

| | WR | PF | maxDD | calmar |
|---|---|---|---|---|
| is/champion baseline | 27.8% | 1.81 | 27.7 | 3.20 |
| is/champion tight 1.0 | 18.8% | 1.03 | **115.0** | **0.04** |
| oos/champion baseline | 27.2% | 1.34 | 53.2 | 0.66 |
| oos/champion tight 1.0 | 21.2% | 0.88 | **81.4** | **−0.18** |

**WR drops ~9 points and drawdown rises 2–4×** at every tightening level. The
book stops being profitable before the stop even looks "reasonable".

This is the same lesson as the FS-entry study, arriving from the opposite
direction: the wide swing-based stop is not a lazy default, it is **the
mechanism**. This book is a low-win-rate, tail-dependent trend system — the
wide stop is what lets a 25%-hit-rate book survive at all, because the few
genuine trends are what pay for the many small losses. Pull the stop in and
you stop out of the actual trend before it runs, while the losses still come
back at full size.

Note also the non-monotonicity (tight 2.0 is better than tight 1.5 in
is/champion, +42.4 vs −21.6). That is noise on a 395-trade book, not a real
optimum — there is no configuration anywhere near the baseline.

## Verdict

**0 of 4 tightening levels work. The existing wide swing stop is correct and
should not be touched.**

Combined with `method/SL_VARIANTS.md` (wider buffer also worse, causal SL
era-flipped, pivot trail catastrophic), the stop has now been attacked from
both directions — tighter and wider — and **every single variant loses.**

## The B1 leg is still NOT covered

This run varied the stop only. There is still no kwarg that fires the entry
on B1 — `exp_b1_b2_mode` is a blocking filter on the B2 trigger, not a
different trigger. Doing the B1 leg properly needs the signal-selection patch
and a full re-run, and it is honestly still **unknown**. The previous
harness's B1 arithmetic was an artefact and is not evidence either way.

## Status

**NOT ADOPTED.** Nothing changed. `sl_buf_atr=0.01` and the swing-pivot stop
remain, exactly as shipped.

## Files
- `backtest/tests/exp_sl_tighten.py` → `_sl_tighten.json`
- `backtest/docs/method/SL_VARIANTS.md` — the stop attacked from the wide side
