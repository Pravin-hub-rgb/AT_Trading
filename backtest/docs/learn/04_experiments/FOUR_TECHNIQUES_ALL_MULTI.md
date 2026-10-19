# The four techniques on all thirteen multi books

2026-10-16. This is the question the owner actually asked: **was the shortlist
right?** Five candidates faced the battery in `FOUR_TECHNIQUES_ALL_CANDIDATES.md`.
The other eight multi books had never faced it. Now all thirteen have.

## The answer, in one line

**The shortlist was right, and it was right for a reason nobody had measured.**
The eight excluded books fail on the same two axes, and neither axis is net R.

---

## The verdict table

`span` is the range of net R across the parameter grid — the doc's cliff test.
`WF` is how often re-optimising on the training window beat leaving the
registered value alone on the next, unseen window.

| book | OOS net | OOS n | T1 span IS | T1 span OOS | WF | break-even slip IS | obs DD pctile IS | >25R paths |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| **107** `mcloff_htf15` | +272.9 | 295 | **14.2R** | 35.0R | **3/3 ✅** | ~105bps | 99.8% | **0.40%** |
| **110** `htf15_tskip6` | +336.2 | 216 | **234.4R** | **205.8R** | **0/3 ❌** | **~135bps** | 95.8% | 2.80% |
| **108** `htfesmcl4` | +339.1 | 425 | **9.0R** | **18.4R** | **3/3 ✅** | ~108bps | **84.4%** | 3.45% |
| 109 `htf15_htffs` | +346.1 | 395 | 14.4R | 36.6R | 3/3 ✅ | ~100bps | 99.4% | 2.90% |
| 106 `htffs` | +313.4 | 388 | 15.3R | 34.1R | 3/3 ✅ | ~100bps | 93.6% | 2.25% |
| sigm_htffs | +201.7 | 224 | 99.8R | 82.5R | **3/3 ✅** | **~150bps** | 90.3% | 1.45% |
| htf15 | +256.6 | 274 | 19.8R | 42.6R | 2/3 | ~90bps | 99.5% | 0.70% |
| mcloff | +216.0 | 293 | 30.9R | 40.0R | 0/3 | ~95bps | 98.4% | 0.85% |
| acc | +226.3 | 301 | 29.7R | 7.9R | n/a | ~100bps | **37.1%** | 1.10% |
| causalfloor | +220.2 | 270 | 70.5R | 22.2R | 1/3 | ~88bps | 97.8% | 1.80% |
| modechop | +190.9 | 259 | 45.2R | 14.9R | 1/3 | ~85bps | 97.6% | 2.45% |
| biasmom05 | +182.8 | 251 | 53.8R | 48.8R | 1/3 | ~92bps | 98.0% | 0.60% |
| sigm | +184.9 | 185 | 106.3R | 83.8R | 1/3 | ~130bps | 55.0% | 0.65% |

## What the eight excluded books show

**None of them beats 107 or 108 on anything that matters.**

- **Net is lower across the board.** The best of the eight is sigm_htffs at
  +201.7R OOS. The worst of the five candidates is 106 at +313.4R. There is no
  overlap between the two groups.
- **Parameter robustness is worse or equal at best.** Four of the eight exceed
  45R of span; only `htf15` at 19.8R is close to the five, and it only gets
  2/3 on walk-forward.
- **Break-even slippage is lower or comparable.** Four of the eight sit at
  85–95bps against the candidates' 100–135bps.
- **T4 is mixed, not better.** `acc` has the most typical ordering of all
  thirteen (37th percentile) and `sigm` and `sigm_htffs` are also undramatic —
  but their absolute drawdowns are 5.8–19.4R on far less profit.

**The shortlist survives the test it was never given.** Not because of any
reason we originally had — net and drawdown alone would have been enough, but
now it is measured rather than assumed.

## The one genuinely interesting finding outside the shortlist

**`sigm_htffs` has the highest break-even slippage of all thirteen books: ~150bps
IS, against 110's ~135bps and the candidates' 100–108bps.**

It also passes walk-forward 3/3. What it does not have is profit — +201.7R OOS
against 107's +272.9R — and its parameter span is 99.8R, ten times 107's.

So it is **the most execution-tolerant book in the registry and it is not
profitable enough to matter.** If slippage turns out to be worse than every
model here assumes, it becomes interesting. On current numbers it does not.

**Note also: both `sigm` books carry `exp_trail_skip_n`, the one knob that
produced the only cliff anywhere in this battery.** Neither cliffs the way 110
does — `sigm` spans 106R and `sigm_htffs` 100R — which is a useful negative
result. The cliff in 110 is specific to that book at that value, not a property
of the knob everywhere.

## Where this leaves the shortlist

The shortlist was correct, but the *margin* over the eight excluded books is
narrower than the numbers suggest. Three of the five candidates
(107, 108, 109) sit within 40R of each other on OOS net, and 106/108/109 overlap
each other by 85–93%. So "the shortlist" is really:

- **the htffs family** (106/108/109) — one bet, three names
- **107** — flat, robust, least typical ordering
- **110** — the highest execution tolerance and the highest expectancy, and the
  only book that fails walk-forward

That is the same five the scorecard produced. The battery confirms the grouping
and does not change it.

## What this does not settle

- **Selection bias across the full universe.** Thirteen books now share a common
  battery, which is better than five, but the research universe was larger than
  thirteen and a Reality Check or PBO across it has not been run.
- **Structural parameters.** `mode`, `htf_rr` and `max_positions` still have no
  cliff test on any of the thirteen books. The review's point that these are
  exposure controls rather than tuning knobs stands, and it is why a flat heat
  map on `cooldown_bars` is weaker evidence than it looks.
- **Execution delay, 2020 crisis, market-path Monte Carlo.** Still not done.
- **Which of 107 and 110 goes live.** Unchanged. The forward window decides, and
  it currently holds 3–15 trades per book.

## Reproduction

```
exp_four_techniques.py t1 --rest     # sensitivity, own load-bearing knob per book
exp_four_techniques.py t2 --rest     # walk-forward
exp_four_techniques.py t3 --rest     # engine-level slippage
exp_four_techniques.py t4 --rest     # 2000 shuffles
```

Each book is swept on its own load-bearing knob rather than a copied grid: the
two `sigm` books and `biasmom05` and `causalfloor` each have a parameter the
others do not, and sweeping a knob that does nothing would have produced another
flattering flat map.