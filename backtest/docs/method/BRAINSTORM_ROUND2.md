# brainstorming, round 2 — and what the round actually found

Date: 2026-10-08. Harness work in this round: `exp_sig_multi.py`,
`exp_register_sig_multi.py`. **One book registered, one idea killed, and the
mechanism behind the best result identified.**

---

## 1. `fsent_sig_multi` registered

`fsent_sig_full`'s filter set, `max_positions` 1 → 0. Registry **151 → 152**.
Candidate, not adopted. Full write-up in `SIG_MULTI_REGISTERED.md`.

| era | n | net | DD | WR |
|---|---:|---:|---:|---:|
| IS | 329 | +484.59 | 13.39 | 45.6% |
| OOS | 195 | +219.82 | 7.64 | 47.2% |

`exp_fastcheck` PASS, differs from parent in exactly one value.

---

## 2. the combined arm is the biggest number in the repo, and it is dead

Two good ideas stacked: the sig filters + concurrency, **and** `trail_delay1`'s
delayed trail.

| era | arm | n | net | DD | WR |
|---|---|---:|---:|---:|---:|
| IS | `sig_multi` (registered) | 329 | +484.6 | 13.4 | 46% |
| IS | serial + `trail_delay1` | 199 | +418.5 | 13.3 | 35% |
| IS | **mp0 + trail** | 301 | **+678.9** | 13.3 | 41% |
| OOS | `sig_multi` (registered) | 194 | +219.8 | 7.6 | 47% |
| OOS | serial + `trail_delay1` | 122 | +182.0 | 7.5 | 41% |
| OOS | **mp0 + trail** | 186 | **+241.1** | 8.2 | 42% |

**+678.9R in sample is the largest number any book in this repo has produced.**
Out of sample it holds at +241.1R. Adding a cap of 3 makes it marginally *better*
again (+680.8 / +244.4).

It does not survive contact with the period control:

| era | survivors | NEW | DROPPED | raw gap | b | verdict |
|---|---:|---:|---:|---:|---:|---|
| IS | 293 | 8 | 36 | +0.0069 | **−0.2993** | underpowered, and **wrong sign** |
| OOS | 180 | 6 | 14 | +0.2965 | +0.1296 | underpowered (MDE 0.4986) |

**In sample the calendar explains 199% of the raw gap** — more than all of it,
leaving `b` negative. The out-of-sample effect is +0.13 against an MDE of 0.50.

**Dropped.** Not registered, no pins written. And the reason it died is the
interesting part.

---

## 3. why it died, and why that is the real finding

**90–100% of the gain is inside the SURVIVORS — trades both books took. It is
almost entirely an EXIT change, not an entry change.**

| era | survivors | exit change worth | of the total | avg bars held change |
|---|---:|---:|---:|---:|
| IS | 293 | **+194.0R** | **100%** | +105.8 bars |
| OOS | 180 | **+15.4R** | **72%** | +92.0 bars |

Only **8 new trades in sample and 6 out of sample** did the combined arm add.
Almost everything came from holding the same trades longer.

Average hold: 190 bars → **299 bars** in sample, 170 → 260 out of sample.

**And that is exactly why the period control kills it.** When the effect lives
inside trades that were taken anyway, the cohort comparison has almost nothing to
compare — 8 against 36, with a raw gap of +0.0069R per trade. There is no
information there to control for, which is what `b = −0.30` is reporting. **A null
this shape is not "underpowered", it is "the question does not apply to this
change".**

## 4. why holding longer earns more — a genuinely asymmetric effect

The breakdown is worth keeping whatever happens to the arm:

| era | survivors | better exit | worse exit | unchanged | avg gain (better) | avg loss (worse) |
|---|---:|---:|---:|---:|---:|---:|
| IS | 293 | 45 | 108 | 140 | **+6.40R** | +0.87R |
| OOS | 180 | 24 | 66 | 90 | **+2.75R** | +0.77R |

**A trailing stop that runs later makes far more trades slightly worse and a
handful much better, and the asymmetry is about 7:1 per trade.**

That is the correct shape for a trend follower and it is why the arm posts the
biggest headline number in the repo. It is also the shape that does not survive a
test built to ask "is this the calendar in disguise" — because it isn't a filter
at all, it is an exit-timing change whose benefit is concentrated in a few long
holds.

**One correction to my own earlier reading.** I described `trail_delay1` as "bank
half at the midpoint, then trail the rest". That is wrong on this evidence.
`exp_trail_half=1` is configured, but **zero survivors took a partial** — 0 of 293
in sample, 0 of 180 out. What the knob pair actually does is **hold longer**:
+106 bars in sample, +92 out. The "half profit" framing in the earlier doc is not
what the engine does on these books.

---

## 5. the third test this round also killed something

The `fsent_sig_trail_delay1` book registered earlier carries `max_positions` absent
and `exp_mltf` absent, so it is serial — but its out-of-sample result (+182.0R) is
**below its own serial parent's** (+194.4R). It was never a candidate. Its IS
number (+418.5R) was the largest in the serial family, and that gap is exactly
what the period control is for. It stays registered because the pins are
re-derivable and its exit behaviour is the subject of this section, not because
the number is good.

---

## verdict

| arm | verdict |
|---|---|
| `fsent_sig_multi` | **registered**, candidate. 99% of the gap survives in both eras, 12/12 half-year cells, tail improves everywhere. Not adopted: OOS magnitude unestablished (b +0.33 vs MDE 2.20), effect 6× smaller than in sample, first OOS half-year worth almost nothing, sibling test structurally unavailable |
| mp0 + trail | **dead.** b negative in sample (the calendar explains 199% of it), underpowered out. 90–100% of the gain is an exit change, so the cohort test does not apply |
| cap 3 | free on both arms — costs 1.5R IS, nothing OOS, lowers drawdown in both. Not adopted separately; it is a tail bound, not an edge |

**Nothing promoted. Shipping book unchanged.** 528 / +533.37 / 13.42 IS, 311 /
+239.59 / 11.88 OOS.

---

## what is actually left on the table

The open question is no longer "which candidate". It is **the 6× gap**: the same
arm is worth +2.16R per trade in sample and +0.33R out of sample. Nothing in
in-sample research can close that, because in-sample research is the thing that
cannot see it. `sig_multi` has passed every gate that can be run on existing data,
and its remaining risk is entirely forward.

Two things I would look at if continuing, neither of which is another knob:

1. **Why does the effect shrink 6×?** The regime decomposition in the FS-side
   autopsy showed `flip` and `decisive` behave differently, and the arm's OOS
   window is half `decisive`. That is a hypothesis about the gap, and it is
   testable on existing data.
2. **The exit-timing finding is real and unexplored.** +6.40R average gain versus
+0.87R average loss is a genuine asymmetry, and it was found by accident here
rather than by looking for it.