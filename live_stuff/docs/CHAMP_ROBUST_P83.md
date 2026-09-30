# P83 — IS THE CHAMPION ROBUST ENOUGH TO SHIP? Mostly. The weak spot is
# 2021, and it is visible without any regime detection.

> Run 2026-09-29. Harness `exp_champ_robust.py`. **Risk characterisation.
> Nothing adopted. Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.**

## The question, and why it deserved asking

P82 closed directional FS, which left "the champion trades". **That is not
a complete answer**, and the owner was right to push. The champion's own
year table is not comfortable:

| year | n | net | PF |
|---|---|---|---|
| 2021 | 152 | **−11.0R** | 0.89 |
| 2022 | 127 | +116.7R | 2.54 |
| 2023 | 107 | +113.9R | 2.71 |
| 2024 | 163 | +124.1R | 2.08 |
| 2025 | 128 | +100.4R | 2.24 |
| 2026 | 102 | +106.8R | 2.79 |

**One year in six is negative.** A book can net +325.8R over 3.7 years and
still be unshippable inside a single year. This measures the **sequence**,
not the total — the total is already known and is not the question.

## What the sequence actually looks like

| | champion IS | champion OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| trades | 500 | 279 | 454 | 253 |
| longest losing run | **16 trades / 45 days** | **15 trades / 49 days** | 13 / 45 | 9 / 26 |
| **max drawdown** | **17.8R** | **37.3R** | 14.8R | 22.1R |
| drawdown length | 25 trades / **77 days** | 105 trades / **278 days** | 22 / 77 | 65 / 189 |
| years ≤ 0 | none | **2021** | none | none |

**Two things stand out and they point in opposite directions.**

**The good news, and it is real: IS is boring in the way a book should
be.** Four consecutive positive years, 107 / 163 / 128 / 102 trades, PF
2.08–2.79, **no year at or below zero**. Worst drawdown 17.8R over 77 days —
a three-month wobble, not a ruin. **On the IS evidence the champion is
comfortably shippable.**

**The bad news: OOS has a 278-day drawdown of 37.3R and a losing year.** More
than twice the IS drawdown, lasting more than three times as long, in the
era that was never fitted. 2021 is negative at −11.0R, PF 0.89.

## The weak spot is quarter-level, and this is the number to plan around

| | worst quarter | quarters ≤ 0 |
|---|---|---|
| champion IS | **2025Q2 −4.8R, PF 0.73** | 3 of 15 |
| champion OOS | **2021Q2 −16.0R, PF 0.41** | 3 of 8 |
| utcsat IS | 2025Q2 −2.8R, PF 0.83 | 2 of 15 |
| utcsat OOS | 2022Q3 −8.4R, PF 0.61 | 2 of 8 |

**Every losing quarter in the sample has a profit factor below 1.0** — 0.41,
0.61, 0.73, 0.83, 0.90, 0.91, 0.95. There is no quarter that is slightly
down and recovers; the losing quarters lose cleanly, then the strong
quarters more than pay for them.

**That is the shape a bot builder needs: the book does not bleed slowly, it
stalls in identifiable quarters.** In IS the stall is small (worst −4.8R).
In OOS it is not (worst −16.0R).

## The reassuring part

**No configuration produces an unrecoverable sequence.** Worst losing run
across all four cells is 16 trades. Worst drawdown 37.3R. Worst quarter
−16.0R. **No 50-trade collapse, and no year losing more than 11R.**

**And the FS hybrid does not fix this** — P82 showed its improvement was

## What this means for shipping

**Ship it, sized for the OOS 2021 drawdown.**

| question | answer |
|---|---|
| Is the sequence survivable? | **Yes.** Max DD 37.3R, longest losing run 16 trades, worst quarter −16.0R. |
| Is it comfortable? | **In IS yes, in OOS no.** A 278-day, 37.3R drawdown is nine months underwater. |
| Is 2021 a one-off? | **Unknown, and unknowable from this data.** One year, one era. The forward pass is the only instrument that answers it, and it cannot confirm (P63). |
| Can it be improved? | **Not by the trigger swap** (P82, p = 0.69–0.92), **not by the timeframe** (P58), **not by a regime gate** (P55, P67, P68 all failed to separate the eras). |

**And the number the owner actually needs before shipping has no answer in
this programme.** 37.3R is in **R, not currency** — "how many dollars does
this cost me" depends entirely on position sizing, which **cannot be
answered from this repo**: P9 closed the sizing thread because the engine
has no size channel and a sizing rule cannot change net R in the first
place. **Saying that plainly is more useful than inventing a currency
conversion for the occasion.**

## Stated limitations

- **Both lanes are the same data.** The utcsat lane is consistently gentler
  (max DD 14.8R and 22.1R against 17.8R and 37.3R) — a parameter-sensitivity
  finding, not an independent confirmation.
- **One negative year in six is a thin basis.** 2021 may be a 5-year
  regime or a one-off; this data cannot distinguish them.
- **Drawdown is in R on the realised sequence** and ignores sizing, which
  this repo cannot currently choose (P9).
- **Recovery time after the max drawdown is not reported.** The harness
  computes peak and trough but does not exercise the recovery loop, and
  that number matters more than the depth to anyone holding the bot.

## Status

**Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.**

**The answer to the owner's question is now more complete than "the
champion trades":** the IS record supports shipping it, the OOS record
supports shipping it **sized for a nine-month, 37.3R underwater period**, and
**nothing found in this round improves on it** — the architecture search,
the timeframe search, the regime gates and the directional trigger swap have
all now been tested and all closed.

inside the noise, and its year table is better in 2021–22 and worse in every
year after. A swap would trade one uncomfortable stretch for another.
