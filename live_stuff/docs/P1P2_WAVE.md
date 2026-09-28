# P1/P2 WAVE ENGINE — the idea is sound, and the engine's swing chain
# structurally cannot support it. Closed with a reason, not a number.

Date: 2026-09-28. `exp_p1p2_wave.py`. Control exact: 500t +325.8R IS.

## What was built

A second engine whose trigger is **structure, not break marks**. The
shipped engine fires on B1/B2/FLIP — "price broke a pivot". P1/P2 fires on
"an impulse leg was followed by a retracement of a known depth", using the
classic Elliott ladder (0.382 / 0.5 / 0.618 / 0.786) on

    ratio = |P2 extent| / |P1 extent|

This was the one direction all four second-researchers independently ranked
first, and the reasoning behind it is correct: it is the only remaining idea
that changes what the system **sees** rather than filtering an exhausted
trade population. The entry-time autopsy is what makes that distinction
necessary.

## The result: one candidate out of 2,900 swings

    [is] 15m swings 2,900   P2 candidates 1

Every band returned 0 trades. The ratio distribution is a single point
(0.640), because there is exactly one signal in the set.

## Why — and this is the useful part

**The swing chain is stitched, not nested.** `btc_swing.py:150-152`:

    # Stitch: the next engine starts on the bar AFTER this swing's
    # end extreme (same rule as Nifty's whole-day chain).
    end_abs = eng.end_idx
    next_start_pos = end_pos + 1

Each swing is computed by a **fresh SwingEngine** seeded at the bar after
the previous swing's end. The swings tile the timeline end to end and
alternate direction by construction. They are **legs of one continuous
sequence**, not nested 1-2-3-4-5 waves.

So there is no "wave 1" to retrace from and no "wave 2" to measure. The
Elliott ratio is **undefined on this data structure**, and my `if num != 1`
filter found one swing in the whole IS history that happened to be the
second element of the chain with a preceding impulse to measure against.

This is the same lesson as the 1h/15m discovery from the second-researcher
round: **the 1h chain and the 15m chain are separate instruments, and
neither one is an Elliott wave count.** The engine is a break-detector with
a sequential stitch. Asking it for wave structure is a category error, and I
should have established that from `btc_swing.py:150` before writing the
harness rather than after.

## What survives

**The thesis is not refuted — it is untestable on this chain, and the fix is
known.** A genuine Elliott labelling needs waves counted on nested
sub-structure: a P1/P2 pair must be extracted from *within* one swing's
internal pivot sequence, not across the chain boundary. That data exists —
`WalkerEngine` emits the raw pivots and `compute_btc_swings` already
attaches every `break_marks` entry — but the nested labelling is a new
labelling pass, not a filter, and it has never been written.

Two cheaper ways to get the same *information* without wave counting:

1. **Retracement depth of the break that produced the entry.** For every
   B2/FLIP entry, how deep was the pullback into the prior leg before it
   broke? That is the same quantity P1/P2 wants, measured inside the
   existing mark set, with no new labelling.
2. **Pivots already in the dicts.** `firstswing.py` keeps `normal_highs` /
   `normal_lows` pools; a ZigZag re-count over those is a different
   segmentation of the same bars.

Option 1 is the one worth running and it is a filter on the *entry
geometry*, not on a post-hoc bucket — the ratio is knowable at the entry
bar.

## Verdict

- **P1/P2 on the swing chain: CLOSED — structurally, not empirically.** One
  candidate in 2,900 swings; the quantity is undefined on a stitched chain.
- **The idea survives as retracement-depth-at-entry**, computable from
  marks the engine already emits, untested.
- Do not re-run this harness. The blocker is the data structure, and it is
  documented at `btc_swing.py:150-152`.

**TWO BUGS WORTH KEEPING** (both caught by running, neither by reading):
`int(s["swing_index"])` is **0-based** — the counter is recorded at
`btc_swing.py:118` before the increment at `:146`, so filtering on `!= 2`
found nothing and `!= 1` found one. And an empty metrics cell had to return
the full key set, not `{n, net}`, or the print crashed before the report.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
