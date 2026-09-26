# Live Drawdown Monitor — Kill-Lines & Deterioration Bands

**Date:** 2026-09-25
**Source:** Stage T Monte Carlo (`exp_montecarlo_dd.py` → `_montecarlo_dd_results.json`), CHECKLIST 24.67 / LOG 67
**Framework:** drawdown video playbook — (1) execution audit first, (2) Monte Carlo = objective normal/abnormal line, (3) deterioration needs multi-metric evidence. **Null hypothesis: the edge is intact until HARD EVIDENCE disproves it. Never act on feelings.**
**Method:** N=10,000 i.i.d. trade permutations + N=10,000 moving-block bootstraps (block=20), seed 42, scopes pooled 2021-26 (primary), IS/OOS sanity. Metrics per sim: maxDD (sum-R and per-trade compounded at **1R = 1% equity**), longest underwater (trades), loss streak, total return%.

---

## 0. What we have today (Stage N percent lens, 1R = 1%)

| Lane | IS maxDD% 2023-26 | OOS maxDD% 2021-22 | Worst month | Underwater |
|---|---|---|---|---|
| champion | 22.7% | 23.6% | −11.9% / −9.3% | ~90% of time |
| utcsat | 20.9% | 22.4% | −11.0% | |
| age10 | 8.1% | 5.3% | −3.1% | |

These are **one historical ordering** — not the worst possible. That is what the Monte Carlo fixes.

## 1. KILL-LINE table (Step 2 — pooled 2021-26, 1R = 1%)

Observed = actual history. P50/P95/P99 = resampled maxDD% distribution. **Line = max(iid P99, block P99)** (conservative — block preserves loss clustering and is consistently worse).

| Lane | obs maxDD% | iid P50/P95/P99 | block P50/P95/P99 | **KILL LINE** | obs percentile (iid/block) |
|---|---|---|---|---|---|
| baseline (champ default) | 42.3 | 34.7 / 49.1 / 55.6 | 37.4 / 54.6 / 63.2 | **63.2%** | 83 / 71 |
| **champion (cand)** | 27.5 | 32.8 / 46.3 / 52.9 | 38.8 / 56.4 / 64.3 | **64.3%** | 17 / **5** |
| **utcsat (cand)** | 25.5 | 31.1 / 44.2 / 50.7 | 32.7 / 47.8 / 55.3 | **55.3%** | 15 / 11 |
| **age10 (cand)** | 8.1 | 8.6 / 13.0 / 15.9 | 8.1 / 10.5 / 12.3 | **15.9%** | 40 / 50 |

**Headline finding:** champion's actual 27.5% DD sits at only the **5th percentile** of block-resampled histories — 95% of alternative orderings of our OWN trades had a WORSE drawdown. Historical maxDD systematically understates risk (video's exact point, now quantified). Median possible DD (38.8% block) is already above our historical max.

**Supporting lines (pooled, block P99 unless noted):**

| Lane | underwater (trades) | loss streak |
|---|---|---|
| baseline | 428 (iid 334) | 25-30 |
| champion | **348** (iid 234) | **31** |
| utcsat | 286 (iid 222) | 29 |
| age10 | 22-31 | 9-12 |

**Risk scaling:** all numbers assume 1R = 1% equity risk. DD% scales ≈ linearly with risk-per-trade — at 0.5%/trade halve the lines (champion ≈ 32%), at 2%/trade double them. Re-run `exp_montecarlo_dd.py` with `RISK_PCT` changed for an exact line. Worked decision table in §1b.

## 1b. Risk-per-trade decision (EXAMPLE — editable, recompute if tolerance changes)

**Formula:** `risk_per_trade% ≈ tolerable_DD% ÷ kill_line%(at 1R=1%) × 1%`
(Pick the DD you can stomach living through; back out the risk that keeps the P99 line under it.)

**Worked example — tolerable DD = 30% (current example value, CHANGE WHENEVER NEEDED):**

| Lane | kill line @1R=1% | risk/trade for 30% tolerance | K2 line at that risk |
|---|---|---|---|
| champion | 64.3% | **≈ 0.47%** | ~30% |
| utcsat | 55.3% | **≈ 0.54%** | ~30% |
| age10 | 15.9% | **≈ 1.89%** (cap: see note) | ~30% |

**Other tolerances (same formula, scale linearly):**

| tolerable DD | champion | utcsat | age10 (capped ≤1.0*) |
|---|---|---|---|
| 20% | 0.31% | 0.36% | 1.00%* |
| 30% | 0.47% | 0.54% | 1.00%* |
| 40% | 0.62% | 0.72% | 1.00%* |

\* age10 formula output is capped at 1.0%/trade regardless of tolerance: its line rests on only 144 pooled trades (wide error), and 1% risk already targets ~16% P99 DD — well inside any sane tolerance. Lift the cap only after the line is re-verified on a larger ledger.

