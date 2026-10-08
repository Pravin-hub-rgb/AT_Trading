# Four mode candidates, registered and pinned — none adoptable, and the reasons are measured

Date: 2026-10-08. Engine post-C17. Harness: `exp_mode_confirm.py`.
Lane-1 book: `fsent_champ_long`. **No book promoted. The shipping book is unchanged.**

## What happened

`exp_mode_sweep.py` ran all 27 router branches against the shipping book for the
first time. Four beat `mode="atr_high"` in both eras and survived removing the top
5 and top 10 trades. Three checks were run before any of them became a book:

1. **Outlier bar at depth** — not just the top-1 the sweep reported
2. **Second lane** — `champion_multi_sw10` and `utcsat_multi_sw10`
3. **`atr_low`'s own threshold** — is the sign flip a finding or one lucky point

## Check 1 — outlier bar at depth. All four pass.

| mode | era | net | max DD | −top1 | −top5 | −top10 | −top25% |
|---|---|---:|---:|---:|---:|---:|---:|
| base (shipping) | IS | +533.4 | 13.4 | +484.7 | +342.5 | +250.3 | −219.7 |
| base | OOS | +239.6 | 11.9 | +213.5 | +135.7 | +82.8 | −122.9 |
| `atr_low` | IS | +721.3 | 28.9 | +672.7 | +514.7 | +399.6 | −280.9 |
| `atr_low` | OOS | +280.7 | 14.6 | +254.6 | **+176.8** | **+121.0** | −121.4 |
| `fd` | IS | +534.8 | 13.4 | +486.2 | +343.9 | +251.8 | −221.5 |
| `fd` | OOS | +276.8 | 12.2 | +250.7 | **+172.9** | **+108.9** | −118.1 |
| `flip_quality` | IS | +534.8 | 13.4 | +486.1 | +343.9 | +251.7 | −217.2 |
| `flip_quality` | OOS | +244.4 | 11.9 | +218.3 | **+140.5** | **+87.7** | −112.9 |
| `union` | IS | +580.0 | 23.8 | +531.4 | +389.2 | +291.3 | −375.9 |
| `union` | OOS | +303.8 | 18.2 | +277.7 | **+199.9** | **+135.3** | −193.3 |

**All four beat the shipping baseline at top-5 and top-10 removal in both eras.**
This is the bar that killed `trail_half` (+42R → +0.77R), `persist=5` (one
2.2-day long) and `chop=55` (two trades at 21R each). None of the four dies here.

## Check 2 — the second lane. All four fail, and this is decisive.

| mode | champion IS | champion OOS | utcsat IS | utcsat OOS |
|---|---:|---:|---:|---:|
| `atr_low` | +144.8 | **−8.4** | +49.6 | **−7.1** |
| `fd` | −6.8 | **−0.9** | −4.2 | +2.0 |
| `flip_quality` | +0.4 | **−7.0** | +4.9 | **−4.1** |
| `union` | −127.4 | **−73.8** | −165.0 | **−36.2** |

Every candidate is negative out of sample on the second lanes. The two lanes are
the same data, so their agreement is not independence — but a candidate that only
works on one lane is not a candidate, and these are all in-sample wins with an
out-of-sample loss on the lanes that were never fitted.

**This is the era-split pattern, and it is the eleventh appearance.** It is what
has closed every regime-conditional tweak in this repo's history.

## Check 3 — `atr_low`'s own threshold. The flip is one point, not a region.

| `atr_low_thresh` | era | n | net | max DD | −top5 | Δ net |
|---|---|---:|---:|---:|---:|---:|
| 0.20 | IS | 547 | +636.1 | 15.2 | +429.5 | +102.7 |
| 0.20 | OOS | 297 | +247.2 | 11.9 | +143.2 | +7.6 |
| 0.25 | IS | 560 | +635.3 | 26.4 | +428.7 | +101.9 |
| 0.25 | OOS | 300 | +240.2 | 12.5 | +136.2 | +0.6 |
| 0.30 | IS | 608 | +668.1 | 24.8 | +461.5 | +134.7 |
| 0.30 | OOS | 302 | +237.7 | 14.9 | +133.8 | **−1.9** |
| **0.35** | **IS** | **641** | **+721.3** | **28.9** | **+514.7** | **+187.9** |
| **0.35** | **OOS** | **315** | **+280.7** | **14.6** | **+176.8** | **+41.1** |
| 0.40 | IS | 642 | +649.3 | 27.9 | +460.6 | +115.9 |
| 0.40 | OOS | 306 | +195.9 | 18.0 | +102.1 | **−43.7** |
| 0.50 | IS | 662 | +671.6 | 27.9 | +483.0 | +138.2 |
| 0.50 | OOS | 337 | +183.4 | 15.6 | +89.7 | **−56.2** |
| 0.60 | IS | 660 | +672.2 | 27.9 | +483.6 | +138.8 |
| 0.60 | OOS | 349 | +188.9 | 16.6 | +95.2 | **−50.7** |

