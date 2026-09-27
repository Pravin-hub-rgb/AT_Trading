# 5-MINUTE CONFIRMATION DELAY — the engine's own built-but-disabled gate

**Date:** 2026-09-27
**Harness:** `live_stuff/tests/exp_5m_confirm.py` → `_5m_confirm.json`
**Result: CLOSED. 0/36 cells significant. Enabling it costs 32–250R per book.**

---

## 1. What prompted this

The user's steer was that we had far more on the table than the 30m/2h plane,
and specifically named three directions: a smaller timeframe (5m) used to read
chop and gate 15m entries, the 2h/30m material, and **gray rather than skip**.

Recon of the **built** engine text (not the source) turned up something that
changes the shape of the question: the 5-minute gate was **already fully
implemented and switched off**.

```
exp_5m_confirm=0        <- the switch
exp_5m_wait_min=240     <- 4h bound on the wait
exp_5m_data=None        <- the 5m candle list
five_m_stats -> {"candidates","confirmed","stop_cancelled","timeout","delayed"}
```

Read carefully (built text ~L1466–1507), the shipped logic is:

* at a 15m signal, `entry_inst = ltf_bar_ts + 900` (the knowable instant);
* scan 5m bars whose **close** falls in `[entry_inst, entry_inst + wait]`, where
  a 5m bar stamped `t` closes at `t+300` — causally correct, matching the
  convention the whole programme uses;
* a bar **confirms** when its close breaks the extreme of the **previous 3** 5m
  bars: `close > max(prev 3 highs)` long, `close < min(prev 3 lows)` short.
  `if _exp_k < 3: continue` enforces the lookback exists;
* entry at that 5m bar's **open**, from the 1m fine data;
* if the stop is touched between signal and confirm, the trade is **cancelled**;
* `busy_until`, `cooldown_bars` and `exp_max_concurrent` are **re-checked at the
  new, later entry time**, so a delayed entry cannot silently stack.

This is a **delay with cancellation**, not a plain skip — structurally much
closer to gray, which is exactly what the user asked for. It was the one
candidate that could plausibly have dodged the slot-cascade problem. It does
not.

Data: 5m exists for `data/bybit` (389,309 bars), `data/unseen/bybit` (210,241),
and `data/btc` (388,201) — **not** for btc-fut, so replication uses `data/btc`.

## 2. Method

Fixed wait ladder `{60, 120, 240, 480}` min, whole grid reported, **no cell
selected**. Lanes `champion` / `utcsat` / `age10`, IS + OOS on bybit, plus
`data/btc` replication. Control reproduces the published book **exactly** in all
six bybit cells (asserted in code, not assumed).

`exp_5m_wait_min` is a real knob, so the pre-registered bar was: same sign in
both eras **and** trimmed-mean difference CI excludes zero in both **and**
replicates on `data/btc` **and** is consistent across the whole ladder.

**A note on the statistics, because the first version was wrong.** The first
`boot()` bootstrapped each book's trimmed mean *against zero* — i.e. "is this
book profitable?" — not the question being asked. It was caught by a smoke test
in which two halves of a single pool from the same distribution produced a CI
that excluded zero, which is impossible for a true null. Resampling *within*
each side measures each side's own mean, never the difference. Replaced with
`boot_diff(a, b)`, which resamples both sides independently and differences them.
Verified: true null straddles (p=0.064), identical books give p=0.95, a real
+1.2R shift excludes zero. **Every CI below comes from the corrected function.**



## 3. Results

`dNet` = gated net − control net.

### bybit IS (3.67y)

| lane | control | w60 | w120 | w240 | w480 |
|---|---|---|---|---|---|
| champion | n500 +325.8 | +75.9 | +76.9 | +104.0 | +104.0 |
| utcsat | n454 +358.9 | +98.0 | +131.6 | +135.5 | +135.5 |
| age10 | n130 +435.7 | +320.3 | +340.2 | +340.0 | +340.0 |

champion dNet: **−249.9 / −248.9 / −221.8 / −221.8**

### bybit OOS (2.0y)

| lane | control | w60 | w120 | w240 | w480 |
|---|---|---|---|---|---|
| champion | n279 +70.2 | +21.7 | +38.5 | +36.3 | +36.3 |
| utcsat | n253 +60.2 | +25.4 | +53.0 | +48.4 | +48.4 |
| age10 | n76 +43.2 | +42.0 | +38.0 | +36.9 | +36.9 |

champion dNet: **−48.5 / −31.7 / −33.9 / −33.9**

### Replication — data/btc

