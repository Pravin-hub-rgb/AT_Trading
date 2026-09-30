# P2 — risk-weighted concurrency

> Queue: "cap the **sum** of open risk instead of counting open positions …
> cheapest real edge candidate." Status: **run, premise valid, no edge.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Harness `exp_risk_concurrency.py`.

## Premise: valid, and for a reason nobody expected

I expected the book to be strictly serial and wrote that assumption into
the harness header. **It is not.** Max concurrent open positions:

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| max concurrent | **6** | **5** | **6** | **3** |

So there *is* something for a risk-sum to weigh, and the queue item was
right to exist. The measurement beat the assumption, in the item's favour.

## Why it is not serial — an engine finding

`v18_streak_halt.py:743`:

```python
busy_until = candles_ltf[exit_idx]["date"]     # DATE string, e.g. "2021-05-03"
```

and `:405` `:577`:

```python
bar_time = sig["bar"]                          # DATETIME string
if busy_until and bar_time <= busy_until: continue
```

One side is date-granular, the other datetime-granular, and they are
compared **as strings**:

```
"2021-05-03 14:00:00" <= "2021-05-03"   ->  False
```

The guard therefore does **not** block re-entry on the exit day, so a new
entry can fire on a 15m bar that is still *before* the previous trade's
exit bar. That is where the 3–6 concurrency comes from.

**Recorded, not fixed.** It is a real inconsistency, but the book is
profitable with it and the champion is pinned at 500t/+325.8R. Changing it
would move the control, which every harness here refuses to do. Worth a
separate experiment on its own merits, not as a footnote to this one.

## The gradient is real and consistent

Stop distance as a percentage of entry price, split at the median:

| | tight half | PF | wide half | PF |
|---|---|---|---|---|
| champion IS | +300.0R | **3.17** | +25.8R | 1.39 |
| champion OOS | +51.6R | **1.75** | +18.6R | 1.38 |
| utcsat IS | +300.7R | **3.35** | +58.2R | 1.67 |
| utcsat OOS | +43.7R | **1.72** | +16.5R | 1.38 |

**Tight-stop trades are far better in all four cells.** Wide stops carry a
worse PF everywhere. This is a genuine, well-behaved ordering.

## And no brake can extract it

Skip the widest X% of stops by distance:

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| skip widest 50% | −25.8R | −18.6R | −58.2R | −16.5R |
| skip widest 30% | −23.7R | −17.6R | −20.7R | +4.0R |
| **skip widest 10%** | **+11.2R** | **+2.4R** | **+13.3R** | **+4.5R** |
| keep widest 50% only | −300.0R | −51.6R | −300.7R | −43.7R |

**`skip widest 10%` is 4/4 positive** — and that is the graveyard brake
lesson landing exactly as predicted: the wide trades are *worse* but still
**profitable**, so every threshold that binds spends more than it earns.

### The number that settles it

The queue already fixed the bar: **M = 193.4R** is the `|dNet|` whose null
95th percentile is exceeded (block bootstrap, length 20, 10,000 draws).

The best arm here reaches **+13.3R** — about **1/15 of M**. Every cell of
every arm is an order of magnitude inside the null. The gradient is real
*and* irrelevant: the trades it would remove are small, and there are many
of them.

## Verdict

**No adoption.** The item's premise was sound and its blocker was, as the
queue said, wrong. But the effect it points at is a quality ordering, not
a removable loss, and quality orderings have repeatedly failed to convert
in this repo.

Recorded for the register: max concurrency is 3–6, not 1, because
`busy_until` is a date compared against a datetime as strings.
