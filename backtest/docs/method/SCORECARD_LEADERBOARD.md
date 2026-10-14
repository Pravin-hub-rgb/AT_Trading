# Scorecard leaderboard - 12 candidates through the owner's framework

**Regenerated 2026-10-14.** Harnesses: `exp_scorecard.py` (measurement), `exp_scorecard_report.py` (this file and `scorecard.html`).
Framework: `backtest/docs/learn/finding optimal book.md`.
Chain: **2840 swings / 7734 marks**, fingerprint `5a4c55331ba079a9` - the marks corrected by the B1 arming fix, V13 and the volatile-B1 work. The previous version of this file predates all of that.

**Net R was deliberately ranked last**, weighted 0.4 of 7.9 total - exactly as the framework asks. That is what makes this leaderboard worth reading: **the book with the biggest return does not finish first.**

Interactive: `scorecard.html` (sortable).

---

# 1. The leaderboard

Lower score is better. Score is a weighted sum of per-tier **ranks** (1 = best), so a book that wins the tiers you care about beats one with a bigger headline.

| # | book | score | neg | OOS R | retention | underwtr | worst roll | top5% | net/DD | **net R** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `champ_long_htf15` | **25.0** | 0 | 255 | 90% | 75 | -9 | -75% | 29 | +760 |
| 2 | `champ_long_mcloff_htf15` | **28.6** | 0 | 270 | 89% | 82 | -20 | -73% | 29 | +810 |
| 3 | `champ_long_htfesmcl4` | **34.5** | **2** | 339 | 79% | 79 | -20 | -84% | 55 | +1110 |
| 4 | `champ_long_mcloff` | **37.9** | 0 | 213 | 75% | 71 | -13 | -80% | 31 | +717 |
| 5 | `sig_multi` | **39.2** | **1** | 183 | 77% | 33 | +1 | -76% | 41 | +556 |
| 6 | `champ_short` | **40.6** | 0 | 195 | 54% | 49 | -5 | -88% | 60 | +764 |
| 7 | `sig_full` | **41.0** | **1** | 134 | 105% | 33 | +17 | -77% | 24 | +343 |
| 8 | `champ_long` | **44.6** | 0 | 215 | 82% | 91 | -14 | -80% | 27 | +682 |
| 9 | `champ_long_biasmom05` | **51.6** | 0 | 182 | 72% | 86 | -6 | -77% | 28 | +643 |
| 10 | `champ_long_mode_fd` | **55.2** | **1** | 193 | 79% | 91 | -14 | -84% | 25 | +648 |
| 11 | `champ_long_mode_atr_low` | **57.1** | 0 | 193 | 85% | 96 | -32 | -85% | 15 | +708 |
| 12 | `champ_long_mode_union` | **68.8** | **2** | 196 | 71% | 113 | -42 | -102% | 15 | +692 |

`neg` counts the book-negative half-years - the owner's decisive test. A book with 0 there has never had a losing half-year in either era.

---

# 2. What the score weights, in the framework's order

| tier | what it measures | weight |
|---|---|---:|
| `neg` | no negative half-year | 1.0 |
| `oos_net` | OOS performance | 1.0 |
| `retention` | OOS retention | 1.0 |
| `dd_duration` | drawdown duration | 1.0 |
| `worst_roll` | worst rolling 50/100 | 1.0 |
| `tail_spread` | tail spread (lower top5% better) | 1.0 |
| `net_dd` | net / DD | 0.7 |
| `cost_2x` | cost 2x survival | 0.5 |
| `simplicity` | simplicity (fewer tuned knobs) | 0.3 |
| `net` | raw net R | 0.4 |

The order is the framework's own: **validity, OOS performance, OOS retention, drawdown, worst rolling periods, distribution of winners, tail dependence, parameter robustness, cost robustness, simplicity, and raw net R last.**

---

# 3. Where this stands

- **The ranking's winner is `champ_long_htf15`** at 25.0.
- **Best OOS retention is `sig_full` at 105%.**
- **Best net/DD is `champ_short` at 60.**

These are three different books answering three different questions, and the framework says retention outranks net/DD. **All twelve are separate, runnable books - this table ranks attention order, it does not retire anything.**

---

# 4. Limits

- **Twelve books, one era split.** Retention has moved by several points between runs, so a 2-3 point gap is not a ranking.
- **Cost sensitivity is an approximation** and is labelled one elsewhere: the per-trade cost is re-applied to the same trade series, so it measures what costs eat, not fills that would differ at a different fee.
- **Tier 0 validity is not recomputed here.** It is enforced by `exp_fastcheck` and the causality audit, and every book in this table passed it.
- **Nothing is adopted by this file.** It orders attention.

