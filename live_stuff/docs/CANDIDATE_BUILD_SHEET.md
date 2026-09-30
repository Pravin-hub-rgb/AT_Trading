# CANDIDATE BUILD SHEET — every documented finding, with its harness

> **Written 2026-09-29. Nothing here is adopted.** This file exists so any
> finding below can later be turned into a new strategy without redoing the
> archaeology. Rule, numbers, harness and wiring are all in one place.
>
> Champion, unchanged throughout: **500t / +325.8R IS**, **279t / +70.1R OOS**.

---

## The bar every candidate must clear

**M = 193.4R** — the `|dNet|` whose null 95th percentile is exceeded (block
bootstrap, length 20, 10,000 draws, preserving count, the 3-loss-streak
process and lag-1..3 dependence). Set by the register, not chosen per
experiment.

**Sign consistency across both lanes and both eras is a separate, weaker
condition.** A 4/4 positive feature can still be inside the null, and this
sheet keeps the two judgements apart rather than collapsing them.

---

## TIER A — 4/4 positive, consistent sign

### A0. Window `cap_days` — a risk control inherited across an architecture change (P49 + P50)

**This is the cleanest finding in the sheet, and the reason is historical
rather than statistical.**

```python
# backend/src/btc/engines/v7_timecap.py
"""v7 — Time Cap for 1h Flip Fixed 3R. Exits at market if hold > cap_days."""
cap_days: int = 30,        # v7's own default
```

**v7 traded the 1h leg directly.** A leg that hit neither −1R nor +3R could
hold for months, so a time cap was added to force a market exit. **For that
architecture it was the right call.** Then the LTF layer arrived; v18
inherited `cap_days=16` as a literal in three call sites and became
**HTF-as-gate, LTF-as-executor**. The number survived the change. The meaning
did not.

| | v7 | v18 (shipped) |
|---|---|---|
| what the 1h leg is | the trade | a gate |
| what a cap exit does | closes one position at market | closes the window **and every LTF entry inside it** |
| is that a risk decision | yes | it is opportunity suppression |

**The cap is doing exactly what it was built to do, on the wrong object.**

Turning it off is 4/4 positive and **adds** trades:

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| `cap_days=16` (shipped) | 500t +325.8R | 279t +70.1R | 454t +359.0R | 253t +60.2R |
| **cap off** | **586t +401.1R** | **313t +125.2R** | **535t +372.6R** | **284t +138.7R** |
| **dNet** | **+75.3R** | **+55.1R** | **+13.7R** | **+78.5R** |
| extra trades | +86 | +34 | +81 | +31 |

**And the mechanism is measured, not inferred.** 12 windows truncated in
champion IS: ten died at −1R, those HTF legs came to **−4.0R** in total, and
the LTF trades taken inside them while still open were **176 trades worth
+88.2R**. Uncapped there are *fewer* HTF legs (309 → 226) yet *more* LTF
trades (500 → 586) — trades per window goes 1.6 → 2.6. **The long windows are
the ones that keep producing, and the cap removes them systematically.**

**Limits, kept next to it:** largest dNet +78.5R against M = 193.4R — real,
4/4, **not a pass**. A 98-day window is three months of directional exposure
and **the v7 rationale is still valid, it just applies to the leg now, not
the window.** The sweep was not monotone. And the cap binds on only 5–6% of
legs, so it is a small-sample effect. `CAPS_P49.md`, `WINDOW_LIFE.md`.

### A1. `decay < 0.75` — SKIP

Skip a 15m entry when the decay feature reads ≥ 0.75.

| lane | era | n kept | net | dNet | PF |
|---|---|---:|---:|---:|---:|
| champion | IS | 307 | +359.9 | **+34.2** | 3.34 |
| champion | OOS | 147 | +77.6 | **+7.5** | 2.05 |
| utcsat | IS | 272 | +362.8 | **+3.8** | 3.65 |
| utcsat | OOS | 134 | +70.1 | **+9.9** | 2.06 |

**The only 4/4-positive feature found in this whole line of work.** Max
dNet +34.2R ≈ 0.18 × M. Real, consistent, inside the null.

