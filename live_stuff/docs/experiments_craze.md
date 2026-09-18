# Experiments — CRAZE Lane (v19+)

**Owner:** Cline (independent lane — zero file conflicts with `experiments.md` / `test_experiments.py`)
**Branch:** `experiments/v19-plus` · **Engine:** frozen at `d19a854` (C14+C15 causal, verified)
**Committed baseline anchor (my harness must reproduce EXACTLY):**
- Coarse (15m exits): **340t / +225.3R gross / +155.9R net / WR 30.0% / PF 2.03**
- Fine (1m exits): 340t / +251.6R gross / **+182.3R net** / PF 2.15 / DD 27.1R / max-consec-loss 16 / all years +

**Hard rules (learned from the 470R -> 216R bug downgrade):**
1. Shipped engine in `backend/` is NEVER edited. All experiments live in my harness file as a copied walk.
2. Baseline identity check: my harness (all experiments OFF) must match the shipped engine trade-for-trade (count, R-sum to 1e-9). Any experiment is reported as delta-from-anchor.
3. Every veto/filter in an experiment receives ONLY `candles[:i+1]` (data up to the entry bar). Look-ahead is structurally impossible, not just reviewed away. The autopsy study may bucket trades using exit info, but any derived rule is re-implemented on truncated data.
4. Entry timing = signal at bar close (ts+900), entry next candle open. Same as shipped.
5. Every result table shows: per-year R, 2023-24 vs 2025-26 half-split, DD, max-consec-losers, trade count. A rule that helps only one half is flagged, not adopted.
6. Fine 1m validation only for experiments that survive coarse + half-split checks.

---

## Experiment List

| # | Name | Version | Status | Trades | Gross R | Half-split OK | Delta vs Base | Notes |
|---|------|---------|--------|--------|---------|---------------|---------------|-------|
| 0 | ANCHOR (identity check vs shipped engine) | v18 | DONE | 340 | +225.3 | n/a | — | exact match required |
| 11 | Split-mb: entry-mb != trail-mb | v19 | TODO | | | | | trail from slower swings rides 2024 trends |
| 12 | mb_1h window sweep (14/20/28) | v19 | TODO | | | | | HTF window granularity |
| 13 | Loss-Autopsy Entry-Veto | v20 | TODO | | | | | rules derived from autopsy of 238 losses |
| 14 | B3 structure confirmation (+ low-mb arm) | v21 | TODO | | | | | structure replaces time-confirmation |
| 15 | Sweep-and-Reclaim qualifier | v22 | TODO | | | | | liquidity-grab fingerprint filter |
| 16 | 1h momentum agreement filter | v22b | TODO | | | | | LTF signal must agree with 1h trend |
| 17 | Soft-halt (progressive confirmation) | v23 | TODO | | | | | escalate confirmation during loss streaks |

---

## Experiment Details

### Exp 11: Split-mb (entry-mb vs trail-mb decoupled)
**Hypothesis:** one mb_15m=50 chain currently serves both entries (wants fast swings) and trail pivots (wants slow swings). Decoupling lets the trail use mb_15m=75-100 pivots -> wider trail -> 2024 trend rides recover (avgW 4.35 -> 5+).
**Change:** signals from mb_entry chain, trail events from mb_trail chain.
**Grid:** mb_entry {40,50,65} x mb_trail {35,50,75,100}; diagonal = anchor.
**Expected:** +20-40R if 2024 recovers toward +100R.

### Exp 12: mb_1h window sweep
**Hypothesis:** HTF window granularity controls signal count/quality; 20 is untested against neighbors.
**Grid:** mb_1h {14, 20, 28} (entry/trail mb_15m fixed at 50).

### Exp 13: Loss Autopsy -> Entry-Veto
**Method:** study all 238 losing trades. Extract ONLY entry-time-knowable features:
- chase score (consecutive same-color closes into entry)
- SL width in ATR units (risk/atr15 — too-tight stops get wicked)
- room-to-move (distance from entry to recent opposing extreme, in risk units)
- chop at entry, ATR% percentile, time-of-day, loss-streak position, window age
Derive veto rules that remove strongly-negative R buckets. Re-implement on truncated data only.
**Expected:** +15-40R if a clean bucket exists.

### Exp 14: B3 structure confirmation
**Hypothesis:** mb is a TIME proxy for swing validity. B3 replaces it with STRUCTURE proof:
- B3-hold: after B2 break, require 2 consecutive closes beyond break level; enter on 2nd
- B3-retest: enter on retest of broken level (limit at break px)
- mb-elimination arm: B3 active + swing mb down to 10-20 (fast swings + structure confirm)
**Expected:** fewer fake breaks, earlier entries, same false-positive rate.

### Exp 15: Sweep-and-Reclaim qualifier
**Hypothesis:** preceding down-swing low swept and reclaimed fast (wick below prior low, close back above within <=2 bars) is a stop-hunt fingerprint that precedes real moves. Long entries require it (and mirror for shorts).
**Expected:** higher WR on remaining trades.

