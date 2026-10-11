# V12 ADDENDUM — read this before starting, it corrects an ambiguity in the main prompt

## The "0 swings" results are NOT a crash

`backend/src/btc/btc_swing.py:156-157`:

```python
if not swing_found:
    break
```

If **one** swing fails to declare, `compute_btc_swings` returns an **empty list** —
after grinding through all 129,715 candles. It does not raise, does not warn, and
does not produce a partial chain.

So every "swings: 0, marks: 0" in the main prompt means the same specific thing:
**the engine could not complete its very first leg.** It is not "the chain
collapsed" in some distributed way, and it is not a syntax or wiring mistake. The
first leg is: seed the engine, let a B1 fire, let direction establish, then break
the opposing chop pivot — and one of those four steps stopped happening.

That is a much narrower problem than the prompt makes it look, and it is the first
thing to instrument. Before changing any gate, run one engine over the first ~600
bars and print, per bar:

```
i, bars_seen, state, dir, armed, e_hi.px, e_lo.px, e_hi_prev.px, e_lo_prev.px,
latest_sealed_high(px,idx), latest_sealed_low(px,idx),
_chop_target_high(), _chop_target_low(), declared
```

and find which step of the first leg stops. The committed engine declares its first
swing at bar 61 (2023-01-01 20:45). Whatever your change does, it must still declare
that swing. Check that single fact before looking at anything on 2025-07-20.

## The gate-removal attempts did not all fail the same way

Recorded precisely, because "0 swings" was reported for three different edits and
they are not interchangeable:

| edit | outcome |
|---|---|
| `_chop_target_*` reads `e_hi_prev` / `e_lo_prev`, all gates kept | 0 swings — **first leg never completes.** For an up leg `e_lo_prev` is the leg's own seed low, which price never revisits, so the FS target never becomes breakable. |
| same, plus the fresh-structure / gap / 2-bars-old gates removed | 0 swings — **different cause.** Those gates are load-bearing for the walker path. |
| V-corner preferred with `or` fallback, gates kept | 0 swings — **cause still unexplained, and this is the one worth chasing.** Logically this edit was a no-op at the time, because `_v_corner_*` was declared but never assigned, so the `or` always fell through to `latest_sealed_*`. If an edit that should have been a no-op produces zero swings, the failure is not in the edit. |

That third row is the important one. Either the observation is wrong, or something
outside the edited functions is affected. Establish which before building on it.

## Suggested order of work, in place of the previous bot's plan

The previous plan ran the five already-failed attempts as if they were new. In this
order, each step is verified before the next is attempted:

**Step 1 — baseline, no edits.** Confirm the committed tree gives 2952 swings /
7993 marks and that the first swing declares at bar 61. If it does not, stop and say
so; the premise of the whole task is wrong.

**Step 2 — instrument only.** Build the per-bar trace above and keep it. Every later
step is read against it. Do not change behaviour in this step.

**Step 3 — make the seal observable.** Confirm on 2025-07-20 exactly when the walker
seals the 14:45 low, and confirm that the B1 path sees the same V at 15:15 without any
seal. This should be a confirmation of what the prompt already claims, not a new
theory. If it does not reproduce, say so — that changes the diagnosis.

**Step 4 — one change at a time, smallest first.** Suggestion, in this order, and
re-run the per-bar trace plus `exp_fs_at_before_after.py` after each:

  4a. spent-level ledger only, chain-wide, no gate changes. Check whether 2024-07-16
      still lands on 19:00. Last time it did not — find out why before going further.
  4b. V-corner as an **additional** candidate alongside the walker pivot, with the
      walker pivot still winning when both exist. This is narrower than "prefer the
      corner" and has not been tried in that form.
  4c. only if 4b is insufficient, the corner takes precedence.

**Step 5 — the full verification set**, and only then hand anything back for the owner
to look at on the chart.

## Two things not to do

- **Do not remove the fresh-structure, gap, or 2-bars-old gates from the walker path.**
  Each removal attempt produced zero swings. If a gate genuinely has to change, change
  it for the corner candidate only, and leave the walker branch exactly as it is.
- **Do not accept "0 swings" as a result.** It is always a first-leg failure and it is
  always diagnosable from the Step 2 trace.

## Reporting

Same as the main prompt, plus one line: after every single edit, state whether the
first swing still declares at bar 61. If it does not, the edit is rejected before
anything else is considered.
