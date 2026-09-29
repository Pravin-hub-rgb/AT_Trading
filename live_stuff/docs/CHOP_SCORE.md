# CHOP SCORE — the "which side" thesis, end to end

> Status: **CLOSED, nothing adopted.** 4 experiments, ~130 arms.
> Champion unchanged: **500t / +325.8R IS**, **279t / +70.1R OOS**.

## The thesis, in the author's words

> "prev n swing judge karenge rolling like 10, 20... jyada recent utna acha...
> agar clearly buying swing ke lows break nahi hue hain toh bullish ka sign hai,
> ya phir selling swing bhi hai aur uske high break hai toh bhi bullish...
> vice versa"

## The feature

Take the last **N swings of both kinds**, in chronological order. For each,
ask whether its own defence held:

| leg | test | means |
|---|---|---|
| buying | low not broken since confirm | bullish |
| selling | high broken since confirm | bullish |

```
score = (buying intact + selling broken) / N - 0.5     in [-0.5, +0.5]
```

Both facts point the same way — buyers holding support, or sellers being
taken out. The mirror is bearish.

**Causality**: only legs confirmed at or before the entry; the window is
chronological so no future swing can enter it. Break tests use candles at or
before the entry only.

## Why this thesis was worth building

`decay_pair()` already returns `(broken_up_frac, broken_dn_frac)` and **every
caller in the repo throws the second value away** (`v, _ = decay_pair(...)`).
This is the only construction in the project that uses both halves.

**It is not the decay feature.** Decay counts broken *buying* legs and
answers **"sit out"**. This counts *both* sides over a rolling window and
answers **"which way"**. Different animals, tested separately and together.

---

## P39 — 15m score as a side gate · `exp_chop_side.py`

LONG only when score > thr, SHORT only when score < −thr.
N ∈ {4,8,12,16,24,32}, thr ∈ {0,.1,.2,.3}. Champion + utcsat, both eras.

### Result: **0 of 32 arms positive.** Not one cell, not one arm.

| N | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 4 | −172.0R | −51.9R | −191.5R | −57.4R |
| 16 | −81.6R | −34.4R | −100.2R | −53.5R |
| 24 | −27.3R | −28.7R | −60.2R | −53.6R |
| 32 | **−10.2R** | −37.1R | −48.7R | −49.1R |

**Partial confirmation of "zyada recent utna acha"** — larger N is
monotonically less bad, 32 swings ≈ 3–4 days:

| N | champion IS dNet |
|---|---|
| 8 | −235.0R |
| 16 | −81.6R |
| 24 | −27.3R |
| 32 | **−10.2R** |

But "less bad" is still negative. At N=32 thr=0.20 the champion OOS survivors
had **PF 3.70** against the champion's own 1.59 — the filter was cutting
*good* trades.

### Why

The 1h window already fixes direction, and **100% of trades match their
window's direction** (log 104 anatomy). A second direction decision at 15m
can only *remove* trades. It never adds information.

---

## P40 — five rewrites · `exp_chop_brainstorm.py`

1. **STRENGTH** — keep the window's side, require |score| large
2. **AGREES** — 15m character agrees with the 1h window
3. **DISAGREES** — the inverse
4. **SCORE × DECAY** — the two features combined
5. **ASYMMETRY** — is the window built from buying or selling legs

### Result: **0 of 11 arms positive in both eras.**

| idea | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 1 STR \|s\|>0.10 | −68.8R | +25.1R | −52.4R | +11.3R |
| 2 AGREES | −57.5R | −45.1R | −94.1R | −64.6R |
| 3 DISAGREES | −268.3R | −25.0R | −264.9R | +4.4R |
| 4 score + decay | −32.6R | +6.9R | −48.1R | +6.4R |
| **4 decay alone** | **+34.2R** | **+7.5R** | **+3.8R** | **+9.9R** |
| 5 mostly BUYING legs | −43.9R | −72.4R | −35.6R | −49.9R |

**The most useful row is #4, twice.** Adding the score to decay makes decay
*worse* in three of four cells. Decay alone beats the combination everywhere.

**AGREES is the most intuitive idea and it lost 4/4** — even though it is the
only one asking a question the engine has never asked.

---

## P41 — the same score, read on the **1h** chain · `exp_score_1h.py`

The correction that mattered. P39/P40 built the score on 15m, where it can
only filter inside a window that already knows its direction. The **1h** read
is available *while the window is still open*, so it can question the window
instead.

**GATE** (agree), **FLIP** (take the other side), **STR** (|score| large).
N ∈ {4,8,12,16,24}.


---

## P42 — the whole line closed · `exp_chop_final.py`

Three things at once.

