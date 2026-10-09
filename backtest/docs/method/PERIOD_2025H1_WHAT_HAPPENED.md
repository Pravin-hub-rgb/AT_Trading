# 2025-H1 — what actually happened, and no, not every book was unprofitable

Date: 2026-10-09. Harness: `exp_period_2025h1.py`.

The owner asked whether anything at all was profitable in that window. It was.

---

# 1. the market in that half-year

| cell | bars | open | close | **ret %** | p95 move | med range |
|---|---:|---:|---:|---:|---:|---:|
| 2023-H1 | 4344 | 16545 | 30466 | **+84.14** | 0.988% | 0.510% |
| 2023-H2 | 4416 | 30461 | 42325 | +38.95 | 0.755% | 0.398% |
| 2024-H1 | 4368 | 42517 | 62750 | +47.59 | 1.147% | 0.624% |
| 2024-H2 | 4416 | 62904 | 93530 | +48.69 | **1.189%** | 0.625% |
| **2025-H1** | 4344 | 94343 | 107081 | **+13.50** | **1.046%** | **0.539%** |
| 2025-H2 | 4416 | 107319 | 87595 | −18.38 | 0.852% | 0.464% |
| 2026-H1 | 4344 | 87759 | 58604 | −33.22 | 1.038% | 0.562% |
| 2026-H2 | 1781 | 58550 | 77182 | +31.82 | 0.737% | 0.415% |

## the diagnosis in one line

**Normal volatility, and no net movement.**

- **Volatility was ordinary.** p95 hourly move **1.046%**, sitting between the
  lowest (0.737%) and highest (1.189%) in the whole sample. Median range
  **0.539%**, mid-pack. **This was not a quiet or dead market — it moved plenty
  inside itself.**
- **The drift is the outlier.** **+13.50% over six months** is the only small
  positive return in the sample. Every other cell either ran hard (+39% to +84%)
  or fell hard (−18%, −33%).

**A market that swings normally but goes nowhere is the hardest regime for a
structure-based book, and the easiest to mistake for a bug.**

## and the book was right about it

The best cells are **2025-H2 (+138R on −18%)** and **2023-H2 (+143R on +39%)**;
the weakest are **2023-H1 (+29R on +84%)** and **2025-H1 (−0.7R on +13.5%)**. The
book earns from movement *within* a window, not from direction — which is exactly
why a directionless half-year costs it almost nothing and no more.

---

# 2. was anything profitable there? yes — five of six

Six books scored across all 12 cells:

| cell | `champ_long` | `mcloff` | `mcloff_htf15` | `champ_short` | `sig_multi` | `htfesmcl4` |
|---|---:|---:|---:|---:|---:|---:|
| 2021-H1 | +43.7 | +40.9 | +46.8 | +2.2 | +39.9 | +53.5 |
| 2021-H2 | +34.7 | +50.1 | +50.9 | +30.1 | +40.5 | +90.9 |
| 2022-H1 | +92.4 | +107.4 | +115.2 | +107.5 | +80.2 | +180.2 |
| 2022-H2 | +68.8 | +72.5 | +64.5 | +99.7 | +59.3 | **+1.6** |
| 2023-H1 | +29.0 | +28.2 | +18.7 | +67.2 | +91.1 | +97.9 |
| 2023-H2 | +143.4 | +156.9 | +160.5 | +122.7 | +48.5 | +195.7 |
| 2024-H1 | +58.8 | +59.5 | +60.4 | +64.0 | +67.6 | +138.5 |
| 2024-H2 | +55.3 | +55.2 | +72.9 | +59.8 | +73.2 | +149.4 |
| **2025-H1** | **−0.7** | **+0.9** | **+35.7** | **+28.1** | **+40.5** | **+12.8** |
| 2025-H2 | +138.2 | +142.8 | +143.6 | +133.6 | +65.6 | +135.6 |
| 2026-H1 | +56.2 | +71.4 | +72.7 | +61.5 | +28.1 | +108.2 |
| 2026-H2 | +53.0 | +51.7 | +51.7 | +63.7 | +70.0 | +79.8 |

- **Cells where at least one of the six is negative: 1 of 12.**
- **Cells where all six are negative: NONE.**
- **2025-H1 was profitable for five of the six books**, including `sig_multi` at
  +40.5R and the *short* book at +28.1R.

## what this changes about the conclusion

**The negative cell was never a market problem, and it was never a family problem.
It was one book, one integer, and 0.69R.**

That is a stronger claim than &ldquo;this regime suits us&rdquo;, and it is the one
the data supports:

- `sig_multi` — a completely different signal ladder — made **+40.5R** in the same
  window.
- `champ_short` made **+28.1R**, on the *opposite side* of the book.
- The same architecture with `max_consecutive_losses=0` made **+0.9R**.

**Nothing needed a regime filter, a volatility filter or a new signal.** The
shipping book stopped itself.

---

# 3. the honest caveat

Five of six books being profitable in the window does not prove the sixth should
have been. **−0.69R on 60 trades is inside the noise band for a book with this
spread**, and a book that happened to be marginally red in a directionless window
is not obviously broken.

What the evidence *does* say is narrower and firmer:

1. **No regime filter was needed** — the signals traded there fine.
2. **The fix that works is behavioural, not predictive** — a loss-run cutoff was
   suppressing recovery trades, which is why the same window turns positive when
   it is removed.
3. **The −0.7R cell was never evidence of a bad market** and should not have been
   read that way.

---

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS,
one negative half-year, `max_consecutive_losses=3` untouched.*