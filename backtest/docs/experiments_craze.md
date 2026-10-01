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
| 14 | **B3 confirmation-entry** | v21 | **DONE 🏆 POTENTIAL BASE (user ruled)** | 206 | **+322.2 / +278.6 net fine** | H1 ✓ H2 −12.0 | **+96.3R net** | WR 40.8%, DD 13.1, avg 1.35R/trade; 2026 partial year |
| 15 | Sweep-and-Reclaim qualifier | v22 | DONE ❌ Phase-1 refuted | 41-186 | +40.3 to +133.7 | — | all below v18 base | per-trade up (+0.98) but volume destroyed; zero loss-predictive power |
| 16 | 1h momentum agreement filter | v22b | DONE ❌ rejected | 273 | +170.1 | — | −55.2R | DD better but gross down |
| 17 | Soft-halt / halt sweep | v23 | DONE ⚠ near-pass — decision deferred to end (user) | 369 | +235.1 (halt=6) | H2 −6.3 | +5.6R net, DD −35% | risk-profile win; combo with B3 = Exp 23 |
| 18 | **3-Mark Judgment System** (B3 = 3rd PIVOT BREAK + flip branches) | v24 | DONE ❌ all 4 arms rejected | 8-134 | +0.1 to +120.9 | — | all below v18 base | Arm D salvage: +0.90R/trade, DD 14.4 (flip exception); price-confirmation > structure-confirmation |
| 19 | **Skip-First-Swing Entry** (observe 1st break, enter on NEXT same-direction swing) | v25 | DONE ❌ refuted by Phase-1 metrics | — | — | — | **−189.2R rough net** | mechanism CONFIRMED (97%), remedy rejected; salvage → Exp 18 flip branches |
| 20 | **Close-Confirmed Initial SL** (56% of SL deaths are wick-only) | v26 | DONE ❌ Phase-1 refuted | — | — | — | **−6.3R rough net** | wick gain eaten by worse close-through fills + killed winners |
| 21 | **Mark-History Entry Autopsy** (entry-time mark features → quality filter) | v27 | DONE ⚠ no actionable bucket | — | — | — | — | FLIP entries 3.7× per-trade vs B2; flip-proximity edge → Exp 18 prioritized |
| 22 | **Second-Swing Conviction Trail** (accelerate trail at 2nd same-swing B2) | v28 | DONE ❌ refuted (walk) | 347 | +161.7 | — | **−63.6R** | mb50 confirmation lag is PROTECTIVE — filters shake-outs; slowness is a feature |
| 23 | **COMBO: B3 k8-close + halt=6** | v29 | DONE 🏆 logged (decision deferred) | 215 | +328.7 / **+283.4 net** | H1 ✓ H2 −2.8 | **+101.1R net** | best combo before their-lane audit |
| 24 | **AUDIT: their-lane OPTIMAL combo verified on shipped engine** | v30 | DONE ✅ **VERIFIED REAL — pending live-risk design** | 515 | +456.2 / **+348.0 net** | H1 ✓ H2 ✓ | **+165.7R net** | multi-LTF alone = +99.9R net; concurrent-position caveat quantified |

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
**Phase 1 RESULT — DONE (exp15_sweep.py, causal, coarse):** sweep-reclaim does NOT separate outcomes in the needed direction.

| Bucket (W = lookback bars) | Trades | Total R | avg R/trade | WR |
|---|---|---|---|---|
| sweep=YES, W=3 | 41 | +40.3 | **+0.98** | 24.4% |
| sweep=NO, W=3 | 299 | +185.0 | +0.62 | 30.8% |
| sweep=YES, W=6 | 104 | +101.4 | **+0.98** | 26.9% |
| sweep=NO, W=6 | 236 | +123.8 | +0.52 | 31.4% |
| sweep=YES, W=10 | 186 | +133.7 | +0.72 | 28.5% |
| sweep=NO, W=10 | 154 | +91.5 | +0.59 | 31.8% |

**Findings:**
- Sweep-at-entry trades DO have better avg R/trade (+0.98 vs +0.52-0.62) — the stop-hunt fingerprint carries *some* per-trade signal — but they are home-run-or-die: LOWER WR (24-27% vs 31%).
- Requiring the sweep slashes volume 3-7x: W=3 -> 41 trades/+40.3R total, W=6 -> 104/+101.4 — both far below the +225.3 anchor. **No configuration beats the base on total R.**
- Vetoing no-sweep entries removes +91 to +185R of positive R — worse.
- Deep losses (r<=-0.95, n=206): 66 (32%) had a sweep at entry ≈ baseline presence (31% at W=6) — **zero loss-predictive power**.
**VERDICT: REJECTED — the qualifier fails as an entry filter in both directions. Per-trade quality up, volume destroyed; not exploitable on this engine.**

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
- **USER RULING (2026-09-18): B3 k8-close = POTENTIAL BASE.** Marked as a good experiment and the potential new baseline. Research continues (week-long); all new experiments report against BOTH the v18 anchor AND the B3 potential base until final adoption. Note: 2026 data is partial (through early Oct) — user projects 2026 closes the −37.3 gap as the year completes.

ARM B (low-mb + B3, coarse): mb30 alone = 444t +170.9R DD 35.6 (bad); mb30+k8 close = 307t +212.3R DD 22.0 (B3 rescues fast swings but still below anchor). mb40+k4 = +192.1. Structure-confirmation does NOT fully replace time-confirmation here — mb50 entry chain stays.

#### Open
- USER RULING: B3 k8-close (net +96.3R, DD halved, H2 −12.0) and/or halt=6 (net +5.6R, DD −35%) — both are param-level changes on the same engine, composable (test needed: B3 + halt=6).
- Exp 15 (sweep-reclaim qualifier): TODO next session.

---

### Exp 18: The 3-Mark Judgment System — B3 as a THIRD PIVOT BREAK (v24)
**Status: DOCUMENTED — QUEUED. Per user: list ALL variants first, then run experiments one by one, logging results. DO NOT RUN until user says the variant list is complete.**

