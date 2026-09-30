# P3 and W2 — what the 1h layer earns, and why `r_touch` lost 130R

> Run 2026-09-29. Harness `exp_htf_standalone.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Closes the queue's last two free items.

## P3 — score the 1h layer's own P&L *(the queue's "highest value" item)*

> "Every run simulates the 1h book three times and throws its P&L away,
> keeping only window bounds. **Nobody has ever reported what the 1h book
> earns standalone.** Either the 1h book carries the edge or the 15m layer
> does."

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 1h FLIP | 355t **+1.9R** PF 1.20 | 204t **−23.6R** PF 0.96 | 355t +1.9R | 204t −23.6R |
| 1h B2 | 309t **−49.6R** PF 0.92 | 194t **−21.7R** PF 0.94 | 309t −49.6R | 194t −21.7R |
| **CASCADE (15m)** | 500t **+325.8R** PF 2.38 | 279t **+70.1R** PF 1.59 | 454t +359.0R | 253t +60.2R |
| cascade R/trade | **+0.652** | +0.251 | +0.791 | +0.238 |

**The 1h layer has no standalone edge.** FLIP is +1.9R gross-positive in IS
and **negative in OOS**; B2 is negative in both eras and both lanes. Net of
costs, both are at or below zero.

**Both pre-registered conditions resolve:**

- **Claim — "cascade beats best 1h standalone on R/trade by ≥2×, both
  eras": PASSES.** 4.6× in IS on the best (FLIP) 1h book.
- **Falsifier — "1h standalone positive in both eras with PF > 1.3 means
  the LTF layer adds nothing": does NOT fire.** 1h is *negative* OOS at
  PF 0.96, and never above PF 1.20 anywhere.

**So the architecture earns its complexity, and the 1h layer is doing
something different from carrying edge.** It is supplying direction. That
direction is worth +325.8R in IS and +70.1R OOS in the 15m layer and is worth
roughly nothing taken on its own — which is the same thing P3-B found from
the other side, where the early read of the leg turned out to be
structurally impossible.

### Two corrections this run had to make

**The primary 1h book is `htf_trades`, not `htf_trades_flip`.** The engine
returns `htf_trades` (the flip book), `htf_trades_b2`, and no
`htf_trades_decisive` at all. The first run of this file looked for keys that
do not exist and reported "flip (empty), b2 −17.8R", which understates the
1h layer by the whole flip book. Verified by dumping the return keys.

**Gross vs net.** `r_multiple` sums to +50.6R for the flip book but `net_r`
gives **+1.9R** — costs are ~0.24R per trade. Every figure above is net.
The first run compared a gross cascade (+445.2R) against gross 1h books,
which flatters the cascade ratio; the honest ratio is 4.6×, not 6.2×.

## W2 — why did `r_touch` lose 130R?

> "Closing at +1.5R should have helped if 25% of windows reach 3R. It
> regressed instead. **Falsifier:** if the MFE distribution is bimodal — a
> mass below 1.5R and a spike at 3.0R — then 1.5R sits in the gap and should
> have been free. If MFE is smooth, 1.5R truncates the runners that make the
> book and the −130R is correct rather than mysterious."

| MFE bucket | champ IS | champ OOS |
|---|---|---|
| < 0.5R | 35.3% | 33.0% |
| 0.5–1.0R | 22.0% | 21.1% |
| 1.0–1.5R | 8.4% | 11.9% |
| **1.5–2.0R** | **4.5%** | **6.7%** |
| **2.0–2.5R** | **4.5%** | **3.6%** |
| **2.5–3.0R** | **3.6%** | **2.1%** |
| **≥ 3.0R** | **21.4%** | **21.1%** |
| **below 1.5 / 1.5–3.0 / ≥3.0** | **65.7 / 12.6 / 21.7%** | **66.0 / 12.4 / 21.6%** |

**The distribution is bimodal, in both eras, and the 1.5–3.0 band is the
thinnest part of it.** 65.7% of legs never reach 1.5R; 21.7% go straight to
3R; only 12.6% live in between.

**By the queue's own falsifier, 1.5R sits in a gap and should have been
free. The −130R is therefore not explained by MFE, and `r_touch` was
rejected for a reason that does not hold up.**

That is a real finding and it is not comfortable: `r_touch` is in the
graveyard with a −130R annotation, and the autopsy says the mechanism does
not account for the loss. **It does not mean `r_touch` should be re-enabled**
— an unexplained regression is still a regression, and 1.5R still truncates
the 21.7% of legs that run past it. It means the recorded *reason* is wrong
and should not be cited again.

## Verdict

**P3 closed: the 1h layer carries no standalone edge; the cascade is 4.6×
its R/trade and the falsifier does not fire. The three-timeframe
architecture is justified.**

**W2 closed: MFE is bimodal, so `r_touch`'s −130R is unexplained by the
mechanism it was blamed on. The blame is retracted, not the rejection.**

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
