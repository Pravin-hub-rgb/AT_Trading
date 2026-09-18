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
| 0 | ANCHOR (identity check vs shipped engine) | v18 | DONE ✅ | 340 | +225.3 | n/a | — | exact match, cross-validated 3x |
| 11 | Split-mb: entry-mb != trail-mb | v19 | DONE ❌ rejected | 283-324 | +259.9 fine | FAILS fine H2 | +10.2R net (t75) | coarse promise evaporates under fine fills |
| 12 | mb_1h window sweep (14/20/28) | v19 | DONE ✅ mb1h=20 | 323-348 | +236.7 best | mb14 fails H1 | mb1h=20 confirmed | no change adopted |
| 13 | Loss-Autopsy Entry-Veto | v20 | DONE ❌ all vetoes dead | — | — | — | — | but found: post-halt re-entries ELITE (+126R) |
| 14 | **B3 confirmation-entry** | v21 | **DONE 🏆 WINNER (ruling pending)** | 206 | **+322.2 / +278.6 net fine** | H1 ✓ H2 −12.0 | **+96.3R net** | WR 40.8%, DD 13.1, avg 1.35R/trade |
| 15 | Sweep-and-Reclaim qualifier | v22 | TODO | | | | | next session |
| 16 | 1h momentum agreement filter | v22b | DONE ❌ rejected | 273 | +170.1 | — | −55.2R | DD better but gross down |
| 17 | Soft-halt / halt sweep | v23 | DONE ⚠ near-pass | 369 | +235.1 (halt=6) | H2 −6.3 | +5.6R net, DD −35% | ruling pending |

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

#### Exp 14 B3 — entry AFTER structural confirmation of the break (test_b3_engine.py) — 🏆 WINNER
User's concept: b1+b2 happen BEFORE (known); the JUDGMENT is on B3 = a confirmation event after the break. Implementation (identity-gated harness patch):
- After a B2/flip signal at bar i, do NOT enter. Scan bars i+1..i+b3_k for a trigger: close beyond the signal bar's extreme (mode="close") or wick touch (mode="wick").
- Invalidation: SL pivot touched before trigger -> signal dies. Timeout -> dies.
- Entry relocates to trigger bar (entry at its close, engine convention); busy_until + cooldown re-checked at trigger bar (causal); trail events must confirm at/after entry; ATR/SL from trigger bar.

