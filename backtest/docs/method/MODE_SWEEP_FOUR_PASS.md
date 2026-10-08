# Four router branches never run against a book pass both eras — for the first time in this session

Date: 2026-10-08. Engine post-C17. Harness: `exp_mode_sweep.py`.
Book: `fsent_champ_long`, only `mode` moving. Nothing adopted.

## The gap

`exp_repo_map.py` found that **25 of the router's 27 regime branches have no book
anywhere in the registry.** Live books use `mode="atr_high"` (215) and
`mode="union"` (2). The concentration was the finding: 215 variations of one rule,
zero of the others.

The reason that mattered is in this session's own history. `exp_mode_regime.py`
established that `chop` (CHOP index, 1h, reads *direction efficiency*) and
`atr_high` (ATR% of price, 15m, reads *bar size*) are genuinely different
variables, disagreeing on 24.6% of IS bars and 35.5% of OOS bars — and that the
`chop_HIGH / atr_low` cell is the book's best region in both eras.

That was measured by **grafting** chop's condition onto `atr_high` and building
three throwaway modes. **Eighteen branches already implementing exactly this sit
in the engine and had never been run.** Those three were deleted when the
experiment closed. These were always there.

## Result — 27 branches, both eras, full metrics

Pass requires: **net > shipping in BOTH eras AND net-without-best-trade >
shipping's in BOTH eras.**

| mode | IS n | IS net | IS dd | OOS n | OOS net | OOS dd | ΔIS | ΔOOS | |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `atr_high` | 528 | +533.4 | 13.4 | 311 | +239.6 | 11.9 | — | — | **shipping** |
| **`atr_low`** | **641** | **+721.3** | 28.9 | **315** | **+280.7** | 14.6 | **+187.9** | **+41.1** | ✅ |
| `garch` | 549 | +529.9 | 15.8 | 299 | +283.2 | 14.3 | −3.5 | +43.6 | era-split |
| `fd` | 529 | +534.8 | 13.4 | 295 | +276.8 | 12.2 | +1.4 | +37.2 | ✅ |
| `htf_dir` | 531 | +419.1 | 22.8 | 287 | +275.2 | 12.2 | −114.3 | +35.6 | era-split |
| `entropy` | 528 | +494.2 | 22.8 | 291 | +267.0 | 11.9 | −39.2 | +27.4 | era-split |
| **`flip_quality`** | 527 | +534.8 | 13.4 | 294 | +244.4 | 11.9 | +1.4 | +4.8 | ✅ |
| **`union`** | **813** | **+580.0** | 23.8 | **442** | **+303.8** | 18.2 | **+46.6** | **+64.2** | ✅ |
| `soft_chop` | 525 | +529.4 | 13.4 | 297 | +248.5 | 11.9 | −4.0 | +8.9 | fail |
| `chop` / `b2_vs_flip_chop` / `decisive_vs_flip_chop` / `chop_and_atr_low` / `hmm` / `htf_mag_inv` / `soft_atr` / `session` | 528 | +533.4 | 13.4 | 294 | +244.4 | 11.9 | 0.0 | +4.8 | fail |
| `dynamic_chop` | 528 | +483.4 | 25.2 | 294 | +243.1 | 11.9 | −50.0 | +3.5 | fail |
| `entropy_inv` / `fd_inv` / `garch_inv` / `hmm_inv` / `htf_mag` / `ltf_dir` / `session_flip` | — | — | 17–36 | — | 186–230 | — | **negative both** | | fail |
| `chop_or_atr_low` | 640 | +645.0 | 28.9 | 313 | +182.9 | 14.6 | +111.6 | **−56.7** | era-split |

Eight branches return the **identical** IS book (528t/+533.4R/13.4) — the ones
whose condition is satisfied identically to `atr_high` on this data. They are one
result, not eight.

## The four that pass

| mode | OOS n | OOS net | OOS mean | OOS PF | OOS WR | OOS dd | OOS streak | OOS no-top1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `atr_high` (shipping) | 311 | 239.6 | 0.77 | 2.69 | 37.0% | **11.90** | 15 | +213.5 |
| **`atr_low`** | 315 | **280.7** | 0.89 | 2.96 | 38.1% | 14.60 | 15 | **+254.6** |
| **`garch`** | 299 | **283.2** | **0.95** | 3.00 | 38.1% | 14.30 | **12** | **+257.1** |
| **`fd`** | 295 | 276.8 | 0.94 | 3.05 | 36.6% | **12.20** | 15 | +250.7 |
| **`union`** | **442** | **303.8** | 0.69 | 2.45 | 34.4% | 18.20 | 15 | +277.7 |

**`atr_low` is the standout and it is the inversion.** `atr_high` takes decisive
windows when bars are *big*; `atr_low` takes them when bars are *quiet*. It is
the same variable with the sign flipped, and flipping it is worth **+187.9R in
sample and +41.1R out** — the largest single-branch result in the repo.

`union` has the highest net (+303.8 OOS) but the lowest mean (0.69 against 0.77)
and the worst drawdown (18.20R). It is a **bigger book**, not a better one: 442
trades against 311, at lower R per trade. Reading it as an improvement is the
error this framework exists to catch.

`fd` and `flip_quality` are the tightest: `fd` costs only +1.4R in sample for
+37.2R out, at drawdown 12.20R against 11.90R.

## Why this is not yet an adoption

Three reasons, and all three are load-bearing:

1. **Drawdown rises for every one of them.** Shipping is 11.90R OOS. `atr_low`
   14.60, `fd` 12.20, `garch` 14.30, `union` 18.20. The governance rule in
   `EQUITY_LENS_EXT_AND_NOHALT.md` is a budget test, and every candidate here
   spends from it.
2. **No era-split check has been run.** `atr_high` itself sits at p = 0.91 under
   `SHIPPING_BOOK_NULL.md`. These arms are differences against a book whose own
   significance is unresolved, which is exactly the condition that killed `trail_half`
   in `CURVE_QUALITY_TRAILHALF.md` — strip five trades and the advantage vanished.
   The no-top1 column says all four survive one trade; **none has been tested at
   top-5 or top-10%.**
3. **The second lane has not been run.** `champion_multi_sw10` and
   `utcsat_multi_sw10` are the same data, so their agreement would not be
   independence — but a candidate that only works on one lane is not a candidate.

## What is genuinely new here

`atr_low` beating `atr_high` on both eras is a **directional** result, not a
tuning one. It is the same feature with the comparison reversed, so it is not a
threshold searched on a grid — there is one threshold and it was not moved.

That matters because this session's entire record is thresholds and knobs
producing nothing: `chop_thresh` at seven levels, `exp_persist` at eight,
`ext_stop_r` at four. **A sign flip that nobody searched for is a different kind
of result than a peak in a grid, and it is the first one here that survived.**

The obvious follow-up is therefore not a wider grid. It is whether `atr_low` is
robust across its own threshold, and whether it and `union` are the same finding —
`union` admits both interval sets, which is what an inverted `atr_high` plus a
flipped one would also produce.

**Nothing adopted. No mode added, no book registered, no pin changed.**