| lane | control | w60 | w120 | w240 |
|---|---|---|---|---|
| champion | n485 +210.9 | +83.0 | +84.4 | +76.1 |
| utcsat | n449 +233.8 | +104.8 | +108.9 | +107.7 |
| age10 | n126 +265.7 | +209.4 | +220.0 | +213.9 |

**VERDICT: 0/36 bootstrapped trimmed-mean difference CIs exclude zero.**

## 4. The mechanism — this is the actual finding

The null CIs and the enormous net loss are not in conflict. They say something
specific and important:

> The gate does **not** make the surviving trades worse. It makes the book
> **structurally more fragile**.

Top-5%-of-trades share of net (Rule 14):

| lane | control | gated (240m) |
|---|---|---|
| bybit/IS champion | 144.8% | **261.0%** |
| bybit/IS utcsat | 127.7% | **186.3%** |
| bybit/OOS champion | 221.7% | **338.0%** |
| bybit/OOS utcsat | 225.4% | 225.6% |
| btc champion | 179.5% | **254.5%** |
| btc utcsat | 155.5% | **177.5%** |

Concentration rises in 6/9 lanes and is flat in the other 3. The gate removes
~35% of trades (500→366 on champion IS) *without* removing the tail. So:

* per-trade quality of survivors — unchanged, hence the null CIs;
* book volume — down sharply;
* tail dependence — **worse**.

## 5. The second finding — a real accounting hole in the built engine

`exp_5m_confirm` re-checks slot state at the **later** entry time. The measured
funnel on champion IS at w60:

```
candidates        524
  timed out        76
  stop-cancelled   13
  survived        435
  became trades   329
```

**106 candidates — 20% of everything that got that far — were silently lost at
the slot re-check.** They are counted in no bucket of `five_m_stats`; the dict
has no field for them. Same pattern on bybit/OOS champion w60: 315 candidates,
50 tmo, 6 stopx → 259 survived → only 193 traded, **66 (21%) lost**.

Pushing an entry later does not merely delay it — it re-queues it into a
competition for a single slot, where a different trade may now be ahead of it.
**The slot is a scarce contended resource, and the cost of an intervention is
not "the trades it removes" but "what it does to the queue."**

This is exactly why gray beat skip by ~67R in the wick work (+28.1R vs −39.0R
IS), and it is why the S1–S6 composition studies could never have answered this
class of question — a composition study measures which trades exist, not what
happens to the slot afterwards.

## 6. Disposition

* **Not adopted. `exp_5m_confirm` stays 0.** The shipped 15m/1h strategy is
  unchanged.
* No production change. `exp_5m_data` / `exp_5m_confirm` were only ever passed
  from the harness; the engine source was not modified.
* The wait ladder is exhausted — w240 and w480 are byte-identical (`tmo=0`), so
  there is no rung beyond 240m to explore. This thread is closed for this gate.
* Per Rule 17 this does **not** reopen the 30m/2h agreement-predicates thread.
  The 5m gate is a different mechanism and a pre-existing engine hook.

## 7. What this redirects

The most valuable measurement in this run is §5, not the null. It says the next
experiments worth running are the ones that change **slot policy**, not entry
predicates. On the shelf, untested:

| knob | default | what it does |
|---|---|---|
| `exp_max_concurrent` | `0` | cap simultaneous LTF positions |
| `exp_window_r_cap` | `0.0` | rolling R cap |
| `exp_window_entry_cap` | `0` | rolling entry count cap |
| `exp_cohort_rearm` | `0` | rearm rule after a cohort loss |
| `exp_defer_h` | `0.0` | defer hours |
| `exp_chop15_lo/hi` | `0.0` | skip when the 15m chop series sits in a band |
| `exp_legskip_r` | `0.0` | leg-skip at an R threshold |

These are exposure brakes and queue rules, not "5m/2h predicates", so Rule 17
does not block them — and per §5 they act on the resource that actually
dominates the outcome. Full inventory: `ENGINE_SHELF.md`.

**Caveat that still binds everything:** the OOS has now been inspected heavily
across this programme. It is not untouched validation for anything new
(Rule 4). Any new predicate still needs genuinely fresh forward data.


**Why.** Requiring a 5m momentum break *before* entry means you only enter when
momentum is already visible on the fast tape. That is precisely the **late,
chased** end of the setup. The early entries — where the 15m swing signal fires
and no 5m momentum is yet visible — are the cheap, well-placed ones that become
the big winners. Waiting for confirmation systematically discards them and
keeps the ones you paid a worse price for.

This is the cleanest demonstration yet of why "wait for more confirmation" is
not a free safety upgrade on a trend system. **Confirmation is a price.**
