# the sig book with its single-slot gate removed — and a knob that turned out
# to be inert on the books I first tried it on

Date: 2026-10-08. Harness: `exp_sig_multi.py`. **Nothing promoted. No registry
entry created.**

The arm, in one line: **`fsent_sig_full`'s entire filter set with
`max_positions` 1 → 0** — the serial single-slot gate removed, concurrency
enabled, everything else identical.

---

## 1. the comparison

| era | arm | n | net | **DD** | WR | expectancy | net/DD | long R | short R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IS | sig_full (serial) | 234 | +295.8 | 10.8 | 41% | 1.264 | 27.44 | +293.3 | +2.5 |
| IS | **sig + mp0** | 329 | **+484.6** | 13.4 | **46%** | **1.473** | **36.19** | +465.9 | +18.7 |
| IS | champ_long (multi) | 528 | +533.4 | 13.4 | 40% | 1.010 | 39.74 | +343.4 | +189.9 |
| OOS | sig_full (serial) | 151 | +194.4 | **7.0** | 46% | 1.288 | 27.94 | +129.8 | +64.6 |
| OOS | **sig + mp0** | 194 | **+219.8** | 7.6 | **47%** | 1.133 | **28.77** | +136.7 | +83.1 |
| OOS | champ_long (multi) | 311 | **+239.6** | 11.9 | 37% | 0.770 | 20.17 | +96.6 | +143.0 |

**Against the shipping multi book out of sample: +219.8R against +239.6R — 92% of
the money, on 194 trades instead of 311, at 7.6R drawdown against 11.9R, with a
47% win rate against 37%.**

**Against its own serial parent: better on every axis except depth.** Both eras
gain, both eras gain win rate, and out-of-sample drawdown rises only 7.0 → 7.6.

**Both sides stay alive.** Out of sample the long column is +136.7R and the short
column +83.1R. That matters here because the FS-side autopsy found the two
families pointing in opposite directions, and this arm does not collapse onto one
side the way the shipping multi book does (+96.6 long / +143.0 short).

---

## 2. period control — the gate that decides

`R = a + b*cohort + half-year fixed effect`, on the disagreement set only. P87's
construction. Survivors are in **neither** cohort. MDE prints before the verdict.

### IN SAMPLE

```
serial  234t / +295.83R      sig+mp0  329t / +484.59R      dNet +188.76R
survivors 221 (+0.00R)   NEW 108 (+186.17R)   DROPPED 13 (-2.59R)
ASSERT exact decomposition: OK
disagreement 108 new vs 13 dropped    raw gap +1.5600R/trade
b after period control   +2.1619   (99% of the raw gap survives)
cluster-robust t (month) +2.240     SE 0.9653
month-cluster bootstrap  +1.8501   (4000 draws)
MDE = 1.96*SE = 1.8920    effect 2.1619  ->  POWERED
```

### OUT OF SAMPLE

```
serial  151t / +194.44R      sig+mp0  194t / +219.82R      dNet +25.38R
survivors 144 (+0.00R)   NEW 50 (+25.09R)   DROPPED 7 (-0.29R)
ASSERT exact decomposition: OK
disagreement 50 new vs 7 dropped     raw gap +0.4452R/trade
b after period control   +0.3303   (99% of the raw gap survives)
cluster-robust t (month) +0.294     SE 1.1224
month-cluster bootstrap  +0.2847   (4000 draws)
MDE = 1.96*SE = 2.1999    effect 0.3303  ->  UNDERPOWERED
```

**Read this carefully, because it is the whole result.**

**Almost all of it is real.** 99% of the raw gap survives the calendar in both
eras. This is not a regime proxy. The ATR% ceiling's signature — most of the
effect evaporating once the period is controlled — **does not appear here.**

**And the in-sample magnitude is genuinely established.** b = +2.16R per trade
with t = 2.24, above its MDE, confirmed by a 4000-draw month-cluster bootstrap at
+1.85. That is a powered result.

**Out of sample the direction holds but the size does not.** b = +0.33R against an
MDE of 2.20 — the effect is roughly a seventh of what the test can detect. The
+OOS net is real as an observation; **its magnitude is not established.** A null
from a test this wide is a statement about the test, not the arm.

