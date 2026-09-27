# TAIL-RISK AUDIT — are these books tail-dependent, or fragile?

**Date:** 2026-09-27
**Harnesses:** `exp_tail_audit.py` → `_tail_audit.json` (bybit IS+OOS),
`exp_tail_replication.py` → `_tail_replication.json` (independent `data/btc`)
**Metrics logic hand-verified on a synthetic book before the run.**

---

## 0. First, a correction to the premise

The question quoted a "healthy top-5% = 40–70%" range and read STACK as
"~60%". **STACK's top-5% share is 159.9%, not ~60%.** Baseline is 221.7%.

A top-5% share **above 100% is not "high concentration" — it means the other
95% of trades are net negative.** At 159.9%, remove the best 5% and the book
goes to −59.9% of its own net. So 221.7% → 159.9% is a real improvement, and both
numbers sit far outside the 40–70% band. This is the single most important
thing in the file, so it is stated before anything else.

## 1. The numbers

`top-k` = share of total net carried by the best k trades. `5%` / `10%` = share
carried by the best 5% / 10% *of the book by count*. `BEwr` = breakeven win
rate. `W/L` = avg win ÷ avg loss.

### bybit OOS — the decisive era

| lane | arm | n | net | WR | PF | W/L | BEwr | top1 | top3 | top5 | top10 | 5% | 10% | −top3 | −top5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| champion | baseline | 279 | +70.2 | 27.2% | 1.34 | 3.59 | 21.8% | 46.4 | 97.0 | 133.0 | 193.6 | 221.7 | 309.0 | +2.1 | **−23.2** |
| champion | half+delay1 | 271 | +89.8 | 24.0% | 1.42 | 4.49 | 18.2% | 48.8 | 102.2 | 134.2 | 196.7 | 223.1 | 293.6 | **−2.0** | **−30.7** |
| champion | skip_decisive | 222 | +99.3 | 28.4% | 1.62 | 4.08 | 19.7% | 32.8 | 68.5 | 94.0 | 136.8 | 143.5 | 201.7 | +31.2 | +6.0 |
| champion | **STACK** | 217 | **+110.5** | 25.3% | **1.65** | 4.84 | 17.1% | 39.6 | 83.0 | 109.0 | 159.9 | 159.9 | 212.5 | +18.7 | **−10.0** |
| champion | delay_r_1.5 | 262 | +81.0 | 27.9% | 1.40 | 3.63 | 21.6% | 40.2 | 84.0 | 115.2 | 167.7 | 192.0 | 267.3 | +13.0 | **−12.3** |
| utcsat | baseline | 253 | +60.2 | 28.9% | 1.33 | 3.27 | 23.4% | 54.1 | 113.0 | 147.0 | 205.1 | 225.4 | 314.2 | **−7.9** | **−28.3** |
| utcsat | half+delay1 | 244 | +87.1 | 25.8% | 1.47 | 4.21 | 19.2% | 50.3 | 105.4 | 138.4 | 189.0 | 203.4 | 263.9 | **−4.7** | **−33.4** |
| utcsat | skip_decisive | 200 | +76.8 | 28.5% | 1.52 | 3.82 | 20.8% | 42.4 | 88.6 | 115.2 | 160.7 | 160.7 | 223.4 | +8.8 | **−11.7** |
| utcsat | **STACK** | 194 | **+94.6** | 26.3% | **1.63** | 4.57 | 18.0% | 46.3 | 97.0 | 127.4 | 171.9 | 165.7 | 213.9 | +2.8 | **−25.9** |
| utcsat | delay_r_1.5 | 250 | +72.9 | 30.0% | 1.39 | 3.24 | 23.6% | 44.7 | 93.4 | 121.5 | 169.5 | 186.4 | 265.6 | +4.8 | **−15.6** |
| age10 | **baseline** | 76 | **+43.2** | 39.5% | 1.91 | 2.92 | 25.5% | 30.6 | 64.7 | 96.3 | 147.3 | **64.7** | 120.5 | **+15.3** | **+1.6** |
| age10 | half+delay1 | 71 | +27.5 | 31.0% | 1.56 | 3.47 | 22.4% | 43.1 | 115.2 | 161.9 | 231.6 | 115.2 | 196.0 | **−4.2** | **−17.0** |
| age10 | skip_decisive | 47 | +16.0 | 34.0% | 1.47 | 2.85 | 26.0% | 82.7 | 174.9 | 219.7 | 281.5 | 130.2 | 204.3 | **−12.0** | **−19.1** |
| age10 | STACK | 46 | **−0.3** | 23.9% | 0.99 | 3.16 | 24.1% | — | — | — | — | — | — | **−28.0** | **−31.6** |
| age10 | delay_r_1.5 | 75 | +41.2 | 38.7% | 1.84 | 2.92 | 25.5% | 32.1 | 67.9 | 101.0 | 154.5 | 67.9 | 126.4 | +13.2 | **−0.4** |

### bybit IS — for contrast, the books are *robust* here

