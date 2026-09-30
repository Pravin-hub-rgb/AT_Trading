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

| variant | IS dNet | OOS dNet |
|---|---:|---:|
| B — current, no cap | +34.2R | +7.5R |
| **C — CAP 1 day** | **+56.6R** | +17.4R |
| E — CAP 2 days | +32.5R | **+25.1R** |
| G — GRAY stale instead of skip | −53.1R | −62.0R |

**C wins IS, E wins OOS.** That conflict is unresolved and is the one open
decision here. Both documented; neither chosen.

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

## The honest summary of the four concentration findings

| feature | concentration | eras agree | extractable |
|---|---|---|---|
| decay | real | yes, 4/4 | no — 0.18 × M |
| window age | real | yes, 4/4 | no — era-flip |
| stop width | real | yes | no — 4/4 negative |
| leg position | real | **no, reverses** | no — 0/15 ranges |

Four features, four real concentrations, one shape: **in a book where the
median trade is roughly break-even, the profitable subset is large and
overlapping, so cutting it removes winners faster than losers.** Decay is
the only one whose sign survives every test, and it is the only one still a
plausible candidate.

---

## Still open, not documented as candidates

| item | state |
|---|---|
| P1 nested swing containment | **not tested** — needs `btc_swing.py:150` + `walker.py:76` edited |
| P4 `cap_days` sweep | not run — literal `16` in three call sites |
| 1d vs 2d age cap | measured, decision not taken |
| P6 / alt breadth | blocked on Bybit perp data |
| forward pass on `data/forward/bybit/` | M now exists, not run |


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
