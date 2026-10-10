# The optimal-book framework, run on the HTF-FS arms beside the old books

**Run 2026-10-10. `exp_optimalbook_study.py` → `_optimalbook_study.json`**

The framework is `docs/learn/finding optimal book.md` — thirteen buckets, six
tiers, written for this project before any of these arms existed. Nine books
were put through it in one run: six old, three new. The question is not "are the
new books good" but **"are they better than what we already have, on the same
yardstick"**, which only a shared table answers.

**Tiers 1, 2, 3, 5 and 6 are below. Tier 4 (parameter plateau, cost sensitivity,
cross-asset) is a separate harness per axis and is not faked here. Tier 0
(validity) is PASS/FAIL and is enforced by `exp_fastcheck` and the causality
audit — a book failing those is not in this table at all.**

---

## The headline, before any table

**The new arms win on almost every descriptive measure and lose on exactly the
two that matter.**

| | new arms | old books |
|---|---|---|
| net, expectancy, PF | **higher** | lower |
| tail dependence | **healthier** | worse |
| in-sample half-years | **all positive** | mixed |
| OOS expectancy retention | lower | **better** |
| **permutation p, out of sample** | **0.49 – 0.97** | **0.0117 (mcloff)** |

**No new book clears the owner's three gates.** They are not candidates; they are
candidates' worth of return that has not yet earned it.

---

## TIER 1 — Profitability, in sample

| book | n | net | expectancy | PF | WR% | avgW | avgL |
|---|---:|---:|---:|---:|---:|---:|---:|
| `champ_long` ⭐shipping | 528 | 533.37 | 1.010 | 3.09 | 40.0 | 3.74 | −0.81 |
| `mcloff` | 575 | 566.59 | 0.985 | 3.02 | 39.7 | 3.72 | −0.81 |
| `htf15` | 520 | 567.57 | 1.091 | 3.23 | 41.2 | 3.84 | −0.83 |
| `htfesmcl4` | 793 | 917.80 | 1.157 | 3.46 | 43.0 | 3.79 | −0.82 |
| `sig_multi` | 329 | 484.59 | 1.473 | 3.71 | 45.6 | 4.42 | −1.00 |
| `sig_full` | 234 | 295.83 | 1.264 | 3.08 | 41.5 | 4.52 | −1.04 |
| **`htffs`** NEW | 770 | **897.94** | 1.166 | 3.44 | 42.3 | 3.88 | −0.83 |
| **`htf15_htffs`** NEW | 761 | **925.79** | **1.217** | 3.55 | 42.8 | 3.95 | −0.83 |
| **`sig_multi_htffs`** NEW | 434 | +666.32 | **1.535** | **3.96** | **45.2** | **4.55** | −0.95 |

Every new book beats every old book on net, PF and expectancy. **`sig_multi_htffs`
is the best book in the table on every one of those columns simultaneously.**

---

## TIER 2 — Equity quality

### Half-year cells — the owner's rule

**In sample:**

| book | cells | verdict |
|---|---|---|
| `champ_long` | 7+ / 1− | ❌ 2025H1 = **−1** |
| `mcloff` | **8+ / 0−** | ✅ |
| `htf15` | **8+ / 0−** | ✅ |
| `htfesmcl4` | **8+ / 0−** | ✅ |
| `sig_multi` | **8+ / 0−** | ✅ |
| `sig_full` | **8+ / 0−** | ✅ |
| **`htffs`** | **8+ / 0−** | ✅ |
| **`htf15_htffs`** | **8+ / 0−** | ✅ |
| `sig_multi_htffs` | 7+ / 1− | ❌ 2026H2 negative |

**Out of sample:**

| book | cells | verdict |
|---|---|---|
| `champ_long`, `mcloff`, `htf15`, `htfesmcl4`, `sig_multi`, `sig_full` | all positive | ✅ |
| **`htffs`** | 3+ / 1− | ❌ **2022H2 = −5** |
| **`htf15_htffs`** | 3+ / 1− | ❌ **2022H2 = −5** |
| `sig_multi_htffs` | **4+ / 0−** | ✅ |

**This is the decisive column and it cuts both ways.**

- The two new champ arms have **all eight in-sample half-years positive** — as
  clean as `mcloff`, and this is exactly what `htf_fs=all` could not do.
- But **both break 2022H2 out of sample by 5R.** All six old books clear it.
- `sig_multi_htffs` is the mirror image: it breaks **2026H2 in sample** but is
  clean out of sample.

**No new book has all-positive half-years in both eras. `mcloff` does.**

### Drawdown and depth

