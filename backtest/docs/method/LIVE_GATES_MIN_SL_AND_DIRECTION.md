# live gates — minimum stop distance, and the opposite-direction lock

Date: 2026-10-08. Harness: `exp_live_gates.py`. Engine: `unified.py`, two new
knobs, **both default OFF** so every shipped pin reproduces unchanged.

Two live blockers the owner raised:

> "bahut chota sl, toh humko min sl ka rule lagana pdega and how it changes the
> net R now... bucket dikhana min point sl kitna liya hai"

> "agar humne long trade liya hai toh jab tak yeh long end nahi hojata tab tak
> short nahi le skte hai - long toh le skte hai but short nahi"

---

## 1. how small is the stop, actually

The engine **already** refuses a stop inside 0.05% of price
(`risk < 0.0005*entry -> continue`). On BTC at 40k that is **$20**, which is
smaller than round-trip fees. So the floor exists but is a formality.

Measured distance from entry to stop, `fsent_champ_long`:

| era | side | p0 | p5 | p25 | p50 | p95 | max |
|---|---|---:|---:|---:|---:|---:|---:|
| IS | long | 0.13% | 0.40% | 0.88% | 1.42% | 4.40% | 8.13% |
| IS | short | 0.12% | 0.38% | 0.58% | 0.99% | 2.75% | 4.63% |
| OOS | long | 0.11% | 0.61% | 1.54% | 2.69% | 8.73% | 16.59% |
| OOS | short | 0.30% | 0.52% | 0.91% | 1.49% | 4.80% | 9.59% |

**The owner's worry is real but smaller than it looked.** In IS the median stop is
**1.42% on longs** — not a rounding error. But the thin tail is genuine: **2 long
trades sit under 0.20%**, and 19 longs under 0.40%.

**Note the era asymmetry.** Out of sample the long median is **2.69%** against
1.42% in sample, and the p0 is 0.11% — the distribution is wider and thinner-tailed
in the unseen era. A floor chosen on IS geometry alone will bite more in OOS.

---

## 2. the min-SL sweep — `exp_min_sl_pct`

**Semantics: SKIP, never widen.** A stop that is too tight is not a small stop, it
is a trade that cannot be placed. Widening would move the risk and the 3R target
with it and turn the sweep into a different book. Skipping keeps every kept
trade's geometry exactly what the pivot said.

### OUT OF SAMPLE (`fsent_champ_long`, base = 311 / +239.6R / dd 11.9)

| floor | kept | dropped | net | expectancy | DD | keptR lost | **net delta** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.00% (shipped) | 311 | 0 | **+239.6** | 0.770 | 11.9 | 0.0 | 0.0 |
| 0.10% | 311 | 0 | +239.6 | 0.770 | 11.9 | 0.0 | 0.0 |
| **0.20%** | 310 | 1 | **+243.6** | **0.786** | 11.9 | **−4.1** | **+4.0** |
| 0.25% | 309 | 2 | +217.4 | 0.704 | 11.9 | +22.1 | −22.1 |
| 0.30% | 308 | 3 | +218.9 | 0.711 | 11.9 | +20.6 | −20.7 |
| 0.40% | 305 | 6 | +226.8 | 0.744 | 11.9 | +20.3 | −12.8 |
| 0.50% | 302 | 9 | +226.1 | 0.749 | 11.9 | +19.9 | −13.4 |
| 0.60% | 290 | 21 | +203.9 | 0.703 | 11.9 | +43.8 | −35.7 |
| 0.80% | 272 | 39 | +158.7 | 0.584 | 11.2 | +93.5 | −80.9 |
| 1.00% | 260 | 51 | +124.8 | 0.480 | 12.7 | +115.6 | −114.7 |
| 1.50% | 215 | 96 | +65.4 | 0.304 | 8.8 | +163.1 | −174.2 |

### IN SAMPLE (base = 528 / +533.4R / dd 13.4)

| floor | kept | dropped | net | expectancy | DD | keptR lost | **net delta** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.20% | 526 | 2 | 470.8 | 0.895 | 13.4 | +76.8 | **−62.6** |
| 0.25% | 522 | 6 | 425.7 | 0.816 | 13.4 | +121.1 | **−107.7** |
| 0.40% | 497 | 31 | 346.8 | 0.698 | 12.3 | +193.4 | **−186.6** |
| 0.60% | 449 | 79 | 316.2 | 0.704 | 12.8 | +239.2 | **−217.2** |
| 1.00% | 360 | 168 | 140.0 | 0.389 | 17.5 | +402.5 | **−393.4** |

### what the sweep says

**`keptR lost` is the column that decides it.** A floor is a risk filter only if
the trades it removes are worth less than they cost. Here they are worth **more**.

