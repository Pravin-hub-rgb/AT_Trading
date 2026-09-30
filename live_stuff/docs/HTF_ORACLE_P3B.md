# P3-B — can the 1h leg be read while the window is still open?

> `OPEN_RESEARCH_QUEUE.md:227` ranked this **#1 of all open items**.
> Status: **run, answered, nothing adopted.** Harness `exp_htf_oracle.py`.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The question

> "1h oracle ko jaldi padho - 1h leg state early read karke 15m layer ko
> real-time guidance do, phir dekho ki ye 1h window gate sach me strong hai
> ya nahi."

At the instant a 15m entry fires, where does the **hypothetical parent 1h
leg** currently stand? Parent entry `pe`, stop `psl`, `risk = |pe − psl|`,
read on fine 1m bars from the parent entry through the 15m entry timestamp:

```
long  leg:  (max high − pe) / risk
short leg:  (pe − min low)  / risk

DEAD    ≤ −1R        PROVED  ≥ +1.5R        NEUTRAL  otherwise
```

**Not `r_touch` again.** `r_touch` closed the window at the first 1.5R touch
and the LTF lost 130R. This closes nothing — it only reads, and the window
ends exactly as in the control.

## Run 1 was void, and the probe is why

The first run computed `(max_high − risk) / risk`, using `risk` where
`parent_entry` belonged. Every bucket was measured from a meaningless
baseline.

**The built-in causality probe caught it** — pushing the read +1h moved
**0/499** buckets, which read as "the read reads nothing" but was a broken
expression. Run 2 gives 24/499, 5/243, 23/453, 3/216 — small but non-zero,
so the read is genuinely reading. The probe stays in the file.

**Lesson matching log 119**: a run whose probe moves *nothing* is suspect,
not a result.

---

## Finding 1 — `DEAD` is structurally impossible

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| DEAD trades | **0** | **0** | **0** | **0** |
| `skip DEAD` dNet | +0.0R | +0.0R | +0.0R | +0.0R |

**Zero in all four cells.** A 15m entry only fires when the 15m swing breaks
with the window's direction, and at that moment the parent leg has not
reached −1R.

**Half the oracle is already implemented in the engine.** The LTF layer
*is* an implicit "parent still alive" filter. That state could never have
been new information.

## Finding 2 — only two states are reachable, and NEUTRAL is the better one

| | NEUTRAL n | NEUTRAL net | NEUTRAL PF | PROVED n | PROVED net | PROVED PF |
|---|---|---|---|---|---|---|
| champion IS | 310 | +231.0R | **2.56** | 189 | +93.6R | 2.10 |
| champion OOS | 156 | +91.9R | **2.20** | 87 | **−6.4R** | 1.07 |
| utcsat IS | 283 | +233.7R | **2.69** | 170 | +124.0R | 2.48 |
| utcsat OOS | 138 | +74.7R | **2.12** | 78 | **−1.1R** | 1.17 |

**NEUTRAL's PF is higher than PROVED's in all four cells.** Once the parent
leg is already +1.5R, the LTF trade is late.

## Finding 3 — both usable actions are 4/4 negative

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| only NEUTRAL (skip PROVED) | −94.8R | +21.8R | −125.3R | +14.5R |
| only PROVED (prove-it-first) | −232.2R | −76.5R | −234.9R | −61.3R |

**`only PROVED` closes W1's second arm** (queue W1: *"require the window to
have already cleared +1R before the 15m layer takes its first trade"*):
**−232.2 / −76.5 / −234.9 / −61.3. Dead 4/4.**

## The pre-registered falsifier

> *"ye live-oracle arm, wahi arm jo sirf window-open information use karti
> hai, se better hona chahiye - dono eras me."*

**The comparison could not be built.** `skip DEAD` retains 500/500 trades,
so it has no coverage to match an open-only arm against — the arm the
falsifier needs to beat does not exist as a distinct book. And of the two
arms that *do* select, both are 4/4 negative.

## What this does and does not settle

**Settled:** the early read is possible, causal, and carries no exploitable
information. One of its two states is already implemented in the engine.
**Not settled:** the queue's harder question — *"ye 1h window gate sach me
strong hai ya nahi."* This run shows the early read adds nothing. It does
**not** show the gate itself is hindsight-only. Those are separate claims
and only the second one would justify the programme's harder conclusion.

`NOIV` (no parent interval matched) is 36/279 OOS champion and 37/253 utcsat
OOS, ~1 in 7 — recorded, unexplained, not load-bearing for any arm here.