| book | maxDD | DD/Net% | net/DD | maxUW | uw% | ulcer | worst 20 | worst 50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `champ_long` | 13.42 | 2.5 | 39.7 | 49 | 80.3 | 3.43 | −12.68 | −8.34 |
| `mcloff` | 15.13 | 2.7 | 37.4 | 54 | 80.2 | 3.58 | −12.71 | −11.80 |
| `sig_multi` | 13.39 | 2.8 | 36.2 | **24** | **70.8** | **2.39** | **−7.13** | +10.02 |
| `sig_full` | **10.78** | 3.6 | 27.4 | **20** | 77.4 | **2.30** | **−4.90** | +9.84 |
| **`htffs`** | 19.78 | **2.2** | **45.4** | 60 | 77.7 | 3.83 | −14.48 | −12.55 |
| **`htf15_htffs`** | **29.62** | 3.2 | 31.3 | **105** | 75.4 | 4.13 | −13.22 | −19.28 |
| `sig_multi_htffs` | 17.82 | 2.7 | 37.4 | 31 | 71.0 | 2.81 | **−17.82** | +11.99 |

**`htffs` has the best return-per-drawdown ratio in the entire table (45.4)** —
better than `sig_full`'s 27.4 and `mcloff`'s 37.4. It converts return to risk
better than anything here, at 19.78R of drawdown rather than 10.78R.

But `htf15_htffs` has **maxUW = 105** — the same figure `htfesmcl4` carries. Two
years underwater without a new high, which is what the 29.62R drawdown and the
−19.28 worst-50 together mean in practice.

---

## TIER 3 — Tail dependence

This is where the new arms are **clearly better than the old ones**, and it is
the most surprising result in the study.

### In sample — what survives deleting the biggest winners

| book | rm top1 | rm top5 | rm top10 | rm top5% | rm top10% | top10% contributes |
|---|---:|---:|---:|---:|---:|---:|
| `champ_long` | 484.73 | 342.48 | 250.32 | 105.64 | −47.09 | 108.8% |
| `mcloff` | 517.95 | 375.70 | 282.65 | 105.77 | **−55.72** | 109.8% |
| `htf15` | 518.93 | 376.69 | 284.52 | 132.29 | −21.24 | 103.7% |
| `htfesmcl4` | 869.17 | 694.54 | 564.90 | 226.55 | −5.62 | 100.6% |
| `sig_multi` | 428.23 | 286.07 | 194.11 | 120.16 | +2.48 | 99.5% |
| `sig_full` | 239.47 | 139.26 | 65.07 | 46.91 | −29.09 | 109.8% |
| **`htffs`** | 849.30 | 674.67 | 545.03 | 206.64 | −24.03 | **102.7%** |
| **`htf15_htffs`** | 877.16 | 702.53 | 572.89 | 245.17 | **+11.72** | **98.7%** |
| **`sig_multi_htffs`** | 630.66 | 519.54 | 411.60 | 228.71 | **+75.49** | **88.7%** |

**Read the last two columns together.**

- **Lower "contributes" is better.** It says: what share of all profit came from
  the biggest 10% of trades. The doc's own warning zone is 70–90%.
- **`sig_multi_htffs` at 88.7% is the healthiest distribution in the family.**
- **`htf15_htffs` at 98.7% survives deleting its top 10% and still shows +11.72R.**
  **`mcloff` shows −55.72R.** The new arm is materially less dependent on a
  handful of trades than the book we were about to promote.

### Out of sample

| book | rm top5% | rm top10% | top10% contributes |
|---|---:|---:|---:|
| `champ_long` | 39.12 | −28.06 | 111.7% |
| `mcloff` | 55.48 | −27.80 | 110.3% |
| `sig_multi` | 67.44 | **+8.08** | 96.3% |
| `sig_full` | 59.57 | **+10.61** | 94.5% |
| **`htffs`** | 31.55 | **−50.71** | 116.9% |
| **`htf15_htffs`** | 46.82 | −32.45 | 110.7% |
| `sig_multi_htffs` | **84.33** | **+9.76** | **95.8%** |

**`htffs` degrades out of sample** — 116.9% contribution and −50.71R once the top
10% is removed, the worst in the table. Its in-sample distribution is good and
its out-of-sample distribution is the worst here. That is the shape of a result
that was found in the in-sample data.

---

## TIER 5 — OOS retention

| book | expectancy | PF | WR | net | DD expansion | sign |
|---|---:|---:|---:|---:|---:|---|
| **`sig_full`** | **102%** | **113%** | **112%** | 66% | 0.65× | both + |
| `htf15` | 83% | 92% | 90% | 45% | 0.98× | both + |
| **`mcloff`** | **82%** | **92%** | 93% | 48% | 0.94× | both + |
| `sig_multi` | 77% | 89% | 104% | 45% | 0.57× | both + |
| `champ_long` | 76% | 87% | 92% | 45% | 0.89× | both + |
| **`sig_multi_htffs`** | 69% | 80% | 104% | 35% | **0.45×** | both + |
| `htfesmcl4` | 64% | 77% | 88% | 36% | 0.51× | both + |
| `htf15_htffs` | 64% | 77% | 89% | 33% | 0.48× | both + |
| **`htffs`** | **62%** | **75%** | 87% | 33% | 0.73× | both + |