- At **0.40%** the floor removes 31 in-sample trades worth **+193.4R**. That is not
  a filter, that is **36% of the book removed for nothing.**
- At **0.60%** it removes 79 trades worth **+239.2R** — 45% of the book.
- Only at **0.20%** does the floor look like insurance, and even then the two eras
  disagree: OOS **+4.0R**, IS **−62.6R**. It removes **2 trades in IS worth +76.8R**.

**The honest read: the small-stop trades are not the losing ones.** They are the
book's edge. A minimum-SL rule tight enough to be live-safe (0.60%+) removes
roughly half the profit, and the ones it removes are the profitable ones.

**That is the finding that matters, and it points somewhere uncomfortable:** if
those tight-stop trades are genuinely the edge, then the book's edge depends on
being able to place stops that a real venue might not fill at the modelled price.
**That is a cost/slippage question, not a filter question, and no min-SL rule
answers it.**

---

## 3. the opposite-direction lock — `exp_no_opposite`

**This is genuinely new.** Three things already existed and none of them is it:

- `max_positions=1` serialises on `busy_until` and blocks **every** entry while any
  trade is open, in both directions — strictly stronger than what was asked.
- `exp_max_concurrent` caps the count and ignores direction.
- `exp_opposite` in the harness is unrelated — it belongs to
  `exp_loss_streak_action in ("override","opposite","augment")` and only allows a
  reverse entry **after a loss streak**.

So the knob had to be built. It uses a separate `_open_dirs` list carrying
direction rather than widening `_open_ivs`, because `_open_ivs`' 2-tuple shape is
unpacked positionally by the concurrency gate and by harnesses.

### how often does a long and a short actually coexist?

| book | era | trades | **opposite overlaps** | same-direction overlaps | net (off) | net (locked) |
|---|---|---:|---:|---:|---:|---:|
| `BASE` | IS | 528 | **8** | 351 | +533.4 | +534.3 |
| `BASE` | OOS | 311 | **4** | 158 | +239.6 | +240.6 |
| `atr_low` | IS | 641 | **22** | 478 | +721.3 | +720.0 |
| `atr_low` | OOS | 315 | **11** | 170 | +280.7 | +285.6 |

**Eight overlapping opposite pairs out of 528 trades in IS, and four out of 311
out of sample.** The rule costs **+0.9R in IS and +1.0R in OOS** for `BASE`.

**The finding is that the book barely does this.** Against **351 same-direction**
overlaps there are **8 opposite-direction** ones — under 2% of the concurrency
that exists. So:

- **The rule is nearly free.** It removes almost nothing and gives back slightly
  *more* net, because the blocked trades were mildly negative on aggregate.
- **It is also nearly pointless as a risk control**, because there is very little
  for it to prevent. The owner's stated worry — "long and short at once nets to
  zero while paying two fees" — is real in principle but this book runs it about
  **1.6% of the time**, on 12 trades across 6.7 years.

The honest position: **it is worth having as a cheap invariant in live code, but
it is not solving a measurable problem in this book, and it should not be adopted
as though it were.** `atr_low` uses it twice as often (22 and 11) and loses 1.3R
and gains 4.9R — also noise.

---

## 4. what to actually do about the small-stop problem

Not a min-SL filter, on this evidence. The three options that survive:

1. **Cost sensitivity, not a floor.** The tight stops are the edge, so the
   question is whether they survive realistic fills. `sl_buf_atr` and the fee
   model are the things to sweep, not the minimum distance.
2. **A floor at 0.20% only.** It is the single level that does not remove the
   edge in OOS (+4.0R). It costs 62.6R in IS, which is why it is not a clean
   answer either — but it is the only level where the two eras are not
   catastrophically opposed.
3. **Leave the geometry alone and constrain the venue.** If the stop cannot be
   placed inside a minimum distance, that is an order-type or tick-size
   constraint on the exchange side, not a book parameter.

---

## verification

- `inspect.signature` — 38 → 40 params, `exp_min_sl_pct=0.0`, `exp_no_opposite=0`
- `exp_fastcheck.py` — **PASS on 5 books**, every pinned field reproduced in both
  eras, confirming both knobs are inert at their defaults
- The engine edit is additive: the shipped `risk<0.0005*entry` line is kept
  **byte-identical**, because `test_experiments_craze.py` anchors on that exact
  line and asserts it appears twice. The first version folded the new check into
  it, broke the anchor, and `exp_fastcheck` failed with `risk filter x2` — the
  harness caught the regression before it could ship.

Nothing changed in the registry. Shipping book unchanged at 528 / +533.37 / 13.42
IS and 311 / +239.59 / 11.88 OOS.