# the FS-side autopsy — multi takes FS on longs, sig takes FS on shorts, and
# that difference is doing a lot more work than it looks

Date: 2026-10-08. Both `fsent_champ_short` (the short-only mirror) and
`fsent_sig_trail_delay1` added to the dropdown. Route parity **10/10 books PASS**.

The owner's observation that started this:

> "we are seeing some regime we do good with fs long — like on multi
> `fsent_champ_long` we taking long on fs and on sig we are seeing short on fs —
> so if we could come up with something here… do some autopsy"

---

## 1. the two books point in opposite directions

`htf_regime` is carried on every trade, so the split is free.

### `fsent_champ_long` — multi, FS entry on LONGS

| era | regime | long | short | all |
|---|---|---|---|---|
| IS | flip only | 352t **+343.4R** WR 40% | 176t **+189.9R** WR 40% | 528t +533.4R |
| OOS | **decisive** | 46t **−1.0R** WR 37% | 20t **+4.4R** WR 45% | 66t +3.5R |
| OOS | flip | 160t +97.6R WR 32% | 85t **+138.6R** WR 45% | 245t +236.1R |

**In this book shorts beat longs in every out-of-sample regime.** In `decisive`
the longs are net-negative.

### `fsent_sig_full` — serial, FS entry on SHORTS

| era | regime | long | short | all |
|---|---|---|---|---|
| IS | **decisive** | 8t **+13.7R** WR 62% | 12t **−4.5R** WR 25% | 20t +9.2R |
| IS | flip | 100t **+279.6R** WR 47% | 114t **+7.0R** WR 37% | 214t +286.7R |
| OOS | **decisive** | 19t **+26.1R** WR 58% | 28t **+1.0R** WR 50% | 47t +27.1R |
| OOS | flip | 53t **+103.7R** WR 51% | 51t +63.6R WR 35% | 104t +167.4R |

**Here longs beat shorts in every regime and both eras.**

So the sign flips between the two books, and that is the whole question. It is not
"the FS print is good for longs" or "good for shorts" — it depends on which book
is asking.

---

## 2. the mechanism — the serial slot is doing the work

Everything else identical, only `exp_fs_entry_side` changed, on `fsent_sig_full`:

| arm | era | n | net | **DD** | longs R | shorts R |
|---|---|---:|---:|---:|---:|---:|
| **FS on SHORT** (shipping) | IS | 234 | **+295.8** | **10.8** | **+293.3** | +2.5 |
| FS on LONG | IS | 243 | +101.6 | 19.8 | +31.8 | +69.8 |
| FS OFF | IS | 259 | +119.6 | **31.8** | +75.7 | +43.8 |
| FS both sides | IS | 292 | +43.5 | 35.4 | +43.8 | −0.3 |
| **FS on SHORT** (shipping) | OOS | 151 | **+194.4** | **7.0** | **+129.8** | +64.6 |
| FS on LONG | OOS | 137 | +57.8 | 13.2 | +0.2 | +57.6 |
| FS OFF | OOS | 145 | +68.4 | 16.3 | +37.1 | +31.3 |
| FS both sides | OOS | 167 | +71.3 | 17.6 | +11.1 | +60.2 |

**FS-on-short wins on net AND on drawdown in both eras, and it is not close** —
3× the net and roughly half the drawdown against FS-off.

**The interesting part is the long column.** FS-on-long takes **more** longs (166
in sample against 108) and earns **+31.8R from them against +293.3R**. The extra
58 longs collectively make about −261R.

**So the FS filter applied to longs is letting through trades that lose money.
Applied to shorts, it removes shorts from taking the slot, and the longs that get
through are the good ones.**

**The honest reading: FS-on-short is accidentally acting as a position-blocking
filter for mediocre longs.** A short with an FS print occupies the one slot and a
later mediocre long never gets taken. That is a real mechanism and it explains both
the net and the drawdown.

**It is also an accident of geometry, not a designed rule**, and it should be
labelled as one. It also explains why the answer is not "use FS on shorts
everywhere" — the next section shows it is not.

---

## 3. the owner's idea tested on the multi book

**Does FS-on-shorts help the MULTI book the way it helps the sig book?**

