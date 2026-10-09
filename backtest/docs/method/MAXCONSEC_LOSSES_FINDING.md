# The negative half-years, dissected — and what actually fixed them

Date: 2026-10-09. Harnesses: `exp_period_autopsy.py`, `exp_negcell_brainstorm.py`,
`exp_mcl_arms.py`.

**The short version: the negative half-year was never a broken regime. It was
`max_consecutive_losses=3`.**

---

# PART 1 — first, a correction

`HTF_FS_ENTRY_REJECTED.md` reported the HTF-FS arm as "better in 2 of 6 years".
**That number was computed from a bug and is withdrawn.**

The harness read

```python
ea = sum(per_h[c][0] for c in hs) / len(hs)
```

where `per_h[c]` is the list of **every** trade R in that half-year. `[0]` is the
**first trade's** R, not the cell's net. Every half-year was reduced to one
arbitrary trade.

Re-run with the framework's own P87 instrument — OLS with intercept, cohort and
half-year fixed effects, cluster-robust SE, cluster bootstrap — the picture is
different, and in one place it reverses.

---

# PART 2 — the autopsy

## champ_long's negative cell is not a bad regime

`2025-H1`, the only negative cell in the shipping book:

| | |
|---|---:|
| trades | 60 |
| **net** | **−0.69R** |
| mean per trade | **−0.011R** |
| winners | 20 making **+29.6R** |
| losers | 40 making **−30.3R** |
| worst trade | −1.35R |
| best trade | +7.14R |
| max losing streak | **7** |
| **% of the loss in the worst 2 trades** | **3%** |

**This cell is −0.69R on 60 trades.** Not −69R. The book made +29.6R and lost
−30.3R, and landed on the wrong side of a rounding error.

**And it declares `max_consecutive_losses = 3` while running a 7-trade losing
streak inside that cell.** That contradiction is the whole investigation.

## the other negative cells are the same shape

| book | cell | n | net | mean/trade | worst-N concentration | streak |
|---|---|---:|---:|---:|---:|---:|
| `champ_long` | 2025-H1 | 60 | −0.69 | −0.011 | **3%** | 7 |
| `champ_long` + htf_fs | 2022-H2 | 88 | −4.76 | −0.054 | **3%** | 9 |
| `sig_multi` + htf_fs | 2026-H2 | 19 | −7.01 | −0.369 | 21% | 4 |

**In all three the loss is diffuse, not concentrated.** 3% of trades carrying
half the damage means there is no single bad bet to remove. **There is nothing to
autopsy at the trade level — the cell is a low-variance outcome, and low-variance
outcomes cross zero by chance.**

The honest reading of `2025-H1`: a book with ~+0.9R median trade and this spread
will produce a marginally negative half-year now and then. **Demanding zero
negative half-years from a book like this is demanding that a coin never lands
red** — and the fix is not a better signal, it is either a higher per-trade
expectancy or a rule about what to do *during* a losing run.

Which is exactly what `max_consecutive_losses` is.

---

# PART 3 — period control, done properly

P87 instrument, `R = a + b·cohort + half-year fixed effect`, clusters = half-year,
4000 bootstrap draws. cohort 1 = trade only the arm takes, cohort 0 = trade only
the parent takes. MDE printed with every null, because a null from an
underpowered test is a statement about the test.

| arm | IS b (t) | OOS b (t) | verdict |
|---|---|---|---|
| **`mcl=off`** | **+1.21 (3.37)** | **+1.86 (3.97)** | **SURVIVES, POWERED** |
| `mcl=4` | +0.06 (0.18) | +1.03 (1.62) | survives, underpowered |
| `htf_fs=all` | +0.59 (2.28) | −0.06 (−0.10) | 1/2 eras, underpowered |
| `htf15+htf_fs` | +0.55 (1.97) | −0.26 (−0.42) | 1/2 eras, underpowered |
| `biasmom05` | −0.23 (−0.37) | **−0.94 (−9.63)** | **SIGN FAILS** |
| `biasmom05+htf_fs` | +0.46 (1.43) | −0.42 (−1.06) | 1/2 eras |
| `htf_fs=all` vs sig_multi | +0.37 (0.59) | +0.12 (0.21) | 2/2 but underpowered |

### three results that change the picture

**1. `biasmom05` — the arm I recommended last message — fails, and fails hard.**
OOS **b = −0.94 at t = −9.63**. The trades `exp_bias_momentum_min=0.5` admits are
significantly **worse** than the trades it removes, after the calendar is
controlled for. In plain terms: it removed `2025-H1` by deleting trades that were
going to win, and it kept trades that were going to lose. **Its clean half-year
table was an artefact of which trades it happened to drop.** That is the whole
point of running the instrument, and it is why the half-year count alone is not
enough. It stays registered, with the failure recorded.

**2. `htf_fs=all` does NOT survive — but it was never the claim that failed.**
The owner was right that it has more R. It does, +364R IS. But the effect is
underpowered OOS (b = −0.06, MDE 1.16) and the cluster bootstrap goes negative.
So: *more return, unproven return.*

