# SECOND-RESEARCHER REVIEW — the proposals came back, and the reviewers
# caught real errors in MY briefing

Date: 2026-09-28. Source: `other bots proposal.md` (four independent sets —
Nemotron 3, Big Pickle, Link3.0, Mimo-V2). Every claim below was
**verified in code before being accepted or rejected.**

## Headline: two of my briefing's claims were WRONG, and I checked

I wrote a prompt telling a second researcher what is and is not closed.
It did not take the briefing on trust, and it was right not to.

### Correction 1 — `chop_thresh=58.0` is INERT on the shipped lane

I listed `mode="atr_high", chop_thresh=58.0` as a live champion parameter.
**It does nothing.** `v18_streak_halt.py:417-418`:

    elif mode=="atr_high":
        use="decisive" if atrp > atr_high_thresh else "flip"

`chop_thresh` is never consulted in that branch. The champion's documented
parameter set contains a knob wired to nothing. **VERIFIED.**

This is not cosmetic. It means any `chop_thresh` sweep reported in the
history varied a parameter the shipped lane never reads. Anyone reasoning
about the champion from those numbers is reasoning about the wrong knob.

### Correction 2 — sw10/sw20 are built from the **1h** stream, not 15m

My briefing (and `HANDOVER_SESSION.md` line 90) said the swing chains all
come from 15m. `exp_5m_confirm.py:186-187`:

    "sw10": _compute_swings(_flow(c1h), "continuous", min_bars=10),
    "sw20": _compute_swings(_flow(c1h), "continuous", min_bars=20)

`c1h` — the **1h** candles. Only `sw15` is 15m. **VERIFIED.** I propagated
an error the handover already contained.

## Two of my "untouched" seeds were also wrong

- **30m and 2h are closed.** `exp_tf_family.py` resampled 30m and ran a
  4-cell factorial including duration-preserved `min_bars`; 2h was run four
  ways. `HTF_2H_PLANE_TEST.md` records 30m costing 84R IS / 55R OOS. I
  listed them as seeds; they are graveyard rows.
- **Scheduled events are closed path-true, with placebos.**
  `SCHEDULED_EVENTS_AUTOPSY.md` ran 4 frozen policies plus ±1-day shift
  placebos; Powell separately, on advance-knowledge grounds. I wrote "an
  audit exists, I do not know if a gate was run." It was run.

I told the other bot to **verify the seed list rather than trust it**, and
it did. Three of my five seeds did not survive that instruction.

## The one real find: `data/flow/bookDepth/`

**3,617 files. 2023-01-01 → 2026-09-25. Never read by any harness** (I
grepped `live_stuff/tests/*.py` and `stat_arb/*.py` — zero hits).

Depth-band notional at ±1..5%, ~30s resolution. A real information set the
repo owns and has never used.

**And it is unusable, for a structural reason worth recording:** it starts
2023-01, so it has no 2021-2022 coverage. Under the repo's own
same-sign-in-both-eras rule it can never pass as-is. Not "weak" —
*structurally excluded*. Same for the `funding/`, `metrics/` and
`premium1h/` siblings in `data/flow/`.

So the honest reading of the microstructure proposals (Nemotron P7,
Link3.0 P6) is: **the concept is sound and the data cannot support the
test.** A useful negative, not a direction.

## What the reviewers proposed, and my assessment

Roughly 30 proposals across four sets. The pattern is consistent: almost
every reviewer, independently, ranked the same idea first.

| proposal | raised by | my read |
|---|---|---|
| **Label/notation redesign** (P1/P2 wave, ZigZag hybrid) | all four | **Strongest remaining idea.** It changes what the system *sees* rather than filtering an exhausted set. No closed row is a relabelling |
| **Multi-swing 1h bias confirmation (2-of-3)** | Nemotron | Genuinely untested — it intervenes on the *bias timeline*, which no closed row touched. Same logic as the label idea: upstream of the filter |
| 1h swing geometry gate | Nemotron | Close to the graveyard's "range width" row. The reviewer flagged the tension themselves, which is the right instinct |
| FS-only with swing-trail | Nemotron | **Already run and closed today** (`FS_ONLY_ENGINE.md`) — and the "2,586 unpriced swings" premise was refuted: all 2,900 carry a B2/FLIP |
| Scheduled-event override | Nemotron | Graveyard takes precedence. Correctly not proposed |
| Position resize | Nemotron | Blocked: no size channel exists, and `exp_max_concurrent` was swept |
| 1m / microstructure | Nemotron, Link3.0 | Data cannot support a two-era test |
| Forward-slice family gate | Mimo-V2 | The most methodologically sound proposal in the set — see below |

Two reviewers proposed things I had already closed today, which is a
**good sign the brief was readable**: they were reasoning from the same
files rather than inventing.

## The one proposal that changes how we should work

**Mimo-V2 P1: spend the forward slice once, on everything at once.**

`data/forward/bybit/` is ~1,203 15m bars from 2026-09-13, never used to
choose anything. Today it produced roughly 60-70 trades on the champion
lane. The proposal: stop spending it one candidate at a time and instead
pre-register a **single family-wise evaluation that rules on all unadopted
survivors simultaneously.**

That is better than what I proposed, and I should say so. My framing was
"one look per slice; it is small, so it can kill but not confirm". Mimo's
is stronger: several candidates can be adjudicated in one pre-registered
pass without burning the slice repeatedly, and the family-wise framing is
honest about the fact that *none* of our survivors deserve individual
confirmation.

## Correcting the record

Three things in my briefing were wrong, all caught by a reviewer who was
told to verify rather than trust:

1. `chop_thresh=58.0` is inert under `mode="atr_high"` — **this changes
   how the champion's parameter history should be read.**
2. sw10/sw20 are built from the **1h** stream, not 15m — I propagated an
   error already in the handover.
3. 30m, 2h and scheduled events are closed, not untouched.

The seed list was three-quarters wrong. The instruction to verify it was
worth more than the seeds themselves.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
