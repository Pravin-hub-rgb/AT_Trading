# ENGINE SHELF — built, tested plumbing nobody turned on

Written 2026-09-27, prompted by the observation that there is far more on the
table than the 30m/2h plane.

## The point

Recon of the **built** engine text (not the source) surfaced a set of
experiment hooks that are fully implemented, carry their own statistics dicts,
and are set to off/neutral in the shipped signature. The 30m/2h plane was the
only place we had been looking. This file is the inventory of everything else
that is already wired.

This is a **scan, not a proposal**. Nothing here is pre-registered or tested
yet. Per Rule 17 the 30m/2h agreement-predicates thread is closed; nothing in
this file reopens it.

## What is actually in the shelf

| Knob | Default | Built behaviour | Status |
|---|---|---|---|
| `exp_5m_confirm` | `0` | 5m close must break the prior-3 5m extreme before entry; cancel if stop touched while waiting; `five_m_stats` breakdown | **TESTED — see 5M_CONFIRM.md. Harmful.** |
| `exp_chop15_lo` / `exp_chop15_hi` | `0.0` / `0.0` | skip when the 15m chop series sits in a band | untested, untuned |
| `exp_5m_wait_min` | `240` | bound on the 5m confirm wait | swept as part of the above |
| `exp_max_concurrent` | `0` | cap simultaneous LTF positions | **not implemented in any engine** — harness patch only (craze.py:106, :760). Swept by P117 on the leg book. |
| `exp_cohort_rearm` | `0` | rearm rule after a cohort loss | untested |
| `exp_defer_h` | `0.0` | defer hours | untested |
| `exp_legskip_r` | `0.0` | leg-skip at an R threshold | untested |
| `exp_window_r_cap` | `0.0` | rolling R cap | untested |
| `exp_window_entry_cap` | `0` | rolling entry count cap | untested |

Two of these are **not** plain skip filters, which matters given the wick
result (skip −39.0R IS vs gray +28.1R IS, a ~67R swing driven by what happens to
the freed slot):

- `exp_5m_confirm` is a **delay with cancellation**. It was the one candidate
  that could plausibly have dodged the slot-cascade. It does not.
- `exp_window_r_cap` / `exp_window_entry_cap` are **exposure brakes**. They
  throttle rather than veto, so the cascade question does not arise in the same
  form.

## The structural finding, which is the real prize

The 5m run produced a mechanism-level number that matters more than its null
result, and it is the direct fruit of the user's "use gray, don't skip" point.

`exp_5m_confirm` re-checks `busy_until` / `cooldown_bars` / `exp_max_concurrent`
at the **new, later** entry time. Pushing an entry later does not just delay it
— it re-queues it into a competition for the single slot, where a different
trade may now be ahead of it. Measured on the champion IS book:

- 524 signals became candidates
- 76 timed out with no confirm
- 13 were cancelled by the stop during the wait
- 435 survived to the entry re-check — but only **329** became trades

**106 candidates, 20% of everything that got this far, were silently lost at the
slot re-check.** They are not counted anywhere in the engine's own stats; the
`five_m_stats` dict does not have a bucket for them. That is a real accounting
hole in the built engine, independent of whether the gate is useful.

So the slot is a **scarce, contended resource**, and the cost of an intervention
is not "the trades it removes" but "what it does to the queue". This is exactly
why gray beat skip by ~67R, and it is the reason a plain composition study
(which is all S1–S6 were) cannot answer the question.

**Consequence for the research programme:** the highest-value next experiments
are the ones that change *slot policy*, not entry predicates. `exp_max_concurrent`
and the window caps are the natural candidates. They are not "5m/2h predicates",
so Rule 17 does not block them. *(Harness-injected knobs, not engine features —
see the status table above.)*

## What this does NOT say

- It does not say the 15m/1h strategy should change. Nothing here was adopted.
- It does not revive 30m/2h agreement predicates.
- It does not make the OOS untouched again. The OOS has been inspected heavily;
  anything new still needs genuinely fresh forward data (Rule 4).
- `exp_5m_confirm` was run against production source **unmodified** — only the
  harness ever passes `exp_5m_data`/`exp_5m_confirm`. No production change.
