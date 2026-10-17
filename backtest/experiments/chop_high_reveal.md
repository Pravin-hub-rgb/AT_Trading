# The one OOS reveal for the chop-high filter

Pre-registered before the era was opened:
`backtest/docs/method/CHOP_HIGH_FILTER_PREREG_2026_10_16.md`, commit 8dea64e.

| era | view | trades | net R | max DD | worst streak | R/trade |
|---|---|---:|---:|---:|---:|---:|
| IS | unfiltered | 497 | +466.92 | 25.08 | 12 | +0.9395 |
| IS | chop >= 10.39 | 249 | +217.21 | 11.37 | 9 | +0.8723 |
| IS | kept 50.1%, dropped 248 | | | | | |
| OOS | unfiltered | 281 | +215.32 | 11.20 | 7 | +0.7663 |
| OOS | chop >= 10.39 | 154 | +116.18 | 5.82 | 6 | +0.7544 |
| OOS | kept 54.8%, dropped 127 | | | | | |

## Verdict, by the rule written in advance

**B** - drawdown ratio 0.520 but net retains only 54.0%

A: dd ratio <= 0.65 and net retains >= 80% -> build a mode
B: dd ratio <= 0.65 and net retains < 80% -> trade-off, owner decides
C: dd ratio > 0.65 -> closed permanently, no engine work

The OOS era is now spent for filtering purposes, as the pre-registration
states. Books measured from here are measured on IS plus the forward window.
## What the verdict actually says

Verdict B means a trade-off, not an improvement, and the numbers deserve to be
read precisely rather than as a half-win.

The risk finding CARRIED. Drawdown ratio 0.453 in sample and 0.520 out of sample -
the pattern was real in both eras, which is not what happens to an artefact. That
part of C2 survived correction and should be recorded as a confirmed fact.

But the mechanism is worth stating plainly: the filter keeps about half the
trades, and the drawdown falls by about half. Per-trade quality does not improve
- it is flat to slightly worse in both eras (0.9395 -> 0.8723 in sample,
0.7663 -> 0.7544 out of sample). So the book is not better made, it is smaller.
Sitting out half the signals would halve the drawdown on any book; this does that
AND makes each remaining trade marginally worse, so it is not even a clean
re-sizing.

Net retained: 46.5% in sample, 54.0% out of sample, against a registration that
required 80%. Per the pre-registration this authorises no engine work.

The pre-registration asked for both sides to be presented and for the owner to
decide. The evidence for using it anyway is that drawdown is genuinely halved in
both eras, which matters if position sizing is set by drawdown rather than by
expectancy. The evidence against is that per-trade quality does not improve and
net per unit of capital committed falls, since the book is idle half the time.
