# P61: the quality advantage is not stable, and the forward pass is 2 trades

> Run 2026-09-29. Harness `exp_stability_forward.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **`cand_4h1h` is DOWNGRADED from registered candidate to NOT A CANDIDATE.**

## This corrects my own framing from P58 and P59

P58 said `cand_4h1h` was "better than the champion on every quality measure
in both eras". P59 registered it as a candidate on that basis. **Both of
those statements are true of the AGGREGATE and misleading about the
DISTRIBUTION.** Broken into calendar periods the advantage is a coin flip,
and its losses are concentrated at the most recent end of the data.

| period | champ R/trade | cand R/trade | cand wins |
|---|---|---|---|
| 2023H1 | +0.897 | **+1.842** | YES |
| 2023H2 | +1.217 | **+2.319** | YES |
| 2024H1 | +1.081 | +0.518 | no |
| 2024H2 | +0.421 | **+1.557** | YES |
| 2025H1 | −0.126 | +0.054 | YES |
| **2025H2** | **+1.470** | **−0.401** | no |
| **2026H1** | **+0.814** | **−0.115** | no |
| **2026H2** | **+1.807** | **+0.056** | no |

**IS: 4 wins, 4 losses out of 8. A coin flip.** The utcsat lane returns
4/8 and 3/4 in OOS — identical in shape, as expected from two correlated
lanes on the same data.

OOS (2021H1, 2021H2, 2022H1, 2022H2): **3 wins, 1 loss** — and the loss is
2022H2, again the most recent OOS period.

**Partitioned by calendar period, fixed before looking. Never by
`r_multiple`, `outcome` or `pnl`** — grouping trades by a realised field is
the P52 lookahead and it has burned this programme before.

## The pattern is the finding, not the count

**The candidate has lost every single period since 2025H2** — three out of
three, in both eras' recent history. And in exactly those periods the
champion is strongest: +1.470, +0.814, +1.807 R/trade against the
candidate's −0.401, −0.115, +0.056.

**So the recent regime rewards the finer book, and the candidate's
aggregate advantage comes from 2023–2024, which is where the champion was
already working.** The aggregate R/trade advantage was partly an artefact
of trade weighting: a book that trades less has its per-trade average less
diluted by a stretch where the champion is strong and it is not.

**That is the fifth appearance of the IS-fitted pattern** — after the P56
window expiry, the P58 granularity finding, the P59 layer-agreement signal
and the P60 union's risk-profile collapse. Here it is the most literal
version of all: the candidate's edge lives in the part of the sample that
looks like the past.

## The forward pass — a smoke test, and it is 2 trades

`data/forward/bybit`, unseen by anything before: 2026-09-13 → 2026-09-25,
**12.5 days**, 1203 × 15m, 301 × 1h, 18049 × 1m. Swings available: **14 on
1h, 26 on 15m.**

| lane | 1h+15m | 4h+1h |
|---|---|---|
| champion | 2 trades, +6.0R | 1 trade, −1.1R |
| utcsat | 2 trades, +6.0R | 1 trade, −1.1R |

**Two trades against one. This settles nothing** and was flagged as
settling nothing before it was run. Its only real value is negative: no
crash, no empty book, no sign error, and both architectures produce
plausible output on unseen data — so the P58 construction ports.

**The reported PF of 6195000000.00 on the champion's two trades is a
display artefact**, not a measurement: both trades were winners, so the
denominator is effectively zero. It is left visible rather than tidied
away, because a PF printed to ten significant figures on n=2 is exactly the
kind of number that gets quoted later as evidence.

## Verdict: `cand_4h1h` is downgraded

**It is not a candidate.** The claim that carried it — better quality in
both eras — does not survive contact with the period distribution, and the
one test that could have been decisive (forward data) has 2 trades in it.

Its numbers are not wrong; they are just aggregates over a distribution
where the advantage is 4-4 in IS, 3-1 in OOS, and negative in all three
most recent periods. **A candidate that only works in the older half of the
sample is not a candidate, it is a fitted artefact** — and the programme's
whole reason for keeping a held-out era and a deck-relative null is to catch
exactly this before it is adopted.

**The union route stays closed (P60). The 1h+15m champion stays the
architecture (P58, from every direction). Nothing is adopted.**

## Stated limitations

- **Half-year buckets on the OOS era give only 4 periods**, so 3-1 is a
  thin reading. It is reported as what it is; the IS 4-4 over 8 periods is
  the stronger of the two.
- **The 12.5-day forward window is far too small to decide anything** and
  was pre-registered as a smoke test. A real forward pass needs months,
  not fortnight, and the data for it does not exist yet.
- **Quarterly or monthly buckets were not run.** Half-years were chosen for
  sample size; finer buckets would thin each cell to a few dozen trades and
  could have been searched until a flattering split appeared. No threshold
  was searched here.
- **The two lanes are the same data** and their agreement is not
  independent confirmation.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
