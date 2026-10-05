# The 1h swing geometry gate at window open

> Run 2026-09-29. Harness `exp_htf_geometry.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Closes `method/OPEN_RESEARCH_QUEUE.md:420`, the last untested Nemotron item.

## The item

> "1h swing geometry gate at bias-window open — magnitude / duration /
> confirmation source, all known at the swing's confirmation instant.
> Overlaps the graveyard's 'range width' row, so it must be pre-registered
> as distinct or it is a re-run."

**Pre-registration used here:** duration is the primary arm, tested alone. A
time measurement cannot be faked by a price-range measure, so if duration
carries signal it is structurally distinct from the range-width row rather
than a re-run. The whole item fails if no arm beats the control in both eras
of both lanes.

## A void run first, disclosed

The first run of this file read geometry off the **leg** dict, which has no
`seg` key. It printed `0 legs with geometry`, a sentinel duration of 384 for
every window and `travel/ATR = 0.00` — and, because every arm was
degenerate, a table of identical rows that could easily have been quoted as
"the gate is inert". Dumping the trade keys showed the real fields
(`entry_idx`, `exit_idx`, `swing_no`, `break_kind`) and, more importantly,
that **the geometry has to come from the 1h swing via `swing_no`, not from
the leg** — the leg's own duration is not knowable at window open, the
swing's is.

## What the geometry actually says

| | champ IS | champ OOS |
|---|---|---|
| swing duration, p50 | 14 bars | 12 bars |
| swing travel / ATR, p50 | 5.32 | 5.29 |

| keep | champ IS | champ OOS |
|---|---|---|
| book (no gate change) | 499t PF 2.38 WR 29.9% | 243t PF 1.77 WR 28.0% |
| **dur > p25** (6 bars) | 369t PF **2.70** WR **31.4%** | 166t PF 1.45 |
| **dur > p60** (19 bars) | 192t PF **3.59** WR **35.9%** dNet −82.3R | 94t PF 1.59 |
| **dur ≤ p25** | 130t PF 1.58 | 77t PF **2.41** |
| **dur ≤ p90** (35 bars) | 461t PF 2.20 | 223t PF 1.88, dNet **+24.5R** |
| **mag > p60** (5.90 ATR) | 199t PF **3.01** WR 34.2% | 82t PF 1.22 |
| **mag ≤ p75** (7.10 ATR) | 377t PF 2.22 | 164t PF **2.01**, dNet **+22.1R** |

## The finding: a clean and complete inversion

**IS wants BIG and LONG. OOS wants SMALL and SHORT.**

| | best cohort in IS | best cohort in OOS |
|---|---|---|
| duration | `> p60` — PF 3.59, WR 35.9% vs book 29.9% | `≤ p25` — PF 2.41 vs book 1.77 |
| magnitude | `> p60` — PF 3.01, WR 34.2% | `≤ p75` — PF 2.01 |

Both features are strongly predictive **within** each era and they point in
**opposite directions across** them. That is not noise in a threshold — it
is the same regime-flip signature that window age, leg position, and the
1h-decay gate have each shown, and here it is as clean as any of them.

**No threshold gives a positive dNet in both eras**, so the item fails its
own pre-registered condition.

## The third arm is vacuous

`keep B2-opening windows` returns **0 windows in all four cells.** Every
gating window opens on a FLIP break. The B2 book is simulated and its P&L
is discarded, exactly as P3 found — and now it is clear that B2 never gates
anything either. **Confirmation source is not a usable feature**, which is
the same shape as the queue's own "2-of-3 swings" closure, where the rule
kept 1,599/1,599 swings because the chain is built in same-direction pairs.

## Verdict

**Closed, negative.** The geometry is genuinely predictive *within* an era —
durations of 19+ bars lift IS win rate from 29.9% to 35.9% — and genuinely
anti-predictive across. It is a regime descriptor, not a gate, and the eras
do not agree on which side of it to trade.

**The honest reading is that this is the fourth independent confirmation
that the 1h layer's usefulness is regime-dependent** — after window age
(p75 cohort beats the book 4/4), leg position (ordering reverses), and the
1h-decay gate (negative IS, positive OOS). Each is a real effect; none
survives being turned into a rule.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
