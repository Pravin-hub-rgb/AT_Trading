# P59: 4h+1h is not a substitute. It is a second, almost disjoint book

> Run 2026-09-29. Harness `exp_cand_cost.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **4h+1h is now registered as a candidate** — as a *complement*, not a
> replacement. See `method/CANDIDATE_BUILD_SHEET.md` and `method/OPEN_RESEARCH_QUEUE.md`.

## The question

P58 found 4h + 1h: the only architecture in the programme that beats the
champion in OOS, in both lanes. Better on every quality measure in both
eras; −113.0R in IS for 214 fewer trades.

**Where does the IS cost come from?** Two possible causes, opposite
decisions:

- **SUBSET** — 4h+1h keeps the champion's good trades and drops its bad
  ones. Then the champion's resolution is buying quantity at a worse
  average, and the candidate is a quality overlay on the existing book.
- **DIFFERENT** — it is a separate bet with its own edge. Then the two
  cannot be blended and the choice is architectural.

## Method

Both books run on identical data, identical parameters, identical lanes.
Trades matched on **(4h bucket, direction)** — the coarsest bar the 4h
layer trades, and direction is what determines a trade, not its entry
minute. **Never on `r_multiple`, `outcome`, `exit_ts` or `pnl`**: this is a
path-true grouping of two live books, not a post-hoc split of realised
results. Partitioning trades by a realised field is the move that produced
the P52 lookahead.

## Result — the books are almost entirely disjoint

| lane / era | group | n | net | R/trade | PF | share of champ |
|---|---|---|---|---|---|---|
| champion IS | SHARED | **19** | +65.1R | **+3.425** | **7.99** | 4% |
| champion IS | CHAMP-ONLY | **478** | **+370.0R** | +0.774 | 2.18 | 96% |
| champion IS | CAND-ONLY | 267 | **+228.9R** | +0.857 | 2.55 | 54% |
| champion OOS | SHARED | **19** | +3.7R | +0.194 | 1.37 | 7% |
| champion OOS | CHAMP-ONLY | **259** | **+103.0R** | +0.398 | 1.61 | 93% |
| champion OOS | CAND-ONLY | 170 | **+119.1R** | +0.700 | 2.22 | 61% |
| utcsat IS | SHARED | 18 | +62.5R | +3.475 | 7.72 | 4% |
| utcsat IS | CHAMP-ONLY | 433 | +393.8R | +0.909 | 2.41 | 96% |
| utcsat IS | CAND-ONLY | 239 | +181.6R | +0.760 | 2.35 | 53% |
| utcsat OOS | SHARED | 15 | +8.4R | +0.560 | 2.20 | 6% |
| utcsat OOS | CHAMP-ONLY | 238 | +84.2R | +0.354 | 1.55 | 94% |
| utcsat OOS | CAND-ONLY | 156 | +92.8R | +0.595 | 2.03 | 62% |

**Only 4–7% of trades are common. The candidate is not a filtered version of
the champion; it is a different book that happens to trade the same asset.**

## The IS cost is volume, not quality

**No exclusive group is negative in any cell.** Champion-only is +370.0R in
IS and +103.0R in OOS. Candidate-only is +228.9R in IS and +119.1R in OOS.

**So the −113.0R is not bad trades being removed — it is 214 fewer trades.**
The champion simply takes more positions and each is worth less. That is the
opposite of the subset hypothesis, and it means:

**This is not a replacement question. It is a combination question.**

The programme's `SKIP` / `GRAY` semantics already exist for exactly this
situation — `SKIP` is a pre-entry reject with the slot free, `GRAY` is a
reject while holding the slot — so a pre-registered union rule is
implementable without inventing a new mechanism.

## The overlap is the interesting part, and it is IS-only

**19 trades, +3.425R each, PF 7.99 in IS.** When the two layers agree, they
agree enormously, and a 7.99 profit factor on 19 trades is the highest
conviction signal anywhere in this programme.

**But in OOS the same 19 trades return +0.194R each at PF 1.37.** So layer
agreement is strong in the era the book was built in and unremarkable out of
it. **That is the third appearance of the same IS-fitted pattern** (P56
window expiry, P58 architecture granularity, here layer agreement), and it
is exactly why the agreement signal is recorded and not acted on.

## What this does and does not license

**It does not license a union.** Deduplicated, the two books' distinct bets
would be worth +664.0R in IS and +225.8R in OOS against the champion's
+325.8R and +70.1R — a 2–3x. **That number is not a result and is not
claimed as one.** The engine holds one position at a time, a union needs a
slot-conflict rule, and any rule chosen now is chosen by looking at these
cells. It also has to beat M = 193.4R, which the candidate's own +27.9R OOS
gain does not.

**What it does license** is registering 4h+1h as a candidate whose weakness
has an identified, non-alarming cause, and queueing one pre-registered
union experiment.

## Candidate record

| field | value |
|---|---|
| **ID** | `cand_4h1h` |
| architecture | 4h HTF + 1h LTF, lag-matched (HTF 3 bars, LTF 12 bars) |
| IS | 286t +212.8R PF 2.59 R/t 0.744 WR 35.3% |
| OOS | 189t +98.0R PF 2.02 R/t 0.519 WR 32.8% |
| utcsat IS/OOS | 257t +165.4R / 171t +72.1R |
| vs champion | −113.0R IS, **+27.9R OOS** |
| status | **CANDIDATE — complement, not replacement. Not adopted.** |
| why | only architecture with better OOS quality on every measure |
| against | does not clear M = 193.4R; 19-trade overlap; one OOS era |
| next | pre-registered union with the champion, then the forward pass |

## Stated limitations

- **Sample size on the overlap is 15–19 trades per cell.** The PF 7.99 in IS
  is a genuine observation and a thin one. It is not used as a filter.
- **The two lanes are highly correlated** and are not independent evidence.
- **The union arithmetic above is a bound, not a measurement** — it assumes
  every distinct bet could be taken, which the single-slot engine forbids.
- **Aggregated OHLC at the 4h layer is synthetic**; bars are stamped with
  their final source bar, so no lookahead.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
