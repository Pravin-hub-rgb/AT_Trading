# ANCHOR BASIS AUDIT — D3 pre-live audit (2026-09-20)

Independent audit of the v18 base anchor (the foundation every experiment sits on).
Findings, fixes, and the exact reproduction matrix. Audit scripts kept in
`backtest/tests/exp_*_cline.py` for re-runs.

## 1. The two valid anchor bases (2x2 reproduction matrix)

| fills      | chop |  n | gross    | DD   | WR    | status |
|------------|------|----|----------|------|-------|--------|
| coarse 15m | 61.8 | 340 | +225.3R | 27.1 | 30.0% | identity-gate basis (test_experiments_craze) |
| coarse 15m | 58.0 | 351 | +211.7R | 23.4 | 27.6% | valid but unused |
| fine 1m    | 58.0 | 351 | +238.0R | 23.4 | 27.6% | **production basis** (all experiments, NET +148.0) |

- The old `_shipped_sw20` pin `{n:351, gross:225.3}` was an IMPOSSIBLE hybrid
  (n from fine+58, gross from coarse+61.8) and always FAILed. Split into
  `_shipped_coarse_618` and `_shipped_fine_58` (see experiment_registry.py).
- Fine fills change EXIT timing only — entry sets are identical between
  fine and coarse (verified: 0 entry-signature diffs).

## 2. Causality: CLEAN (no lookahead)

Truncation probe — truncate all data (chains rebuilt, fine data cut) at time T;
every pre-T trade must still exist with identical R:

| probe                        | cut 1 (2025-06) | cut 2 (2026-03) |
|------------------------------|-----------------|-----------------|
| anchor (shipped, BP, fine)   | 233/233 exact   | 307/307 exact   |
| champion multi sw10          | 318/318 exact   | 435/435 exact   |

Swing chains (15m mb50 + 1h mb20) and the signal stream are byte-identical on
the prefix between full-history and truncated data. C14 (closed-1h chop gate)
and C15 (+2700 knowable-instant window gate) verified present and effective.
v7_timecap walk: forward-sequential, cap entry-relative, SL-before-target
same-bar (conservative).

## 3. Trail ratchet — FIXED & ADOPTED (2026-09-20): condition + ordering

Two-part fix, both applied to `v18_streak_halt.py` (coarse AND fine loops):

1. **Condition fix**: the ratchet applies whenever the candidate is beyond the
   current stop — the old `cand < lo` guard DROPPED events whose activation bar
   had already traded through the new level (structural optimism; live cannot
   escape the dip).
2. **Ordering fix**: the ratchet applies BEFORE the SL check within each bar —
   the stop is armed at the activation instant (bar open) and the same bar is
   enforced against the new level. (The condition fix alone left a one-bar lag.)

**The entire champion optimism was exactly 2 trades** — t462 + t463, two
overlapping mltf shorts (2026-05-27/28) that both escaped ONE bounce on
**2026-05-28 23:15-23:16 IST** (down-swing origin 73588.90 confirmed 23:00;
breach mid-minute). Audit trail of t462's exit, each stage verified:

| engine state | exit | R | why |
|---|---|---|---|
| pre-fix (event dropped via 1m-range peek) | 2026-06-07 @ 61992.8 | +31.36 | needed the activation minute's FULL range to decide — un-implementable live |
| condition-only fix | 2026-05-28 23:16 @ 73656.5 | +4.887 | stop armed one bar late |
| **condition + ordering (final)** | **2026-05-28 23:15 @ 73588.90** | **+5.041** | armed at open, filled AT the level |

Design ruling tested and closed: "skip swings already breached at confirmation"
(strict open-based validity) was implemented and compared — **0 of 500 trades
differ** from the always-ratchet rule, because at every decision instant the
level was either valid (apply -> correct stop) or gapped (never occurs here).

Post-fix re-pin (all verified by re-run; pins exact in experiment_registry.py):

| run | pre-fix | post-fix (ADOPTED) | delta |
|-----------------|----------------------|--------------------|-------|
| anchor fine+58 | 351t +238.0 / +148.0 N | 351t +211.6 / +122.0 N | -26.5R |
| champion sw10 | 500t +486.3 / +366.1 N | 500t +445.2G / **+325.8 N** / DD 17.8 | -40.3R |
| champion sw20 | 487t / +232.6 N | 487t +322.7G / +208.4 N | -24.2R |
| single sw20 | 371t +104.0 N | 372t +180.5G / +90.1 N | -13.9R |
| single sw10 | 395t +95.9 N | 396t +178.3G / +82.0 N | -13.9R |
| baseline sw20 | 371t +148.2 N | 372t +212.8G / +122.3 N | -25.9R |
| baseline sw10 | 394t +163.6 N | 395t +233.0G / +137.7 N | -25.9R |

Note: the coarse+chop61.8 identity anchor (340t/+225.3R) is UNCHANGED by both
fixes — that trade set never hits the drop/ordering cases — so all historical
coarse-basis docs remain valid. Trade counts shifted by +1 on the
single/baseline configs (halt/cooldown sequencing cascade). DDs unchanged.

## 3b. 1h HTF side — no trailing, nothing to fix (verified 2026-09-20)

The HTF window walk (`v7_timecap.py`) is called by v18 with `trailing="off"` and
`breakeven_r=0.0` on all three tracks (flip/decisive/b2, v18 lines 94-96):
fixed SL at the swing pivot, fixed 3R target, 16-day cap — NO ratchet exists on
the 1h side. The v7 ratchet code (the same `cand < lo` pattern) is behind
`elif trailing=="swing"` and events are only built in that mode -> DEAD CODE in
this pipeline; the D3 bug is structurally impossible there. Same-bar ordering on
the 1h side is conservative (SL checked before the 3R target). Empirical proof:
the coarse identity anchor (340t/+225.3R, full 1h HTF walk) is byte-identical
before and after the engine fix.

NOTE: v7's dead trail block is deliberately left unfixed — v7 is shared by other
historical lanes that may pass trailing="swing"; touching it would silently
change those legacy numbers. Do not enable v7 trailing without auditing this.


## 3c. Robustness probes on the final champion (2026-09-20, post-fixes)

- **1m data gapless**: 1,945,711 fine bars, ZERO missing minutes, largest gap 0.
  The walk never jumps a hole; no gap-hidden SL risk.
- **Cost stress** (champion +445.2G): x1.5 fees = +277.8N; x2 = +229.8N;
  x3 = +133.8N; x3 fees + x3 funding = +86.9N. Breakeven ~4.4x assumed costs.
- **Concurrency cap** (greedy entry-order post-filter): cap5 = 499t +446.2R
  (BETTER than uncapped — cuts one bad overlap); cap4 +442.7; cap3 +434.0;
  cap2 +404.4; cap1 +293.2. Live can cap 4-5 positions at zero edge cost.
- **No stale trades**: outcomes = {sl:187, trail:313}; last trade closes
  2026-09-09, before data end (2026-09-13).

## 3d. Pattern family from the loss autopsy (2026-09-20)

