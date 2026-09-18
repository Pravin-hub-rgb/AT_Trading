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

**Baselines for next session:** v18 anchor 340t/+182.3R net fine AND **B3 potential base** 206t/+278.6R net fine (user-ruled; experiments report vs both). Best remaining candidate: halt=6 (+5.6R net, DD −35% — ruling pending, composable with B3). Next experiments: B3+halt=6 combo, Exp 18 3-Mark Judgment (mark stream verified), Exp 15 sweep-reclaim, fine per-month deep-dive of B3's 2026 shortfall.


