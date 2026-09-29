# P15 — brutal test of `decay<0.75`. Causality proven; one falsifier fires.

`exp_gray_brutal.py`. Pins reproduced first. Spec followed exactly:
**GRAY the signal, no new trade, no shift, survivors keep their own entry,
exit and R.**

## PART A — causality, proven not asserted

One real greyed trade, dumped in full so it can be checked by hand
against the raw CSV.

```
trade entry_ts = 1674181800  (2023-01-20 08:00:00)  dir=long  r=2.164R
decay AT that instant = 0.75  ->  GREY

leg#  confirmed (UTC)          its low    worst low after conf, UP TO entry   broken?
0     2023-01-16 03:00         20303.0         20385.0                        no
1     2023-01-17 05:15         20667.0         20385.0                        YES
2     2023-01-17 14:30         20824.5         20385.0                        YES
3     2023-01-18 04:00         20985.0         20385.0                        YES

broken = 3 of 4  ->  decay = 0.75   MATCHES
last 1m bar read = 2023-01-20 02:30
```

**The last leg confirmed 2023-01-18 04:00 — nearly two days before the
2023-01-20 08:00 entry.** The worst low used is 20385.0, measured only up
to the entry bar. The decay fraction recomputed by hand from the printed
table equals the engine's value exactly.

**This is not hindsight.** The information was on the screen two days
before the trade was taken.

## PART B — robustness

| IS | n | net | WR | PF | DD | R/trade |
|---|---|---|---|---|---|---|
| champion | 500 | +356.9R | 30.0% | 2.38 | 17.8R | +0.890 |
| **greyed** | **307** | **+383.9R** | **33.6%** | **3.34** | **13.8R** | **+1.427** |
| the greyed-out set | 193 | −27.1R | 17.6% | 0.79 | — | −0.140 |

**The 193 greyed trades are 17.6% WR and NET NEGATIVE.** They are not a
mixed bag being trimmed — they are a genuinely bad cohort. **R/trade
improves 60%, from +0.890 to +1.427.**

### 1. By calendar year — **falsifier (a) FIRES**

| year | champion | greyed | |
|---|---|---|---|
| 2023 | +95.0R (107) | **+113.2R (69)** | ✅ |
| 2024 | +93.9R (161) | **+116.3R (102)** | ✅ |
| **2025** | **+79.2R (130)** | **+56.9R (79)** | ❌ **WORSE** |
| 2026 | +88.8R (102) | **+97.6R (57)** | ✅ |

**2025 gets worse, −22.3R.** 3 of 4 years improve, one degrades. **This is
a real blemish and it is reported rather than averaged away.** It also
matches P8's finding that every IS year sits inside its own null, so no
year-level conclusion was ever resolvable.

### 2. By direction — **both sides improve, not one-sided**

| | champion | greyed |
|---|---|---|
| **long** | 273t +291.3R, WR 31.9%, PF 3.01, **DD 20.1R** | 193t **+291.2R**, WR 34.2%, **PF 3.81, DD 9.7R** |
| **short** | 227t +65.6R, WR 27.8%, PF 1.69, DD 23.8R | 114t **+92.7R**, WR 32.5%, **PF 2.58**, DD 18.5R |

Falsifier (b) does not fire. **Longs keep the same net with 80 fewer
trades and half the drawdown; shorts improve by +27R.** The mechanism is
not "shorts were the problem."

### 4. Ex-top-5 — **falsifier (c) does not fire**

| | n | net | WR | PF | R/trade |
|---|---|---|---|---|---|
| champion ex-best-5 | 495 | +138.9R | 29.3% | 1.70 | +0.457 |
| **greyed ex-best-5** | 302 | **+165.8R** | 32.5% | **2.17** | **+0.726** |

**With the 5 best trades removed, the greyed book still beats the
champion by +27R** and improves R/trade by 59%. **The gain is not the tail
moving — the body of the book genuinely improved.**

### 6. Threshold plateau — **falsifier (d) does not fire**

| threshold | n | net | WR | PF |
|---|---|---|---|---|
| decay < 0.5 | 164 | +88.6R | 29.3% | 2.10 |
| **decay < 0.6** | **307** | **+383.9R** | **33.6%** | **3.34** |
| decay < 0.7 | 307 | +383.9R | 33.6% | 3.34 |
| **decay < 0.75** | **307** | **+383.9R** | **33.6%** | **3.34** |
| decay < 0.8 | 431 | +397.5R | 31.6% | 2.74 |
| decay < 1.01 (all) | 500 | +356.9R | 30.0% | 2.38 |

**0.6 / 0.7 / 0.75 are literally the same trade set** — decay only takes
values 0, 0.25, 0.5, 0.75, 1.0, so anything in (0.5, 0.75] is the same
arm. **That is a plateau in the only sense that matters here: the arm is
insensitive to where in that band the threshold sits.** No threshold was
tuned inside the gap.

## Scorecard

| falsifier | result |
|---|---|
| (a) no year worse | ❌ **2025 is −22.3R worse** |
| (b) not one direction | ✅ both sides improve |
| (c) ex-top-5 holds | ✅ +165.8R vs +138.9R, R/trade +59% |
| (d) threshold plateau | ✅ 0.6–0.75 identical trade set |
| causality | ✅ **proven**, two days of information before entry |

## The honest verdict

**This is a real effect, not a grid artifact — but it is not a clean
pass.**

Against it: **2025 degrades.** That is a pre-registered falsifier firing,
and it should be reported as such rather than averaged into a headline.

For it, and these are the parts that survive the worst scrutiny:
- the **greyed cohort is 17.6% WR and net negative** — not a marginal
  trim
- **R/trade up 60%** and **DD down 23%**
- **both directions** improve, so it is not a side effect
- **ex-top-5 the greyed book still wins by +27R**, so the body improved
- **the threshold is not fitted** — 0.6, 0.7 and 0.75 are the same arm
- and the strongest one: **P11 predicted this direction with no bar in
  mind**, before any of this was searched

**Still not adoptable.** The 2025 regression, plus the fact that this
threshold was chosen from a grid, means the only thing that would settle
it is the **forward slice at n≥50** — the one arbiter that has not been
used to select anything.

**Recommended next step: freeze `decay < 0.75` exactly as it stands and
run it on the forward window.** No further tuning. If it holds there,
adopt; if not, it goes in the graveyard next to `exp_trail_half` and
`partial_r` with a note that it looked excellent on paper.
