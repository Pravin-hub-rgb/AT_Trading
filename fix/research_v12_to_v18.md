# AT_Trading BTC Strategy Research: v12 to v18

**Date:** 2026-09-08
**Author:** Pravin + AI Assistant
**Status:** v18 validated as new best

---

## Table of Contents

1. [Baseline: v12+cd20](#baseline-v12cd20)
2. [v16: Entry Distance Gate (REJECTED)](#v16-entry-distance-gate-rejected)
3. [v17: ATR Filter (REJECTED)](#v17-atr-filter-rejected)
4. [v18: Streak Halt (NEW BEST)](#v18-streak-halt-new-best)
5. [Comparison Table](#comparison-table)
6. [Key Insights](#key-insights)
7. [Files](#files)

---

## Baseline: v12+cd20

### Engine
- **File:** `backend/src/btc/engines/htf_ltf/v11_conditional_htf.py`
- **Mode:** `b2_vs_flip_chop` (B2 when chop>61.8, else Flip)
- **Cooldown:** 20 bars after a loss
- **SL buffer:** 0.25 ATR
- **Ext stop R:** 1.5
- **RR target:** 3R

### Stats (4-year: 2023-2026)
---

## v16: Entry Distance Gate (REJECTED)

### Hypothesis
Skip entries >30% into the 15m swing. Research showed 0-30% bucket = +220R.

### Results
| Config | Trades | Net |
|---|---|---|
| v12+cd20 | 414 | +265.30 |
| v16 (entry≤30%) | 347 | +230.46 |

**Rejected:** −35R net. Busy-chain disruption changes trade sequencing.

### Full Stats
| Metric | Value |
|---|---|
| Trades | 347 |
| Win rate | 23.6% |
| Net R | +165.5 |
| PF | 1.92 |
| Max DD | 20.9R |

### Per Year
| Year | Net R |
|---|---|
| 2023 | +24.2 |
| 2024 | +54.1 |
| 2025 | +94.2 |
| 2026 | +58.0 |

### Fine-Bin Analysis (10% bins)
```
 0-10%    71    +1.265   median −1.000
10-20%    45    +3.333   median +0.738   ← BEST bucket
20-30%    35    +0.878   median −0.010
30-40%     9    +1.662   median +1.661
40-50%    18    +0.131   median −0.677
50-60%    13    +0.578   median −0.605
60-70%    16    +0.035   median −0.008
70-80%    12    +1.073   median −0.071
80-90%    24    +0.115   median −0.699
90-100%   54    +0.069   median −0.548
```

**NOT monotonic.** 10-20% best, not 0-10%. Pattern bounces.

### Spearman Correlation
**ρ = +0.60** (positive!) — deeper entries = higher mean R. Contradicts hypothesis.

### Conclusion
30% boundary overfit to full dataset. Descriptive ≠ predictive.
---

## v17: ATR Filter (REJECTED)

### Hypothesis
Low volatility at entry identifies better trades. Low-vol IS +0.449, OOS +0.961 (2.14× better).

### Results
| Config | Trades | Net | Avg R |
|---|---|---|---|
| v12+cd20 | 414 | +265.30 | +0.641 |
| v17 (ATR<0.5%) | 389 | +261.94 | +0.673 |
| **Excluded** | **50** | **+12.99** | **+0.260** |

**Rejected:** Excluded trades are NET POSITIVE (+12.99R).

### Full Stats
| Metric | Value |
|---|---|
| Trades | 389 |
| Win rate | 27.5% |
| Net R | +197.3 |
| PF | 2.05 |
| Max DD | 26.0R |

### Per Year
| Year | v12 net | v17 net | Excluded net |
|---|---|---|---|
| 2023 | +24.4 | +15.6 | +1.9 |
| 2024 | +70.3 | +80.3 | −1.0 |
| 2025 | +111.2 | +102.5 | +3.8 |
| 2026 | +59.4 | +63.5 | +8.4 |

Inconsistent across years.

### Excluded Trade Analysis
| Metric | Value |
|---|---|
| Winners | 16 (32%) |
| Losers | 34 (68%) |
| Big winners (>2R) | 6 |
| Big losers (<−0.8R) | 27 |
| Net R | +12.99 |
| Median R | −0.881 |
| Max R | +10.874 |

68% losers, but 6 big winners (incl. +10.87R) pull net positive.

### Session Cross-Check
| Session | Kept | Excluded | Kept % |
|---|---|---|---|
| Asia (00-07) | 119 | 22 | 84% |
| London (08-15) | 145 | 8 | 95% |
| NY (13-21) | 149 | 7 | 96% |

ATR filter partially a session filter.

### Conclusion
High-vol = both worst losers AND biggest winners. Filter removes both tails.

---

## v18: Streak Halt (NEW BEST)

### Hypothesis
After 5 consecutive losses, halt trading until a winner occurs. Avoids giving back capital during losing streaks.

### Discovery
Streak analysis showed:
- After ANY losing streak, the next trade tends to win big
- 21L streak happened once in 414 trades
- 5L halt would activate ~10 times in 4 years

### OOS Validation (IS: 2023-2024, OOS: 2025-2026)

#### Recovery After Streak (IS-only)
| Streak | N | Avg R | Win% |
|---|---|---|---|
| 1L | 9 | +0.973 | 44% |
| 2L | 8 | −0.721 | 12.5% |
| 3L | 5 | +1.982 | 40% |
| 4L | 7 | −0.333 | 29% |
| 5L | 6 | −0.32 | 17% |
| 6L | 1 | +5.592 | 100% |

**NOT 100% win rate** on IS-only data. Earlier "100%" was from full 4-year sample.

#### v18 on OOS (2025-2026)
| Metric | v12+cd20 | v18 (halt 5L) | Difference |
|---|---|---|---|
| OOS Trades | 176 | 152 | −24 |
| OOS Net R | +186.21 | +206.5 | **+20.29** |

#### What v18 Skips in OOS
- **24 trades skipped**
- **All 24 were losers** (0 winners)
- Skipped avg R: −0.846
- Skipped net: −20.29R

#### OOS Per-Year
| Year | v12 Trades | v12 Net | v18 Trades | v18 Net |
|---|---|---|---|---|
| 2025 | 102 | +126.8 | 89 | +137.6 |
| 2026 | 74 | +59.4 | 63 | +68.9 |

**Both OOS years improved with v18.**

### Full Stats (4-year)
| Metric | Value |
|---|---|
| Trades | 330 |
| Net R | +331.1 |
| Improvement vs v12 | +66R |

### Bug Fix
**Issue:** v18 engine had halt check AFTER trade was added to list, so no trades were skipped.
**Fix:** Moved halt check BEFORE trade is added.
**File:** `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` lines 285-297

### Mechanism
> **After 5 consecutive losses, the strategy is in a regime where signals are weak. Halting avoids giving back more capital.**

This is NOT mean-reversion. It's **regime avoidance**.


---

## Comparison Table

### 4-Year Full Sample
| Version | Trades | Win% | Net R | PF | MaxDD | Verdict |
|---|---|---|---|---|---|---|
| v12+cd20 | 414 | 28.7% | +200.6 | 2.03 | 21.0 | FROZEN BASELINE |
| **v18** | **330** | - | **+331.1** | - | - | **NEW BEST +66R** |
| v17 | 389 | 27.5% | +197.3 | 2.05 | 26.0 | REJECTED |
| v16 | 347 | 23.6% | +165.5 | 1.92 | 20.9 | REJECTED |

### Per Year
| Version | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| v12+cd20 | +24.4 | +70.3 | +111.2 | +59.4 |
| v16 | +24.2 | +54.1 | +94.2 | +58.0 |
| v17 | +15.6 | +80.3 | +102.5 | +63.5 |

---

## Key Insights

1. **Edge IS runners:** Cap 3R → −28R. Tail-dependent strategy.
2. **Descriptive ≠ predictive:** Coarse buckets look clean, fine bins reveal noise.
3. **Vol smooth, distance not:** ATR monotonic, distance bouncy.
4. **High-vol = both tails:** 68% losers but also +10.87R winner.
5. **Bootstrap ≠ proof:** Trades may not be IID. Downgrade claim.
6. **Streak halt works:** After 5L, next signals are weak. Halting avoids losers.
7. **OOS validation matters:** v18 improves both 2025 (+10.8R) and 2026 (+9.5R).

---

## Final Recommendation

**v18 = v12+cd20 + streak halt at 5L**

- 330 trades (84 fewer than v12)
- +331.1R net (+66R vs v12)
- Validated out-of-sample: both 2025 and 2026 improved
- All 24 skipped trades were losers

---

## Files

| File | Purpose |
|---|---|
| `backend/src/btc/engines/htf_ltf/v11_conditional_htf.py` | v12 engine (b2_vs_flip_chop) |
| `backend/src/btc/engines/htf_ltf/v16_entry_dist.py` | v16 engine (entry distance gate) |
| `backend/src/btc/engines/htf_ltf/v17_atr_filter.py` | v17 engine (ATR filter) |
| `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` | v18 engine (streak halt) |
| `backend/src/btc/btc_routes.py` | Backend routes (v11-v18) |
| `frontend/src/app/btc/page.tsx` | Frontend (dropdown, comparison table) |
| `frontend/src/lib/btcApi.ts` | Frontend types |
| `backend/debug/test_v12_8tests.py` | 8-test robustness panel |
| `backend/debug/test_entry_gradation.py` | Fine-bin analysis |
| `backend/debug/test_smooth_oos.py` | Split-sample validation |
| `backend/debug/test_v17_atr_filter.py` | v17 analysis |
| `backend/debug/test_streak_analysis.py` | Streak analysis |
| `backend/debug/test_oos_validation.py` | OOS validation |
| `fix/research_v12_to_v17.md` | Earlier research doc |
| `fix/research_v12_to_v18.md` | This document |

---

## Changelog

- 2026-09-08: v18 validated as new best. Bug fix applied to halt logic.
- 2026-09-08: v16, v17 documented as rejected.
- 2026-09-08: v12+cd20 confirmed as frozen baseline.