### A2. `decay < 0.75` + **window age cap** — best decay result

The decay leg's lookback is stale-prone, and stale legs turned out to be
*good*. Capping their age recovered the rest.

| variant | IS dNet | OOS dNet | |
|---|---:|---:|---|
| B — current, no cap | +34.2R | +7.5R | |
| **C — CAP 1 day** | +56.6R | +17.4R | ⚠️ **NOT REPRODUCED** |
| E — CAP 2 days | +32.5R | **+25.1R** | ⚠️ **NOT REPRODUCED** |
| G — GRAY stale instead of skip | −53.1R | −62.0R | |

⚠️ **C and E did not reproduce in P49.** Sweeping the *leg-age* cap over
0.5–7 days produced no arm close to them, and a 1-day cap is not viable on
that definition at all — the oldest of the last 4 buying legs is
**p50 = 3.05 days**, so a 1-day cap keeps 3 trades. Whatever these rows
measured, it was not leg age. **The original P38 definition must be
recovered before this decision can be asked.** `CAPS_P49.md`.

**What P49 does confirm is the direction:** the cap helps OOS and hurts IS
at every value, and removing it is the best arm.

**Note G:** GRAY the stale set instead of skipping it is *worse than doing
nothing* in both eras. GRAY only pays when the gray set is mostly winners,
and the stale set is not.

---

## TIER B — strong in IS, negative in OOS

### B1. 1h character strength + decay, N = 8

Read the 1h rolling character score (buying intact + selling broken, over 8
1h swings), require `|score| > 0.10` **and** `decay < 0.75`.

| lane | era | n | net | dNet | PF | DD |
|---|---|---:|---:|---:|---:|---:|
| champion | IS | 249 | +368.8 | **+43.0** | **3.92** | **11.4** |
| champion | OOS | 114 | +15.9 | **−54.2** | 1.42 | 28.9 |
| utcsat | IS | 193 | +310.9 | −48.1 | 4.31 | 13.1 |
| utcsat | OOS | 85 | +66.6 | +6.4 | 2.51 | 20.6 |

**The single best IS number of the session, and the arm that collapses
hardest OOS.** Same setting, both extremes. 2/4 lanes only.

The score itself is closed in `CHOP_SCORE.md` as a standalone feature; it
survives here only as a modifier.

---

## TIER C — era-flipped

### C1. Leg position — the best price-action ordering found

`(entry − leg_low) / (leg_high − leg_low)`, scale-free by construction.

| bucket | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 0.0–0.2 | +150.5R PF 4.51 | +6.1R PF 1.37 | +148.7R PF 4.58 | +10.2R PF 1.54 |
| 0.2–0.4 | +142.1R PF 3.73 | +5.2R PF 1.33 | +141.1R PF 3.84 | +0.8R PF 1.20 |
| 0.4–0.6 | −13.1R PF 1.20 | **+48.2R PF 2.62** | −4.6R PF 1.31 | **+43.9R PF 2.63** |
| 0.6–0.8 | −20.6R PF 1.05 | +16.6R PF 1.65 | −7.1R PF 1.17 | +10.3R PF 1.50 |
| 0.8–1.0 | +67.0R PF 2.34 | −6.0R PF 0.98 | +80.8R PF 2.76 | −5.0R PF 1.01 |

---

## TIER D — dead, do not rebuild

| finding | why dead |
|---|---|
| 1h character score as a side filter | 0/32 arms positive |
| 1h score, five rewrites | 0/11 |
| 1h FLIP (direction override) | 0/10, champ OOS −83R |
| full book re-decided from the score | 0/12 |
| stop width as a filter | 4/4 negative; corr with ATR 0.52–0.71, i.e. a volatility proxy |
| risk-weighted concurrency | premise valid, max concurrent 3–6, but no brake binds profitably |
| 1h oracle early read | `DEAD` structurally impossible (0 trades, 4/4 cells) |
| ZigZag vs shipped chain | Jaccard 0.0003–0.0134 — effectively disjoint |

---

## Harnesses

