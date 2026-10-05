# ARE THE BIG WINS SPREAD EVENLY? And what cushion that implies

**Date:** 2026-09-27 · **Harness:** `exp_win_spacing.py` → `_win_spacing.json`
Champion baseline. Thresholds are the repo's own — 3R+, 5R+ (LOSS_AUTOPSY /
EQUITY_CURVE_STUDY) and 10R+ ("monsters", 17 trades in champion IS).

**Not chosen here.** They already exist in the docs, so nothing was picked to
make the answer look better.

---

## 0. The question

The walk showed that long underwater stretches happen. It did not show whether
the big wins arrive on a schedule or in clumps. That distinction decides sizing:

- **evenly spaced** → a book you can size to a known drawdown
- **clumped** → a book where the gap is unbounded and the only defence is a
  small enough lot

## 1. The numbers

| era | thr | wins | % of book | % of net | med gap | **max gap** | **max days** | worst gap R | **cushion** | worst gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| IS | 3R+ | 61 | 12.2% | 197.0% | 5.0 | **25** | 99 | −23.8 | **−23.8** | tr 468→494, 63d |
| IS | 5R+ | 41 | 8.2% | 173.7% | 11.0 | **30** | 99 | −23.8 | **−23.8** | tr 468→494, 63d |
| IS | 10R+ | 17 | 3.4% | 125.2% | 31.0 | **78** | 232 | −24.1 | **−24.1** | tr 7→50, 151d |
| OOS | 3R+ | 28 | 10.0% | 313.2% | 4.0 | **60** | 138 | −37.2 | **−37.2** | tr 46→107, 138d |
| OOS | 5R+ | 17 | 6.1% | 255.8% | 1.0 | **94** | 231 | −37.1 | **−42.7** | tr 46→141, **231d** |
| OOS | 10R+ | 5 | 1.8% | 133.0% | 42.0 | **157** | **408** | −45.7 | **−45.7** | tr 21→179, **408d** |

`cushion` = the largest R decline that occurred *between* two consecutive
qualifying wins — i.e. what the equity had to absorb, and for how long, before
the next one arrived. This is the real cushion requirement, and it is a
different number from the book max drawdown because the max DD may already be
partly filled.

## 2. The answer: the wins are NOT evenly spread

Three things, and they are the reason this is a patience game rather than a
statistical one.

**1. The median gap is short. The max gap is enormous.**

- IS 3R+: median gap **5 trades**, max gap **25** — 5× the median
- IS 10R+: median **31 trades**, max **78**
- **OOS 5R+: median gap 1 trade, max gap 94** — a 94-trade wait after a
  one-trade wait
- **OOS 10R+: 5 wins in 279 trades, gaps up to 157 trades / 408 days**

A book whose typical wait between 5R+ wins is *one trade* but whose worst wait
is *231 days* has no usable schedule. You cannot size against a distribution
with a 5× tail in it, because the tail is where you live.

**2. Between OOS trades 46 and 141 there was a 231-day stretch with no 5R+ win
at all**, and the equity fell **−42.7R** across it (Apr 2021 → Dec 2021). That
is the single most important line in this document. It is the whole "first nine
months nothing" experience, measured rather than described.

**3. The monsters are the whole book, and they are the rarest.**

- IS: 17 trades ≥10R carry **125.2%** of net (3.4% of the book)
- OOS: **5 trades** ≥10R carry **133.0%** of net (1.8% of the book)
- OOS: those 5 monsters were up to **157 trades / 408 days** apart

So on OOS the strategy ran for **over a year** between monster arrivals. Any
cushion sized on "average monster interval" would have failed.

## 3. What this means for the cushion

The existing studies each measure a piece. Together they now form one picture:

| what you have | what it gives |
|---|---|
| leverage sweep | how many R the account can survive per trade |
| max drawdown (IS 27.7 / OOS 53.2) | worst peak-to-trough on a whole book |
| longest losing streak (16 / 15) | worst run of consecutive −1R |
| decile walk (7 / 17 blocks underwater) | how long a flat stretch *feels* like |
| **win spacing (this one)** | **how long you wait for the trade that pays, and how much it costs to wait** |

The gap-not-filled cushion is the largest of the lot:

| | IS | OOS |
|---|---:|---:|
| longest losing streak | 16.0R | 15.0R |
| book max drawdown | 27.7R | 53.2R |
| **cushion between 5R+ wins** | **23.8R** | **42.7R** |
| **cushion between 10R+ wins** | **24.1R** | **45.7R** |

**The cushion you need is ~24R in a normal era and ~43–46R in a stressed one**,
and in the stressed era it must be held for **up to 231–408 days**. That is the
honest number. It is roughly 1.6× the IS max drawdown and 0.8× the OOS one — but
it is the number that actually describes the *waiting*, and it is not visible in
any of the other four studies.

**Practical translation:** at 1R fixed risk, the account must be able to sit
through roughly 25 consecutive-R losses of drift (IS) and ~45 (OOS) without a
new monster arriving, over a period that can exceed a year. The lever is
therefore **lot size relative to that cushion**, not any entry filter — which is
the same conclusion `method/IS_IT_RIGHT.md`, `method/TAIL_RISK_AUDIT.md`, `method/DECILE_WALK.md` and
`START_SENSITIVITY.md` each reached independently, now with the mechanism
measured rather than inferred.

## 4. Honest limits

- **IS max gap (25–78 trades) is much shorter than OOS (60–157 trades).** Part of
  that is era and part is sample size: IS has 500 trades and 17 monsters, OOS has
  279 and 5. With n=5 monsters the max gap is barely a statistic. Treat the OOS
  10R+ row as **one observed instance, not an estimate**.
- The 3R+ cushion (~24R IS / ~37R OOS) and the 5R+ cushion (~24R / ~43R) are
  close, which is reassuring: the wait is not specific to one threshold.
- This measures the *spacing that occurred*, not a distribution to extrapolate.
  It says the worst observed wait was 231 days. It cannot say the next one will
  not be longer.
- Both periods are heavily inspected (Rule 4). No unseen regime has been
  measured.

**No production change.** `backend/` untouched.
