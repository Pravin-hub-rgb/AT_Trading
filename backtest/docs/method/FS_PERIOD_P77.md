# P77 — PERIOD PARTITION. 6 of 8 in IS, 4 of 4 in OOS. The era-split, seventh time.

> Run 2026-09-29. Harness `exp_fs_period.py`. **NOT ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The FS hybrid is closed on the same evidence that closed cand_4h1h —
> and on a worse split than that.**

## What ran

The P61 test applied to the FS hybrid for the first time: calendar half-year
partition, fixed before looking, never grouped by `r_multiple` / `outcome` /
`pnl`. Plus a per-year breakdown, because the owner's observation was specific
— *"the hybrid's performance in 2021-22 is better, that's the only place
anything has matched it."* That is measured below rather than asserted.

## PART A — the period split

**IS (2023–2026), hybrid mean R/trade vs champion:**

| period | nCtl | ctl R/t | nHyb | hyb R/t | winner |
|---|---|---|---|---|---|
| 2023H1 | 49 | +1.095 | 75 | +0.228 | **ctl** |
| 2023H2 | 54 | +1.331 | 61 | +1.294 | **ctl** |
| 2024H1 | 71 | +1.171 | 81 | +0.201 | **ctl** |
| 2024H2 | 72 | +0.611 | 101 | +0.633 | hyb |
| 2025H1 | 50 | +0.005 | 66 | +0.352 | hyb |
| 2025H2 | 67 | +1.480 | 85 | +0.710 | **ctl** |
| 2026H1 | 69 | +0.789 | 84 | +0.620 | **ctl** |
| 2026H2 | 22 | +2.728 | 39 | +1.421 | **ctl** |

**Hybrid wins 2, loses 6 of 8.**

**OOS (2021–2022):**

| period | nCtl | ctl R/t | nHyb | hyb R/t | winner |
|---|---|---|---|---|---|
| 2021H1 | 69 | +0.041 | 89 | +0.083 | hyb |
| 2021H2 | 68 | +0.152 | 77 | +0.513 | hyb |
| 2022H1 | 60 | +0.465 | 79 | +1.177 | hyb |
| 2022H2 | 56 | +0.921 | 81 | +1.126 | hyb |

**Hybrid wins 4, loses 0 of 4.**

## PART B — the owner's observation, confirmed

| year | champion n / net / PF | hybrid n / net / PF | hybrid better? |
|---|---|---|---|
| **2021** | 137 / **−1.2R** / 1.15 | 166 / **+35.1R** / 1.62 | **YES** |
| **2022** | 116 / +61.4R / 2.12 | 160 / **+163.9R** / **4.36** | **YES — 2.7×** |
| 2023 | 103 / +99.4R / 3.04 | 136 / +73.9R / 2.83 | no |
| 2024 | 143 / +98.9R / 2.29 | 182 / +59.0R / 1.97 | no |
| 2025 | 117 / +69.3R / 2.33 | 151 / +59.5R / 2.42 | no |
| 2026 | 91 / +91.4R / 3.14 | 123 / +88.3R / 3.38 | no |

**The owner's read was exactly right, and it is the whole finding.** The
hybrid wins **2021 and 2022** and loses **2023, 2024, 2025 and 2026**. It
loses on net in every single IS year, and it wins on net in every single OOS
year, with 2022 at PF 4.36 against the champion's 2.12.

**And in 2021 the champion is −1.2R at PF 1.15 while the hybrid is +35.1R at
PF 1.62.** The single most striking cell in the whole programme — the
champion does not trade profitably in that year at all.

## What this settles

**The FS hybrid is the seventh appearance of the era-split signature.**
P56 window expiry · P58 granularity · P59 layer agreement · P60 union risk
profile · P61 cand_4h1h stability · P66 30m granularity · **P77 this.**

**Its IS split of 2-6 is worse than `cand_4h1h`'s 4-4.** That arm was
downgraded on a coin flip. This one loses six of eight.

**The +163.4R OOS "win" that P73 and P75 led with is an era artefact of
exactly the kind this programme has now caught seven times.** The aggregate
was carried entirely by the two oldest years in the sample, and it loses in
every year after them.

**And the mechanism is the one `method/FS_ENTRY.md` named in advance:**

> *"When you actually buy a swing after it has been confirmed big, it is the
> worst thing you can buy — because the move that made it big has already
> happened."*

**An FS entry is by construction earlier and less confirmed than a break
entry. That is an edge in a market where early, unconfirmed entries are
rewarded and a drag in one where confirmation is what pays.** 2021-22 and
2023-26 are two such markets. `method/FS_ENTRY.md` also recorded that ~36-37% of
the book disappears when you wait for FS, which is the same fact seen from
the other side: the champion's break entries exist because waiting pays in
the era it was fitted.

## Verdict

**Closed. Not adopted, and the earlier "promising hybrid" framing is
withdrawn.**

This is the correct outcome and it is the programme working, not failing:
an arm that produced **+163.4R of OOS profit, a doubled profit factor, a
halved drawdown and more trades than the champion** was caught by the
partition test, and it turns out to be **good at exactly one thing — trading
in 2021 and 2022.**

**What would have to be true for FS entries to be usable is now stated in
one sentence: the market has to reward being early.** That is a statement
about the market, not about the engine, and no live feature tested this
round separates the two regimes — P55 proved that for swing geometry, P67
for volatility, P68 for price.

## Stated limitations

- **Only two OOS years exist**, so "4 of 4 half-years" is four cells of the
  same two years. It is consistent, and it is not much evidence.
- **Both lanes are the same data.** The utcsat lane was run and the printout
  truncated from the log; the champion-lane result is reported because it is
  the one the pins and the queue discuss, and the utcsat half-year split
  should be read before this is quoted.
- **No threshold was searched** and none should be — there is no threshold
  here, just a calendar partition fixed in advance.
- **The 2021 champion result (−1.2R, PF 1.15) is itself striking** and is a
  separate finding: it says the champion does not make money in that year.
  That is worth its own look and it is not what this run was for.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