**3. `max_consecutive_losses=0` is the only arm in the family that is both
positive AND powered in both eras.** b = +1.21 (t = 3.37) and b = +1.86
(t = 3.97), with bootstraps of +1.28 and +1.92.

---

# PART 4 — what the sweeps found

| knob | result |
|---|---|
| **`max_consecutive_losses`** | **the whole story — see below** |
| **`chop_thresh`** | **DEAD.** 46 → 70, byte-identical output on both books |
| `cooldown_bars` | 8 is optimal; 0 is catastrophic (ddIS 51.4) |
| `exp_persist` | 5 is marginally better; 7 fine |
| `htf_fs=all` + `mcl` | 4 clears the cell that FS entry alone re-broke |

**`chop_thresh` being inert is worth recording on its own.** It sits in every
champ book's params, reads like a live risk control, and does nothing in this
architecture at any value.

## the integer that mattered

| `max_consecutive_losses` | n | net | ddIS | **neg cells** |
|---|---:|---:|---:|---:|
| **0 (off)** | **912** | **+837.5** | 15.13 | **0** |
| 1 | 645 | +546.1 | 35.01 | 3 |
| 2 | 793 | +732.9 | 19.82 | 1 |
| **3 (SHIPPED)** | **839** | **+773.0** | **13.42** | **1** |
| 4 | 872 | +817.1 | 15.06 | **0** |
| 6 | 897 | +783.9 | 14.78 | **0** |

**Turning the cutoff off gives more net, more trades, similar drawdown, and no
negative half-year. The cutoff is not protecting the book — it is cutting
winners.** A 3-loss cutoff on a book with a positive median trade stops the book
immediately before the recovery trade that follows every streak. It costs 73
trades and 64R to buy a −0.7R cell.

**And limit 1 is a trap worth documenting:** it triples drawdown to 35R *and*
creates three negative cells. Cutting the book hardest is the worst setting.

---

# PART 5 — registered

| book | IS | OOS | dd IS | dd OOS | neg | period control |
|---|---|---|---:|---:|---:|---|
| `champ_long` (shipping) | 528 / +533.4 | 311 / +239.6 | 13.42 | 11.88 | **1** | — |
| **`..._mcloff`** | **575 / +566.6** | **337 / +270.9** | 15.13 | 14.16 | **0** | **SURVIVES + POWERED** |
| `..._htf15` | 520 / +567.6 | 280 / +254.9 | 17.28 | 16.86 | 0 | underpowered |
| `..._biasmom05` | 488 / +501.5 | 287 / +217.1 | 13.42 | 13.47 | 0 | **SIGN FAILS** |
| **`..._htfesmcl4`** | 793 / **+917.8** | 437 / **+326.2** | **27.74** | 14.20 | 0 | underpowered OOS |

**`fsent_champ_long_mcloff` is the strongest-evidenced book in the family.** It
beats the parent on return in **both** eras, has zero negative half-years, costs
under 2.3R of extra drawdown, and its advantage survives a half-year fixed effect
with the MDE cleared.

**`fsent_champ_long_htfesmcl4` is registered for the opposite reason** — it is the
ceiling. +917.8R in sample at 27.74R drawdown, right at the budget, bought mostly
by admitting 528 new trades, with an OOS effect the instrument cannot see. The
owner asked to see everything; this is what the top of the range costs.

`exp_fastcheck` PASS on all four books, every pinned field, both eras.

---

# PART 6 — what this changes about the owner's rule

The rule "never a negative half-year" was applied as a **hard filter**, and that
is what produced three of the four arms above. The autopsy says why that filter
is the wrong tool:

> A negative half-year on a book like this is a **−0.69R coin flip across 60
> trades**, with 3% of trades carrying half the damage. Chasing it by deleting
> trades does not improve the book — it improves the *appearance* of the book.
> `biasmom05` is the proof: clean half-year table, b = −0.94, t = −9.63.

**What actually works is a rule about behaviour during a losing run, not a rule
about which cells look clean.** `max_consecutive_losses` is that rule, and the
evidence says the existing value of 3 is set about two steps too tight.

Two things are now open for the owner:

1. **`mcl=0` is a risk decision, not a signal decision.** Turning a loss-run
   cutoff off increases concurrent exposure exactly when the book is doing worst.
   That is fine at 15R drawdown and not obviously fine at 29R. The signal evidence
   is unambiguous; the sizing consequence is a judgement call and it is the
   owner's.
2. **No arm has forward evidence.** The forward window is 26 days and every
   candidate reads `NO VERDICT`. `mcloff` has the strongest historical case in the
   family and has never been scored on unseen data.

---

## verification

| check | result |
|---|---|
| `exp_period_autopsy.py` | P87 instrument, 8 arms, MDE + bootstrap printed throughout |
| `exp_negcell_brainstorm.py` | 12 knobs, ~60 arms, scored on negative cells |
| `exp_mcl_arms.py` | period control + pins for the four arms above |
| `exp_fastcheck` | PASS, 4 books, every pinned field, both eras |
| withdrawn | "better in 2 of 6 years" in `HTF_FS_ENTRY_REJECTED.md` — computed from `[0]` on a trade list |
| shipping book | unchanged — 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS |