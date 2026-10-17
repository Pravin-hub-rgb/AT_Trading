# Profit concentration in time

The four validation techniques do not ask where the money arrived. A
book whose in-sample profit is one month of an otherwise flat series
passes all four and is still a different object from one that earns
steadily.

| book | era | trades | net | best month | best month R | share of net | worst month | net without best month |
|---|---|---:|---:|---|---:|---:|---:|---:|
| 107 | IS | 525 | +538.4 | 2023-12 | +131.3 | 24% | 2023-04 (-11.5) | +407.1 |
| 107 | OOS | 295 | +272.9 | 2021-09 | +55.4 | 20% | 2021-08 (-5.5) | +217.6 |
| 110 | IS | 395 | +644.0 | 2023-12 | +119.5 | 19% | 2023-04 (-8.8) | +524.5 |
| 110 | OOS | 216 | +336.2 | 2021-09 | +82.1 | 24% | 2022-12 (-7.7) | +254.0 |
| 106 | IS | 751 | +757.0 | 2023-10 | +116.9 | 15% | 2025-12 (-9.9) | +640.1 |
| 106 | OOS | 388 | +313.4 | 2022-05 | +98.6 | 32% | 2022-12 (-9.2) | +214.8 |
| 109 | IS | 754 | +764.8 | 2023-10 | +116.9 | 15% | 2025-01 (-10.3) | +647.9 |
| 109 | OOS | 395 | +346.1 | 2022-05 | +103.2 | 30% | 2022-12 (-9.2) | +242.9 |
| 108 | IS | 762 | +771.9 | 2023-10 | +120.1 | 16% | 2025-12 (-11.3) | +651.7 |
| 108 | OOS | 425 | +339.1 | 2022-05 | +101.1 | 30% | 2021-08 (-6.3) | +238.0 |

---

## Monthly net R, IS era

Only the months that matter are printed in full for 107 and 110; the rest
are summarised, because the question is where the profit sits, not the
whole ledger.

### 107 — top 6 months, of 44

| month | net R |
|---|---:|
| 2023-12 | +131.3 |
| 2026-02 | +47.4 |
| 2026-08 | +42.6 |
| 2025-09 | +41.8 |
| 2025-11 | +41.5 |
| 2025-07 | +31.0 |

Yearly: 2023 +172.8 · 2024 +98.1 · 2025 +120.7 · 2026 +146.9

### 110 — top 6 months, of 44

| month | net R |
|---|---:|
| 2023-12 | +119.5 |
| 2026-08 | +48.7 |
| 2026-02 | +47.8 |
| 2026-05 | +45.4 |
| 2025-07 | +45.0 |
| 2025-11 | +45.0 |

Yearly: 2023 +229.6 · 2024 +112.5 · 2025 +123.7 · 2026 +178.3

---

## How to read this

- **share of net above roughly 25 percent for a single month** means the
  book has a period it depends on. That is not disqualifying by itself,
  but it is a different risk from steady accrual and the sizing answer
  should differ.
- **net without best month** is the floor. A book that goes negative there
  is one good run away from being a losing strategy.
- **negative months count** is the floor check in the other direction. Many
  small negative months with steady positives is a healthy shape; one big
  positive month is a fragile one.
- None of the four validation techniques can see this. They care about the
  distribution of trades, not about where in calendar time the trades
  landed.