**The +41.1R OOS gain exists at exactly one threshold.** At 0.30 it is −1.9R and
at 0.40 it is −43.7R. In sample the gain is large everywhere (+102 to +188).

So the sign flip is real in sample and a single-point coincidence out of sample.
That is the grid-peak failure `CEILING_RELPRICE_P69.md` warns about by name:
"choosing it because it is the peak of a four-point grid is exactly the search
this programme has refused everywhere else."

**The result I would have called promising on the sweep is, three checks later, a
threshold peak on the lane it was fitted in.**

## Verdict

Adoption required all of: net better in both eras, drawdown no worse in both
eras, survive top-5 and top-10, and hold on the second lane.

| mode | net both eras | DD no worse | survives depth | holds lane 2 | |
|---|---|---|---|---|---|
| `atr_low` | ✅ | ❌ 28.9 / 14.6 | ✅ | ❌ | blocked on drawdown, lane 2 |
| `fd` | ✅ | ❌ 12.2 | ✅ | ❌ | blocked on drawdown, lane 2 |
| `flip_quality` | ✅ | ✅ flat | ✅ | ❌ | **blocked on lane 2** |
| `union` | ✅ | ❌ 18.2 | ✅ | ❌ | blocked on drawdown, lane 2 |

**NONE IS ADOPTABLE.**

`flip_quality` came closest — it holds the base drawdown exactly at 13.4R IS /
11.9R OOS and passes every depth check. It is blocked solely by the second lane,
where it loses 7.0R out of sample on champion and 4.1R on utcsat, for a
lane-1 gain of +4.8R.

## Books registered and pinned

| book | IS | OOS | pins verified |
|---|---|---|---|
| `fsent_champ_long_mode_atr_low` | 641 / +721.3 / 28.90 | 315 / +280.7 / 14.60 | `exp_fastcheck` OK both eras |
| `fsent_champ_long_mode_fd` | 529 / +534.8 / 13.40 | 295 / +276.8 / 12.20 | OK |
| `fsent_champ_long_mode_flip_quality` | 527 / +534.8 / 13.40 | 294 / +244.4 / 11.90 | OK |
| `fsent_champ_long_mode_union` | 813 / +580.0 / 23.80 | 442 / +303.8 / 18.20 | OK |

All four reproduce exactly from the engine, on both eras. They are registered so
the next round starts from a pin rather than from prose, **and so the claim can be
re-checked by anyone who disagrees with it.** None is promoted.

## What is worth keeping from this

The map finding was real and the sweep was worth running — 25 branches had never
been measured, and three of them turned out to be ahead on the lane they were
tested on. What killed them was not scepticism about the numbers; it was running
the numbers somewhere they had not been run before.

`mode="atr_low"` remains the most interesting thing in the repo's unexplored
space, and not because +187.9R is real. **It is interesting because it is a sign
flip rather than a tuned threshold, and a sign flip is the one kind of result
this session's record of grid peaks would not have predicted.** It still fails the
lane test, and until it does not, it stays a registered candidate.

## Limitations

- The two lanes are the same data. Lane 2 is a consistency check, not
  independence.
- The depth bar is top-N removal on trade count. It does not address the fact
  that the shipping book's own edge is unresolved at p = 0.91
  (`SHIPPING_BOOK_NULL.md`), so every delta here is against a book whose
  significance is not established.
- `atr_low`'s threshold grid is seven points on one lane. No second lane grid was
  run, so the OOS peak at 0.35 has not been checked for being a lane-1 artefact
  specifically.
- No drawdown-duration or ulcer criterion was applied in the adoption test beyond
  reporting them. `union`'s ulcer and duration are materially worse and a stricter
  criterion would have failed it earlier.

**Nothing promoted. `fsent_champ_long` unchanged at 528 / +533.37 / 13.42 IS and
311 / +239.59 / 11.88 OOS.**