Autopsy on the king + swingpause single (hour/weekday/kind/direction/bars):

- **Weekend bleed**: on the swingpause single, Sat = 37t **-16.1R @ 89.2% loss
  rate**, Sun = 40t **-14.6R @ 80.0%** — 77 trades for -30.7R. On the multi,
  ~neutral (110t for -1.9R).
- **Entry kinds**: on the swingpause single, B2 = 178t for **-0.6R** while FLIP
  carries everything (+260.7R). On the multi, B2 is +82.4R (keep it there).
- Longs dominate on both (multi: +339.5 long vs +105.7 short); shorts positive —
  not cut. Hour-of-day patterns look strong (19:00 worst) but are data-mining
  bait — not pursued.
- Bars-held profile confirms the trail-runner shape: trades <96 bars = -277R
  (multi), trades >=96 bars = +722R; top-10 trades = 74% of gross.

Experiments (7 configs, all pinned; references: king +325.8/17.8/18.3,
swingpause single +174.8/23.4/7.5):

| config | n | NET | DD | NET/DD | verdict |
|---|---|---|---|---|---|
| **nowknd_swingpause_single** | **294** | **+217.6** | **18.2** | **12.0** | **NEW BEST SINGLE** (+42.8R, -5.2DD vs swingpause single) |
| legskip2 multi | 269 | +267.3 | 17.2 | 15.5 | near-king quality at 46% fewer trades (minY +57 vs +102) |
| fliponly swingpause single | 237 | +179.7 | 21.9 | 8.2 | mild upgrade over swingpause single |
| wage24 multi | 362 | +243.9 | 23.1 | 10.6 | DEAD — young windows carry the edge (-82R) |
| nowknd multi | 400 | +307.8 | 17.1 | 17.9 | ~neutral on king (weekend bleed is a single-config effect) |
| fliponly multi | 285 | +242.7 | 24.3 | 10.0 | worse (B2 earns its keep on multi) |
| nowknd single (no pause) | 320 | +113.9 | 30.5 | 3.7 | WORSE — weekend skip only works ON TOP OF the swingpause |

### 3d-2. TIMEZONE ALIGNMENT of the weekend filter (2026-09-20) — user caught it

The CSV date strings are IST (ts are true UTC epochs; date = ts+5:30 — verified:
1m bar "2026-05-28 23:15" = gmtime 17:45 UTC; data starts 05:30 IST = UTC midnight).
So the first "weekend skip" skipped IST-Sat/Sun — NOT the true UTC weekend.
Dual-convention autopsy on the swingpause single:

| weekday | by IST date | by TRUE UTC |
|---|---|---|
| Sat | -16.1R @ 89.2% | **-23.9R @ 90.7%** |
| Sun | -14.6R @ 80.0% | **+51.7R @ 70.2%** (UTC Sun evening = IST Mon open, the best session) |

The bleed is a **UTC-SATURDAY** effect, not a generic weekend effect. Measured
(both lane variants consolidated: `utcsat_multi_sw10` / `utcsat_swingpause_single`):

| config | n | NET | DD | verdict |
|---|---|---|---|---|
| **utcsat_multi (UTC-Sat skip)** | **454** | **+359.0** | **14.8** | **NEW KING** (+33.2R, -3.0DD vs old king; NET-DD 24.3) |
| utc_wknd_swingpause single (UTC Sat+Sun) | 286 | +150.0 | 23.1 | worse — UTC Sun is profitable, keep it |
| utcsat_swingpause single (UTC-Sat only) | 325 | +166.3 | 23.3 | mild (-8.5 vs IST variant) |
| nowknd_swingpause single (IST Sat+Sun) | 294 | +217.6 | 18.2 | still best SINGLE (cascade effects differ per config) |

Lesson: on this dataset, ALWAYS derive calendar features from ts (UTC), never
from the IST date strings — an innocent-looking 5h30m offset flipped "weekend"
from a -31R filter into a +33R one on the multi.

Caveat: 7 configs tested against autopsy-derived patterns = multiple-comparison
risk. nowknd_swingpause_single needs a sw20/param-neighborhood validation before
it replaces the swingpause single as the default single config.

## 7. Cooldown-family experiments (2026-09-20) — swing-pause adopted for singles

New loss-reactive gates added to the patcher (all causal, decided at entry time):
`exp_skipwin` (skip the first N HTF windows opened after a loss),
`exp_skipwin_halt` (same but only after a HALT fires),
`exp_swingpause` (block entries until the most recent confirmed 15m swing has a
pivot AFTER the loss — i.e. fresh structure exists).

Results (fine/c58 basis, pins locked in registry; king = +325.8/17.8, baseline
single = +137.7/29.2):

