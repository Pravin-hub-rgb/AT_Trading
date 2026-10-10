# The window floor, the leak it exposed, and what a negative half-year actually is

Date: 2026-10-10. Harnesses: `exp_window_floor.py`, `exp_window_floor_causality.py`,
`exp_window_leak.py`, `exp_neg_vs_pos.py`.

Three findings. The first is a bug in the shipping book. The second settles a
question the whole cycle was built on.

---

# 1. The window floor was never a knob — and it had a hole in it

`unified.py` carried a literal `s + 2700` gate. It was never a parameter, so it
had never been swept. It is now `exp_window_floor_s`, default **2700**, and the
default reproduces every pin byte-identically (`exp_fastcheck` PASS).

**Sweeping it down looks wonderful, and it is a lookahead.**

| floor | trades | net | negative cells |
|---|---:|---:|---:|
| **0** | 859 | **+793.2** | **0** |
| 900 | 855 | **+801.1** | **0** |
| 1800 | 847 | +782.0 | 0 |
| 2700 (shipped) | 839 | +773.0 | 1 |
| 3600 | 833 | +778.7 | 1 |
| 7200 | 821 | +778.7 | **0** |
| mode `fs` | 859 | **+793.2** | **0** |

`floor 0` looks like the best result in the sweep. It is also the exact number you
get from **trading before the HTF window candle closed.**

## why 2700 is arithmetic, not a tuning value

`s` is the window start, which is the entry bar's **open** timestamp. C15's own
comment says the start is knowable from the flip candle **close**, which is
`s + 3600` on a 1h plane. An LTF entry is knowable at `bar_ts + 900`. So an entry
can honestly be inside the window only when

```
bar_ts + 900 > s + 3600      =>      bar_ts > s + 2700
```

**2700 is `(3600 − 900)`.** It is not a number someone picked; it is the difference
between when the HTF candle closes and when the LTF bar inside it settles.

The gate is written as `_floor < entry_ts`, so it admits any entry in
**`(s + 2700, s + 3600]`** — a 900-second band in which the entry is knowable but
the window candle has not closed. **The shipped gate should have been `s + 3600`.**

## the leak, measured

`exp_window_floor_causality.py` counts entries whose knowable instant precedes the
window candle close:

| arm | trades | net | leaked entries |
|---|---:|---:|---:|
| floor 2700 (shipped) | 839 | +773.0 | **6** |
| floor 0 | 859 | +793.2 | **28** |
| floor 900 | 855 | +801.1 | **24** |
| mode `fs` | 859 | +793.2 | **28** |
| mode `max` | 839 | +773.0 | 6 |
| **floor 3600** | 833 | +778.7 | **0** |
| **floor 7200** | 821 | +778.7 | **0** |

**Every leaked trade is exactly 900 seconds early.** Not scattered — a clean
off-by-one-bar, which is what confirms it is arithmetic rather than something
pathological.

## what the leaked trades are worth

| entry | era | R |
|---|---|---:|
| 2022-03-19 | OOS | −1.27 |
| 2022-08-24 | OOS | −1.13 |
| 2022-09-10 | OOS | −1.06 |
| 2023-05-13 | IS | −1.22 |
| 2025-03-10 | IS | −1.06 |
| 2026-08-28 | IS | **+1.00** |
| | | **−4.73R** |

**The leak costs the champion 4.73R.** Five of six are losers. Correcting it makes
the book *better*, not worse — which is a rare and useful shape for a
correctness fix to have.

## the leak is in every fsent book

| book | trades | leaked | worth |
|---|---:|---:|---:|
| `champ_long` | 839 | 6 | −4.73R |
| `mcloff` | 912 | 7 | −5.29R |
| `mcloff_htf15` | 859 | 7 | −4.45R |
| `htf15` | 800 | 6 | −4.38R |
| `htfesmcl4` | 1230 | 4 | **+8.80R** |
| `champ_short` | 844 | 6 | **+3.87R** |
| `sig_multi` | 523 | 2 | −0.20R |
| `sig_full` | 385 | 2 | −0.20R |

