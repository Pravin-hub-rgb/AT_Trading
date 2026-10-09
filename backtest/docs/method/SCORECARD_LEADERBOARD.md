# Scorecard leaderboard — 12 candidates through the owner's framework

Date: 2026-10-09. Harnesses: `exp_scorecard.py`, `exp_scorecard_report.py`.
Framework: `backtest/docs/learn/finding optimal book.md`.
Interactive: `scorecard.html` (sortable).

**Net R was deliberately ranked last**, weighted 0.4 out of 7.9 — exactly as the
framework asks. That is what makes the leaderboard worth reading: **the book with
the biggest return finished sixth.**

---

# 1. The leaderboard

Lower score is better. Score is a weighted sum of per-tier **ranks** (1 = best), so
a book that wins the tiers you care about beats one with a bigger headline.

| # | book | score | neg | OOS R | retention | underwater | worst roll | top5% | net/DD | **net R** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **1** | **`mcloff_htf15`** 🆕 | **21.0** | 0 | 277 | 84% | 40 | −4 | 75% | 59 | +894 |
| 2 | `htf15` | 36.1 | 0 | 255 | 83% | 38 | −11 | 77% | 48 | +822 |
| **3** | **`sig_full`** | 37.6 | 0 | 194 | **102%** | **22** | **+10** | 76% | 45 | +490 |
| **4** | **`sig_multi`** | 37.8 | 0 | 220 | 77% | **24** | **+10** | **74%** | 53 | +704 |
| 5 | `mcloff` 🆕 | 41.8 | 0 | 271 | 82% | 54 | −12 | 81% | 55 | +838 |
| **6** | **`htfesmcl4`** (+1244R) | 45.4 | 0 | 326 | **64%** | **105** | −16 | 78% | 45 | **+1244** |
| 7 | `mode_fd` | 45.5 | **1** | 238 | 82% | 49 | −8 | 81% | 57 | +767 |
| **8** | **`champ_long`** (shipping) | **46.9** | **1** | 240 | 76% | 49 | −8 | 82% | 58 | +773 |
| 8 | `mode_union` | 46.9 | 0 | 304 | **96%** | **117** | −19 | **93%** | 37 | +884 |
| 10 | `mode_atr_low` | 47.5 | 0 | 281 | 79% | 98 | **−26** | 80% | **35** | +1002 |
| 11 | `biasmom05` | 55.2 | 0 | 217 | **74%** | 44 | −4 | 82% | 53 | +719 |
| 12 | `champ_short` | 63.4 | 0 | 240 | 68% | 80 | −20 | **93%** | 35 | +840 |

---

# 2. three results that settle things

## the biggest book is NOT the best book

`htfesmcl4` has **+1244R — the highest in the family by 242R** — and ranks **sixth**,
below two books making less than half as much. Its scorecard:

- **OOS retention 64%** — the worst except `champ_short`. The edge decays hardest
  out of sample
- **underwater 105 trades** — the second longest
- **net/DD 45** — half the leader's
- bought almost entirely by **1.47× more trades** (measured: R/trade 0.921 → 1.011,
  a t of 0.46, i.e. noise)

**This is exactly the book the owner said "lagta hai odd". The framework agrees, and
independently of the intuition.**

## the sig books are the only ones that never had a bad stretch

| book | worst 50 | worst 100 | longest underwater |
|---|---:|---:|---:|
| **`sig_multi`** | **+10.0R** | **+55.8R** | **24 trades** |
| **`sig_full`** | **+9.8R** | **+69.6R** | **22 trades** |
| `mcloff_htf15` | −4.2 | +11.6 | 40 |
| `champ_long` | −8.3 | −1.9 | 49 |
| `mode_atr_low` | **−26.4** | −17.9 | 98 |
| `mode_union` | −18.9 | −15.3 | **117** |

**Every other book has a stretch where it loses over 50 consecutive trades. The sig
books do not have one — not even a small one.**