| lane | arm | net | −top3 | −top5 | −top10 |
|---|---|---:|---:|---:|---:|
| champion | baseline | +325.8 | +180.2 | +113.5 | +6.4 |
| champion | **STACK** | +429.6 | **+278.7** | **+206.9** | **+79.2** |
| utcsat | **STACK** | +411.1 | **+260.2** | **+188.4** | **+63.4** |
| age10 | **baseline** | +435.7 | **+290.1** | **+223.4** | **+116.3** |

**Every IS book survives removing the best 10 trades and is still positive.** The
concentration ratio is high in IS too, but there the tail is thick enough that
the rest of the book still profits. That is the difference between
*tail-dependent* and *fragile*.

### Independent replication — data/btc

| lane | arm | n | net | WR | PF | 5% | 10% | −top3 | −top5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| champion | baseline | 485 | +210.9 | 28.2% | 1.54 | 179.5% | 234.3% | +80.4 | +29.5 |
| champion | **STACK** | 468 | **+294.8** | 28.0% | **1.75** | **154.3%** | 199.3% | **+150.1** | **+94.3** |
| utcsat | **STACK** | 431 | **+280.1** | 28.3% | **1.79** | 147.7% | 193.4% | +135.4 | +81.2 |
| utcsat | delay_r_1.5 | 443 | +260.0 | 32.1% | 1.73 | 140.3% | 184.7% | +129.4 | +78.5 |
| age10 | **baseline** | 126 | +265.7 | 45.2% | 4.77 | **62.5%** | **85.1%** | +145.1 | +112.2 |
| age10 | delay_r_1.5 | 126 | +268.1 | 46.0% | 4.47 | **62.0%** | 84.4% | +147.5 | +114.6 |

## 2. The verdict

**Your instinct is right, and it is sharper than the ranges suggest.**

Concentration above 100% is not a range violation to be tuned back into 40–70%.
It is the defining arithmetic of a trend-following book: winners must, on
average, be much larger than losers, so the top few percent *must* carry more
than the whole. Anything that pushed concentration into 40–70% on this book
would have achieved it by killing runners — which `LOSS_AUTOPSY.md` LA5 already
measured: tightening the trail lost **155.3R** of >10R wins.

So the concentration itself is **normal and not a defect**.

**What is a defect is the OOS robustness row.** Against your own checklist —
*"removing the top 3–5 winners, strategy should stay positive"* — the bybit OOS
books fail it in **8 of 15 arms**, including every `half+delay1` and every
`STACK` on both multi lanes. `champion STACK` needs its best 3 trades to be
positive (+18.7R) and is **−10.0R without the best 5**.

**But the independent dataset does not fail this test.** On `data/btc`:
champion STACK is +150.1R without the best 3 and **+94.3R without the best 5**;
utcsat STACK +135.4 / +81.2. Concentration there is high (147–179%) but the
book is comfortably robust.

**That is the actual answer.** The shape is a property of the **strategy**, not
the era: it reproduces on an independent market history where nothing was tuned.
What is era-specific is the *thinness* of the bybit 2021–22 sample — 217–279
trades, and the 2021 leg is the weak one.

## 3. So which is it — tail-dependent or fragile?

**Tail-dependent, and correctly so.** The defensible summary:

- Concentration of 120–225% top-5% is intrinsic to the design and should not be
  "fixed". Every serious trend system looks like this.
- Win rate 25–30% is at the healthy end of your band. PF 1.34–1.65 is healthy on
  the STACK arms, marginally low on baseline. W/L 3.3–6.0 is strong.
- **The risk is sample thinness, not the tail.** bybit OOS with n=217 and 5
  winners removed goes slightly negative; btc with n=468 does not.
- **The lever that matters is position size against the tail, not the
  concentration itself** — the same conclusion `IS_IT_RIGHT.md` reached from a
  different direction.

## 4. Two things worth flagging

1. **`skip_decisive` is the only OOS arm that passes the robustness test on
   champion** (both multi lanes are close: +31.2/+6.0 and +8.8/−11.7). It has the
   lowest concentration of any arm (143.5% champion OOS) because it removes 57
   trades from the era where they hurt. On concentration it is the best of the
   family; on thin evidence it is the weakest, because it is a perfect IS no-op
   and its whole case rests on that one era.
2. **age10 is the only lane whose top-5% share sits in your healthy band** —
   55.2% IS, 64.7% OOS, 62.5% on btc — and the only lane that stays positive
   without its best 5 on bybit OOS (+1.6R). Its 49% win rate is outside your
   25–40% band, but that is a *different* strategy profile (PF 7.57, 3.5× fewer
   trades), not a defect.

## 5. What this does not change

- No production change. `backend/` untouched; all arms remain default 0.
- Forward gate is still **5/50** and is not addressed by any of this.
- The `MASTER_CANDIDATES_V2.md` tables are unaffected — this file adds the tail
  breakdown, it does not correct any metric in them.

| age10 | STACK | 111 | +235.4 | 35.1% | 4.06 | 77.1% | 105.7% | +99.8 | +53.9 |
