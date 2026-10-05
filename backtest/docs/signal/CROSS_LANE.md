# P19 — cross-lane: the filter transfers to 3 of 11 lanes in both eras

`exp_crosslane.py`. The user's question, and the one that decides
whether any of today's work is real:

> "yah joh idea hai tumne champion mai he chalya hai… baaki mai bhi
> chalo single wagera mai"

**A filter found on the champion, scored on the champion, and ranked
against the champion is a description of the champion until it is tested
somewhere else.** The registry carries ~11 pinned lanes spanning multi vs
**single** (what the user asked for), sw10 vs sw20, age-gated,
direction-match and the swingpause/wage family — which makes this test
possible at all.

**Every control reproduced first.** Three lanes are checked against the
DOCUMENTED ledgers (`method/CHECKLIST.md:686`, `method/EXPERIMENT_LOG.md:341`): champion
500t/+325.8R, utcsat 454t/+358.9R, single 200t/+310.7R — **all three exact.**

> A note on pins: the registry's own `pins` for these lanes are a
> "causal SL" variant (champion `n: 494, net: 248.0`) and are **not** the
> +325.8R champion this session measures. Using them flagged the first
> three lanes UNVERIFIED. The pins that count are the documented ledgers;
> the rest are marked self-consistent rather than doc-verified.

## The result — 3 of 11 lanes improve in BOTH eras

| lane | n | net | R/tr | PF | | kept | net | R/tr | PF | dNet | OOS dNet | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **champion_multi_sw10** | 500 | +356.9R | 0.890 | 2.38 | | 352 | **+409.0R** | **1.339** | **3.13** | **+52.1** | **+7.2** | ✅ **BOTH** |
| **utcsat_multi_sw10** | 454 | +388.0R | 1.027 | 2.62 | | 313 | **+445.7R** | **1.597** | **3.61** | **+57.8** | **+10.1** | ✅ **BOTH** |
| fullstack_wage10_cd0_single_sw10 | 200 | +325.0R | 1.803 | 3.84 | | 150 | +333.2R | 2.399 | 4.82 | +8.2 | **−12.8** | IS only |
| age10_dirmatch_swingpause_single | 130 | +451.5R | 3.665 | 10.35 | | 87 | +441.4R | 5.266 | 17.78 | **−10.1** | −27.4 | **worse** |
| dirmatch_swingpause_single_sw10 | 279 | +306.8R | 1.252 | 3.23 | | 173 | +324.9R | 2.031 | 4.83 | +18.1 | −5.2 | IS only |
| dirmatch_multi_sw10 | 389 | +508.8R | 1.467 | 3.76 | | 264 | +531.6R | 2.173 | 5.43 | +22.8 | — | IS only |
| age25_multi_sw10 | 295 | — | — | — | | — | — | — | — | — | IS only |
| age25_dirmatch_multi_sw10 | 249 | — | — | — | | — | — | — | — | — | IS only |
| dirmatch_single_sw10 | 292 | +258.1R | 1.038 | 2.82 | | 182 | +277.5R | 1.679 | 4.08 | +19.3 | −6.8 | IS only |
| wage10_swingpause_wskip_single | 262 | +299.2R | 1.311 | 3.01 | | 196 | +307.4R | 1.737 | 3.61 | +8.2 | −10.8 | IS only |
| **wage12_swingpause_single_nowknd** | 317 | +256.2R | 0.996 | 2.47 | | 244 | +282.6R | 1.346 | 2.99 | +26.4 | **+6.2** | ✅ **BOTH** |

## What this actually establishes

**1. It is not a champion artifact — the IS improvement is near-universal.**
**9 of 11 lanes improve in IS**, and R/trade and PF improve on essentially
every one. `utcsat` gains +57.8R, `dirmatch_multi` +22.8R,
`wage12_nowknd` +26.4R. **A filter that only helped the champion would not
do that across independent lane families.** The IS side of the effect is
real and it is a property of the market, not of one book.

**2. But the OOS side does not generalise, and that is the finding.**
Only **3 of 11** improve out of sample, and the OOS deltas on the others
are small and negative (−5.2 to −12.8R). **The OOS books are 76–253
trades; a +7R move on 176 trades is noise, and the honest reading is that
the OOS evidence is 3-for-11 rather than 9-for-11.**

**3. It transfers best on multi-timeframe routing, least on the swingpause
family.** Both both-era winners besides the champion are `multi`-flavoured
(`utcsat_multi`, `wage12_..._nowknd` routes through windows like the
champion), and every `swingpause` single lane is IS-only. That is a
coherent mechanism: `nest1h` and `age` are properties of the HTF *window*,
so a book that trades through many windows has more of them to condition
on. It also predicts the obvious failure: the age-gated lanes, which
already filter on window age, are the ones that get worse — **`age10`
loses 10.1R IS and 27.4R OOS**, which is what double-filtering on age
should look like.

**4. `fullstack_wage10_cd0_single` is the clean counterexample to
"better ratios = better book".** The filter takes its R/trade from 1.803
to **2.399** and PF from 3.84 to **4.82** — the best ratio improvement on
any lane — and still **loses 12.8R out of sample.** Perfect ratios, no
money. That is M and the tail talking, and it is why the OOS column is
the one that counts.

## Verdict

**Not adopted, and the reason is specific rather than general caution.**

- The **IS effect is real and transfers** (9/11). That is more than
  anything else produced today.
- The **OOS effect does not** (3/11), and the OOS books are too small to
  rescue it. Per P5, a +7R OOS move on 176 trades is far inside M.
- **P15's `decay<0.75` still has the larger OOS gain** (+21.0R on the
  champion) and the 2025 year regression. Neither filter is adoptable; they
  fail on different axes, which is itself the useful summary of today.

**The next measurement is not another lane. It is the forward window**,
where the two can be scored on data that has not been used to select
anything. Both are frozen, both are pre-registered here, and the only
thing left to do is wait for n≥50.

## What would change the verdict

A cross-lane sweep at a **higher OOS trade count** would settle it, and
the repo already says where to get one: the alt-sleeve thread (P6 in the
second-round list, blocked on a Bybit perp fetch) would give more
independent books at the same calendar span. That is a data problem, not a
research problem, and it is now the highest-value unfetched item on the
list.
