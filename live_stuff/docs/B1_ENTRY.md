# B1 ENTRY — path-true, and it fails. The last open direction is now closed.

`CLOSED_DO_NOT_REPEAT.md` listed B1 as the one genuinely untested idea. It is
tested now, properly, with the stop variants the user asked for. **B1 loses.**

## The patch

The entry trigger is `_collect_signals(swings_ltf, "decisive", ...)`, and
inside it the mark kinds come from `{"b2": ("B2",), "flip": ("FLIP",)}`. There
was no `"b1"` key, so B1 entry had never been reachable — and `exp_b1_b2_mode`
cannot help, because it *blocks* the B2 trigger rather than changing it.

The harness rebuilds `btc_engine` in memory with `"b1": ("B1",)` added and
installs it before the craze loader imports it. No shared file is edited;
SL, trail, cooldown, loss streak and window caps then all run untouched, so
this is a real path-true run.

**Controls: all four reference ledgers exact** (500/+325.8, 454/+358.9,
279/+70.2, 253/+60.2) — so the patch is provably inert when switched off.

## Results

### IS — B1 loses badly at every stop

| arm | is/champion | is/utcsat |
|---|---|---|
| **B2/flip SL+0.0 (shipped)** | **500t +325.8R** | **454t +358.9R** |
| B1 SL+0.0 | 221t **−34.9R** | 212t **−18.6R** |
| B1 SL+0.5 | 213t −89.4R | 200t −24.6R |
| B1 SL+1.0 | 195t −43.6R | 181t +26.8R |
| B1 SL+1.5 | 157t −114.6R | 152t −87.5R |
| B1 SL+2.0 | 124t −92.3R | 115t −87.5R |

B1 produces **less than half the trades** (221 vs 500) and is net-negative in
9 of the 10 IS cells. Tightening the stop makes it worse, not better — WR
falls from 27.8% to 11–17%.

### OOS — B1 looks better, on a much smaller book

| arm | oos/champion | oos/utcsat |
|---|---|---|
| **B2/flip SL+0.0 (shipped)** | **279t +70.2R** | **253t +60.2R** |
| B1 SL+0.0 | 133t +7.6R | 124t +21.3R |
| B1 SL+1.0 | 111t +43.8R | 106t +71.3R |
| B1 SL+2.0 | 72t **+85.6R** | 69t **+88.6R** |

At SL+2.0 both OOS cells beat the shipped book (+15.4R and +28.4R) with
**better drawdown** (28.0 vs 53.2, 24.3 vs 29.4).

## Why this is not a result

Two independent disqualifiers, either of which is fatal on its own:

1. **The era split is exactly backwards.** B1 is catastrophic in IS (−34.9R,
   −18.6R) and mildly positive in OOS. The repo's standing bar requires the
   same sign in both eras. This is the **sixth** IS/OOS flip in this line of
   work.
2. **The OOS "wins" are on 69–72 trades**, against a shipped book of 253–279.
   `SL_VARIANTS.md` already showed that X-only "passes" on 7 and 9 trades are
   small-n noise. A +15R edge on n=72, found by picking the best of five stop
   levels, is the same shape of result.

The stop sweep is also where the danger sits: SL+2.0 is the *last* value
tried, and it is the one that "wins" in OOS. Taking the best of five
pre-registered levels and reporting only the winner in the era where the rest
lose is how a null gets dressed up.

## What it tells us

The B1 mark fires much earlier, so it catches the move before the market has
committed — and gets stopped out on noise. Its win rate is 11–24% against the
book's 27–29%. **The B2/flip trigger is not a late, conservative choice; it
is the point where the swing has proven itself.** Moving entry earlier and
tightening the stop are the same mistake in two forms, and the shipped
configuration sits at the optimum of both axes.

## Status

**NOT ADOPTED.** Nothing changed. The engine's `decisive` (B2/FLIP) trigger
and swing-pivot stop are untouched; the B1 key exists only in an in-memory
copy built by the harness, never on disk.

With this, every direction in `CLOSED_DO_NOT_REPEAT.md` is now tested. The
only items still open there are the true FS-only engine and the live
size-state gap — neither of which is an entry-timing idea.

## Files
- `live_stuff/tests/exp_b1_entry.py` → `_b1_entry.json`
- `live_stuff/docs/CLOSED_DO_NOT_REPEAT.md` — update this row