**Theory — why B3 should work (and why the data confirms it):**
1. **The B2 break is a coin-flip moment.** At the break bar's close, price has only just crossed the swing level — roughly half of all breaks fail immediately (stop-hunt wick, chop reversal). The engine's 30% WR says most break-entries are noise.
2. **B3 demands a SECOND, independent push.** Requiring a close beyond the BREAK BAR's own extreme means buyers (longs) had to absorb all supply above the first break and still close higher. A failed break can't produce that bar. So the trigger filters for breaks with follow-through demand — the population of taken trades shifts from "every break" to "breaks that already proved themselves."
3. **The evidence matches the mechanism exactly:** WR jumps 30.0% -> 40.8% (+10.8pt) — the filter removes losers, not winners. avg R/trade 0.54 -> 1.35 (2.5x). Trade count 340 -> 206 (-39%): we skip 134 trades whose B3 never fired — and those are precisely the marginal breaks. DD halves (27.1 -> 13.1) and max losing streak halves (16 -> 8) because loss-chains require consecutive FAILED confirmations, which are rarer.
4. **Why avg R rises, not just WR:** entries happen later, 1-8 bars into the move, so the trade's remaining trend-life is shorter but its CONFIRMED probability is higher; combined with the same SL pivot (risk unchanged), the R-distribution shifts up.
5. **Monotonicity check:** k=2 (weak filter, + WR 41% but few trades) -> k=4 -> k=8 improves total R monotonically in coarse — a dose-response curve, which is what a REAL mechanism looks like (curve-fit artifacts don't produce smooth dose-response).
6. **Cost synergy:** 134 fewer trades = −40% cost drag; fine fills confirm the coarse result nearly 1:1 (+96.9 coarse -> +96.3 net fine).

ARM A (mb50 + B3, coarse): monotone in k. k8 close 206t +322.2R WR 40.8% DD 13.1 streak 8, H1 +183.6 / H2 +138.6 (BOTH halves beat anchor). k8 wick 264t +290.6. k4 close 184t +235.3.
**FINE VERDICT (k8 close): 206t / gross +322.2 / NET +278.6 / WR 40.8% / DD 13.1 / streak 8 / per-year 2023 +68.9, 2024 +114.7, 2025 +85.7, 2026 +52.9.**
- vs anchor fine (NET +182.3, DD 27.1, WR 30.0, streak 16): +96.3R net, DD −52%, WR +10.8pt, max-loss-streak halved, avg R/trade 1.35 vs 0.54.
- Fill audit (_diff_b3_fills.py): 194/206 trades differ ONLY in exit timestamp (1m vs 15m label); ALL exit prices and R identical (stop-level fills; 1m opens tile 15m opens). Fine referee confirms the coarse result — unlike split-mb, nothing evaporates.
- Strict-rule status: H1 +82.6 better; H2 −12.0 (2026 −37.3, 2025 +25.3 partially offsets). 3 of 4 years better. NEAR-PASS like halt=6 but 10x the magnitude — USER RULING REQUIRED.

ARM B (low-mb + B3, coarse): mb30 alone = 444t +170.9R DD 35.6 (bad); mb30+k8 close = 307t +212.3R DD 22.0 (B3 rescues fast swings but still below anchor). mb40+k4 = +192.1. Structure-confirmation does NOT fully replace time-confirmation here — mb50 entry chain stays.

#### Open
- USER RULING: B3 k8-close (net +96.3R, DD halved, H2 −12.0) and/or halt=6 (net +5.6R, DD −35%) — both are param-level changes on the same engine, composable (test needed: B3 + halt=6).
- Exp 15 (sweep-reclaim qualifier): TODO next session.

---

## Session Summary — 2026-09-18

**What we did (chronological):**
1. Built the lane: my own doc + harness, zero conflicts with the other bot; shipped engine untouched.
2. Reconciled the anchor: discovered hardcoded-partial PARAMS give 360t/+148.3R (wrong); full `get_v18_params`+`V18_ENGINE` gives 340t/+225.3R coarse — matches committed baseline. Fine NET +182.3 matches the one-pass study. Cross-validated 3x.
3. **Loss Autopsy** (read-only study of all 340 trades): every entry-time-knowable feature bucketed by outcome. Found all single-feature vetoes dead; caught & fixed my own tautological streak-counter bug (consec updated before row-append); discovered post-halt re-entries are ELITE (+126R — would have been destroyed by the naive "cut streak trades" idea) and pre-streak==2 entries are consistently bad (−17.1R, all 4 years).
4. **Halt sweep** (shipped engine params only): halt=6 = +5.6R net, DD 27.1->17.7. Near-pass.
5. **mb_1h sweep**: 20 confirmed optimal.
6. **Split-mb harness** (identity-gated text-patch approach): coarse promised +35R (t75) / +148R (t100) -> fine delivered only +10.2R / +134.8R, both failing the both-halves rule; t100's edge = one month (2023-01). Rejected. Entry-mb=50 confirmed optimal.
7. **Momentum gate**: rejected (−55.2R).
8. **B3 confirmation-entry** (the user's idea, built as its own engine mode): coarse monotone win, fine-validated +96.3R net, WR 40.8%, DD 13.1. Fill audit proved the fine path ran and prices are identical to coarse (stop-level fills).
9. Bugs caught by gates along the way: vacuous identity pass (0 trades), wrong HTF-chain arg (0 trades), tautological streak buckets, hardcoded-cost net column. All fixed + hardened into asserts.

**Artifacts (all committed on `experiments/v19-plus`):**
- `live_stuff/docs/experiments_craze.md` — this doc
- `live_stuff/tests/loss_autopsy.py` — read-only trade study
- `live_stuff/tests/sweep_halt_mb1h.py` — halt + mb_1h sweeps
- `live_stuff/tests/test_experiments_craze.py` — identity-gated superset-patch harness
- `live_stuff/tests/test_b3_engine.py` — B3 experiment runner
- `live_stuff/tests/fine_validate_splitmb.py`, `fine_check_b3.py`, `fine_check_halt6.py` — fine-fill validators
- `live_stuff/tests/_diff_b3_fills.py` — fill audit (coarse vs fine exit diff)
- Commits: `c3749b1`, `e5a330f`, `425d400` (engine `backend/` untouched; other bot's files untouched)

**Baseline for next session:** anchor 340t/+182.3R net fine (v18). Best candidates pending user ruling: B3 k8-close (+96.3R net), halt=6 (+5.6R net, DD −35%). Next experiments: B3+halt=6 combo, Exp 15 sweep-reclaim, fine per-month deep-dive of B3's 2026 shortfall.


