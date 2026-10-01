# Research Policy Correction — Legacy +30R/yr Screen

**Date:** 2026-09-24  
**Status:** Active research policy note  
**Scope:** Research docs, experiment harnesses, experiment logs  
**Not in scope:** Production engine/live code, frozen raw result JSONs, trade measurements

---

## 1. What changed

For a period of this project’s research work, experimental arms were judged against a fixed internal screen:

```text
dNet/yr ≥ +30 on both IS and OOS
```

That number was an **internal conservative screening heuristic**, not a user-defined production rule, not a legal/compliance gate, and not an independently validated adoption threshold.

It is now classified as:

```text
legacy 30R/year research screen
```

---

## 2. Current policy

For new and re-scored research:

1. Report **raw P&L** (IS/OOS net R, dNet, dNet/yr) as descriptive measurements.
2. Report **equity-curve effects** separately (maxDD, ulcer, calmar, drawdown duration, recovery, etc.).
3. Report **configuration coverage** (which bases/periods helped or hurt).
4. Report **material caveats** (harm on a reference config, era dependence, skew, reused OOS).
5. Do **not** treat any fixed R/year number as an automatic ship or fail gate.
6. Baseline is a **comparison anchor**, not an independently production-validated system.
7. Positive P&L + improved equity = **evidence of potential** (open research candidate), not automatic deployment authorization.
8. Harm on an applicable period/configuration remains a **material research caveat**.

### Label map (legacy → current)

| Legacy wording | Current reading |
|---|---|
| SHIP / clears ship bar | Would have cleared legacy 30R screen (historical only) |
| BELOW BAR / below ship bar | Below legacy 30R screen (historical only) |
| does not ship | Not adopted as a production change |
| DEAD because of +30 only | Re-read as mixed/no robust evidence unless the mechanism itself failed |
| DEAD for measured negative results | Remains DEAD (historical research verdict) |

---

## 3. What is intentionally preserved

### Frozen raw result JSONs (unchanged)

These remain audit artifacts of what the harnesses originally wrote:

- `_trail_slower_results_{is,oos}.json`
- `_cohort_sizing_results_{is,oos}.json`
- `_equity_quality_results.json`
- `_skip_decisive_ship_results.json`
- `_streak_salvage_results_{is,oos}.json`

They may contain keys/labels such as `ship`, `ship_bar`, `ship_30yr`, `BELOW BAR`. Those keys are **historical metadata evidence that the old internal policy existed**. They are not current decision rules.

Measurement fields in those files (`net`, `dNet_yr`, equity metrics, trade counts) remain authoritative for numbers.

### Genuine DEAD verdicts

Experiments that failed on measured results (negative net on both sides, destroyed coverage, catastrophic drawdown, mechanism confirmed harmful) remain **DEAD**. This correction does not resurrect them.

### SHIPPED engine / identity-gate language

Phrases like “SHIPPED engine”, “shipped baseline”, “identity gate vs shipped” refer to the **production reference engine**, not the legacy +30R screen. Those are unchanged.

---

## 4. Open research candidates under current policy (no production change)

| Candidate | Status |
|---|---|
| `exp_trail_half=1` + `exp_trail_delay_r=1.0` on multi | Positive multi P&L + equity-supported; default-off; not universal (hurts age10 single) |
| `exp_skip_decisive=1` on multi only | Positive OOS equity insurance; IS no-op on multi; hurts age10 if stacked; default-off |
| cohort sizing | IS positive, OOS hurt — era-dependent; closed as universal claim |
| age10 trail variants | Equity/reference config degrades under tested arms — closed for trail bolt-ons |

Full tables: `EQUITY_CURVE_STUDY.md`.

---

## 5. Related docs

- `EQUITY_CURVE_STUDY.md` — equity-lens re-score of the 2026-09-24 batch
- `STRATEGY_STATE_OF_PLAY.md` §12 — dual reporting guidance (no fixed ship gate)
- `CHECKLIST.md` 24.18–24.23 — research verdicts for skip_decisive / cohort / trail / equity study
- `EXPERIMENT_LOG.md` — top research-policy note + selective legacy-label cleanup

---

## 6. Out of scope / do not change

- `backend/` production and live code
- Frozen raw JSON result files
- Experiment trade lists or recomputed metrics
- Genuine historical DEAD results
- `MASTER_LEADERBOARD` absolute “+30R in 2027 = real edge” forward gate (different meaning: absolute performance expectation for a year, not a variant ship bar)
