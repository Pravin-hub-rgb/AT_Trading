# LEARN — index

Everything written while working this problem, sorted by what a reader needs it
for. Read in this order if you are new; jump straight to the one you need if you
are not.

**The short version: no strategy is cleared for deployment.** The deciding
document is `02_verdict/PBO_DSR_GATE.md`. Read that first if you want the
answer and have no patience for the rest.

---

## 00_reference — what the work was built from

Inputs. Not findings. These shaped the method; they are not evidence about the
strategies.

| file | what it is |
|---|---|
| `finding optimal book.md` | the 13-bucket quality scorecard this repo was designed around |
| `4 backtesting techniques behind winning strategies.md` | the source for T1 (sensitivity), T2 (walk-forward), T3 (stress), T4 (Monte Carlo) |
| `margin mode.md` | old note on margin configuration, unrelated to strategy selection |

---

## 01_rules — what was decided in advance

These were written before the results they govern. That ordering is the whole
point of them, so do not edit them to fit an outcome — amend them and date the
amendment instead.

| file | what it fixes |
|---|---|
| `SELECTION_RULES.md` | the five-gate sequence, thresholds declared before the 13-book battery ran |
| `FORWARD_TESTING_CONTRACT.md` | era boundaries, the no-tuning rule, when the forward window may be looked at |
| `LIVE_CONFIGURATION.md` | live wiring and defaults |
| `FINALISATION_CHECKLIST.md` | what remains before anything goes live |

---

## 02_verdict — what the answer turned out to be

| file | verdict |
|---|---|
| **`PBO_DSR_GATE.md`** | **PBO 0.57–1.00 against a 0.15 bar; DSR fails for all 13 books in both eras. The history does not identify which book to deploy.** |
| `ALL13_GATES.md` | the five-gate verdict per book — no survivor |
| `VERIFIED_SUITE.md` | full metric suite with independently cross-checked implementations |

The gate sequence had already produced no survivor; PBO and DSR establish that
statistically rather than leaving it as a judgement call.

---

## 03_methodology_corrections — things that were wrong, and what fixed them

Kept deliberately. A reader who finds the same bug in future needs to know it
was already hit.

| file | what happened |
|---|---|
| `RETRACTION_SYNTHETIC_CLAIM.md` | the 1m candle data was declared synthetic on a heuristic that turned out to be normal exchange behaviour; verified byte-for-byte against a fresh download and retracted |
| `SLIPPAGE_REPORT.md` | what the cost model actually charges, and the largest component it omits |
| `REAL_SLIPPAGE.md` | slippage measured from real Bybit data, and why candle bars cannot show a gap |
| `METHODOLOGY_REVIEW_RESPONSE.md` | response to an external critique of method, including the parts that were accepted |
| `GATE_DIAGNOSTIC.md` | which gate was doing the rejecting, and why |

Three bugs were found in this codebase during one session — a profit-factor
cross-check that could not fail, a drawdown percentage understated 17x, and an
ulcer index overstated 286x. A fourth was my own reasoning: the retraction
above. Assume more.

---

## 04_experiments — the raw evidence

Superseded by the verdict, kept for the record. Each is one question asked once.

| file | question |
|---|---|
| `FOUR_TECHNIQUES_REPORT.md` | T1–T4 on the original candidates |
| `FOUR_TECHNIQUES_ALL_CANDIDATES.md` | T1–T4 across the five scorecard candidates |
| `FOUR_TECHNIQUES_ALL_MULTI.md` | T1–T4 across all thirteen multi books |
| `ATR_SENSITIVITY.md` | is `atr_high_thresh` live, and is `atr_low_thresh` inert? |
| `MONTE_CARLO_SURVIVABILITY.md` | shuffled orderings, drawdown tails, recovery |
| `SIZING_AND_RUIN.md` | equity ruin at explicit risk fractions; corrects an earlier "0% ruin" claim |
| `CAPITAL_HEAD_TO_HEAD.md` | same capital, all books, side by side |
| `HTFRR_DECOMPOSITION.md` | what `htf_rr` actually controls — window lifetime as well as target |
| `EXTENSION_CENSUS.md` | which knobs are load-bearing across the registry |
| `STOP_GATE_PERCENTILE.md` | the stop gate percentile rejected |
| `BREAKEVEN_AND_TRAIL.md` | HTF breakeven and trailing rejected |
| `FREQUENCY_AND_DIRECTION.md` | trade count vs best target; the retrospective-static-count caveat |
| `DIRECTIONAL_RULE.md` | long-5/short-3 target: helps 107, hurts 110, not adopted |

---

## The one-line version

Everything here supports a strategy family with a positive measured expectancy
on real Bybit data with verified costs and clean stop fills. None of it
identifies which of the thirteen variants to deploy, because thirteen variants
were tried and the trial count was never accounted for. That is what the next
step has to be: forward evidence on a frozen candidate, scored once.