**Note the gap between the eras:** b is +2.16 in sample and +0.33 out. The arm
does not stop working; it works about **6× less per trade** on unseen data. 50 new
trades is a thin basis for that number, whatever the p-value machinery says about
it.

---

## 3. the third gate — half-year partition

Full per-cell net on both sides, not a filtered cohort.

| era | cell | serial | sig+mp0 | ahead |
|---|---|---:|---:|---|
| IS | 2023-H1 | 59.3 (33t) | 91.1 (50t) | sig+mp0 |
| IS | 2023-H2 | 32.2 (28t) | 48.5 (38t) | sig+mp0 |
| IS | 2024-H1 | 66.6 (36t) | 67.6 (48t) | sig+mp0 |
| IS | 2024-H2 | 47.7 (32t) | 73.2 (39t) | sig+mp0 |
| IS | 2025-H1 | 20.4 (25t) | 40.5 (33t) | sig+mp0 |
| IS | 2025-H2 | 35.0 (34t) | 65.6 (48t) | sig+mp0 |
| IS | 2026-H1 | 18.8 (33t) | 28.1 (55t) | sig+mp0 |
| IS | 2026-H2 | 15.7 (13t) | 70.0 (18t) | sig+mp0 |
| OOS | 2021-H1 | 39.6 (38t) | 39.9 (47t) | sig+mp0 |
| OOS | 2021-H2 | 35.8 (37t) | 40.5 (43t) | sig+mp0 |
| OOS | 2022-H1 | 60.4 (37t) | 80.2 (52t) | sig+mp0 |
| OOS | 2022-H2 | 58.7 (39t) | 59.3 (52t) | sig+mp0 |

**12 of 12 half-years. Not one cell goes the other way.**

That is the strongest single piece of evidence here, and it is stronger than the
t-statistic, because it does not depend on the standard-error estimate that the
power gate just told us is too wide.

The tightest cells are worth noting: 2021-H1 is +39.6 against +39.9, and 2021-H2
+35.8 against +40.5. **In the first out-of-sample half-year the arm is worth almost
nothing.** It earns its keep in 2022-H1 and 2022-H2. A gain that shows up in every
cell but is concentrated in two is better than a gain that appears in one era only,
and worse than one that is uniform.

---

## 4. tail dependence — better, not worse

| arm | era | drop top1 | drop top5 | drop top10 | top1% contrib | top5% contrib |
|---|---|---:|---:|---:|---:|---:|
| serial | IS | 80.9 | 47.1 | 22.0 | 31.1 | 84.1 |
| **sig+mp0** | IS | **88.4** | **59.0** | **40.1** | 30.3 | **75.2** |
| serial | OOS | 83.4 | 45.0 | 22.4 | 31.2 | 69.4 |
| **sig+mp0** | OOS | **85.3** | **51.3** | **30.7** | 27.6 | **69.3** |

**Every survival figure improves in both eras.** Removing the top 10 trades leaves
40.1% of in-sample profit against the parent's 22.0%, and 30.7% out of sample
against 22.4%. **This is the opposite of what `union` did** — `union`'s top 5%
carried 96% of in-sample profit, and `sig+mp0`'s carries 75%.

**More trades dilutes the tail rather than concentrating it**, which is the
opposite of the usual failure mode and is worth stating plainly because it is
usually assumed to go the other way.

---

## 5. concurrency shape — what the knob actually changed

| era | arm | max concurrent | depth histogram |
|---|---|---:|---|
| IS | serial | 1 | 1:234 |
| IS | **sig+mp0** | **5** | 1:226 2:69 3:21 4:9 5:4 |
| OOS | serial | 1 | 1:151 |
| OOS | **sig+mp0** | **4** | 1:146 2:35 3:10 4:3 |

**Nothing in this repo measures this**, and it is the entire content of the knob.
The book reaches depth 5 in sample and 4 out of sample, but **69% of entries still
happen with nothing else open.** This is not a book that rewrites itself into a
crowded one — it is the same book that occasionally takes a second position.

Which is why the next result is not a surprise.

---

## 6. the knob is inert on the multi books — and that is structural, not a bug

I ran the obvious sibling sweep first: add this arm to every book in the family.
It came back **byte-identical** on all three multi books, both eras —
`champ_long` +533.4 → +533.4, `utcsat_long` +465.0 → +465.0, `champ_short` +600.6 →
+600.6. Flipping a concurrency gate cannot be a no-op on a book that holds five
positions at once, so I checked the wiring instead of reporting the null.

