# How long does a 1h window actually live?

> Run 2026-09-29. Harness `exp_window_life.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> This is the diagnostic behind P49's "turn the cap off" direction.

## The question asked

> "like mahino tak htf same bias? woh hua hoga nah — −1R pe mara hai, +3R pe
> mara hai, bas"

A window is supposed to end at −1R, at +3R, or at 16 days. So: what does the
duration distribution actually look like, and **is the 16-day cap removing
windows that were still working?**

## Answer: the cap binds on a small tail, and that tail is the productive one

| duration | champ IS | champ OOS | utcsat OOS |
|---|---|---|---|
| p50 | 1.11 d | 1.06 d | 1.18 d |
| p90 | 9.96 d | 7.19 d | 7.99 d |
| **max, capped** | **16.00 d** | 16.00 d | 16.00 d |
| **max, uncapped** | **98.10 d** | **76.82 d** | 76.82 d |
| legs at the 16d cap | 19/309 (6.1%) | 9/194 (4.6%) | 9/194 (4.6%) |

**So the honest answer to the question: no, most windows are short — the
median is barely over a day — but the tail runs to three months.** The 16
days is not a representative window life, it is a ceiling, and only 5–6% of
legs are anywhere near it.

## What the cap actually kills

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| windows truncated | 12 | 3 | 12 | 3 |
| life if uncapped | p50 2.6 d, max 44.2 d | max 3.5 d | max 44.2 d | max 3.5 d |
| reached +3R | 2 (17%) | 2 (67%) | 2 (17%) | 2 (67%) |
| **died at −1R** | **10 (83%)** | 1 (33%) | **10 (83%)** | 1 (33%) |
| **those HTF legs, total** | **−4.0R** | +5.0R | −4.0R | +5.0R |
| **extra LTF trades they allowed** | **176, +88.2R** | **70, +40.7R** | 160, +38.0R | 60, +67.1R |

## The finding

**Ten of twelve truncated windows died at −1R — and the LTF trades taken
inside them while they were still open were worth +88.2R.** The parent leg's
own outcome was −4.0R. The money was never in the leg.

**This inverts what the cap was assumed to be.** The queue treats the 16-day
cap as a risk control. It is not. It is a brake on the only thing that
makes money: closing a window at −1R also closes the LTF layer inside it, and
those LTF entries were profitable.

There is a second effect that makes the same point. Uncapped, the book has
**fewer** HTF legs (309 → 226 in champion IS) because a long window blocks
its successors — yet **more** LTF trades (500 → 586). Trades per window goes
from **1.6 to 2.6**. The long windows are not idle; they are the ones that
keep producing, and the cap removes them systematically.

## Honest limits — these matter and are not buried

- **+75.3R / +55.1R / +13.7R / +78.5R is still well inside M = 193.4R.**
  Real, 4/4, and not a pass.
- **A 98-day window is three months of directional exposure.** The engine has
  no rule that would stop a bias persisting that long, and the fact that it
  made money here does not make it safe. This is the strongest argument
  *against* turning the cap off, and it belongs next to the +75.3R.
- **P49's sweep was not monotone** — `cap_days=24` is anomalously bad in both
  OOS cells while 20 and 32 on either side are fine — so a single good value
  is partly noise. The direction is the finding, not a number.
- **The cap binds on only 5–6% of legs**, so this is a small-sample effect
  even though its net looks large.

## What this suggests, and what it does not

**Suggests:** the window should be allowed to run to its own −1R/+3R
resolution, and the 16 days removed as a parameter that has never earned its
place. The legs the cap kills are unprofitable; the trades inside them are not.

**Does not suggest:** that a 98-day directional window is acceptable to hold.
The right next question is whether some *finer* ceiling — on age, or on
drawdown within the window — captures the win without the three-month
exposure. That is a new experiment, not a result.

The engine also offers no mechanism for a window that simply never resolves:
with the cap off, a bias can persist indefinitely, and this dataset says the
rare long ones paid. That is an observation about 2021–2024, not a property
to rely on.