### PART 1 — 1h conviction × 15m decay

The best IS number of the entire thesis:

| N | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 8 | **+43.0R** | −54.2R | −48.1R | −55.3R |
| 10 | −1.0R | −49.9R | — | −54.8R |
| 12 | −12.5R | — | — | −48.8R |

`1h |s|>0.10 AND decay<0.75` at N=8, champion IS: **PF 3.92, DD 11.4,
249 trades, +43.0R.** That is the high-water mark of the thesis.

It is also the arm that collapses hardest in OOS (−54.2R). **The best IS
result and the worst OOS result are the same setting.**

### PART 2 — re-decide the whole book from the character

The hardest version: **ignore the 1h window entirely**, take the side the
score says is strong. If direction is the whole edge and the character can
read direction, only this could show it.

**Result: 0 of 12 arms positive.** Best is utcsat OOS N=10 at +2.2R, inside
noise on 81 trades.

```
champion IS  N=8  −256.9R      champion OOS  N=8  −65.3R
utcsat   IS  N=8  −252.0R      utcsat   OOS  N=8  −64.1R
```

### PART 3 — GRAY vs SKIP · **THIS ARM IS INVALID**

`SKIP 1h-weak losers` printed **+645.2R, PF 12.27, 69.4% hit**.
**This is label leakage, not a finding.** The selection was:

```python
lost = [t for t in tr if abs(t[k] or 0) > 0.10 and float(t["r_multiple"]) < 0]
```

It read the realised R to decide which trades were losers. The GRAY version
of the same arm is contaminated identically and its −59.3R is equally
meaningless. **Both numbers are discarded, not merely unadopted.**

The valid GRAY/SKIP comparison uses decay only, and it **reverses P33**:

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| decay SKIP | **+34.2R** | +7.5R | **+3.8R** | **+9.9R** |
| decay GRAY | −7.1R | — | −32.5R | −3.5R |

**SKIP beats GRAY 4/4 here, where P33 found GRAY better.** The difference is
breadth: P33 grayed a narrow stale-leg slice; this grays every trade with
decay ≥ 0.75, winners included. GRAY only pays when the gray set is mostly
winners. Otherwise deleting the losers outright wins.

---

## Verdict

**CLOSED. Nothing adopted. Champion unchanged.**

The thesis was tested in four places it could plausibly have worked:

| # | construction | result |
|---|---|---|
| 1 | 15m side filter | 0/32 |
| 2 | five rewrites | 0/11 |
| 3 | 1h conviction read | 1/40, IS only |
| 4 | full direction override | 0/12 |

The reason is structural and was visible from the first run: **the 1h window
is the authority on direction and the book is 100% consistent with it.** A
feature that reads direction has nothing left to decide. Decay survives this
line's entire assault because it answers a *different* question — not which
side, but whether to sit out at all.

**Every positive here is IS-only or OOS-only. Never both, on either lane.
That is the era-flip pattern, and it is why none of it ships.**

### Recorded, not hidden

- The unused second half of `decay_pair()` is still unused. This thesis was
  the only thing that ever wanted it, and it did not pay.
- N=4 makes any threshold below 0.25 inert.
- 1h FLIP is dead 10/10. Do not retry.
- 30m and 4h character reads were never tested. The 2h plane test (log 104)
  suggests other planes select a worse trade set, but that is about the
  window, not about this feature.

### Harnesses

`exp_chop_side.py` · `exp_chop_brainstorm.py` · `exp_score_1h.py` ·
`exp_chop_final.py`

### FLIP: dead, **0 of 10 arms positive.**

```
champion OOS  N=4  −83.0R      N=8  −83.1R
utcsat   OOS  all  −59 to −64R
```

Direction override does not work. Recorded so it is never retried.

### GATE: mixed, no win.

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| N=8 | −53.8R | −41.0R | −92.7R | −60.8R |
| N=12 | −56.9R | −29.4R | −90.3R | −49.8R |

PF is genuinely good in IS (2.92–3.15) but net is negative — cutting winners.

### STR N=8: the only arm that ever went positive

| | IS | OOS | PF (IS) | DD (IS) |
|---|---|---|---|---|
| champion | **+15.1R** | −55.0R | 2.69 | 16.6 |
| utcsat | **+14.3R** | −65.9R | 2.98 | 15.0 |

**Two IS cells positive, both OOS cells strongly negative.** Era-flip.

### An anomaly worth recording

At N=4 the threshold is inert — `|s|>0.1` and `|s|>0.2` select the **same
trades**. With 4 legs the score is one of {0, ±0.25, ±0.5}, so both reduce to
"score > 0". Anyone reading a single-N result without checking that is
reading a threshold that does not exist.