#### The marks (exact definitions)
- **Mark = a swing pivot/extreme break** emitted by the swing chain (the walker's B-marks).
- **B1** = the FIRST extreme break in a direction (e.g. up). Marks the start of a bias.
- **B2** = a SECOND consecutive extreme break in the SAME direction (breaks the next extreme of that direction's swing).
- **FLIP** = an extreme break in the OPPOSITE direction of the current bias.
- Current v18 behavior: it TRADES ON THE 2ND MARK (the B2 break itself, or a flip). Exp 14's B3 k8-close added a candle-level confirmation AFTER that 2nd mark. Neither of those is this experiment.

#### The core principle (user's theory)
**The first two marks are CONTEXT ONLY — no trading decision on them. The decision is the THIRD mark.** The third mark can be:
- a **B3** = a THIRD extreme break in the same direction (B1↑ B2↑ B3↑ → trade ↑), or
- a **flip-branch** (see the combination table below).

**Crucial distinction vs Exp 14:** Exp 14's B3 was a CANDLE rule (close beyond the break bar's extreme within k bars). Exp 18's B3 is a STRUCTURAL rule — the 3rd mark must be another genuine PIVOT BREAK from the swing chain. B1 = 1st extreme break, B2 = 2nd extreme break, B3 = 3rd extreme break. "We have so much income" — the marks are free information the walker already produces.

#### Combination table (all branches, B1↑ shown; mirror for down)
| # | Marks 1-2 (context, NO action) | 3rd mark | Interpretation | Action variant |
|---|---|---|---|---|
| P1 | B1↑, B2↑ | **B3↑** (3rd same-dir extreme break) | continuation confirmed by 3rd break | **trade ↑** at B3 mark's close |
| P2 | B1↑, B2↑ | **FLIP↓** (opposite break) | the up-move failed after two breaks — flip overcame TWO marks | V2a: **trade ↓** (flip has power) / V2b: skip / V2c: no action, wait for 4th mark |
| P3 | B1↑, FLIP↓ | **B2↑** (break back in B1's direction) | the flip failed; original direction re-proven | **trade ↑** |
| P4 | B1↑, FLIP↓ | **FLIP↓ again** (new extreme in flip direction) | double-flip — reversal confirmed | **trade ↓** |
| P5 (EXCEPTION) | B1↑, FLIP↓ | *(the flip itself is enough)* | "a flip itself is telling: I have too much power, I'm flipping B1's direction — go with it" | **trade ↓ immediately on the 1st flip** (2-mark judgment, flips ONLY) |

**State machine:** track the last two marks (kind1, dir1, kind2, dir2). When mark 3 arrives, classify by the table. After any trade decision (or skipped 3rd mark), the state resets/rolls forward (new B1 basis). Edge cases to define at implementation: which mark resets the counter after a flip; whether a 4th mark can act if the 3rd was a no-action flip (V2c); timeouts on stale marks.

#### Research arms (each run SEPARATELY against the anchor; half-split + fine rules apply)
- **A. Pure 3rd-break:** trade ONLY on P1 (B1↑B2↑B3↑ → ↑). P2/P3/P4/P5 = no trade. Isolates "is the 3rd extreme break alone better than v18's 2nd-mark entry?"
- **B. Full table:** P1 trade ↑, P3 trade ↑, P4 trade ↓, P2 per chosen variant (V2a/b/c).
- **C. Flip-exception:** P5 rule added on top (1st flip after B1 = immediate trade ↓) — plus B on top of it.
- **D. Stacked:** 3rd pivot break (this exp) AND Exp 14's k8-close price confirmation both required. Two independent confirmations.
- **E. Low-mb arm:** with 3-mark structural confirmation, retry faster entry chains (mb 30/40) — "might not need minbar at all" (structure confirmation replacing time confirmation, round 2).

#### Causal notes
- The 3rd mark's decision happens at that mark's bar close (pivot break known at close); entry next candle open — same convention as shipped.
- The mark stream must come from the walker's real-time emission (marks are known when emitted) — no re-walking history.
- Data prerequisite BEFORE coding: dump the actual mark stream from `_collect_signals`/walker (kind, direction, bar, price) and verify B1/B2/FLIP attribution matches the definitions above, incl. how flips re-baseline the bias.

#### Acceptance
- Same as all experiments: identity gate vs shipped (marks-off = identical), truncated-data discipline, per-year + half-splits, fine 1m validation for survivors, results logged below.

#### Results
**Phase 1 — ALL ARMS RUN (exp18_marks.py, mark-stream state machine, identity-gated, coarse):**

| Arm | Trades | Gross | WR | DD | streak | H1 | H2 | Verdict |
|---|---|---|---|---|---|---|---|---|
| v18 anchor | 340 | +225.3 | 30.0% | 27.1 | 16 | +101.0 | +124.3 | base |
| P1 (pure 3rd-break: B1↑B2↑B3↑) | **8** | −0.1R | 12.5% | 5.2 | 6 | +2.9 | −3.0 | ❌ structurally RARE — 3 consecutive same-dir breaks without an opposite mark in between almost never happen (8 in 3.7 yrs); the 3rd mark is usually B1-kind of the next swing |
| full (every 3-mark resolution trades 3rd mark: P1+P2+P3+P4) | 101 | +59.9 | 27.7% | 17.0 | 9 | +23.1 | +36.8 | ❌ per-trade +0.59 < anchor's +0.66 |
| P2b (full minus pure-reversal P2) | 40 | +22.0 | 30.0% | 7.6 | 6 | +11.4 | +10.6 | ❌ too few trades |
| D (flip exception: trade 1st flip after B1 immediately; + P1; P2-flips trade) | 134 | **+120.9** | 29.9% | **14.4** | 11 | +50.6 | +70.3 | ❌ on net R (all 134 trades are FLIP marks) — BUT per-trade +0.90 > anchor's +0.66 and DD halved: a quality-over-quantity profile |

**VERDICT: ALL FOUR ARMS FAIL vs the v18 base on net R. The 3rd-mark judgment as a REPLACEMENT for v18's 2nd-mark entry does not work.**
- Why P1 is empty: the retrace between swings almost always breaks an opposite pivot (emitting a FLIP mark) before a 3rd same-dir break fires — sequences die at mark 2-3 and reset. Structural rarity, not a bug (mark stream verified: 7,752 marks, identity gate passed).
- Arm D is the salvage: trading the FIRST flip after B1 (the user's "flip has too much power" exception) produces fewer-but-better trades (+0.90/trade, DD halved) — a candidate for a low-frequency overlay, not a base replacement.
- **Research insight (important):** confirmation via PRICE (Exp 14's candle close beyond the break extreme, +96.3R net) works; confirmation via STRUCTURE (waiting for a 3rd pivot break) is too slow — the market's retrace breaks an opposite pivot first. Price-confirmation beats structure-confirmation on this engine.

---

### Exp 19: Skip-First-Swing Entry — observe the first break, enter on the NEXT same-direction swing (v25)
**Status: DOCUMENTED — QUEUED. Phase 1 (metrics research) runs before the experiment. Per user: no experiments until the full variant list is done.**

#### The theory (user's)
- v18 baseline: we enter directly at the FIRST B2 — e.g. for a long, the break of a **buying swing**.
- The SL research hypothesis: when v18 hits its SL, the swing whose extreme got taken out is the swing we entered on — and it gets broken by the **NEXT swing that forms after entry** (for a long: the opposite **selling swing** forming after our buying swing; its formation IS the event that breaks our pivot low). Mirror for shorts (enter selling swing, the next buying swing kills it).
- So: the first same-direction swing is a *probe*. Instead of trading the probe, **observe** it. If the market makes ANOTHER same-direction swing after it (the market re-proves the direction), THAT second same-direction swing is where the real move lives — enter on that one instead.
- Skipping rule: if the next swing that forms is the OPPOSITE direction, the original signal is dead — which is exactly the loss case v18 would have taken.

#### Phase 1 — METRICS RESEARCH (read-only, autopsy-style, runs first)
**SL-swing attribution study.** For every v18 SL loss (132 of them at −1R) plus trail losses:
- identify the swing whose extreme = the SL level (`sl_pivot` of the trade) and its direction vs the trade direction;
- determine whether the SL break coincided with the formation/confirmation of the NEXT OPPOSITE swing (the selling swing forming after our long entry);
- measure: what % of SL losses are "SL hit = next opposite swing confirmed";
- also measure the counterfactual: for each loss, did a same-direction swing form AFTER the entry signal but BEFORE the SL hit? (If yes, the skip-first rule would have moved the entry there — where would that entry's SL have been, and would it have survived?)
- Output table: bucketed by year + half-split, with the % of the loss book this rule would remove, and the counterfactual R of "second-swing entries" for the SAME setups.

**This phase decides whether Phase 2 is worth running** — if the metrics say most SL hits are NOT next-opposite-swing events, the theory needs revision before coding.

#### Phase 2 — EXPERIMENT ARMS (only if Phase 1 supports the theory)
- **A. Base rule:** at v18's qualifying entry signal (B2/flip of a buying swing for long), do NOT enter. Wait for the NEXT swing. If it is same-direction (a new buying swing) and produces its own qualifying mark (its flip/B2 break) → **enter at that mark** (entry at mark's close, engine convention; SL = the NEW swing's pivot — more recent structure). If the next swing is opposite-direction → signal dead, no trade.
- **B. Observation-swing mb sweep (user's "quicker information" idea):** the second swing can be detected on a FASTER chain — mb ∈ {30, 40, 50}. Lower mb = the next swing confirms sooner = earlier second entry. Trade-off: faster swings = more noise in what counts as "the next swing."
- **C. Optional stack:** Phase-2-A entry + Exp 14's k8-close price confirmation on the second swing's mark.
- **D. Timeout question (define before coding):** does the observation state expire, or does it live until EITHER an opposite swing kills it OR a same-direction swing triggers? User's framing suggests: lives until one of the two happens (no time expiry) — that's the default; a timeout variant can be an arm if Phase 1 shows stale observations hurt.

#### Causal notes
- Every observation/decision uses only marks + candles known at that bar's close. The second swing's mark is knowable when the walker emits it. Entry at mark's close, next candle open — shipped convention.
- The observation state must be walk-sequential (one pending observation at a time, like the engine's busy_until logic) — defined in implementation.
- Mark-stream prerequisite (shared with Exp 18): dump and verify the actual B1/B2/FLIP attribution from `_collect_signals`/walker before building.

#### Acceptance
- Identity gate vs shipped (rule-off = identical), truncated-data discipline, per-year + half-splits, fine 1m validation for survivors, results logged below.

#### Results
**Phase 1 METRICS — DONE (exp19_metrics2.py, mark-based, causal pivot checks):**

Population: 340 trades → **132 direct SL losses (−1R book)**, 102 winners.

| Metric | Result | Meaning |
|---|---|---|
| **M3' — SL hit = next opposite swing's mark** | **128/132 (97%)** | ✅ **USER'S MECHANISM CONFIRMED** — the SL is broken almost exactly when the opposite swing forms (mark within ±2 bars of death) |
| M1 — death quality | 58/132 (44%) close-beyond-SL; **74 (56%) wick-only** | most SL deaths are wick spikes, not structural closes |
| M2' — same-dir NEW-swing B2 between entry and death | **0/132 (0%)** | the "second buying swing" the rule wants to enter on NEVER forms before the trade dies |

**Counterfactual of the skip-first rule (marks-based, causal):**
- Loss book: all 132 losses have NO second same-swing before death → the rule **skips all 132** → **+132.0R**
- Win book: 75/102 winners DO get a second same-swing → moved: only 34 still win, **41 turn into losses**; 27 winners skipped entirely → **−321.2R**
- **ROUGH NET: −189.2R → PHASE 2 AS SPECIFIED IS REFUTED.**

**Verdict:** the theory's *diagnosis* is right (97% — SL hits ARE the next opposite swing forming), but the *remedy* (enter on the next same-direction swing) enters too late — by the time the second swing's B2 marks, the move is already spent; 41 of 75 moved winners die. The edge lives in the FIRST-swing entry.
**Salvage:** the correct exploitation of the 97% finding is Exp 18's flip branches (P2/P3/P4/P5) — "what does the opposite swing's formation mean" is exactly the flip-logic already queued. Also noted: 56% wick-only deaths (stop-buffer territory, tested before — sl_buf variations are structural, not free).
**Phase 2 arms A/B/C: NOT built (refuted by Phase 1). Arm D (no-timeout observation) is subsumed by Exp 18.**

---

### Exp 20: Close-Confirmed Initial SL (v26) — from the M1 death-quality metric
**Phase 1 RESULT — DONE (exp20_close_sl.py, sign bug caught & fixed pre-verdict):**
- SL losses (132): only **7 saved** (+36.6R window R); **125 close-through** at −161.5R total (avg −1.29R — each close-through fill is WORSE than the −1R touch fill).
- Winners/trail-negs: 35 killed early (−47.2R) — and this is an UPPER BOUND on kills (ignores trail ratchet).
- **ROUGH NET: −6.3R** (2023 −6.4, 2024 −1.8, 2025 +1.3, 2026 +0.7 — mixed, mildly negative).
**VERDICT: REJECTED.** The wick-survival gain (+36.6R) is eaten by worse close-through fills (+29.5R extra loss on the 125) and early-killed winners. The wick deaths are the price of touch-stops, not free money.

### Exp 21: Mark-History Entry Autopsy (v27) — from the mark-stream discovery
**Phase 1 RESULT — DONE (exp21_mark_autopsy.py):**
- **Entry kind: FLIP entries avg +1.09R/trade (n=159, +173.2R) vs B2 entries avg +0.29R/trade (n=181, +52.1R)** — flip entries 3.7x better per trade. BUT B2 entries are net-positive → vetoing them LOSES 52.1R. Not actionable as a veto; it PRIORITIZES Exp 18's flip branches (P2/P4/P5) — flip marks carry the edge.
- Depth gradient: depth=1 (fresh after flip) avg +0.98R vs depth=2 avg +0.27R; depth>=4 veto = −0.9R total, halves mixed → not actionable.
- bsf 24-49 (mid-age flip) veto: −13.3R total but H1 −22.4 / H2 +9.1 → FAILS half-consistency → not actionable.
- reclaim feature: no discrimination (328/340 have it — definition too loose).
**VERDICT: NO clean actionable bucket. Phase-1 diagnostic value: flip-proximity edge confirmed → Exp 18 flip branches move to the front of the queue.**

### Exp 22: Second-Swing Conviction Trail (v28) — from the M2' asymmetry
**Source:** Exp 19 M2' asymmetry: 74% of winners had a 2nd same-direction swing's B2 mark before exit; losers NEVER do (they die before the market can re-prove).
**Theory:** the 2nd same-swing B2 mark is a *conviction event* — the market re-proved the direction. Once it fires, tighten the trail faster (ratchet the stop to the new swing's origin pivot at its B2 MARK instead of waiting for its mb50 confirmation).
**Implementation (identity-gated harness):** trail events for same-dir swings activate at their B2 mark bar instead of confirmed_at bar. Same pivots, earlier activation; all ratchet conditions (`sl_cur < cand < low`) still gate.
**RESULT — DONE (exp22_conv.py, coarse walk):**
- Conviction trail: **347t / +161.7R / WR 27.4% / DD 27.1** vs anchor 340t / +225.3R / WR 30.0% / DD 27.1 → **−63.6R, every year worse** (2023 19.6 vs 28.4, 2024 66.5 vs 72.5, 2025 47.1 vs 60.4, 2026 28.5 vs 63.9).
**VERDICT: REJECTED.** The mb50 confirmation lag is not a defect — it is PROTECTIVE: between a swing's break-mark and its confirmation, price wobbles, and ratcheting the stop to the young swing's origin during that wobble shakes the trade out of dips it would otherwise survive. Waiting for confirmation filters shake-outs. (Fits the earlier finding: the variant's trail confirmed the same pivots — the lag IS the edge.)
**Research meta-lesson (3 of 3):** every "make the trail/reactiveness tighter or earlier" idea tested (ATR-chandelier, end_px, conviction-mark ratchet) lost to the patient mb50 confirmation trail. The engine's slowness is a feature.




### Exp 23: COMBO — B3 k8-close + halt=6 (v29) — both param-level, composable
**Rationale:** B3 (Exp 14) and halt=6 (Exp 17) are independent near-passes on different mechanisms (entry confirmation vs streak tolerance). User instruction: document findings, defer all pick-decisions until ALL experiments are done; run this combo now.

| Config | Trades | Gross | NET (fine) | WR | DD | streak | H1 | H2 |
|---|---|---|---|---|---|---|---|---|
| v18 anchor | 340 | +225.3 (coarse) | +182.3 | 30.0% | 27.1 | 16 | +101.0 | +150.6 |
| B3 k8-close alone | 206 | +322.2 | +278.6 | 40.8% | 13.1 | 8 | +183.6 | +138.6 |
| halt=6 alone | 369 | +235.1 | +187.9 | 28.2% | 17.7 | 14 | +117.1 | +144.3 |
| **COMBO** | **215** | **+328.7** | **+283.4** | **40.9%** | **14.1** | **8** | **+181.0** | **+147.8** |

Combo per-year (fine): 2023 +66.9, 2024 +114.1, 2025 +91.2, 2026 +56.6 — all positive.
**Read:** the combo adds +4.8R net over B3 alone and nearly closes the H2 gap vs v18 (+147.8 vs +150.6 → only −2.8 short now; B3 alone was −12.0). DD 14.1 vs B3's 13.1 (marginal give-back for the H2 repair). All years positive. Best net figure of the entire research program so far.
**Status: DONE — logged. Decision deferred until all experiments complete (per user).**

---

### Exp 24: AUDIT of the other lane's results + OPTIMAL combo verification (v30)
**Task:** their docs (EXPERIMENT_RESULTS.md / EXPERIMENTS.md) claim baseline 351t/+238.0R and an OPTIMAL combo (mb1h=10, chop=55, persist=2, cd=0, multi-LTF) at 515t/+456.2R gross/+322.5R net (+174.6R delta). User asked: legit numbers, or bugs hiding?

#### Audit finding 1 — their harness is a PARALLEL ENGINE, not v18
- Their baseline (their exact invocation, fine fills): **351t / +238.03R** — reproduces their doc, BUT the shipped engine gives **340t / +251.6R** on the same data.
- Trade-by-trade diff: **256 common entries with IDENTICAL R** (walk math identical) + **84 shipped-only vs 95 their-only trades** — the SIGNAL SELECTION diverges from Jan 2023. Their "code audit: all simulation logic identical" claim is wrong at the selection level.
- Their harness's no-fine path is degenerate (returns 1 trade at +1048R — an open trade run to end-of-data on a micro-risk SL). All their numbers came from the fine path.

#### Audit finding 2 — the OPTIMAL combo SURVIVES on the shipped engine (ported via identity-gated patches: persist hysteresis + multi-LTF/no-busy)
| Config | Trades | Gross (coarse) | NET (fine) | WR | DD | vs v18 net |
|---|---|---|---|---|---|---|
| v18 anchor | 340 | +225.3 | +182.3 | 30.0% | 27.1 | — |
| multi-LTF alone (cd=10 kept) | 410 | +340.7 | **+282.2** | 31.5% | 28.8 | **+99.9R** |
| SAFE (mb1h10+chop55+persist2) | 367 | +241.4 | +194.0 | 25.0% | 30.0 | +11.7R |
| **OPTIMAL (SAFE + cd0 + mltf)** | **515** | **+456.2** | **+348.0** | 28.0% | 23.3 | **+165.7R** |
- Per-year OPTIMAL (fine): 2023 +94.4, 2024 +135.0, 2025 +84.4, 2026 +142.3 — all positive, all above the anchor's year. **Both halves crush the anchor (H1 +229.4 vs +101.0; H2 +226.7 vs +150.6)** — passes the strict rule B3 failed.
- Piece-by-piece on shipped: multi-LTF alone +115.4R coarse (**the biggest single lever found anywhere**); persist2 +7.8R; chop55 alone −43.2R; cd0 alone −1.4R; mb1h10 alone −36.8R — the combo's edge is mostly multi-LTF, with the rest as modifiers.

#### Audit finding 3 — the live-risk caveat, quantified
Multi-LTF removes the one-trade-at-a-time barrier (v18's design) → **concurrent positions**:
- multi-LTF alone: max 5 concurrent; 87.6% of bars at ≤1 position, 11.2% at 2-3, ~1.1% at 4-5
- OPTIMAL: max 5 concurrent; 80.7% at ≤1, 17.9% at 2-3, 1.4% at 4-5
- R-accounting treats each trade as independent 1R — with 2-5 open positions the REAL dollar risk multiplies during overlaps. R-DD understates dollar-DD in those windows.
**Pending design work (Phase 2):** concurrency cap (e.g. max 2-3 open trades) to capture most of the edge with bounded exposure; live re-entry latency effects (their own doc flags this); cd=0 live-validity (rapid re-entry after SL).

#### Status
- VERIFIED REAL on the shipped engine, fine fills, both halves. Decision deferred with the rest.
- Next: concurrency-capped variant (cap=2, cap=3) to find the exposure/edge trade-off.

---

### Exp 25: RECONCILIATION — the 351t vs 340t mystery SOLVED (production params restored)
**The other bot was RIGHT.** Root cause found: my scripts' param construction
`_p = get_v18_params(INSTRUMENT); _p.update(V18_ENGINE)` let `V18_ENGINE["chop_thresh"]=61.8`
**clobber** the Bybit production `chop_thresh=58.0` (btc_routes.py:914-918). Every session
experiment before Exp 25 ran at chop 61.8 — a valid variant, but NOT the production param set.
His audit output (351 common trades, zero divergence, identical R) is correct once both sides
run at production params.

**Production anchor (chop=58, btc_routes 914-941 params): 351t / +238.03R fine gross / +163.7R NET / WR 27.6% / DD 23.4**
(per-year fine: 2023 +38.8, 2024 +81.1, 2025 +37.6, 2026 +80.5 — matches his numbers exactly; audit v4 + his audit agree.)

**Key experiments RE-RUN at production params (coarse deltas / fine NETs):**

| Config | Trades | Gross coarse | NET fine | vs anchor NET (+163.7) | H1/H2 vs anchor |
|---|---|---|---|---|---|
| v18 anchor | 351 | +211.7 | +163.7 | — | — |
| B3 k8-close | 207 | +303.7 | **+258.3** | **+94.6** | H1 +57.6 ✓ / H2 +8.0 ✓ **(strict rule now PASSES)** |
| COMBO B3+halt6 | 216 | +325.2 | **+278.1** | **+114.4** | H1 +63.2 ✓ / H2 +24.0 ✓ **(PASSES)** |
| multi-LTF alone (cd=10) | 421 | +280.2 | +217.0 | +53.3 | H1 +51.7 ✓ / H2 +16.8 ✓ **(PASSES)** |
| their OPTIMAL (chop55+mb1h10+persist2+cd0+mltf) | 515 | +429.8 | **+348.0** | **+184.3** | H1 +109.5 ✓ / H2 +108.6 ✓ **(PASSES)** |

**MAJOR: at production params, the former near-passes become FULL passes** — B3, the B3+halt6
combo, multi-LTF, and their OPTIMAL all beat the anchor on BOTH halves. The earlier H2
shortfalls were partly artifacts of comparing against the chop-61.8 anchor.
**Corrections to the record:**
- Exp 24 "Audit finding 1" is WITHDRAWN: their harness is NOT a parallel engine — the
  divergence was my chop-61.8 params. Their harness == shipped engine at production params.
- All pre-Exp-25 craze-lane numbers (B3 +96.3 net, combo +283.4, multi-LTF +282.2, OPTIMAL
  +348.0-vs-182.3) were measured at chop 61.8 and are superseded by this table. Directional
  conclusions unchanged; the new decision menu uses the production table above.
- The regression test anchor (340t/+225.3) was chop-61.8 — updated to production (351t) below.
**Decision menu (production, fine NET): v18 +163.7 | B3 +258.3 | B3+halt6 combo +278.1 |
multi-LTF +217.0 | their OPTIMAL +348.0 (concurrent-position caveat applies). Final pick
deferred until all experiments done (user process).**

---

### Exp 26: GRAND SWEEP — their levers x our levers at production params (v31)
**All 20 configs, coarse (identity-gated shipped engine), top candidates fine-validated. Base: v18 351t / +211.7 coarse / +163.7 NET fine.**

#### Coarse sweep (full grid)

| # | Config | Trades | Gross | DD | Note |
|---|---|---|---|---|---|
| S0 | anchor | 351 | +211.7 | 23.4 | — |
| S1 | mltf | 421 | +280.2 | 23.4 | +68.5 |
| S2 | mltf+cd0 | 471 | +284.4 | 24.1 | |
| S3 | mltf+cd5 | 429 | +298.5 | 23.4 | |
| S5 | mltf+persist2 | 420 | +300.7 | 33.0 | |
| **S6** | **mltf+persist5** | **409** | **+362.8** | 33.4 | fine NET **+307.2** |
| S7 | mltf+cd0+persist5 | 460 | +262.5 | 32.4 | cd0 hurts with persist5 |
| S8 | mltf+mb1h10 | 442 | +303.4 | 39.3 | DD spike |
| **S9** | **mltf+mb1h10+chop55** | **460** | **+405.8** | **38.2** | fine NET **+335.6** |
| S10 | mltf+persist2+mb1h10+chop55 | 452 | +347.0 | 32.7 | |
| **S11** | **their-OPTIMAL** | **515** | **+429.8** | **23.3** | fine NET **+348.0** |
| S12 | B3 k8 alone | 207 | +303.7 | 15.5 | |
| S13 | B3+mltf | 207 | +303.7 | 15.5 | **identical to S12 — mltf adds NOTHING on B3** |
| S14 | B3+mltf+cd0 | 212 | +298.8 | 17.5 | cd0 hurts B3 |
| **S15** | **B3+their-OPTIMAL** | **247** | **+355.4** | **12.0** | fine NET **+300.4** — **R/DD king (25.0)** |
| S16 | B3+mltf+persist5 | 202 | +299.7 | 24.8 | |
| S17 | B3+halt6+mltf (=Exp25 combo+mltf) | 216 | +325.2 | 17.5 | mltf adds nothing on combo either |
| S19 | their-OPTIMAL+halt6 | 573 | +397.2 | 31.5 | halt6 HURTS their combo; fine +301.1 |

#### Fine NET (production params) — the decision menu

> **⚠️ PRE-FIX NUMBERS:** These results use an older cost model and pre-B3-fix values. Post-fix authoritative numbers are in [EXPERIMENT_RESULTS.md §17](EXPERIMENT_RESULTS.md#17-post-fix-results-b3-entry-price-bug-fixed) and [EXPERIMENTS.md](EXPERIMENTS.md).

| Config | Trades | NET fine | DD | NET/DD | vs anchor |
|---|---|---|---|---|---|
| v18 anchor | 351 | +163.7 | 23.4 | 7.0 | — |
| B3 k8 alone | 207 | +258.3 | 15.5 | 16.7 | +94.6 |
| COMBO B3+halt6 | 216 | +278.1 | 17.5 | 15.9 | +114.4 |
| mltf alone | 410 | +217.0 | 23.4 | 9.3 | +53.3 |
| mltf+persist5 | 409 | +307.2 | 33.4 | 9.2 | +143.5 |
| mltf+mb1h10+chop55 | 460 | +335.6 | 38.2 | 8.8 | +171.9 |
| **their-OPTIMAL** | 515 | **+348.0** | 23.3 | 14.9 | **+184.3** |
| OPTIMAL+halt6 | 574 | +301.1 | 31.5 | 9.6 | +137.4 |
| **S15 B3+OPTIMAL** | 248 | **+300.4** | **12.0** | **25.0** | +136.7 |

> **Post-fix authoritative champion:** OPT-cd10 + w24 + ext1.5 = **+337.7** / DD 19.2 (multi-position, needs concurrency cap). See [EXPERIMENTS.md](EXPERIMENTS.md) row 1.

**Findings:**
1. **their-OPTIMAL stays the NET king (+348.0)** — but S15 (B3 stacked on it) is the **risk-adjusted king**: +300.4 net with DD 12.0 (NET/DD 25.0 vs OPTIMAL's 14.9), WR 34.3%, only 248 trades (lower concurrency exposure than OPTIMAL's 515).
2. **B3 absorbs mltf completely** (S13 == S12 identical) — B3's delayed entries already consume the re-entry space; multi-LTF adds nothing on top of B3.
3. **cd0 hurts everything it touches** in our stacks (S7, S14) — its value only shows inside their-OPTIMAL's specific stack.
4. **halt6 hurts their-OPTIMAL** (S19 −55R net vs OPTIMAL) but helped B3 stacks — context-dependent.
5. persist5 is a real modifier on mltf (+82.6 coarse over mltf alone).
6. All multi-LTF configs carry the concurrent-position caveat (Exp 24: max 5 open, mostly 1).
**Status: DONE — logged. All decisions deferred until experiment list exhausted (user process).**

---

### Exp 27: Opposite-Mark Stop Accelerator (audit Q7 — trail-side exploit of the 97% finding)
**Premise (Exp 19):** 97% of SL deaths coincide with the next opposite swing forming. Instead of an entry filter, exit/tighten when the opposite mark confirms while in a trade.
**Arms (coarse, production params):** `all` = exit at close of first opposite-dir break-mark bar; `loss` = only if unrealized R < 0; `fliploss` = FLIP-kind only + R < 0.

| Base | all | loss | fliploss | Base ref |
|---|---|---|---|---|
| anchor | 472t +138.9 | 381t +183.3 | 365t +174.9 | 351t +211.7 |
| B3 | 267t +236.9 | 219t +267.7 | 213t +295.8 | 207t +303.7 |

**REFUTED on every arm, both bases.** `all` exits 465/472 anchor trades at the first opposite mark — the mark stream fires far too early on eventual winners. Even the most conservative arm (fliploss on B3) loses −7.9R. This is the **4th independent confirmation** of the Exp 22 meta-lesson: early/tighter exits destroy more winner-R than they save in loser-R. The 97% finding is diagnostic (why trades die), not actionable (when to exit).
**Status: DONE — refuted, strengthens design constraint below.**

---

### Exp 28: Audit Response — other bot's 10-question audit, answered with runs (v31)
All runs identity-gated, production params (chop=58). Scripts: `exp28_audit.py` (coarse), `exp28_fine.py`, `exp28c_cd.py`.

**Q1 — Is S15 really "B3 stacked on multi-LTF"? NO — renamed.**
B3+chop55+mb1h10+persist2+cd0 **without mltf**: 242t / +361.3 coarse / **NET +307.2 fine / DD 12.0** — vs S15 (with mltf): 247t / +355.4 / +300.4 / 12.0. mltf adds ~nothing (+5 trades, −6.8R net). **The edge is the params, not multi-LTF.** S15 renamed **"B3-OPT"** (B3 with OPTIMAL params). Bonus: B3-OPT is **single-position** — no concurrency design needed at all. (Concurrency caveat now applies ONLY to mltf-carrying configs.)

**Q2 — cd0 inside the stack: real, not curve-fit, but context-dependent.**
OPTIMAL with cd=10: 453t / NET +282.2 / DD 32.7 vs cd=0: 515t / +348.0 / 23.3. cd0 is worth **+65.8R net in-stack** (and cuts DD). Mechanism: mb1h10+chop55 produce denser entry opportunities; cooldown=10 blocks profitable immediate re-entries. It hurt OUR stacks (S7/S14) because those entry streams are sparser. cd0 is the least-independent knob in the stack — its value is conditional on the dense-entry regime.
**B3-OPT exception (exp28c):** cd0 vs cd=10 is a wash — NET +307.2 vs +306.6, DD 12.0 both. **B3-OPT does NOT need cd0** → production cooldown stays, and the cd0 live-risk question does not apply to B3-OPT.

**Q3 — The "82R coarse→fine drop" was a gross/net comparison error. There is NO fill-sensitivity drop.**
Trade-level reconciliation: OPTIMAL coarse +429.8 vs fine **+456.2 GROSS** — 515/515 trades matched, zero vanished, per-trade drift +26.3R total (fine granularity HELPS this engine). The apparent "drop" = 108.2R of costs across 515 trades (≈0.21R/trade, same rate as every config). B3 reconciles identically (247/247 matched, drift 0.0). No live-fill red flag beyond the already-modeled costs.

**Q4 — Temporal stability at 3 cuts (50/66/75%; fixed config, NOT re-optimized walk-forward — honest limitation):**
OPTIMAL is the most balanced: seg2 positive at every cut (+231.8/+201.2/+147.8) vs seg1 (+198.1/+228.6/+282.0). B3-OPT passes all cuts but front-loaded (+207.9→+147.5 at 50%; +276.8→+78.6 at 75%). Anchor weakest (seg2 +81.1 at 75%). True re-optimizing walk-forward still NOT run on any config — open item.

**Q5 — halt sweep: production halt=3 already optimal for OPTIMAL.**
OPTIMAL: halt3 +429.8 > halt5 +411.1 > halt6 +397.2 > halt4 +310.4 (cliff at 4 = single-halt fragility note). B3-OPT/S15: halt6 +385.9 > halt3 +355.4 but NON-MONOTONE (halt5 +301.8) → the halt6 gain is noise. Keep halt=3 everywhere.

**Q6 — persist2 vs persist5 head-to-head in-stack: persist2 wins.**
OPTIMAL persist5: 475t +332.7 vs persist2: 515t +429.8. Original choice survives; persist5 only helps in sparse configs (S6 mltf alone).

**Q7 — see Exp 27: refuted (all arms, both bases).**

**Q9 — B3 2026 monthly: diffuse drift, not a structural break.**
Jan–Sep: +5.8, +19.9, +20.4, −1.0, −0.2, +8.7, +0.8, +1.3, +0.6 — no catastrophic month; worst is −1.0R. Low activity (45 trades) with small edges = noise, not regime break.

**Q10 — S15/B3-OPT max-DD window: shallow grind, not a blowup.**
12.0R over **23 trades / 113 days** (anchor: 23.4R over 27 trades / 118.7 days). Comparable duration, half the depth. Not a 3-trade blip; fill-quality sensitivity is not elevated.

**Q8 — DESIGN CONSTRAINT (permanent, applies to all future experiments):**
> **"Slowness is a feature."** The mb50 trail-confirmation lag is protective. Four independent refutations now: ATR-chandelier, end_px window, conviction-mark ratchet (Exp 22), opposite-mark accelerator (Exp 27). ANY modification that makes exits earlier/tighter must argue against this prior before it earns a fine run. Losing trades dying at −1R is the cost of winners running; the autopsy numbers (post-halt re-entries +126R) depend on it.

**Updated decision menu after audit (fine NET):** v18 +163.7 | B3 +258.3 | B3+halt6 +278.1 | mltf +217.0 | mltf+persist5 +307.2 | **B3-OPT +307.2 (single-position, DD 12.0)** | mltf+mb1h10+chop55 +335.6 | their-OPTIMAL +348.0 (concurrency). B3-OPT now matches mltf+persist5 NET with half the DD and no concurrency complexity.

**Status: DONE — all 10 audit items answered with runs. Remaining open: true re-optimizing walk-forward (Q4 limitation).**

---

### Exp 30: TRUE ANCHORED WALK-FORWARD — the Q4 debt, PAID (v32)
**Design:** 72-combo grid (chop {52,55,58} x mb1h {10,20} x persist {0,2,5} x halt {3,6} x B3 {off,k8}, cd=10 fixed). Each combo runs once over the full period (coarse, identity-gated); trades sliced by entry-ts. 6 anchored steps (~6mo test windows); at each step the combo with best train NET (cost-adjusted) is frozen and applied to the unseen test window. Baselines: fixed B3-OPT+halt6 cd10 and fixed anchor, sliced identically. Caveat: halt-state carries across boundaries (same for all combos).

| Test window | Chosen combo (chop/mb/pers/halt/B3) | Train NET | Test NET | Fixed B3-OPT+halt6 | Anchor |
|---|---|---|---|---|---|
| 2023H2 | 58/10/0/3/on | +62.4 | +26.2 | +22.8 | +25.6 |
| 2024H1 | 58/10/0/3/on | +88.6 | +50.4 | +98.4 | +26.1 |
| 2024H2 | 55/10/0/3/on | +193.9 | +49.2 | +33.7 | +30.8 |
| 2025H1 | 55/10/0/3/on | +243.0 | **−10.6** | −16.2 | −17.2 |
| 2025H2 | 55/10/0/3/on | +232.4 | +58.7 | +67.2 | +35.0 |
| 2026 (9mo) | 55/10/0/3/on | +291.1 | +46.6 | +75.0 | +39.7 |

**WF total test NET: +220.4 | fixed B3-OPT+halt6: +280.9 | fixed anchor: +140.0**
**Verdict: PASS — three separate ways:**
1. **WF beats anchor +57%** out-of-sample (+220.4 vs +140.0) — the B3/mb1h10 edge is not a full-sample artifact.
2. **WF retains 78% of the fixed config** — for hindsight-chosen params to still beat adaptive re-selection is strong anti-overfit evidence.
3. **5/6 test windows positive**; the one negative window (2025H1) was negative for EVERY config — regime, not config.
4. The optimizer independently picked **B3 ON + mb1h10 in all 6 steps** — it converged on our family from raw data. (It preferred persist=0 over persist=2 — the two are close; noted.)
**Status: DONE — overfit question CLOSED. The fixed config survives true out-of-sample testing.**

---

### Exp 31: HTF-SIDE LEVER SWEEP — first experiments on the 1h side (v32)
The whole program had touched only LTF entry/trail. These levers live on the HTF (1h) side. Swept at two bases (anchor production, B3-OPT+halt6 cd10), coarse, identity-gated. Scripts: `exp31_htf_sweep.py`, `exp31b_lb_ext.py`, `exp31c_lb_fine.py`.

**Lever 1 — chop lookback `lb` (shipped 14): THE find. Monotone dose-response.**

| lb | anchor gross | B3-OPT+halt6 gross | B3-OPT DD | note |
|---|---|---|---|---|
| 10 | +196.3 | +365.9 | 11.5 | too twitchy |
| **14 (shipped)** | +211.7 | +392.0 | 14.0 | base |
| 30 | **+260.8** | +406.4 | 11.4 | anchor peak |
| 40 | +195.5 | +415.2 | **10.4** | |
| **50** | +190.0 | **+427.8** | 11.4 | **B3-OPT peak** |
| 60 | +201.6 | +369.0 | 11.0 | rolloff |

Slower chop-regime detection (30-50 bar lookback vs 14) = fewer whipsaw regime flips = better trades on BOTH bases. Plateau 30-50 on B3-OPT is broad (robust, not a spike).

**Lever 2 — `htf_rr` (1h window-close R-target, shipped 3.0): shipped value OPTIMAL.** All variants (2.0/2.5/3.5/4.0) worse on both bases. Robustness confirmation.
**Lever 3 — `ext_stop_r` (entry extension filter, shipped 1.5): shipped value OPTIMAL.** 1.0/1.25 much worse (over-filtering), 2.0 ≈ base. Robustness confirmation.

**Exp 31c — FINE VALIDATION of the lb find (B3-OPT+halt6 cd10):**

| Config | Trades | Gross | NET | WR | DD | H1 | H2 | per-year |
|---|---|---|---|---|---|---|---|---|
| lb=14 (base) | 250 | +391.5 | +335.5 | 34.4 | 14.0 | +238.2 | +153.3 | all pos |
| lb=40 | 233 | +414.8 | +364.7 | 36.1 | 10.4 | +248.8 | +166.0 | all pos |
| **lb=50** | **225** | **+427.4** | **+380.7** | **36.4** | **11.4** | +255.0 | +172.4 | **all pos** |

**lb=50 = NEW single-position NET KING: +380.7 net** (beats their-OPTIMAL's +348.0 while staying single-position, production cooldown, DD 11.4, WR 36.4%). Added to the final metrics doc.
**Status: DONE — lb=50 promoted to the decision menu as the new leader. Mechanism: slower regime flip = fewer whipsaw windows. Caveat: lb was selected on full-sample data (coarse) and fine-validated; the WF grid did not include lb — a future WF re-run with lb in the grid would make this airtight.**

---

### Exp 32: FINAL INTERACTION SWEEPS — closing the param story before freezing (v33)
Scripts: `exp32_final_tuning.py`, `exp32b_trail_fine.py`. Base: B3-OPT+halt6 cd10 (chop55, lb50, trail mb50 = +427.8 coarse / +380.7 net). Identity gate enforced (351t exact — note: the gate initially ran at chop61.8 due to a BASE-default clobber in the script; fixed and re-verified).

**A — chop x lb 2D interaction (coarse):** the surface is a ridge, no revolution. (55,50)=+427.8 and (52,60)=+428.0 are tied at the top; chop58/lb30=+408. Our pick sits on the ridge. **chop55 and lb50 are NOT redundant but their optimum is flat** — no interaction surprise.

**B — persist re-check at (52,60):** persist2 (+428.0) > persist0 (+398.3) > persist5 (+316.1). **persist=2 confirmed at the new operating point** — the WF optimizer's persist=0 preference was an lb=14-era artifact; at lb=50 the hysteresis earns its keep.

**C — LTF trail-mb re-check (Exp 11's decoupling, revisited at the new stack):**
| trail-mb | coarse @ (52,60) | note |
|---|---|---|
| 50 (shipped) | +428.0 | base |
| **65** | **+447.8** | local peak |
| 80 | +418.8 | rolloff |

**Fine validation:**
| Config | Trades | Gross | NET | WR | DD | H1 | H2 | per-year |
|---|---|---|---|---|---|---|---|---|
| (55,50,trail50) = current pick | 225 | +427.4 | **+380.7** | 36.4 | 11.4 | +255.0 | +172.4 | all pos |
| (55,50,trail65) | 217 | +404.0 | +357.6 | 34.6 | 11.4 | +290.5 | +113.5 | all pos |
| **(52,60,trail65)** | **228** | **+447.8** | **+400.4** | 36.0 | 13.1 | +315.6 | +132.2 | all pos |

**Reading (important):** (52,60,trail65) is the new paper king (+400.4 net) with ZERO coarse-to-fine drift — but it changes **three parameters at once** vs the WF-validated family (chop 52, lb 60, trail65) and carries two red flags: (1) 2025 is its weakest year (+41.1 vs our pick's +72.5) — more front-loaded than the current pick; (2) trail65's gain *evaporates* at (55,50) (+357.6), meaning it only pays in the slower-regime corner — a real interaction, but also exactly the shape curve-fitting takes. The current pick (55,50,trail50) is the conservative, plateau-dwelling choice; (52,60,trail65) is the aggressive one. **Decision deferred to user per process.**
**Status: DONE — param story complete. Every lever now swept: entry (b3_k, mode), regime (chop, lb, persist), windows (mb1h, htf_rr, ext), risk (halt), cadence (cd), trail (mb, via split-mb machinery). Remaining validation: WF grid extension with lb+trail65 (optional).**

---

### Exp 33: VERIFY the other lane's updated menu — one row WRONG, the rest confirmed (v34)
**Their published menu claims (EXPERIMENT_RESULTS.md §16):** config 2 "B3-OPT lb14 halt3 cd10 = 215t / +350.9 net / DD 9.6 / NET-DD 36.5" AND "B3-OPT lb50 halt3 cd10 = IDENTICAL numbers". Neither config had been run in our lane.

**Our verification (identity-gated, fine fills, production base, script `exp33_verify_halt3.py`):**

| Config | Trades | NET | DD | DD dur | H1 | H2 | both-halves |
|---|---|---|---|---|---|---|---|
| B3-OPT halt3 cd10 lb14 | 222 | **+262.6** | 12.1 | 15t/70d | +188.2 | +123.2 | PASS |
| B3-OPT halt3 cd10 lb50 | 213 | **+310.1** | 10.0 | 14t/70d | +226.7 | +130.7 | PASS |
| (ref) B3-OPT lb50 **halt6** cd10 | 225 | +380.7 | 11.4 | 25t/113d | +255.0 | +172.4 | PASS |

**Findings:**
1. **Their config-2 row is WRONG on the shipped engine.** Claimed 215t/+350.9/DD 9.6 for both lb14 and lb50 halt3. Actual: lb14 +262.6 (DD 12.1), lb50 +310.1 (DD 10.0) — and the two trade lists are **NOT identical (166 differing trades)**, so the "identical" presentation is impossible. They should re-check their harness for this variant (their other rows all match us to the decimal — this one looks like a copy/paste or a variant mislabel on their side).
2. **halt6 vs halt3 at lb50: +380.7 vs +310.1 — halt6 wins by +70.6R net.** The halt6 upgrade is even more valuable at lb50 than at lb14.
3. **The "400ish" number is REAL and verified by both lanes:** (52,60,trail65) = 228t / +400.4 net / DD 13.1 — zero coarse-to-fine drift on our side, exact match on theirs. It remains the aggressive 3-knob variant, front-loaded (their verdict "weaker", ours "overfit risk flagged"), no WF yet.
4. **Their lb50 walk-forward extension (test_wf_lb50.py): "lb=50 beats lb=14 at every test split, CI entirely above zero"** — consistent with every lb comparison we've run; a positive cross-check that closes the WF-with-lb debt from their side.
5. All other menu rows (anchor, OPTIMAL, B3-OPT cd0, halt6 lb50, (52,60,trail65)) match our numbers exactly — the two lanes remain in full agreement except config 2.
**Status: DONE — menu corrected on our side: the true lowest-DD row is B3-OPT lb50 halt3 (+310.1 / DD 10.0 / NET-DD 31), and the leader is still B3-OPT lb50 halt6 (+380.7 / DD 11.4).**

---

### Exp 34/35: 🚨 B3 STALE-FILL BUG — every B3 number in BOTH lanes was inflated; caught by the live-feasibility audit (v35)

**⚠️ ALL PRE-FIX B3 RESULTS IN THIS DOC ARE SUPERSEDED. The non-B3 results (anchor, OPTIMAL family, mltf family) are unaffected — they fill at the signal-bar close, which is executable live (fill drift measured: median 0.000%).**

**Root cause (found by exp34 late-entry repricing):** the B3 relocation patch set `i=_jj` (trigger bar) but the engine had already captured `entry=float(candles_ltf[i]["close"])` from the **signal bar** — up to 8 bars BEFORE the actual entry moment. On breakouts the signal-bar close is far below (longs) / above (shorts) the trigger price, so every B3 trade got a systematically favorable stale fill. Example trade: recorded entry 21303.5, executable price at the trigger close was 21486 — an instant ~182-pt gift, R recorded +29.0R.

**Detection:** exp34's same-instant repricing (fill at next bar open == trigger close instant) should have equaled base exactly; instead it showed +63.0 vs +301.9 — the mismatch exposed the bug. (A first version of the test ALSO had a bug — a 3R winner cap that faked a collapse — caught and fixed before drawing conclusions.)

**Fix:** one line in the harness B3 patch: re-capture `entry=float(candles_ltf[i]["close"])` AFTER relocation; SL/risk/target re-base automatically (ATR from trigger bar). Identity gate unaffected (b3_k=0 → no-op; 351t exact verified post-fix).

**Post-fix self-validation (exp34):** same-instant repricing now equals base EXACTLY (+85.9 == +85.9; +146.1 == +146.1; fill drift median 0.000%). Slippage ×10 costs −11.8R (fine). 15-min-late execution: king +69.9 (−16R, still positive) — automation required but tolerant. Bootstrap: king CI [−0.02, +0.86] (P>0 = 96.8% — NOT 95%-significant); AGGR CI [+0.15, +1.18] (99.6%).

**Exp 35 re-sweep (fine, funding-inclusive, post-fix) — the honest B3 family:**

| Config (post-fix) | Trades | NET | npt | WR | PF | DD | per-year |
|---|---|---|---|---|---|---|---|
| their-OPTIMAL (no B3, ref) | 515 | **+322.5** | +0.626 | 28.0 | 2.33 | 23.3 | all pos |
| **B3 k4 h3 lb14 p0 (best honest B3)** | 202 | **+109.1** | +0.540 | 34.7 | 2.32 | 9.4 | all pos |
| B3 k4 h3 lb50 p2 | 184 | +96.6 | +0.525 | 34.2 | 2.25 | 9.1 | all pos |
| B3-OPT lb50 halt6 (was "king" +365.4) | 217 | **+85.9** | +0.396 | 32.3 | 2.01 | 11.0 | all pos |
| B3 k8 h6 lb50 p0 | 223 | +90.0 | +0.403 | 33.2 | 2.03 | 11.6 | all pos |
| B3-OPT lb50 halt6 cd0 | 224 | +79.0 | +0.353 | 31.7 | 1.92 | 11.0 | all pos |
| v18 anchor (ref, mb20) | 351 | +148.0 | +0.422 | 27.6 | 2.02 | 23.4 | all pos |

**The brutal conclusions:**
1. **Every B3 config post-fix (+70 to +109) underperforms the plain anchor (+148.0).** B3's entire measured edge was the fill bug. The idea "wait for close confirmation" — the user's own concept, the program's flagship — does not survive honest fills in this form.
2. **The parameter landscape flipped:** k4 now beats k8 (k8 was tuned to inflated fills); lb50 ≈ lb14; persist ≈ irrelevant. All B3-era sweep conclusions are void.
3. **The real leader is their-OPTIMAL (+322.5, no B3)** — with its known caveats (multi-position, cd0). Second: S9 (+312.2, mltf). The multi-LTF family was always honest — it never used B3.
4. **What survives of the whole program:** the anchor (+148.0) is real; the mltf/OPTIMAL improvements are real (+174.5 over anchor); lb/persist/trail/halt findings are void for B3 (untested on non-B3 stacks — lb especially was B3-specific: it HURT the anchor per the other lane's own verification).
5. Possible salvage (not run): B3 with a LIMIT order at the signal close level instead of market-at-trigger (the stale fill becomes a limit fill — some of those may genuinely execute as price retraces). That would be a new experiment with real live constraints (may never fill).
**Status: DONE — the program's biggest lesson: validate the fill before believing the trade.**

---

### Exp 36: Reconcile the other lane's audit — 2 claims confirmed EXACTLY, 1 REFUTED (v36)
Script: `exp36_reconcile.py` (fine fills, funding-inclusive).

**(a) anchor lb=30 fine: NET +196.3 — CONFIRMED, exact match with their claim.** 349t, gross +287.1, fees 73.6, funding 17.2, DD 23.6. **This is a NEW verified single-position leader: the shipped engine + ONE parameter (lb 14→30), no B3, no mltf, cd10 — +196.3 net vs anchor-lb14's +148.0 (+48.3 from the single lb change, fine-validated on both lanes).**
**(c) B3-OPT lb50 halt3 fine: NET +115.4 — CONFIRMED, exact match.** (Note: exp35's grid accidentally ran at chop58 — its halt3-lb50 row (+78.0) was chop58, not chop55. At chop55 the post-fix number is +115.4. Labeling bug in exp35, now documented.)
**(b) their "mltf cd=10: ZERO overlapping positions, identical to single" — REFUTED on our harness.** Measured concurrent positions: **mltf cd10 (mb20): max 5 open; S9 (mb10+chop55): max 4 open.** And mltf-cd10 (421t) != anchor (351t) — not identical. The concurrency caveat is NOT moot for cd10 — it applies to ALL mltf configs. Concurrency design (or caps) remains mandatory before live.

**Updated honest leaderboard (fine, funding-inclusive, post-fix):**
| # | Config | NET | DD | Position |
|---|---|---|---|---|
| 1 | their-OPTIMAL | +322.5 | 23.3 | multi (≤5), cd0 |
| 2 | S9 (mltf+mb1h10+chop55) | +312.2 | 38.2 | multi (≤4), cd10 |
| 3 | multi-LTF+persist5 | +287.5 | 33.4 | multi |
| 4 | OPTIMAL+halt6 | +273.7 | 31.5 | multi, cd0 |
| 5 | multi-LTF alone | +197.6 | 23.4 | multi (≤5), cd10 |
| **6** | **anchor lb30 (shipped + lb 14→30)** | **+196.3** | 23.6 | **single, cd10 — best no-mltf, no-B3** |
| 7 | anchor lb14 (production) | +148.0 | 23.4 | single |
| 8 | (52,60,trail65) | +146.1 | 13.9 | single |
| 9 | B3-OPT lb50 halt3 | +115.4 | 10.2 | single |
| 10 | B3-OPT lb50 halt6 | +112.5 | 12.2 | single |

**Remaining before final pick — ALL CLOSED 2026-09-24:**
- **(i) anchor-lb30 stress battery + per-year/both-halves — DONE** (`exp_closeout_battery.py`): lb30 w0 n=349 NET +170.5 WR 27.5% PF 1.59 PIN OK (pins re-baselined post-`ee574f9` trail-ordering fix, fine nets ~−26R). Per-year: 2023 −1.0 / 2024 +95.6 / 2025 +27.3 / 2026 +48.5 (all-years-positive FAIL — 2023 −1.0 ≈ breakeven not structural bleed). Both-halves PASS: H1 +69.0 / H2 +101.5. Cost stress PASS: ×1.5 +133.7 / ×2.0 +96.9 / ×3.0 +23.3.
- **(ii) concurrency-cap design for the mltf leaders — DONE**: offline N4 cap3 on their-OPTIMAL +4.3R / −1.5R DD → +326.8 NET / DD 21.8 (removes breakeven/worse 2+ overlaps). Path-true `exp_maxconc_path.py`: cap=5 FREE (champion/king dIS +1.1 / dOOS 0.0), cap=4 near-free, cap=2/3 cost real R, single no-op. **Design pick: offline cap3 + path-true exp_max_concurrent=5 as live risk limit.**
- **(iii) cd0 latency validation for OPTIMAL — DONE**: OPT-cd0 n=515 NET +296.7 — no latency collapse vs cd10.

The B3 limit-order salvage idea was tested 2026-09-24 — DEAD (multi dIS −160/−173; swingpause both-sides +8.5/+14.4 ≈ 2R/yr ≪ ship; see EXPERIMENT_LOG). B3 family fully closed.
**Status: DONE — all three remaining items closed 2026-09-24. Final pick ready.**

---

## D3 Cooldown Family — Swing Pause, Skip-Windows, Wage Gate

Three loss-reactive entry gates tested in the D3 family. All causal (decided at entry time from past data only).

### D3-1: Skip-Windows (`exp_skipwin`)
After a loss at time L, block entries while the covering HTF window is one of the first N windows OPENED after L. Theory: the same broken bias track produces bad re-entries.

| Config | Trades | NET R | DD | Verdict |
|---|---|---|---|---|
| skipwin1_multi_sw10 | 144 | −1.1 | 38.8 | **DEAD** |
| skipwin2_multi_sw10 | 105 | −26.1 | 34.2 | **DEAD** |
| skipwin1_single_sw10 | 138 | −4.3 | 40.0 | **DEAD** |

**Finding:** Window-skipping after losses destroys the edge. The next window in the same regime track is exactly where recovery trades live.

### D3-2: Skip-Windows after Halt (`exp_skipwin_halt`)
Same as skip-win but only triggered after a HALT (3 consecutive losses), not individual losses.

| Config | Trades | NET R | DD | Verdict |
|---|---|---|---|---|
| skipwinhalt_multi_sw10 | 323 | +102.6 | 20.1 | **DEAD** (−223R vs king) |
| skipwinhalt_single_sw10 | 276 | +71.8 | 27.0 | **DEAD** |

### D3-3: Swing Pause (`exp_swingpause`) — NEW BEST SINGLE
After a loss, block entries until a NEW 15m swing **formed AFTER** that loss confirms. This is a STRUCTURAL condition, not a timer.

**Implementation (from `test_experiments_craze.py`):**
```python
# Build confirmation timestamps from 15m swing chain
_sw_pairs = sorted((candle_ts_ltf[int(sw["confirmed_at_idx"])],
                     candle_ts_ltf[int(sw["seg"]["start_idx"])])
                    for sw in swings_ltf ...)
confs_ts = [p[0] for p in _sw_pairs]   # confirmation timestamps
pivs_ts  = [p[1] for p in _sw_pairs]   # pivot-start timestamps

# On loss:
if r_multiple < 0:
    last_loss_ts = int(exit_ts)

# At each entry candidate:
if exp_swingpause > 0 and last_loss_ts > 0:
    _si = bisect_right(confs_ts, candle_ts[i]) - 1
    if _si < 0 or pivs_ts[_si] <= last_loss_ts:
        continue  # no fresh structure since loss → skip
```

**What it checks:** Find the most recent confirmed 15m swing. If its pivot started BEFORE the last loss, skip — the market hasn't built a new leg yet. If its pivot started AFTER the loss, the structure is fresh → allow entry.

**Key property:** No loss = no block (zero impact on winning streaks). cd=0 + pause ≡ cd=8 + pause (174.7 vs 174.8) — the structural pause fully replaces the bar-cooldown timer.

| Config | Trades | NET R | DD | NET/DD | Verdict |
|---|---|---|---|---|---|
| swingpause_multi_sw10 | 443 | +231.0 | 19.8 | 11.7 | Hurts king (−94.8R) |
| **swingpause_single_sw10** | **357** | **+174.8** | **23.4** | **7.5** | **+37.1R / −5.8DD vs baseline** |
| swingpause_cd0_single_sw10 | 357 | +174.7 | 23.4 | 7.5 | cd=0 ≡ cd=8 |
| swingpause_single_sw20 | 338 | +120.0 | 34.1 | 3.5 | ~neutral on sw20 |

**Do NOT add swing-pause to the multi king** — overlapping runners need those entries.

---

## Wage Gate (`exp_wage_h`) — Window Age Filter

Skip entries inside HTF windows younger than N hours. Age = `signal_bar_ts − window_start_ts`.

**Theory:** Fresh windows often produce false breakouts. First-day LTF signals are discovery cost: the autopsy bucket `wage 0–24h` was 75t −11.9R.

**Implementation (from `test_experiments_craze.py`):**
```python
# Inside the window membership check:
if exp_wage_h > 0 and (bar_ts - s) / 3600.0 < exp_wage_h:
    continue  # window too young → skip
```

**Validation:** Plateau 10-16h, stack-independent, cross-chain transferable, walk-forward stable.

| Config | Trades | NET R | DD | NET/DD | Verdict |
|---|---|---|---|---|---|
| wage0 (no wait) | 500 | +325.8 | 17.8 | 18.3 | Baseline |
| **wage10** | **261** | **+282.9** | **14.7** | **19.2** | **Best risk-adjusted single** |
| wage12 | 246 | +270.8 | 15.3 | 17.7 | Plateau |
| wage16 | 231 | +265.2 | 15.8 | 16.8 | Plateau |
| wage24 | 196 | +223.1 | 19.8 | 11.3 | Old N5 (too aggressive) |

**Key:** wage_h on single helps (fewer, older, better trades → DD improves). wage_h on multi HURTS (blocks profitable entries in overlap coverage). See [EXP40C_EXP41_WAGE_EXT.md](EXP40C_EXP41_WAGE_EXT.md) for full matrix.

---

## sw10 / sw20 — 1h Swing Sensitivity

| Name | Parameter | What it means |
|---|---|---|
| `sw20` | `min_bars_1h=20` | Production default. Needs 20 consecutive 1h bars to confirm a swing. Fewer signals, slower flips. |
| `sw10` | `min_bars_1h=10` | Twitchier. Needs only 10 bars. More HTF windows, more entry signals, more trades. |

**Why it matters:** sw10 produces 500 trades vs sw20's 372 on the champion multi. The extra trades from faster 1h swings are net profitable (+325.8R vs +208.4R). On single configs, sw10 also wins but the gap is smaller.

Also known as `mb10`/`mb20` (min_bars) in some docs. Same thing.

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
- `backtest/docs/experiments_craze.md` — this doc
- `backtest/tests/loss_autopsy.py` — read-only trade study
- `backtest/tests/sweep_halt_mb1h.py` — halt + mb_1h sweeps
- `backtest/tests/test_experiments_craze.py` — identity-gated superset-patch harness
- `backtest/tests/test_b3_engine.py` — B3 experiment runner
- `backtest/tests/fine_validate_splitmb.py`, `fine_check_b3.py`, `fine_check_halt6.py` — fine-fill validators
- `backtest/tests/_diff_b3_fills.py` — fill audit (coarse vs fine exit diff)
- Commits: `c3749b1`, `e5a330f`, `425d400` (engine `backend/` untouched; other bot's files untouched)

**Baselines for next session:** v18 anchor 340t/+182.3R net fine AND **B3 potential base** 206t/+278.6R net fine (user-ruled; experiments report vs both). Best remaining candidate: halt=6 (+5.6R net, DD −35% — ruling pending, composable with B3). Next experiments: B3+halt=6 combo, Exp 18 3-Mark Judgment (mark stream verified), Exp 15 sweep-reclaim, fine per-month deep-dive of B3's 2026 shortfall.

---

## Cross-references: Other Lane Experiments

> The following experiments were run by the other lane (not CRAZE). Listed here
> for completeness; full records live in their own docs.

### Exp N5/N6: Wage Gate + ext_stop Matrix (other lane)
- **Full record:** [EXP40C_EXP41_WAGE_EXT.md](EXP40C_EXP41_WAGE_EXT.md)
- **Key findings:** w24 is base-dependent (hurts lb30 −11.3R, helps A4 +19.8R). ext2.5 adopted on lb30 (+34.8R) and OPT-cd10 (+32.0R). Anti-synergy: w0 → wide ext, w24 → tight ext. Never mix.
- **Status:** Validated rebuild confirmed coarse 4/4 + fine 5/5. N5 deleted-harness numbers non-authoritative.


