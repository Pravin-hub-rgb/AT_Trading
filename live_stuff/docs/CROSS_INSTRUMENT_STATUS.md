# CROSS-INSTRUMENT STATUS — the 1m hunt ended; the 6/8 candidate is here

Date: 2026-09-28. Read before proposing any new instrument work.

## The short version

**The strongest result in this repo is not in the graveyard and not in the
1m thread. It is `24.95` Cross-Asset Transfer, and it already passed.**

While looking for "something new" after the 1m family closed, I found that
cross-instrument work was done on 2026-09-27 and is **NOT** in
`CLOSED_DO_NOT_REPEAT.md` (that file lists losses; this is a pass, so it was
never written there). Flagging it so it does not get re-run or, worse,
missed.

## What 24.95 actually found

Frozen v18 lanes (no retune, no flags) on Binance fapi **ETHUSDT** and
**SOLUSDT** perps — instruments and a venue no engine run had ever seen.
Eras mirrored from the BTC loaders: IS 2023-01→2026-09, OOS 2021-01→2022-12.
Same windows, different instrument **and** different venue.

**Transfer PASS 6/8:**

| lane | ETH IS | ETH OOS | SOL IS | SOL OOS |
|---|---|---|---|---|
| champion | 431t +16.0R | 279t **+27.9R** | 530t **+226.3R** | 363t **+153.8R** |
| utcsat | 392t **−7.4R** | 251t +56.1R | 466t +156.1R | 316t +122.2R |
| fullstack | 205t +11.2R | 110t +52.0R | 209t +55.3R | 143t **−17.4R** |
| **age10** | 122t **+131.4R** | 69t **+139.4R** | 134t **+273.5R** | 90t **+136.4R** |

**`age10` is the only lane that is kills-clean on BOTH assets** — zero
counted K1-K7 kills in both eras, WR 0.44-0.55 (the only lane clearing
literal K6), Sharpe 1.13-1.99, maxDD ≤ 13.2R.

Two facts that make this interesting beyond "it passed":

- **SOL >> ETH** on aggregate net (1,106.1R vs 426.5R).
- **The correlation signature splits.** ETH's monthly net correlates with
  BTC champion 0.16-0.21 IS / 0.59-0.71 OOS — it transfers *with* BTC
  behaviour. SOL is −0.28..+0.31 — a **decorrelated book that expresses the
  edge differently**. Those are two different animals and would justify
  different risk treatment.

## Status: CANDIDATE, not adopted — and correctly so

A transfer PASS is a candidate for the user's adoption decision, never an
automatic production change. Six of the eight passing units are
counted-kill-tainted, and ETH's economics are thin (champion IS +16.0R
over 431 trades, Sharpe 0.08, DD 104.2R).

**The clean unit is `age10` on both assets.** That is the only thing in the
repo with: both eras positive, no counted kills, healthy WR, Sharpe > 1,
and DD under 14R.

## What this means for the 1m thread

Worth stating plainly, because the two threads are in tension:

- The 1m hunt produced 0/196 trigger cells, 0/24 book cells, a failed
  replication and a dead feature family — because a 1m book pays
  **0.79R per round trip** against a gross edge of −0.018R.
- `age10` on SOL pays the same Bybit cost convention and still returns
  **+273.5R IS / +136.4R OOS on 134/90 trades**.

**Trade count, not timeframe, was the binding constraint all along.** The
15m `age10` book is small (n=130/76) and that smallness is exactly why it
transfers cleanly. A 1m book at 20,000 trades could never have done this,
at any win rate.

So if the goal is more deployed edge, the direction is **more instruments
on the small `age10` book**, not a finer timeframe.

## Suggested next steps (none run yet)

1. **Extend `age10` to the remaining scan-fut alts** (AVAX/BNB/LTC/LINK/
   DOT/MATIC/NEAR/OP/ADA/ARBU/SUI/WIF/XRP/DOGE/APT — 15 symbols with
   15m+1h on disk). ETH and SOL are 2 of 17. This is the single cheapest
   expansion and it reuses a frozen lane.
2. **Decide the ETH question**: is +16.0R IS / Sharpe 0.08 worth deploying,
   or is ETH only useful as a diversifier given its 0.59-0.71 OOS
   correlation to BTC?
3. **Treat SOL as a separate sleeve**, not a BTC satellite — the
   decorrelation suggests different sizing, and that is an engineering
   question (live size state is still missing, see §8 of the handover).

**Nothing adopted.** Production untouched. This note records an existing
candidate; it does not create one.