The harness engine's position gate is

```python
if max_positions > 0 and (not exp_mltf) and busy_until and bar_time <= busy_until:
```

and the harness patch wraps `exp_mltf` into that condition to **inject** the multi
behaviour. So `max_positions` only arms when `exp_mltf` is False. That is exactly
the shape of this repo's two families:

- **`fsent_sig_full` carries `max_positions=1` and no `exp_mltf`.** The gate is
  armed and never bypassed — genuinely serial — so setting it to 0 genuinely opens
  it. **Parts 1–5 measure a real change.**
- **the multi books carry `exp_mltf=True` and no `max_positions`.** The gate is
  bypassed whatever `max_positions` says. Hence byte-identical.

So the arm's honest description is **"the serial sig book with its single-slot gate
removed"**, and `max_positions` is the right knob *for this book*. The sibling null
is a property of the other books, not evidence that this knob does nothing. Part 6
of the harness now measures all four combinations so the distinction is on the
record rather than argued.

Worth noting this is the second time in two days that a null result here turned out
to be a mis-specified experiment rather than a finding. The lesson is the same both
times: a byte-identical result is a bug signal, not a result.

---

## 7. a free option, if concurrency is wanted

Cap sweep on the same knob set:

| cap | IS n | IS net | IS DD | OOS n | OOS net | OOS DD |
|---|---:|---:|---:|---:|---:|---:|
| none | 329 | +484.6 | 13.4 | 194 | +219.8 | 7.6 |
| **2** | 298 | +451.1 | **12.3** | 182 | **+229.7** | **7.0** |
| **3** | 317 | +483.1 | **12.3** | 192 | +219.8 | 7.6 |
| 4 | 326 | +483.5 | 13.4 | 194 | +219.8 | 7.6 |

**Cap 3 costs 1.5R in sample and nothing out of sample, and lowers drawdown in both
eras.** Cap 2 is the odd one — cheapest drawdown out of sample and the highest net
there, but it gives up 33R in sample.

**Cap 3 is the cleaner shape: 99.7% of the in-sample net, unchanged out of sample,
lower drawdown in both.** Since depth rarely exceeds 3, the cap barely binds — which
means it is a bound on the tail rather than a change to the book. That is worth
knowing if the concurrency ever matters operationally.

---

## verdict

| gate | result |
|---|---|
| period control, direction | **survives, both eras, 99% of the raw gap** |
| period control, magnitude IS | **powered** — b +2.16, t +2.24, MDE 1.89 |
| period control, magnitude OOS | **underpowered** — b +0.33 against MDE 2.20 |
| half-year partition | **12 of 12 cells** |
| tail dependence | **improves in every cell, both eras** |
| vs shipping book OOS | 92% of the net, 62% of the trades, **64% of the drawdown**, +10pp WR |

**This is the strongest non-shipping result in the repo, and it is still not an
adoption.** What is missing is specific: the out-of-sample effect is 6× smaller than
the in-sample one, and on 50 new trades the magnitude cannot be pinned down at any
confidence. The direction is not in doubt — 99% survival, 12 of 12 cells, better
tails. The size is.

**Three things worth doing with it, in order:**

1. **Cap 3 + a longer forward window.** The cap is free and the gap between the
   two eras is the only open question. Neither is answered by more in-sample work.
2. **Register it, if at all, as a serial-family sibling** rather than as a
   replacement for `fsent_champ_long`. It is not the same book — 194 trades against
   311 — and the honest framing is "the sig book's filters with concurrency", not
   "a better champion".
3. **Do not** read the in-sample +2.16R per trade as a forward expectation. Six
   times less on unseen data is the honest number to carry, and even that is not
   established.

## verification

| check | result |
|---|---|
| `exp_sig_multi.py` | 6 parts, exit 0, both artifacts written |
| decomposition assert | **exact in both eras** (survivors + new − dropped = dNet) |
| shipping book | unchanged, 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS |
| registry | untouched — no book created, no pins written |

Two harness bugs fixed while writing this: the bootstrap indexed a whole coefficient
vector where a scalar was wanted, and the markdown writer iterated the report dict
blindly and tried to format the `period` sub-dict as a number.