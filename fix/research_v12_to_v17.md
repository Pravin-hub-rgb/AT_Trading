## v16 — Entry Distance Gate (REJECTED)

### Hypothesis
Skip entries >30% into the 15m swing. Research showed 0-30% bucket = +220R.

### Results
| Config | Trades | Net |
|---|---|---|
| v12+cd20 | 414 | +265.30 |
| v16 (entry<=30%) | 347 | +230.46 |

**Rejected:** −35R net. Busy-chain disruption changes trade sequencing.

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

## v17 — ATR<0.5% Filter (REJECTED)

### Hypothesis
Low volatility at entry identifies better trades. Low-vol IS +0.449, OOS +0.961 (2.14× better).

### Results
| Config | Trades | Net | Avg R |
|---|---|---|---|
| v12+cd20 | 414 | +265.30 | +0.641 |
| v17 (ATR<0.5%) | 389 | +261.94 | +0.673 |
| **Excluded** | **50** | **+12.99** | **+0.260** |

**Rejected:** Excluded trades are NET POSITIVE (+12.99R).

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

### Per-Year
| Year | v12 net | v17 net | Excluded net |
|---|---|---|---|
| 2023 | +24.4 | +15.6 | +1.9 |
| 2024 | +70.3 | +80.3 | −1.0 |
| 2025 | +111.2 | +102.5 | +3.8 |
| 2026 | +59.4 | +63.5 | +8.4 |

Inconsistent across years.

### Conclusion
High-vol = both worst losers AND biggest winners. Filter removes both tails.

---

## Split-Sample Validation (IS: 2023-2024, OOS: 2025-2026)

### Distance → R
| Bin | IS mean | OOS mean |
|---|---|---|
| 0-10% | +1.104 | +1.499 |
| 10-20% | +2.489 | +4.297 |
| 20-30% | +0.584 | +1.125 |
| 30-40% | +0.305 | +3.358 |
| 90-100% | −0.086 | +0.408 |

**IS violations: 2/9 | OOS violations: 3/9** — NOT smooth in OOS.

### Volatility → R
| Vol | IS n | IS mean | OOS n | OOS mean |
|---|---|---|---|---|
| Low <0.5% | 207 | +0.449 | 163 | +0.961 |
| Med <0.8% | 25 | +0.107 | 11 | +0.085 |
| High ≥0.8% | 3 | −0.297 | 5 | +2.616 |

**Volatility IS smooth.** Low vol best in both periods.

### Best IS Bucket Validation
**entry<33% + ATR<0.5%:** IS mean +0.685 → OOS mean +1.099 (1.60× better, HOLDS UP)

But combined filter still removes +12.99R net positive trades.

---

## Key Insights

1. **Edge IS runners:** Cap 3R → −28R. Tail-dependent strategy.
2. **Descriptive ≠ predictive:** Coarse buckets look clean, fine bins reveal noise.
3. **Vol smooth, distance not:** ATR monotonic, distance bouncy.
4. **High-vol = both tails:** 68% losers but also +10.87R winner.
5. **Bootstrap ≠ proof:** Trades may not be IID. Downgrade claim.

---

## Final Recommendation

**v12+cd20 frozen baseline.** No filter improves it without removing runners.

---

## Files

| File | Purpose |
|---|---|
| `backend/src/btc/engines/htf_ltf/v12_cooldown.py` | v12 engine |
| `backend/src/btc/engines/htf_ltf/v16_entry_dist.py` | v16 engine |
| `backend/src/btc/engines/htf_ltf/v17_atr_filter.py` | v17 engine |
| `backend/debug/test_v12_8tests.py` | 8-test panel |
| `backend/debug/test_entry_gradation.py` | Fine-bin analysis |
| `backend/debug/test_smooth_oos.py` | Split-sample |
| `backend/debug/test_v17_atr_filter.py` | v17 analysis |
| `fix/research_v12_to_v17.md` | Full research doc |