**How to change this later:** edit the tolerance row above (or the30% example) and re-apply the formula; for an exact (non-linear) line set `RISK_PCT` in `exp_montecarlo_dd.py` to the chosen risk and re-run (~2 min) — the kill-line table then speaks directly in your chosen risk units. **These numbers are a decision aid, not a production config: final risk% is a capital/risk-appetite call, documented here so it is made once, calmly, and not mid-drawdown.**

## 2. Normal-vs-abnormal bands by sample size (Step 3 — pooled, P5..P95 = 90% interval)

At n live trades, these ranges are NORMAL (healthy strategy will land outside them 10% of the time by chance):

| Lane | n | avgR/trade | WR% | maxDD% |
|---|---|---|---|---|
| champion | 50 | −0.34 .. +2.27 | 16..36 | 7.8..25.3 |
| champion | 100 | −0.02 .. +1.74 | 19..33 | 11.2..32.5 |
| champion | 200 | **+0.23** .. +1.39 | 22..30 | 15.4..39.2 |
| champion | 300 | **+0.38** .. +1.20 | 23..29 | 18.1..41.2 |
| utcsat | 50 | −0.31 .. +2.27 | 18..36 | 7.5..24.2 |
| utcsat | 100 | +0.00 .. +1.73 | 20..34 | 10.8..31.0 |
| utcsat | 200 | +0.26 .. +1.38 | 22..31 | 15.0..37.0 |
| utcsat | 300 | +0.42 .. +1.21 | 24..30 | 17.7..39.8 |
| age10 | 50 | +1.71 .. +6.17 | 38..56 | 3.8..10.9 |
| age10 | 100 | +2.73 .. +4.85 | 43..52 | 5.3..12.6 |
| baseline | 100 | −0.15 .. +1.33 | 21..35 | 10.5..31.5 |
| baseline | 300 | +0.16 .. +0.87 | 24..31 | 17.6..42.5 |

**Key read:** at n=100 even a healthy baseline can show **negative avgR (P5 = −0.15)** — do NOT call deterioration before ~200 trades. age10 pools only 144 trades → bands only to n=100; its n>100 bands are extrapolation-free (not computed).

## 3. Pre-registered action criteria (decided BEFORE live — no improvising)

- **K1 — execution mismatch ⇒ INSTANT kill (demo only).** Any of: entry/exit times ≠ backtest on same dates, missing/extra trades, realized costs > 2× assumed (0.055% fee + 0.005%/0.010% slip per side), funding/settlement cadence ≠ 8h, timezone ≠ UTC candle closes, config parity broken (risk%, cooldown, halt, multi-cap). This is an execution problem, not an edge verdict — fix and re-verify overlay before live resumes.
- **K2 — DD above kill line ⇒ abnormal, investigate/off.** Live compounded DD% > line at your risk% (champion 64.3% @1R=1%, utcsat 55.3%, age10 15.9%). Crossing historical maxDD alone (e.g., 27.5%→30%) is **NORMAL** — barely above median.
- **K3 — deterioration evidence ⇒ act.** Requires **n ≥ 200 live trades** AND **≥ 2 of 3**: avgR < P5 band, WR% < P5 band, maxDD% > P95 band (n-specific, §2). One metric or small sample = not evidence.
- **Underwater too long:** trades-in-current-DD > line (champion 348) = abnormal duration flag (combine with K3, not standalone).
- **Forbidden (from video + our research policy):** panic-off on feelings, hindsight stories ("market changed"), risk-up on recent winners (that rule is untested — would be a NEW strategy), parameter tweaks mid-drawdown, switching strategies on/off by mood.

## 4. Execution audit checklist (Step 1 — run on first live month, then monthly)

- [ ] Export live trades; overlay on backtest of the same dates — entry/exit times match (UTC, bar-close + entry rule)
- [ ] No missing trades / no extra trades beyond documented cadence (cooldown/halt explain every skip)
- [ ] Realized fees+slippage+funding vs assumed cost model — per-trade net R difference < 0.05R median
- [ ] Data source = Bybit BTCUSDT perp candles (same exchange, same timezone)
- [ ] Config parity: 1R% risk, cooldown, halt=3, multi caps, slippage params, cost params
- [ ] Equity curve shape overlay: no crazy divergence over first 50 trades

## 5. Caveats

- Per-trade compounding used here (MC needs a fixed ordering rule); Stage N monthly-chain gave champion IS 22.7% vs this method 25.5% — same ballpark, not identical.
- Resampling assumes future trades look like past trades; block=20 only partially preserves regime clustering. Lines are **necessary-not-sufficient** — they define "unusual", not "dead".
- Selection bias from the large research search is NOT corrected here (Stage-4 note) — the lines describe the ledger we have, they do not re-prove the edge.
- All at 1R = 1%; change `RISK_PCT` and re-run for other risk levels.