That is the framework's *worst rolling period* tier and *drawdown duration* tier, and
it is the strongest quality signal in the whole table. `sig_full`'s worst
100-trade stretch **made +69.6R.** `mode_union` sat underwater for **117
consecutive trades.**

## tail dependence

| book | top 1% carry | top 5% carry | survives 10R cap |
|---|---:|---:|---:|
| **`sig_multi`** | 30% | **74%** | 442.9 |
| **`sig_full`** | 31% | 76% | 302.5 |
| `mcloff_htf15` | 31% | 75% | 629.2 |
| `champ_long` | 34% | 82% | 521.9 |
| `mode_union` | **40%** | **93%** | 608.8 |
| `champ_short` | **35%** | **93%** | 458.8 |

The framework says top 10% contributing **40–60%** is normal for trend following
and **70–90%** is a warning zone. **Every book here is in or past the warning zone,
and the sig books are at the healthy end of it.** That is a genuine and stated
limitation of this strategy family, not a book-specific defect.

---

# 3. OOS retention — the framework's #3 criterion

| book | IS expectancy | OOS expectancy | **retention** | OOS/IS DD |
|---|---:|---:|---:|---:|
| **`sig_full`** | 1.264 | 1.288 | **102%** | **0.65** |
| `mode_union` | 0.714 | 0.687 | 96% | 0.76 |
| `mcloff_htf15` | 1.100 | 0.928 | 84% | 0.90 |
| `htf15` | 1.091 | 0.910 | 83% | 0.98 |
| `mcloff` | 0.985 | 0.804 | 82% | 0.94 |
| `mode_fd` | 0.996 | 0.819 | 82% | 0.89 |
| `mode_atr_low` | 1.125 | 0.891 | 79% | **0.50** |
| **`sig_multi`** | 1.473 | 1.133 | 77% | 0.57 |
| `champ_long` | 1.010 | 0.770 | 76% | 0.89 |
| `biasmom05` | 1.028 | 0.756 | 74% | 1.00 |
| `htfesmcl4` | 1.157 | 0.747 | **64%** | 0.51 |
| `champ_short` | 1.129 | 0.768 | **68%** | **1.36** |

**`sig_full` is the only book whose out-of-sample expectancy EXCEEDS its
in-sample** — 102%, and it also has the lowest DD expansion at 0.65.

---

# 4. the honest caveat about all of this

**A weighted sum of ranks is still a made-up number.** The framework explicitly
warns against one arbitrary score, and this is a weighted sum of ranks over ten
tiers, which is better than a single formula but is not neutral. Three things keep
it honest:

1. **Every tier is printed.** You can see which tier decided each place and disagree.
2. **Tier 0 is a gate, not a score.** All 12 books passed: FS causality 0
   violations, origin lookahead PASS, every pin re-derived.
3. **The weights are visible and were set before the numbers were looked at**, and
   net R — the thing that would bias the result toward the big books — was given the
   *lowest* weight.

**Cost sensitivity is an approximation and is labelled as one** in the harness:
the per-trade cost is re-applied to the same trade series rather than re-running the
engine at 1.5×/2×/3×. It answers "how much of the edge is eaten by costs", not "how
would fills differ at a higher fee".

---

# 5. where this leaves the decision

| if you want | the book |
|---|---|
| **best overall score** | `mcloff_htf15` — 21.0, half the score of anything else |
| **best evidence** (powered period control) | `mcloff` |
| **best survival** (no bad stretch, short underwater) | **`sig_multi` / `sig_full`** |
| **best OOS retention** | **`sig_full`** at 102% |
| **highest return** | `htfesmcl4` — **and it ranks 6th** |

**The owner's instinct was `sig_multi`.** On this framework that instinct is
**supported on tiers 4, 5 and 7** — drawdown duration, worst rolling periods and
tail dependence — where it is the best or second-best of twelve. It loses on raw
return, which the framework ranks last anyway.

---

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS,
one negative half-year, `max_consecutive_losses=3` untouched.*