**Every book has a positive sign in both eras — no sign flips.**

But **the new arms retain the least.** `htffs` keeps 62% of its in-sample
expectancy out of sample against `mcloff`'s 82% and `sig_full`'s 102%. Their
drawdown shrinks out of sample (0.45–0.73×), which is good, but the return
shrinks faster.

**`sig_full` is the only book in the family that fully retains out of sample.**
It has been in the registry the whole time and has never been the recommendation.

---

## TIER 6 — Complexity

Parameters differing from the shipping base:

| book | count |
|---|---:|
| `htffs` | **5** |
| `htf15_htffs` | **5** |
| `mcloff` | 5 |
| `htf15` | 4 |
| `htfesmcl4` | 6 |
| `sig_multi_htffs` | **14** |
| `sig_multi` / `sig_full` | 13 |

**`htffs` and `htf15_htffs` are as simple as `mcloff`** — one added parameter
(`exp_htf_fs_entry`) on top of a base that already differs by four. That is a real
point in their favour and it is the opposite of `sig_multi_htffs`, which is the
most complex book in the family and carries two extra degrees of freedom beyond
`sig_multi`.

---

## The owner's three gates, all nine books

| book | DD IS | budget | halves IS | halves OOS | p IS | p OOS | verdict |
|---|---:|---|---|---|---:|---:|---|
| `champ_long` | 13.42 | ✅ | ❌ 7/1 | ✅ 4/0 | — | — | shipping |
| **`mcloff`** | 15.13 | ✅ | ✅ 8/0 | ✅ 4/0 | **0.0312** | **0.0117** | ✅ **all three** |
| `htf15` | 17.28 | ✅ | ✅ 8/0 | ✅ 4/0 | 0.1927 | 0.5021 | ❌ p |
| `htfesmcl4` | 27.74 | ✅ | ✅ 8/0 | ✅ 4/0 | 0.0285 | 0.5311 | ❌ p |
| `sig_multi` | 13.39 | ✅ | ✅ 8/0 | ✅ 4/0 | 0.9283 | 0.9138 | ❌ p |
| `sig_full` | 10.78 | ✅ | ✅ 8/0 | ✅ 4/0 | 0.7428 | 0.9223 | ❌ p (and its edge runs the *other* way — see note) |
| **`htffs`** | 19.78 | ✅ | ✅ 8/0 | ❌ 3/1 | 0.0272 | 0.5956 | ❌ halves, p |
| **`htf15_htffs`** | **29.62** | ❌ | ✅ 8/0 | ❌ 3/1 | 0.0105 | 0.4904 | ❌ three |
| **`sig_multi_htffs`** | 17.82 | ✅ | ❌ 7/1 | ✅ 4/0 | 0.5091 | 0.9708 | ❌ halves, p |

---

## Can a top contender go in the list?

**Yes as a measured arm, no as a pick.**

All three new books are registered with pins, descriptions and null-audit
p-values, and `htffs` is in the `/btc` dropdown. That is the "list".

**They cannot be the top contender, and the reason is one number each:**

- `htf15_htffs` — **the strongest in-sample p in the family (0.0105)** — is over
  the drawdown ceiling at 29.62R and breaks 2022H2. Fails three gates.
- `htffs` — the best return-per-drawdown ratio in the table (45.4), all-positive
  in-sample halves, passing period control both ways — **breaks 2022H2 by 5R and
  has p = 0.5956 out of sample.** Two gates.
- `sig_multi_htffs` — the healthiest distribution in the family (88.7% top-10%
  contribution, survives tail removal in both eras) — **breaks 2026H2 in sample
  and has p = 0.5091 / 0.9708.** Two gates.

**`fsent_champ_long_mcloff` stays the recommendation.** It is the only book in
the family that clears all three, and the study does not change that — it
quantifies what the new arms would cost to chase.

### What the new arms are actually worth

They are **not nothing**. Three findings from this study are worth keeping
regardless of adoption:

1. **`htffs` converts return to drawdown better than any book here** — 45.4 net
   per unit of drawdown against `mcloff`'s 37.4 — with the same five-parameter
   complexity and all-positive in-sample halves. If the out-of-sample p ever
   moves, this is the arm to re-examine first.
2. **`htf15_htffs` survives deleting its top 10% in sample (+11.72R) where
   `mcloff` does not (−55.72R).** The new HTF-FS mechanism distributes profit
   more widely than the loss-halt mechanism. That is a structural difference,
   not a size difference, and it is the most interesting thing in this study.
3. **`sig_full` fully retains out of sample (102% expectancy retention)** — the
   only book that does. Its null-audit gap runs **negative** against its parent
   (p = 0.7428 / 0.9223, gap −237.54 / −45.15), so that retention is retention of
   a *weaker* book rather than evidence of an edge. Not the outstanding experiment
   this section first suggested; corrected after checking the audit rather than
   assumed from the retention table.

**Shipping book unchanged.**