### Exp 16: 1h momentum agreement
**Hypothesis:** LTF counter-trend signals inside windows underperform. Require last closed 1h close > 3-bar 1h MA for longs (mirror for shorts), evaluated at the C14-aligned (close-known) 1h bar.
**Expected:** small trade-count drop, positive R delta.

### Exp 17: Soft-halt
**Hypothesis:** full skip after 3 losses freezes good regimes (16-loss streaks, 56-trade DD trench). Escalate instead: after 3 losses require B3-hold; after 5 require sweep-reclaim too. Keep trading, filter junk.

---

## Results Log

### 2026-09-18 — Session 1

**ANCHOR cross-validated 3x:** coarse 340t / +225.3R gross (replay_harness data + get_v18_params). Note: hardcoded-partial PARAMS give 360t/+148.3R — always use full get_v18_params+V18_ENGINE. Fine anchor NET +182.3 (cost 69.3) matches committed one-pass study exactly.

#### Autopsy (loss_autopsy.py) — 340 trades: 238 losses avg −0.92 / 102 wins avg +4.35
- **All single-feature entry vetoes DEAD**: chase>=3 removes +59.2R of WINNERS; SL-width has no tight stops (geometry); room/chop/apct buckets not robust; 00-04 UTC marginal (−3.1R).
- **streak counter bug caught & fixed**: v1 updated consec before row-append → tautological buckets. Fixed to PRE-ENTRY streak.
- **Post-halt re-entries (pre-streak>=3) are ELITE**: 111t, WR 37.8%, +126.0R coarse, both halves positive. The naive "cut losing-streak trades" veto would have DESTROYED +126R. Never adopt unmeasured.
- **pre-streak==2 entries consistently bad**: 55t, −17.1R, negative in ALL 4 years → motivated halt sweep.

#### Exp 17 halt sweep (shipped engine, coarse) — sweep_halt_mb1h.py
| halt | t | gross | DD | streak | H1 | H2 |
|---|---|---|---|---|---|---|
| 1 | 254 | +171.1 | 25.8 | 19 | +81.8 | +89.3 |
| 2 | 317 | +219.7 | 15.1 | 9 | +112.7 | +107.0 |
| 3 anchor | 340 | +225.3 | 27.1 | 16 | +101.0 | +124.3 |
| 4 | 351 | +140.4 | 19.5 | 13 | +49.4 | +91.0 |
| 5 | 362 | +212.6 | 21.0 | 11 | +96.2 | +116.4 |
| 6 | 369 | +235.1 | 17.7 | 14 | +117.1 | +118.0 |
| 8 | 372 | +224.4 | 19.6 | 12 | +113.2 | +111.2 |

- **halt=6 FINE: 369t / NET +187.9 (+5.6) / DD 17.7 (vs 27.1) / H1 +117.1 (better) / H2 +144.3 (−6.3 worse).**
- Verdict: NEAR-PASS pending ruling. Strong risk-adjusted case (NET/DD 10.6 vs 6.7, max DD −35%), +5.6R net, but technically fails strict both-halves by −6.3 on H2.

#### Exp 11 split-mb (harness, identity-gated) — test_experiments_craze.py + fine_validate_splitmb.py
Coarse grid (entry-mb -> trail-mb): e40/e65 ALL worse (entry-mb=50 confirmed optimal). Trail decoupling monotone:
- t75 coarse +260.1 (+34.8), t100 coarse +373.5 (+148.2). Identity gate: all patched modules byte-identical to shipped when flags off.
**FINE VERDICT (the referee):**
- anchor fine NET +182.3 / H1 +101.0 / H2 +150.6
- e50/t75 fine: 324t NET +192.5 (+10.2) but H2 −27.5 → FAILS both-halves.
- e50/t100 fine: 283t NET +317.1 (+134.8) but H2 −30.7 AND edge concentrated in ONE month (2023-01 = +173.5R of +253.6 H1) → FAILS both-halves + single-regime concentration. NOT adoption-grade.
- Lesson recorded: coarse split-mb gains mostly evaporate or concentrate under fine fills + half-split rule. The rule did its job.

#### Exp 12 mb_1h sweep (coarse)
- mb_1h=14: +236.7 but H1 worse than anchor (−6.4) → fail rule. mb_1h=28: +166.5 worse. **mb_1h=20 confirmed.**

#### Exp 16 momentum gate (1h close vs 3-bar MA, C14-aligned) — REJECTED
- 273t / +170.1R coarse (−55.2 vs anchor) despite DD 12.0. Gross down; rejected per goal (higher avg R).

#### Open
- Exp 14 (B3 hold/retest + low-mb arm) and Exp 15 (sweep-reclaim): TODO — need deeper walk patches (next session).
- Ruling needed from user: halt=6 adoption (risk-adjusted win, strict-rule near-miss).

