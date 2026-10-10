# The null audit — M was wrong by 2×, and three candidates clear the test that matters

Date: 2026-10-10. Harness: `exp_null_audit.py`, 4000 draws, seed 20261010.
**Closes the registry half of P5, which had never been run.**

---

# 1. The owner was right that M was stale, and the reason is worse than staleness

`BASE_BOOK_NULL.md` quotes its own pins in its first paragraph:

> *Pins reproduced first, both exact (**IS 500t / +325.8R** NET, **OOS 279t / +70.1R** NET).*

**That is `champion_multi_sw10`, not the shipping book.** `fsent_champ_long` is
528t / +533.37R IS and 311t / +239.59R OOS. The doc even opens with a correction
notice about having been re-derived after C16 changed the SL pivot — and still
carries the old book's numbers.

Those quoted pins do not match the registry either: `champion_multi_sw10` is
**502 / +279.33**, not 500 / +325.8.

**So M was measured on one book, labelled as though it applied to another, and its
inputs had drifted from the registry too.** The header even calls itself *"M is
larger than the book"* — a claim that stops being true the moment the book changes.

**And M is an absolute R figure, which cannot be a portable bar.** A null's width
scales with the book's trade count and its per-trade spread. `BOOTSTRAP_NULL_P63.md`
already says this in general terms — *"comparing that width to a fixed two-year null
is comparing two different things"* — and then the registry went on quoting M as a
fixed threshold anyway.

## re-derived on the book that actually ships

| era | n | observed | null mean | p05 \|net\| | **M (p95)** | percentile |
|---|---:|---:|---:|---:|---:|---:|
| IS | 528 | +533.37 | +515.48 | 303.09 | **771.09** | 57.9 |
| OOS | 311 | +239.59 | +253.27 | 127.67 | **384.36** | 45.1 |

**The quoted M was 381.7 / 205.5. The real M is 771.09 / 384.36 — roughly double.**

**Every dNet result in the repo has therefore been judged against a bar about half
the size it should have been**, in the permissive direction. Anything quoted as
"clearing M" needs re-checking, and nothing clears the corrected one on absolute
net: the largest dNet in the family is `htfesmcl4` at +384.43R IS against a bar of
771.09R.

---

# 2. But the absolute net is the wrong test for this question

The shipping book sits at the **58th and 45th percentile of a reshuffle of its own
trades**. Its *absolute* net is not distinguishable from reordering itself.

**That is not the same statement as "no candidate is better than its parent",** and
conflating the two is how the earlier M-based audit I ran produced its misleading
result — it reported *"1 of 28 clears M"* on a bar that was half the right size,
using a metric that does not answer the question.

The question for a candidate is: **does swapping the parent's trades for this
arm's trades do better than swapping them at random?** That is the paired
permutation test, and `SHIPPING_BOOK_NULL.md` (2026-10-08) is the right harness for
it — with a control that must return p = 1.00 when the answer is genuinely zero.

## the self-test, which is the only reason to believe the rest

| era | dNet | p | verdict |
|---|---:|---:|---|
| IS | 0.0000 | 1.0000 | ✅ correct — identical trades |
| OOS | 0.0000 | 1.0000 | ✅ correct |

**The harness returns p = 1.00 when it should and not by accident.** Two bugs had to
be fixed before it would run at all, both worth recording: the degenerate case
(one side empty) returned `None` instead of p = 1.0, which is exactly the
self-test's own case; and the permutation pool indexed `base[]` with the *arm's* keys
and raised `KeyError`. A naive "use base for both" fix would have silently
substituted the wrong R values for half the pool and produced a plausible p-value.

---

# 3. The result: three of fifteen clear, and only one in both eras

| book | dNet IS | **p IS** | dNet OOS | **p OOS** | significant |
|---|---:|---:|---:|---:|---|
| **`fsent_champ_long_mcloff`** | +33.22 | **0.0312** | +31.32 | **0.0117** | **BOTH** |
| `fsent_champ_long_mcloff_htf15` | +82.80 | **0.0115** | +37.76 | 0.1445 | IS only |
| `fsent_champ_long_htfesmcl4` | +384.44 | **0.0285** | +86.63 | 0.5311 | IS only |
| `fsent_champ_long_htf15` | +34.20 | 0.1927 | +15.29 | 0.5021 | no |
| `fsent_champ_long_mode_atr_low` | +187.97 | 0.1045 | +41.13 | 0.0987 | no |
| `fsent_champ_long_mode_union` | +46.67 | 0.7276 | +64.22 | 0.2104 | no |
| `fsent_champ_long_mode_fd` | +1.44 | 0.9153 | +37.24 | 0.2362 | no |
| `fsent_champ_long_biasmom05` | −31.89 | 0.2414 | −22.46 | 0.2632 | no |
| `fsent_champ_short` | +67.23 | 0.6888 | −0.06 | 0.9993 | no |
| `fsent_utcsat_short` | +63.34 | 0.7061 | −9.94 | 0.9180 | no |
| `fsent_utcsat_long` | −68.37 | 0.2247 | −0.83 | 1.0000 | no |
| `fsent_champ_trailhalf` | +2.82 | 0.9378 | +42.49 | 0.4974 | no |
| `fsent_sig_full` | −237.54 | 0.7428 | −45.15 | 0.9223 | no |
| `fsent_sig_multi` | −48.78 | 0.9283 | −19.77 | 0.9138 | no |

## `mcloff` is the only book significant in both eras

It is also the only book in the family that passes every other test it has been
given:

| test | `mcloff` |
|---|---|
| period control | **POWERED, b > 0 in both eras, t = 3.37 / 3.97** |
| paired permutation | **p = 0.0312 IS, p = 0.0117 OOS** |
| negative half-years | **0 of 12** |
| net, both eras | **higher than the parent in both** |
| drawdown | 15.13R IS, within budget |

**That is the first candidate in this programme to clear a null.** Every other
proposal was required to and did not; the shipping book was not required to and
does not either, at p = 0.74 / 0.91 on its own trades.

---

# 4. What the two tests mean together

Both statements are true and they are about different objects:

- **The shipping book's absolute net is not distinguishable from a reshuffle of its
  own trades.** Its edge is real in the sense that it was selected on evidence, but
  its magnitude cannot be separated from luck at 528 trades with a wide tail.
- **`mcloff`'s trade selection is significantly better than its parent's.** Not by a
  wide margin, and not in the sense of "this is a much better book" — +33R on 528
  trades. But it is the one change in this family that survives a test designed to
  kill it.

**That is the distinction this whole cycle has been circling.** The scorecard ranked
books on tiers; the period control asked whether an arm's edge survives the
calendar; the permutation asks whether the arm's *choice of trades* beats its
parent's. Three different questions, and only the last one comes back positive for
one book.

---

# 5. What this changes

| before | after |
|---|---|
| "no candidate clears M, on a bar that was half the right size" | **the bar was wrong; on the right bar nothing clears the absolute test, as expected** |
| "1 of 28 clears M" | **that number is withdrawn — wrong bar, wrong test** |
| "`mcloff` has the strongest evidence" | **`mcloff` is the only book that clears a null, in both eras** |

**The recommendation is unchanged and now rests on more than one kind of evidence:
`fsent_champ_long_mcloff`.**

**And the honest limit, unchanged:** its OOS era is 2021-22, reused data, not a
holdout. A permutation against the parent is not forward validation. The forward
window is still 26 days and still says `NO VERDICT`.

---

*No pin moved. No book modified. `BASE_BOOK_NULL.md`'s M is superseded by the
771.09 / 384.36 above and its quoted pins are wrong for the book it names.*