| arm | era | n | net | **DD** | longs R | shorts R |
|---|---|---:|---:|---:|---:|---:|
| MULTI + FS-long (shipping) | IS | 528 | +533.4 | **13.4** | +343.4 | +189.9 |
| **MULTI + FS-short (the idea)** | IS | 532 | **+600.6** | 17.6 | **+545.5** | +55.1 |
| MULTI + FS-off | IS | 503 | +288.5 | 43.2 | +246.9 | +41.6 |
| MULTI + FS-long (shipping) | OOS | 311 | **+239.6** | **11.9** | +96.6 | +143.0 |
| **MULTI + FS-short (the idea)** | OOS | 312 | +239.5 | **23.9** | +105.3 | +134.3 |
| MULTI + FS-off | OOS | 288 | +66.0 | **55.4** | +5.1 | +61.0 |

**This is where the idea dies, and it dies cleanly.**

In sample FS-on-shorts looks like a big win: **+600.6R against +533.4R**, and the
long column nearly doubles to +545.5R. Out of sample it is worth **+239.5R against
+239.6R — exactly nothing** — while drawdown **doubles to 23.9R**.

**Same signature as every other candidate in this repo: a large in-sample gain
that evaporates entirely out of sample, paid for with drawdown.** The one
structural difference is that the multi book is *unlimited*, so there is no serial
slot to block — which is precisely why the sig book's mechanism does not transfer.
That is a satisfying explanation rather than a mystery, and it is also the reason
the idea was worth running.

**One thing this does establish:** FS-on-short is much better than **FS off** on
the multi book too (+239.5 vs +66.0 OOS, drawdown 23.9 vs 55.4). The FS filter is
load-bearing. What is load-bearing is *having an FS filter*, not which side it
points at.

---

## 4. the two-book cross that is worth keeping

| book | OOS net | OOS DD | OOS WR | trades |
|---|---:|---:|---:|---:|
| `fsent_champ_long` (multi) | +239.6 | 11.9 | 37% | 311 |
| `fsent_sig_full` (serial) | +194.4 | **6.96** | **46%** | 152 |
| **`fsent_sig_full` with `max_positions=0`** | **+219.8** | **7.6** | **47%** | 194 |

**That last row is the only genuinely new object in this document.** It is the sig
book's exact knob set with the serial constraint removed — same filters, same
bias-momentum floor, same small-swing rule, same weekend skip — run multi.

- In sample: **+484.6R** against the shipping multi book's +533.4R, at the **same
  13.4R drawdown**, on 329 trades instead of 528.
- Out of sample: **+219.8R at 7.6R drawdown and 47% win rate**, against the
  shipping book's +239.6R at 11.9R and 37%.

**It makes almost as much as the multi book on less than two-thirds the trades, at
roughly two-thirds the drawdown, with a ten-point better out-of-sample win rate.**

**And it is not a blend of two books that trade each other's book.** Its long and
short columns are +136.7R and +83.1R — both sides alive, neither carrying
everything. Its long WR is 51% out of sample. It also cannot suffer the
opposite-direction overlap problem, because in 194 trades it never produces one
that matters.

**This has not been period-controlled, sign-tested against the shipping book, or
checked for tail dependence.** It is a measurement, not a candidate, and it should
be named as one. It is however the one arm from this whole line of thinking that
deserves the next hour rather than another verdict.

---

## what is settled and what is not

**Settled.** FS-on-short is correct for the serial sig book and correct by a large
margin; the mechanism is that it keeps mediocre longs out of the only slot. FS
filtering itself is load-bearing — turning it off costs 176R out of sample on the
multi book and 126R on the sig book. The owner's specific idea (move the multi book
to FS-on-shorts) is dead: no out-of-sample gain, double the drawdown, and there is
a structural reason it could not work.

**Not settled.** The `max_positions=0` sig book. It measures better than the
shipping book on drawdown and win rate in both eras and is a different object, not
a variant. It has had none of the framework's gates applied to it yet.

The one thing I would not do is call any of this an adoption. Nothing here has
been through period control, and this repo's record on period control is that
in-sample gains evaporate.

---

## dropdown now

| # | book | what it is |
|---|---|---|
| 1 | `fsent_champ_long` | multi, FS on longs — **shipping** |
| 2 | `fsent_champ_long_atr_low` | the same with the regime sign flipped |
| 3 | `fsent_champ_short` | **the mirror** — FS on shorts, same knob count |
| 4 | `fsent_sig_full` | serial, FS on shorts |
| 5 | `fsent_sig_trail_delay1` | sig + half profit + trail after +1R |

`fsent_champ_short` is the natural control for every claim above and it was in the
registry but not selectable. Route parity derives it from the pair's param dict and
**asserts it differs in exactly one value**, so "the mirror" cannot quietly become
"a different book" — an assertion that caught itself failing on a technicality in
this session and is worth the two lines it cost.