| finding | harness |
|---|---|
| decay < 0.75 | `exp_decay_switch.py`, `exp_decay_purge.py` |
| decay + age cap | `exp_decay_gray_skip.py`, `exp_directional_decay.py` |
| 1h score (closed) | `exp_chop_side.py`, `exp_chop_brainstorm.py`, `exp_score_1h.py`, `exp_chop_final.py` |
| leak proof | `exp_leak_proof.py` |
| 1h oracle | `exp_htf_oracle.py` |
| risk-weighted concurrency | `exp_risk_concurrency.py` |
| P7 / W1 sweep | `exp_queue_sweep.py` |
| leg position, stop decomposition | `exp_stop_decomp.py` |

**All are post-process only — they read a champion book and repartition it.
None edits the engine.** That is why the control reproduces exactly in every
cell.

---

## How to build a new strategy from any row above

1. Take the rule **as written**. Do not re-tune the threshold — several were
   chosen post-hoc, and a retune is a different and weaker claim.
2. Run it **path-true** on both lanes and both eras. Post-process evidence
   does not survive being wired into the engine; log 104's 2h test is the
   standing reminder that the plane and the chain carry the edge.
3. Report `|dNet| > M = 193.4R` in **both** eras, and the sign in **both**
   lanes. A row clearing only one is era-fitted.
4. For anything gated on window age or the 1h leg, confirm the input is
   known **at the 15m entry instant**, not reconstructed from the window's
   eventual end.
5. Keep the gray/skip distinction. Every GRAY result in this file is worse
   than the equivalent SKIP, and one of them is worse than doing nothing.

---

## The honest summary of the concentration findings

| feature | concentration | eras agree | extractable |
|---|---|---|---|
| **cap_days off** | real, measured mechanism | **yes, 4/4** | no — 0.4 × M |
| decay | real | yes, 4/4 | no — 0.18 × M |
| window age | real | yes, 4/4 | no — era-flip |
| stop width | real | yes | no — 4/4 negative |
| leg position | real | **no, reverses** | no — 0/15 ranges |

Four features, four real concentrations, one shape: **in a book where the
median trade is roughly break-even, the profitable subset is large and
overlapping, so cutting it removes winners faster than losers.** Decay is
the only one whose sign survives every test, and it is the only one still a
plausible candidate.

## The one finding whose reason is structural, not statistical

`cap_days` is the only item here whose case does not rest on a number
clearing a threshold. **A trade-exit control written for a standalone-HTF
architecture was inherited by a gate-based one, where the same exit now
suppresses the LTF layer.** The number it produces (+78.5R) does not clear
M. The reasoning does not need M at all, and it is the one item here that
survives if every dNet in this sheet turns out to be noise.

That is also why it should be resolved by a *decision* — drop the cap, or
replace it with a ceiling that still limits the leg — rather than by looking
for a better threshold.


---

## Still open, not documented as candidates

| still open, not documented as candidates | state |
|---|---|
| 1d vs 2d age cap | **not reproducible** — see the ⚠️ under A2 |
| P6 / alt breadth | blocked on Bybit perp data |
| forward pass on `data/forward/bybit/` | M now exists, not run |

**P1 nesting was closed on 2026-09-29 without the rebuild** — containment
measured on the existing chain came out *below* the book in all four cells,
and the cohort that is good is the one nesting would exclude. `NESTING_P1.md`.

**P4 `cap_days` was swept and closed on 2026-09-29** — the 16-day cap costs R
4/4, now documented as candidate A0. `CAPS_P49.md`.


**The ordering reverses between eras** — IS rewards 0.0–0.2, OOS rewards
0.4–0.6, in both lanes. **All 15 contiguous ranges fail**; 0 clear M in both
eras of either lane. Concentration real, extractable edge not.

Its only honest use is diagnostic: which entry style the current regime is
rewarding.

### C2. Window age

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| p75 cohort WR | 33.9% | 29.0% | — | 31.7% |
| whole book WR | 30.0% | 28.0% | 30.8% | 29.6% |

The oldest quartile of windows beats the book in **all four cells** — older
windows are not tired. But every fade threshold flips sign between eras and
the largest `|dNet|` is 17.1R.