| config | n | NET | DD | NET/DD | verdict |
|---|---|---|---|---|---|
| skipwin1 multi | 144 | -1.1 | 38.8 | — | DEAD (per-loss window skip amputates winners) |
| skipwin2 multi | 105 | -26.1 | 34.2 | — | DEAD |
| swingpause multi | 443 | +231.0 | 19.8 | 11.7 | hurts the king (-94.8R; overlapping runners need those entries) |
| skipwinhalt multi | 323 | +102.6 | 20.1 | 5.1 | DEAD (worse than halt3's own next-entry skip) |
| skipwinhalt single | 276 | +71.8 | 27.0 | 2.7 | DEAD |
| **swingpause single** | **357** | **+174.8** | **23.4** | **7.5** | **NEW best single config** (+37.1R, -5.8DD vs baseline; NET/DD 4.7->7.5) |
| swingpause cd0 single | 357 | +174.7 | 23.4 | 7.5 | pause fully SUBSUMES the bar-cooldown (cd8==cd0) |
| swingpause single sw20 | 338 | +120.0 | 34.1 | 3.5 | ~neutral (vs +122.3/37.3) |
| skipwin1 single | 138 | -4.3 | 40.0 | — | DEAD |

Conclusions:
1. Window-skipping after losses destroys the edge in every variant — the regime
   track's next window is exactly where the recovery trades live.
2. The structural pause ("no re-entry until a swing formed AFTER the loss
   confirms") is the right loss-reactive gate FOR SINGLE-POSITION configs:
   better R, better DD, and it replaces the bar-cooldown timer entirely (a
   cleaner rule to implement live). Do NOT add it to the multi king.
3. The king (+325.8/17.8) remains untouched and undefeated.


## 3e. Risk-width gate — DEAD, and the autopsy pitfall (2026-09-20)

Fine stop-width bins on the single autopsy: stops >=1.5% of price = 72t,
**-7.1R net**, big-win contribution +7.8R — passed the pre-registered cut rule.
Implemented `exp_risk_max_pct` and measured:

| config | autopsy predicted | actual |
|---|---|---|
| rmax15 single | ~+267 / low DD | **+91.7 / DD 38.1** |
| rmax10 single | ~+263 | +195.5 / DD 31.4 |
| rmax15 multi | ~+334 | +259.4 / DD 35.6 |

ALL worse than their references. Root cause: the trade sequence is
**path-dependent** — removing scattered mid-sequence trades reshuffles the
halt/cooldown/busy cascade and the entire downstream trade set changes. A
per-trade bucket autopsy cannot predict the system-level effect. Note the
contrast: the gates that WORKED (weekend skip, swing-pause) remove contiguous
blocks of activity on structural/regime conditions; the gates that FAIL
(B3, risk-width) cherry-pick individual trades scattered through the sequence.

Rule added to the playbook: no more per-trade feature filters in this system
unless validated by full-path re-run (which is what the registry pin run is).
The wide stops are also functionally "survivors" — a far stop is hard to hit,
so cutting them re-tightens the book and halts fire more (WR fell 25.8->23.2,
streak 14->15, DD blew out).


### 3f. Chop math parity + Efficiency Ratio thesis (2026-09-20)

**Chop parity: PASS.** Independent reimplementation of the Choppiness Index
(100*log10(sumTR/(Hi-Lo))/log10(14), TR=max(H-L,|H-PC|,|L-PC|)) vs the engine's
`_chop_series_1h`: max abs diff = 0.0 across all 32,429 1h bars. The engine's
chop is a textbook-correct implementation; the C14 closed-candle mapping on top
was already audited. Nothing to fix.

**Efficiency Ratio thesis: REJECTED by the pre-registered rule.** ER24
(Kaufman: |net displacement| / path length, 1h closes, C14 instant) bucketed at
every champion + swingpause-single entry: NO bucket is net-negative on either
config, and the low-ER buckets contain +105R of real >=2R winners on the
single. Cutting them fails "spare the winners" (the B3 / risk-width trap).
On the multi ER24 is flat noise — the edge is structure-break + trail, which
works IN chop; that is the flip-window design and it does not need 1h trend.
No `exp_er` gate added to the engine (dead kwargs are clutter); the bucket
table lives in this doc as the tombstone for the ER road.

**15m ER20 (other-bot F6) — ALSO REJECTED, path-true (2026-09-23).** Their
claim (ER<0.10 → n=93 / −17.7R) does not reproduce on our champion trade-list:
our ER<0.10 bucket is **n=99 / +107.3R / bigWin +162.5** (2nd-best bucket;
best is 0.30–0.50 at +277R). Temporary `exp_er_min`/`exp_er_max` patch +
`exp_causal_autopsy_path.py`:

| variant | dIS | dOOS | swingpause dIS | king dIS |
|---|---|---|---|---|
| er_min=0.10 | **−199.2** | −35.1 | −107.8 | −201.9 |
| band 0.10–0.50 | −182.6 | −49.7 | −118.4 | −205.1 |
| F1 runmag=2.0 causal | −108.2 | −32.0 | +0.2 raw (leak) | — |
| F7 risk_max=2.0 | −24.7 | −48.4 | −6.9 | — |

Both ER roads (1h/24 and 15m/20) are dead. ER kwargs reverted from the
patcher (clutter). Harness kept: `backtest/tests/exp_causal_autopsy_path.py`.

**Live-snapshot runmag gate — LAST OPEN SALVAGE PATH, ALSO REJECTED (2026-09-23).**
Trade-list under causal live labels: run mag 2%+ = −9.9R / bigW 2 (passes the
playbook rule; every other live bucket is positive — live OPPOSED +147.7,
live age 51+ +136.7). Implemented `exp_max_live_runmag` + precomputed
`replay_live_state` start_idx (`exp_alignment_live_gate_path.py`):

| config | live_runmag=2.0 dIS/dOOS | 3.0 | 4.0 | batch+causal ref |
|---|---|---|---|---|
| champion | **−24.2 / −36.4** | −6.1 / −3.6 | −3.0 / −4.9 | −108 / −32 |
| swingpause single | −6.0 / −3.6 | +2.3 / −13.5 | −4.7 / +1.2 | −18.5 / +0.2 |
| utcsat king | −41.2 / −7.0 | −7.5 / **+21.4** | −3.4 / +11.6 | −123.6 / −9.6 |

2.0 hurts both sides on champion. 3.0/4.0 are noise (|d| < 8 with mixed signs).
King 3.0's OOS +21 fails the both-sides rule (IS −7.5). The cut saves ~10R of
losers on the trade-list but cascades −24R through halt/cooldown — same path
trap as §3e. **No gate ships. The live-snapshot methodology (replay_live_state
+ path-true harness) is the salvage; the gates are not.** Kwargs reverted from
the patcher. Harness kept: `backtest/tests/exp_alignment_live_gate_path.py`.

Meta-note: after the risk-width failure (section 3e), bucket autopsies are
HYPOTHESIS GENERATION ONLY — no gate goes into the engine without a full-path
re-run, and no full-path run happens unless the bucket passes the rule
(net-negative + negligible big-win contribution). ER failed at the first gate,
which is the cheap way to die. Live-runmag passed the trade-list rule and still
failed full-path — the playbook holds.


### 3f-2. Old-engine ports — 5 lineage candidates path-true (2026-09-23)

Five never-tested ideas recovered from the version lineage map (v6 ADX, E5
session, 4h cousin, v9 conditional cap, v2 flip-break). All wired into the
craze patcher as default-off kwargs, identity-gated (340t/+225.3 IDENTICAL),
then run both-sides (IS champion/king/swingpause + OOS 2021-22) via
`backtest/tests/exp_oldengines_path.py`. 4h swings synthesized from 1h
(ts//14400): IS 8108 bars/392 swings, OOS 4379/240.

| candidate | flag(s) | champion dIS/dOOS | king dIS/dOOS | swingpause dIS/dOOS | verdict |
|---|---|---|---|---|---|
| ADX≥20/25/30 (15m) | exp_adx_min | −137..−240 / −48..−113 | −162..−274 / −45..−102 | −60..−120 / +2..+23 | **DEAD** (fails both-sides every base) |
| only/skip 16-20 UTC | exp_only/skip_hour | −132..−346 / −38..−115 | −157..−346 / −27..−62 | −74..−146 / −10..+33 | **DEAD** (extends curfew/hour-of-day family) |
| 4h dir confirm | exp_htf4_confirm | −162 / −51 | −194 / −25 | −66 / +29 | **DEAD** (IS always bleeds) |
| v9 cap 2R→30d | exp_htf_extend_r=2 | −6.2 / −3.1 | −21.3 / +7.7 | −13.9 / +5.3 | **DEAD** (noise, mixed signs) |
| flip-break (LTF close vs pe) | exp_flip_break | −189 / +18 | −218 / +17 | **+7.6 / +8.3** | MARGINAL on single only; DEAD on multi |

flip-break is the only both-sides pass (swingpause NET +29.6/+16.2) but ~8R/yr
multi starves without FLIP overlaps. This is a marginal research result, not a universal pass/fail threshold. Flag KEPT
for stack research. ADX/session/htf4/v9 kwargs REVERTED (dead = clutter).
Harness kept: `backtest/tests/exp_oldengines_path.py`.


### 3f-3. Idea A — HMM regime router path-true (2026-09-23)

New engine modes `hmm` / `hmm_inv` (like entropy/fd/session): 2-state Gaussian
HMM on 1h log-returns, Baum-Welch on first 45% only, causal forward-filter the
full series, route P(range)×100 > chop_thresh → B2 else FLIP. Identity gate
green post-add (340t/+225.3 IDENTICAL — modes gated on `mode in ("hmm","hmm_inv")`).
Both-sides via `backtest/tests/exp_hmm_path.py` (champion/king/swingpause × IS+OOS),
chop_thresh 50/55/58/61 + inv.

| config | best hmm dIS/dOOS (NET) | hmm_inv | verdict |
|---|---|---|---|
| champion_multi_sw10 | ct=61: +3.6 / −2.4 (NET +329.4/+67.7) | −232 / −62 | **DEAD** (OOS down) |
| utcsat_multi_sw10 | ct=61: +10.7 / −1.6 (NET +369.6/+58.6) | −260 / −45 | **DEAD** (OOS down) |
| swingpause single | ct=50: +5.0 / −1.6 | −92 / −29 | **DEAD** (OOS down; ct≥55 both sides down) |

Trade counts shift ±10–30t so the router is active; it just never improves OOS.
hmm_inv catastrophic as expected (confirms range→B2 polarity is right).
Same class as entropy/fd: classifier is structurally sound, no true-OOS edge.
mode branches KEPT in engine for reference (matches entropy/fd precedent).


### 3f-4. Param sweep + in-engine caps + Idea E + stack (2026-09-23)

Four follow-ons after §3f-3, all both-sides via dedicated harnesses.

**atr_high_thresh** (`exp_atrhigh_sweep.py`): grid 0.40–0.90 on mode=atr_high
kings. Best both-sides = noise (champion 0.70 +0/+4.4 NET; swingpause 0.55
+3.4/+5.3). 0.40 opens OOS +47..+69 but kills IS −70..−95 (era flip).
**0.65 confirmed near-optimal. Param family closed.**

**exp_max_concurrent** (`exp_maxconc_path.py`): position cap. ~~in-engine~~ — **it is not in any engine.**
cap=5 multi = **FREE** (champion/king dIS +1.1 / dOOS 0.0). cap=4 near-free
(champion OOS −6.2). cap=2/3 cost real R. single = no-op.
**~~ALIVE deployment enabler~~ — path-true validates offline audit 3c; use
cap=5 for live risk. **← RETRACTED 2026-10-01, WRONG. See the correction below.**

**CORRECTION 2026-10-01.** This recommended a code path that does not exist.
`exp_max_concurrent` has **zero occurrences under backend/src** — v18 and v19 both
return 0 hits. It exists only as a source patch injected by
`test_experiments_craze.py:106` (default) and `:760-763` (enforcement). At the
default of 0 the injected block is a silent no-op, so every experiment that did
not set the flag ran uncapped and looked correct. Nothing could fail, so nothing
was ever validated.

**The cap logic itself is correct, and the numbers stand as research results.**
Its enforcement counts open trades at `candle_ts[i]`, which is the same clock as
`entry_ts` (`v19_champion.py:834`); the suspected `+900` unit mismatch does not
exist, because `ts + 900` in this repo is the *HTF-close alignment* operation
(`v19_champion.py:320,346,354`), a different question. P117's independent overlap
audit agrees exactly with every cap — cap=1 → observed max 1, cap=4 → 4,
cap=5 → 5 — which would be impossible if the count were off by a bar.

Re-derived on the leg book by P117: cap5 dNet **+1.1R IS / +0.0R OOS**,
reproducing this grid. The OOS arm is partly vacuous: max concurrency on the leg
OOS book is 5, so cap=6 cannot bind there. Sweep script: `exp_engine_knobs.py`.

**Idea E regime-transition skip** (`exp_regime_skip.py`): exp_regime_skip =
|Δchop over 4×15m| > 5..20. Best both-sides: champion >10 +30.9/+2.3 NET;
swingpause >10 +4.8/+6.2. King never both-sides at magnitude.
**MARGINAL / MIXED** (~8R/yr; no automatic adoption gate). Flag KEPT for stack research.

**Stack flip×regime** (`exp_stack_marginals.py`): exp_flip_break=1 +
exp_regime_skip=8/10/12. swingpause STACK flip+reg8 = **+38.7/+27.7 BOTH**
(best stack; turns swingpause OOS NET −17.0 → +10.7). champion/king: flip-break
still kills IS (−78..−218). **MARGINAL / MIXED** (~10R/yr; no automatic adoption gate). Recipe kept for research.

Harnesses: `exp_atrhigh_sweep.py`, `exp_maxconc_path.py`, `exp_regime_skip.py`,
`exp_stack_marginals.py`.


### 3f-5. Soft multi-mode ensemble — Idea D (2026-09-23)

Modes added to engine (signature + branches, identity green):
- `mode=soft_chop` — chop in (ct±soft_width) → decisive(B2+FLIP); above → B2; below → FLIP
- `mode=soft_atr` — production atr_high softened; band falls back to chop
- `mode=soft_ensemble` — mean ramp(chop, ATR%·100, 100−entropy, FD) as range score 0–100;
  high→B2, low→FLIP, band→decisive. `soft_width` default 4.0 (0 = hard).

Harness `exp_soft_ensemble.py`: widths soft_chop 0/2/4/6/8, soft_atr 0.05–0.20,
soft_ens 4/8/12/16 × champion/king/swingpause × IS+OOS.

**Result: DEAD / not supported as a universal improvement.**
- champion: no both-sides pass (soft_chop w=6 +8.9/−1.8; all soft_atr/ens OOS down)
- king: max both-sides soft_chop w=2 +0/+1.6 (noise); soft_atr OOS −3..−13
- swingpause: only both-sides soft_ens w=12 **+14.3/+3.4 NET**; soft_atr w=0.20 IS +32 but OOS −11.4 fails

Wide bands open OOS trades but kill IS on multi (−97..−139). Softening the
production atr_high path only degrades OOS. The binary switch at the right
threshold already captures the regime edge — smoothing loses it (same class
as HMM/entropy/fd: classifier sophistication ≠ edge).

**Verdict:** modes KEPT in engine for reference; does not ship.


### 3f-6. Pivot-break trail (fix/more ideas.md L24-36) — 2026-09-23

`exp_pivot_trail=1`: instead of swing-start ratchet, trail to the intervening
extreme when a pivot breaks — LONG: pivot = up-swing end, on break SL = min low
since last break/entry; SHORT mirror (pivot = down-swing end, max high).

Wired in craze: precompute break bars once (`_pb_long`/`_pb_short`) before the
trade loop; per-trade segment chain from entry. Identity green at default 0.

**Result: DEAD.**
- champion: n 500→515, dIS **−159**, dOOS **−70** (NET +325.8/+70.1 → +169.8/−2.5)
- king: dIS −154, dOOS −49
- swingpause: dIS −84, dOOS +37 (mixed, fails both-sides)
- trail_max_dist=1.0/0.6 stacks: **no-op** — pivot path never enters the
  swing-start append block the filter guards
- +regime>10: still −150+ IS on multi

Mechanics: intervening extreme ≈ initial risk zone → no breakeven protection,
or ratchets into a noise low that gets wicked. Swing-start trail only advances
when a NEW same-dir swing confirms (structure complete), which is strictly
better timing. Harness `exp_pivot_trail.py`.


### 3f-7. True re-optimizing walk-forward (WFO) — 2026-09-23

Backlog close: every prior WF was fixed-config stability. `exp_wfo_true.py`
re-PICKS knobs on train, freezes for test (exp30 pattern, fine fills, net_r).

- Grid: 48 combos = mode(atr_high 0.60/0.65/0.70 | b2_vs_flip_chop 55/58/61.8)
  × ext 1.5/3.0 × cd 0/8 × persist 0/7 × halt 3, champion base, full IS once
- Steps: expanding year — train 2023→test 2024, 2023-24→2025, 2023-25→2026
- Baselines same test slices: fixed champion registry params; oracle = single
  best combo on full IS (in-sample upper bound)

**Result: ALIVE — WFO holds.**
| | test NET |
|---|---|
| WF (re-pick each step) | **+247.8** |
| Fixed champion on same windows | +238.9 |
| Oracle (full-IS best fixed) | +258.8 |

Retention vs fixed champion **104%**; WFO/oracle (selection efficiency) **96%**.
Chosen combo identical all 3 steps: b2_vs_flip_chop / chop=61.8 / ext=3 / cd=8
/ persist=0 (full-IS NET +350.1 vs champ +325.8-class). Selection is stable —
not flailing across years. Protects the +30R/yr claim: re-optimizing does not
uncover a better path that fixed params are missing, and does not collapse OOS.

Caveat: engine halt-state carries across boundaries in full-period runs (same
for all combos; identical to exp30 convention). JSON: `_exp_wfo_true.json`.


### 3f-8. ETH/BTC ratio momentum skip — Idea G (2026-09-23)

`exp_eth_skip` / `exp_eth_lb` / `exp_eth_closes` wired into craze (kwargs +
path-true precompute `_eth_mom[bar]` from ETH 1h closes aligned to candles_htf
by index; gate at filter-append: skip if mom > thresh). ETH fetched from
Binance 2021-01→present via `scripts/download_eth.py` (START_IST changed) so
OOS 2021-22 has full ETH coverage (zeros=0 both sides).

Harness `exp_eth_ratio.py`: mom24/48/72 × thr 5/8/12% × champion/king/swingpause × IS+OOS.

**Result: DEAD / noise.**
- champion: best both-sides mom24>8% **dNET +1.2/+8.0** (≈ 2R/yr); mom24>5% dOOS +19 but dIS −9 fails
- king: mom24>8% +1.2/+6.0; mom24>5% dOOS +14 but dIS −2
- swingpause: mom24>5% dOOS +11.9 but dIS −7.1; 8%+ OOS flat-down

Nothing clears +30R/yr. Correlation/cross-asset filter family closed for
ETH/BTC ratio. Flag KEPT for reference. Identity green at default 0.


### 3f-9. GARCH regime router — Idea F (2026-09-23)

`mode=garch` / `garch_inv` added to engine: `_garch_regime_1h` freezes
ω/α/β from train prefix (45%), recursive σ² = ω + αε² + βσ² on 1h log-returns,
range-score = 100×(1 − trailing rank of predicted vol over lb=96), mapped to
LTF bars. Router: score > chop_thresh → B2 else FLIP (inv opposite).

Harness `exp_garch_path.py`: ct 50/55/58/61 + inv × champion/king/swingpause × IS+OOS.

**Result: DEAD.**
- champion: best ct=61 dNET **−54.4/−34.7** (all ct negative both sides)
- king: best ct=61 dNET **−32.8/−11.5** (all ct negative both sides)
- swingpause: OOS only +3.4..+14.9 at ct=58/61/inv but dIS −75..−143 fails hard
- garch_inv catastrophic as expected

Same class as HMM/entropy/fd: sophisticated vol classifier ≠ edge. Predicted-
vol quiet/trend split does not beat production atr_high/b2_vs_flip on OOS.
Mode branches KEPT for reference (matches HMM/entropy precedent). Identity green.


### 3f-10. B3 structure confirmation — both-sides path-true (2026-09-23)

`b3_k` already in craze (kwargs b3_k / b3_mode): after B2/flip signal at bar i,
scan bars i+1..i+b3_k for close/wick beyond signal-bar extreme; entry relocates
to trigger bar; timeout dies. Previously tested IS-only on anchor (206t +278.6R
fine absolute) and deferred by user.

Harness `exp_b3_path.py`: k=4/8/12 × close/wick × champion/king/swingpause × IS+OOS.

**Result: DEAD.**
- champion: all k/mode dIS **−247..−287** / dOOS −50..−77 (n 500→107-169 OOS)
- king: all dIS **−257..−283** / dOOS −27..−51
- swingpause: OOS +13..+39 (both-sides sign pass at k=8) but dIS **−67..−152** fails hard; best OOS +39.0 ≈ 10R/yr ≪ +30R/yr ship

Confirmation delay destroys coverage and most of the edge on multi (needs FLIP
overlaps). Old absolute numbers were not delta vs current production bases.
First-swing entries remain the edge (v1 family already proved skip-first dies).
Does not ship. Flag KEPT for reference. Identity green.


### 3g. Sequential one-pass causal study — HARNESS ARTIFACT RESOLVED, NUMBERS CERTIFIED (2026-09-20, corrected 2026-09-21)

`exp_onepass_cline.py` implements the C10 one-pass spec for champion_multi_sw10:
causal 30d/20d slices (L3 consistent), chains rebuilt fresh, L1 open-window-as-
active-bias patch, L4 +2-bar discovery pad, extra-entry capture, and a
chronological sequential state machine (cooldown 8 + halt3) for the live-expected
number.

**Initial result: 0/490 reproduction.** Correctly diagnosed as a signal-collection
artifact — NOT a live gap. The harness rebuilds swing chains from causal slices
(cut at entry+2bars). The batch engine attaches B2/FLIP marks to swings AFTER
declaration (~5-19h after the mark bar). At the causal cut, the generating swing
hasn't declared yet, so the mark is invisible in the rebuilt chain. But the mark
itself is a price-vs-known-level fact (close beyond the prev confirmed swing's
end), computable at every candle close without any declaration. The live engine
computes marks in real-time as price breaks known levels — it doesn't need the
swing to "declare."

**Corrected diagnosis (150/150 trace + exit-capped check on 857 trades):**
- Every entry fires BEFORE its own swing's FS confirmation (pre-FS marks).
- Every entry is knowable live at candle close: prev swing's FS confirms →
  level is final → price breaks level → mark fires → entry at close.
- `filter_pre_fs=True` correctly gates: rejects marks before prev swing's FS.
  0 violations of the tradability rule on both configs.
- Exit-capped check: 147 multi / 101 single entries had post-entry-extreme
  stops (SL finalized after entry in batch). Of those, 0 survived in batch
  where live's tighter stop would have killed them. R divergence: +0.0R.
- Stop-level differences change position size in dollars, never in R — every
  one of those trades died at exactly -1.0R regardless of stop width.

**Conclusion: the batch +325.8 / +359.0 numbers ARE the live numbers.** The
one-pass v2 (causal mark collector) would give a precise live-expected number,
but the batch is certified as the floor — live may be higher due to earlier
mark visibility and sequential extras.

Playbook lesson: the "0/490 blocker" was a declaration-lag artifact of how the
batch engine discovers signals (retroactive attachment to declared swings), not
a structural live gap. For price-vs-level signals, marks are pure candle-close
facts. Never re-diagnose live-faithfulness from chain-rebuild harness results
without tracing the actual signal rule candle-by-candle.


### 3h. Entry-quality autopsy — FILTERS DEAD, SYSTEM EDGE IS TRAIL (2026-09-21)

Phase 1: measured 7 entry-time metrics (risk%, swing quality, entry depth,
candle strength, swing age, same-dir count, hour-of-day) across 487 champion
trades. Best separators: risk% (tight = big winners), swing age (fresh = best),
FLIP >> B2. But all separations small relative to R distribution.

Phase 2: implemented 3 patcher gates (`exp_entry_candle_min`, `exp_entry_swing_age_max`,
`exp_entry_skip_b2_doji`) and tested 5 configs on both king bases. **All 5 lost R
vs the kings.** Every entry-quality filter worsened NET and drawdown.

| filter | vs king multi | vs king single |
|--------|--------------|----------------|
| skip B2+doji | -23.1R, DD+3.7 | -59.1R, DD+16.5 |
| skip swing age>50 | -58.6R, DD+2.2 | -46.5R, DD+12.1 |
| combined B2+age | -53.4R, DD+1.0 | — |

Conclusion: the system's edge is the trail mechanism (quick losers, run winners)
and the swing pause (reactive). Entry quality is noise — the trail handles bad
entries naturally by cutting at -1R. Preventive entry gating is counterproductive.
Multiple-comparisons budget spent on this family; no further entry-quality
experiments recommended.


### 3i. FINAL CERTIFICATION — BACKTEST PHASE COMPLETE (2026-09-21)

**Certified live-implementable configs:**

| config | n | NET | DD | WR | NET-DD | status |
|--------|---|-----|----|----|--------|--------|
| utcsat_multi_sw10 | 454 | +359.0R | 14.8 | 30.8% | 24.3 | optimistic king |
| champion_multi_sw10 | 500 | +325.8R | 17.8 | 30.0% | 18.3 | conservative king |
| nowknd_swingpause_single_sw10 | 294 | +217.6R | 18.2 | 29.6% | 12.0 | best single |

**Certification checklist:**
- [x] Trail ratchet: condition + ordering FIXED (§3)
- [x] Partial R formula: FIXED (§3)
- [x] Causality: CLEAN (truncation probes, §2)
- [x] Identity gate: patched-off == shipped (340t/+225.3R IDENTICAL)
- [x] Cost stress test: breakeven at 4.4x costs; tripled costs still +87R
- [x] Prev-FS rule: 0 violations on 857 trades (§3g)
- [x] Exit-capped check: 0 R divergence (§3g)
- [x] Entry-quality filters: ALL DEAD (§3h)
- [x] Cooldown research: swing-pause adopted, window-skip dead (§3d)
- [x] UTC-weekend: Sat skip adopted for multi (§3d-2)
- [x] Concurrency: cap-5 optimal, exp_max_concurrent implemented (§3d-3)

**Remaining honest asterisks:**
- Execution reality beyond modeled 0.5bp/1bp slippage (latency, partial fills).
- UTC-Saturday edge is era-dependent (2023-24 bleed, 2025-26 neutral).
- Wide-stop trades = smaller $ position for same 1R — sizing must follow stop width.

**What's next:** paper trade both kings, track Saturday coverage, build live engine.


### 3h. LTF regime gates — chop15 band + ATR blow-off (2026-09-20) — STRONG PASS

Autopsy on king + swingpause single found a **band** effect (non-monotone, the
realness signature): 15m-chop (28-bar Choppiness on the 15m series) in the
transition zone [55, 61) is a kill zone on BOTH configs (multi 100t -21.9R @ 81%;
single 62t -23.2R @ 88.7%) while chop < 55 is strongly positive and >= 61
recovers. Also: 15m ATR5/ATR20 >= 1.4 (vol blow-off) kills the single
(77t -27.9R, bigWin +10.6) but is ~neutral on the multi. Cadence was degenerate
(skipped). Implemented as two causal gates (`exp_chop15_lo/hi` band,
`exp_atr_ratio_max`) and measured FULL-PATH:

| config | n | NET | DD | NET/DD | verdict |
|---|---|---|---|---|---|
| chopband multi | 432 | +350.7 | 17.6 | 19.9 | beats unfiltered king (+24.9R) |
| **utcsat_chopband multi (stack)** | 392 | +362.2 | 18.1 | 19.9 | ties utcsat NET (+3.2R, +3.3DD — wash on quality) |
| chopband swingpause single | 317 | +227.6 | 20.0 | 11.4 | +52.8R vs swingpause single |
| atrr swingpause single | 316 | +182.2 | 21.2 | 8.6 | mild (+7.4R, -2.2DD) |
| **fullstack single (weekend+pause+band+atrr)** | **225** | **+282.9** | **12.5** | **22.6** | **BEST QUALITY PROFILE OF THE SESSION** |

Notes: full-path EXCEEDED the autopsy predictions (chopband single predicted
~+198, delivered +227.6) — the cascade effects were favourable here, unlike the
risk-width case. All six pins locked. The chop15 band is NOT the same gate as
the HTF chop track-selection (chop_thresh 58): it is the SAME formula applied to
the 15m series, measuring micro-structure choppiness at the entry bar, and its
effect is a band with recovery on both sides — the transition-zone signature.

Overfitting discipline: this is the 4th stacked filter family on one dataset.
The fullstack single (+282.9/12.5) and utcsat_chopband multi (+362.2/18.1) get
the validation batch (sw20 / cd0 / threshold neighbourhood) before either
replaces a pinned leader, and the sequential one-pass study (after L5) remains
the final arbiter.

**VALIDATION RESULT (same day, full-path): CHOP BAND REJECTED, ATR GATE NEUTRAL.**

Temporal split of the chop15 [55,61) bleed on the swingpause single:
2023 -6.3R (n=7), **2024 -22.8R (n=26, 96.2% loss)**, 2025 -7.9R, 2026 +13.8R
(POSITIVE). The band's entire edge is 2024 — same era-dependence as the multi's
Saturday. Neighbour bands [50,55) = +39.1R and [61,66) = +3.2R are positive —
sharp edges that align suspiciously with my own autopsy bucket boundaries.

Full-path validation on the sw20 chain (the cross-config test):
- chopband_swingpause_single_sw20: 309t **+86.3 / DD 31.0** vs swingpause sw20
  +120.0 / 34.1 -> **-33.7R, WORSE. The chop band does not transfer.**
- chopband_atrr sw20: +107.8 / 27.1 -> -12.2R, still worse.
- atrr_swingpause_single_sw20: +116.7 / 33.0 vs +120.0 / 34.1 -> NEUTRAL
  (-3.3R, -1.1DD). The ATR gate is temporally stable (4/4 years negative:
  -10.1/-10.4/-3.6/-3.8) but does not transfer across chains either.
- atrr_cd0_single: +180.4 / 21.2 -> consistent with cd8 (+182.2).

VERDICTS:
- `exp_chop15_lo/hi` band: REJECTED — sw10+2024-specific, fails cross-chain and
  temporal validation. Kept in the engine default-off with pinned negative
  results; do not stack into any default config.
- `exp_atr_ratio_max`: OPTIONAL/NEUTRAL — temporally stable but chain-neutral;
  keep default-off. A defensible "risk hygiene" gate, not an edge.
- `fullstack_swingpause_single_sw10` (+282.9/12.5): its extra +65R over
  nowknd_swingpause_single comes substantially from the rejected chop band —
  DISCOUNT IT. The validated single leader remains
  `nowknd_swingpause_single_sw10` (+217.6 / 18.2).

Playbook rule (final form): the only filters that ever survived full validation
in this system are STRUCTURAL and PERIOD-LEVEL (weekend calendar, fresh-structure
pause, UTC-Saturday liquidity). Every per-trade or per-bar indicator gate tested
(B3, risk-width, ER, chop15 band, ATR-ratio) either fails validation or is
neutral. The edge is in WHEN the market is tradeable, not in entry feature
conditions.


### 3i-2. WAGE12/10 validation — STRONG PASS, new best single (2026-09-21)

The other bot's kingsweep flagged wage_h=12 on the best single (+278.6 vs
+217.6). Full validation battery (all full-path, all pinned):

| test | result | verdict |
|---|---|---|
| replication (wage12, weekend+pause base) | 259t +278.6 / 16.6 | matches his sweep exactly |
| neighbourhood 8/10/12/16/20 | +265.7 / **+282.9** / +278.6 / +270.8 / +212.6 (DD 14.7-15.3) | **SMOOTH PLATEAU over 10-16h** — not a spike |
| stack interaction (wage12, no weekend skip) | +235.7 / 21.7 vs pause-only +174.8 / 23.4 | +60.9R INDEPENDENT of the weekend filter |
| cross-chain (wage12, sw20) | +144.5 / 29.2 vs pause-only sw20 +120.0 / 34.1 | +24.5R, -4.9DD — TRANSFERS |
| WF segments | all wage 8-16 variants: every segment positive, minY >= +47 | stable |

Mechanism: skip entries inside HTF windows younger than N hours — a fresh flip
is an unproven bias; requiring ~10-16h of window age before LTF entries filters
premature breaks. Same structural class as the swing-pause (mature structure),
applied to the window instead of the loss. wage20 declines (over-aged windows
miss fresh follow-through) — a real optimum, not a monotone.

**New best single: `wage10_swingpause_wskip_single_sw10` = 261t / +282.9R NET /
DD 14.7 / NET-DD 19.2.** (wage12 is within noise of the plateau peak — either
10 or 12 is defensible; both pinned.) The multi kings are unchanged: the same
wage12 on the utcsat multi gave +351.5 / 17.9 (slightly worse than +359.0) —
the multi's overlapping entries already cover young-window trades.


### 3j. UNION DUAL-QUALIFICATION — the OOS-robust configuration (2026-09-22)

**Background:** the other bot's mode sweep found `mode=union` (entries gated by
B2 AND FLIP windows simultaneously) as the new king with filters. Independently,
the B2/FLIP IS/OOS split showed B2 marks are OOS-robust (+14.7 IS / +38.8 OOS)
while FLIP marks are curve-fitted (+193.6 IS / -18.4 OOS).

**The 2x2 autopsy** (mark kind x window type, union+filters, IS=2023-24, OOS=2025+):

| (mark, window) | IS | OOS |
|---|---|---|
| B2 + FLIPwin | 1R/10t | 8R/10t |
| B2 + B2win | 30R/12t | 7R/12t |
| **B2 + BOTH** | 9R/2t | **36R/7t** |
| **FLIP + FLIPwin** | **79R/16t** | **-2R/11t** ← fragile cell |
| FLIP + B2win | 25R/11t | 14R/11t |
| FLIP + BOTH | 99R/13t | 6R/5t |

Marginals: dual-qualified (BOTH windows) = best in both eras (+7.19 IS avg,
+3.48 OOS avg). FLIP-window-only = fades badly (+3.08 -> +0.28).

**Implementation:** `exp_union_dual_only` (patcher, default-off) — in union mode,
tracks which window type matched (B2 / FLIP / both); when ON, skips
FLIP-window-only matches (the fragile cell).

**Results (full-path, registry group `dualunion`):**

| config | full n | IS | OOS | IS/OOS |
|---|---|---|---|---|
| union_multi | 120 | 64t +186.5/8.7 | 57t +44.4/5.2 | 4.2x |
| dualunion_multi | 78 | 40t +125.7/6.4 | 38t +46.0/6.0 | **2.7x** |

The dual gate gives up -68.5R of IS profit (fragile trades) but delivers
+1.6R more OOS, +8pp WR (50% vs 42%), and cuts the IS/OOS degradation ratio
from 4.2x to 2.7x — the most era-consistent config of the session.

**Files / how to run:**
- Patch: `backtest/tests/test_experiments_craze.py` (section 3g-5, `exp_union_dual_only`)
- Configs: `experiment_registry.py` keys `union_multi`, `dualunion_multi` (group `dualunion`)
- Run: `python backtest/tests/run_experiment.py --group dualunion`
- IS/OOS split script: `%TEMP%/dual_oos.py` pattern in this session's log (split at 2025-01-01)

**Status: dualunion_multi = OOS king (46.0R/6.0DD @ 50% WR). Full-history king
remains bm05_utcsat_multi (+370.6). The two measure different things: batch NET
vs era-robustness. For live, OOS consistency is the more important property.**


### 3k. STRUCTURAL ALIGNMENT — dir match + swing age (2026-09-22) — 💰 BIGGEST FIND OF THE SESSION

**The pre-entry feature autopsy** on champion_multi_sw10 found three monotone
relationships (claimed as "all computed causally at entry bar from the forming swing"):

> ## ⚠ REFUTED 2026-09-23 — LOOKAHEAD via final chain labels
>
> Hostile audit (`docs/D3_ALIGNMENT_LOOKAHEAD_AUDIT.md`): the selector reads
> **final** `dir`/`start_idx` from the **full-history** `swings_ltf` without
> `confirmed_at_idx <= i`. **353/500** picks confirm after entry; **194/500**
> dir labels and **353/500** age labels differ vs chains recomputed on
> `data[:i+1]`. Under entry-knowable labels the 125/125 becomes
> **271 opposed / +250.7R / WR 30.3%**. Path-true gate (`exp_dir_causal=1`):
> dirmatch NET **+479.9 → +75.0**; age10 configs → **0 trades**.
> **Do not ship dirmatch/age10/age25_dirmatch.** Other bot's prefix-identical
> proof used one date cut + min_bars=35 and compared swing *lists*, not the selector.

| feature | bucket | n | avg R | WR | verdict |
|---|---|---|---|---|---|
| forming swing dir vs trade dir | MATCHES | 375 | +1.52 | 40.0% | keep |
| | **OPPOSES** | **125** | **−1.00** | **0.0%** | **100% LOSERS** |
| swing age at entry | 0-10 bars | 172 | **+2.72** | 43.6% | keep |
| | 51+ bars | 112 | −0.65 | **9.8%** | stale |
| running magnitude | <0.5% | 86 | **+3.51** | 29.1% | keep |
| | 4%+ | 16 | −0.83 | 0.0% | chasing |

**The 125 opposed-direction entries lost 125/125 times (−125R, zero winners in
3.7 years).** — **descriptive of full-history final labels only; not a live gate.**

Implementation: `exp_require_dir_match`, `exp_max_swing_age`,
`exp_max_running_mag` (patcher section 3g-6). Full-path results:

| config | n | NET | DD | WR | worst6 | minY | NET-DD |
|---|---|---|---|---|---|---|---|
| king (ref) | 500 | +325.8 | 17.8 | 30.0% | +46.2 | +102.2 | 18.3 |
| **dirmatch only** | **389** | **+479.9** | **13.8** | **38.6%** | +41.8 | **+135.0** | **34.8** |
| age25 only | 295 | +355.6 | 12.8 | 37.3% | +42.1 | +101.7 | 27.8 |
| **dirmatch + age25** | 249 | **+386.7** | **9.8** | **43.8%** | **+48.2** | +81.9 | **39.5** |
| 🔥 **dirmatch + age10** | **151** | **+455.5** | **6.0** | **51.7%** | +38.9 | +98.9 | **75.9** |

Why it survives full-path (unlike per-trade filters): **removing 100%-losers
cannot cascade into bad states.** The downstream cooldown/halt sequence can only
improve when a guaranteed loser is removed. This is the first per-trade filter
that passes the playbook — because it's not a *filter*, it's a *bug fix* (the
engine should never have been taking counter-swing entries).

**New kings:**
- **Highest NET: `dirmatch_multi_sw10` = 389t / +479.9R / DD 13.8** (+154R over king)
- **Best quality: `age25_dirmatch_multi_sw10` = 249t / +386.7R / DD 9.8** (NET-DD 39.5)
- **Monster: `age10_dirmatch_multi_sw10` = 151t / +455.5R / DD 6.0 / WR 51.7%** (NET-DD 75.9)

All 6 WF segments positive on every config. Identity gate green. Pins locked.

**Validation needed before adoption:** temporal split (per-year), cross-chain
(sw20), and OOS split — the same battery as every previous find. The 100%-loser
claim (125/125) has a strong prior (fighting live structure), but n=125 needs
the cross-config check.

> **Update 2026-09-23:** temporal/OOS/sw20 all "passed" under the same
> full-history labels — that battery **cannot** catch this leak. The missing
> check was **per-entry truncated chain / `confirmed_at_idx <= i`**. See
> `D3_ALIGNMENT_LOOKAHEAD_AUDIT.md`. Results above are **REFUTED for live use**.

**FILES & HOW TO RUN (for the other bot to verify):**

1. Autopsy harness (reproduces all 7 feature tables + the 100%-loser finding):
   ```
   python backtest/tests/exp_alignment_autopsy.py
   ```
2. Full-path gate results (the 4 configs above):
   ```
   python backtest/tests/run_experiment.py --group alignment
   ```
3. Singles with alignment (the BEST EVER config):
   ```
   python backtest/tests/run_experiment.py age10_dirmatch_swingpause_single_sw10
   # expect: 130t +435.7R DD 5.7 WR 53.8%
   ```
4. Engine gates: `test_experiments_craze.py` section 3g-6
   (`exp_require_dir_match`, `exp_max_swing_age`, `exp_max_running_mag`,
   all default-off, identity-gated).
5. Pins: `experiment_registry.py` — `dirmatch_multi_sw10` (389/479.9/13.8),
   `age25_dirmatch_multi_sw10` (249/386.7/9.8),
   `age10_dirmatch_multi_sw10` (151/455.5/6.0),
   `dirmatch_swingpause_single_sw10` (279/288.1/14.1),
   `age10_dirmatch_swingpause_single_sw10` (130/435.7/5.7),
   `dirmatch_single_sw10` (292/237.7/15.7).

Note: the autopsy harness may show slightly different bucket counts than the
original inline run (running-magnitude bins: 97/141/177/73/12 vs 86/129/177/92/16)
— the generating-swing lookup picks the LAST swing with start_idx <= entry,
which can differ by one swing when swings overlap. The dir-match finding
(125/125 losers) is identical either way — that is the robust result.


## 4. min_bars_15m = 50 (docs once said 35 — wrong)
The 15m chain length is the most sensitive knob in the system:
mb35 -> 437t / +58.3R (collapse) vs mb50 -> 351t / +238.0R (production).
Guard added in run_experiment.py (hard assert on drift).

## 5. Cost model re-verified

fee 0.055%/side (entry+exit notional / risk), slip 0.5bp entry + 1bp exit / risk,
funding bars/32 x 0.01% x (entry/risk) = 0.01%/8h hold-weighted.
Champion totals: 96.0R fee+slip + 24.2R funding = 120.2R.

## 6. Bookkeeping fixes applied (2026-09-20)

0. **Trail-event drop fix APPLIED to the engine** (`v18_streak_halt.py`, both
   loops — see section 3). All champion/baseline pins re-pinned to post-fix
   values. Champion multi sw10: +366.1 -> **+325.5R NET / DD 17.8**.

1. Registry: `_shipped_sw20` hybrid pin split into `_shipped_coarse_618` +
   `_shipped_fine_58` (both pin-OK, verified by re-run). The old `_shipped_sw15`
   row was removed: the runner fixes the LTF chain at sw15 (mb50) and
   `cfg["swing"]` selects only the HTF window chain, so a sw15 row is not
   expressible — and `_shipped_coarse_618` IS the craze identity twin
   (340t/+225.3R, verified identical to the gate).
2. Runner: identity gate runs before ANY experiment (patched-off must equal
   shipped exactly, coarse+61.8 basis; hard-fail on divergence).
3. Runner: hard asserts on min_bars_15m=50 / min_bars_1h=20.
4. Runner: every result row labeled with fill basis + effective chop
   (`fine/c58.0` style) in evaluate()/format_row().
5. test_experiments_craze.main(): removed dead `build_module(split_mb=True)` /
   `build_module(momentum=True)` constructor kwargs (crashed after the
   superset-patcher refactor); both phases now run via runtime kwargs.