**On `htfesmcl4` and `champ_short` the leak flatters them.** That is worth knowing
before either is compared against a corrected book.

## registered: `fsent_champ_long_causalfloor`

IS 513 / +529.84 / 13.62 · OOS 308 / +248.90 / 11.88 · **zero leaked trades**

**Two honest caveats.** 7200 was chosen from a sweep and is the only value clearing
both the leak and the negative cell, so it carries selection pressure. **The causal
minimum is 3600**, which also removes every leaked trade but keeps `2025-H1`.

And nothing is adopted: a 15-minute head start on 6 trades out of 839 that happens
to cost the book money is a bug to note, not an emergency to re-ship over.

---

# 2. What a negative half-year actually is

The owner asked for an autopsy of the negative cells against the positive ones.
**155 cells across 13 books.**

| | cells | R/trade | win rate | payoff | **loss concentration** | **max losing streak** |
|---|---:|---:|---:|---:|---:|---:|
| **negative** | **6** | −0.028 | 33.5% | 1.88 | **35.2%** | **8.3** |
| **positive** | **149** | +1.128 | 39.6% | 4.92 | **36.1%** | **8.1** |

**The two columns are the same on the two dimensions that would distinguish a
regime:**

- **Loss concentration 35.2% vs 36.1%.** A real bad regime concentrates its damage
  in a few trades you could identify and avoid. These do not — the loss is spread
  exactly as evenly as in the good cells.
- **Losing streak 8.3 vs 8.1.** The negative cells do not run longer losing
  sequences. They are not worse stretches.

**A negative half-year is not a regime. It is the book's normal +1.13R/trade
expectancy producing a few fewer winners than usual, in a book whose single trades
swing ±4.3R.**

**6 of 155 cells is 3.9%** — about what you expect from a book with this
expectancy and this spread landing red by chance.

**There is nothing in the negative cells to filter for.** Every knob tried this
cycle that produced a clean table did it by removing trades, not by finding a
condition — which is exactly what `biasmom05` did, and its period control came back
at **b = −0.94, t = −9.63**.

---

# 3. The loss-run fix is not "set it to 0" — it varies by book

The champion fix generalised, but not uniformly:

| book | as-is | mcl=0 | mcl=2 | mcl=4 | mcl=6 |
|---|---|---|---|---|---|
| `champ_long` | 1 neg | ✅ **0** | 1 | ✅ **0** | ✅ **0** |
| `mode_fd` | 1 neg | ✅ **0** | 1 | ✅ **0** | ✅ **0** |
| `flip_quality` | 1 neg | ✅ **0** | 1 | ✅ **0** | ✅ **0** |
| `utcsat_short` | 1 neg | ❌ still neg | ✅ **0** | ✅ **0** | ❌ still neg |
| `utcsat_long` | 1 neg | ❌ still neg | ❌ | ✅ **0** | ✅ **0** |
| `utcsat_trailhalf` | 1 neg | ❌ | ❌ | ❌ | ❌ |

**`utcsat_trailhalf` is immune to every value.** Its `2025-H1` needs a different
fix, and the honest answer is that it may not have one.

And the champion-family books are fixed at **0, 4 or 6 but not 2** — so "turn it
off" is one point on a plateau, not a law.

---

# What this changes

**The cycle's central claim survives, and is now sharper.** The negative half-year
was never a market problem — five of six books were profitable in `2025-H1` — and
it is not a book problem either. It is the distribution of a book with real
expectancy and large per-trade variance, and the only lever that moves it is
behavioural (stop cutting recovery trades), not predictive (find the regime).

**One real bug surfaced while looking for it**: a 900-second entry band on the
start side of every fsent window. Small, and on the shipping book it costs rather
than flatters — but it was not known before the floor became a parameter, and two
of the eight books benefit from it.

---

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS,
one negative half-year, window floor 2700 untouched.*