# sMZX INDEPENDENT REPLICATION — BINANCE PERP: 2/4, NOT REPLICATED

The pre-registered rule for this run was **4/4 cells**. It scored **2/4**.
Reported as a failure. The *shape* of the failure is the interesting part.

## What was run

Harness `exp_smzx_binance_replication.py`. The full sMZX audit — flat book,
flat-leverage control, sMZX real, 50-draw size shuffle — re-run on **BINANCE
PERP** (`data/btc-fut`), a different venue and microstructure, with the
thresholds copied **verbatim** (M2 `>=3.0`, ZC `<=0.846`, X `<1.0`, size
`1.5^count`). No re-tuning: a replication that adjusts the thresholds is not
a replication.

Era windows were **derived from the bybit book at runtime** and mirrored onto
binance, so both venues are measured over identical market periods.

## Result — 2/4, and the split is by era, not by lane

### OOS (2020-12-31 → 2022-12-31) — 2/2 SELECTION, emphatic

| Cell | flat | A flat lev | **B sMZX** | C shuffled | shuffles beating B |
|---|---|---|---|---|---|
| oos/champion | +17.8, DD 26.5, cal 0.335 | +31.0, DD 30.8 | **+79.4, DD 28.3, cal 1.401** | +26.7 ±15.3 | **0/50** |
| oos/utcsat | +7.6, DD 36.5, cal 0.103 | +18.0, DD 43.2 | **+68.5, DD 39.1, cal 0.877** | +19.4 ±12.7 | **0/50** |

100th percentile in both. Not one random size assignment out of 50 beat the
real flags. On `oos/utcsat` the flat book earns **+7.6R over two years** —
essentially no edge — and the arm turns it into **+68.5R**, a 9× improvement,
with drawdown only 36.5 → 39.1.

### IS (2022-12-31 → 2026-09-12) — 0/2, fails the bar

| Cell | flat | A flat lev | **B sMZX** | C shuffled | shuffles beating B |
|---|---|---|---|---|---|
| is/champion | +255.4, DD 44.5, cal 1.563 | +390.6, DD 54.5 | +461.7, DD **60.7**, cal 2.072 | +398.5 ±49.3 | **6/50** |
| is/utcsat | +208.1, DD 41.5, cal 1.367 | +319.5, DD 50.8 | +385.4, DD **54.6**, cal 1.925 | +321.8 ±43.8 | **5/50** |

88th and 90th percentile — 5-6 of 50 random assignments beat the real flags.
And here the arm **worsens** drawdown (44.5 → 60.7, 41.5 → 54.6), the
opposite of what it did on bybit, where drawdown improved.

## What the split actually means

The arm's value is **inversely proportional to how good the base book
already is**:

| | base book | selection percentile | DD effect |
|---|---|---|---|
| OOS 2020-22 (thin edge) | +17.8R / +7.6R | **100th** | ~flat (+1.8 / +2.6) |
| IS 2022-26 (thick edge) | +255.4R / +208.1R | 88-90th | **worse (+16.2 / +13.1)** |

That is coherent rather than contradictory. M2/ZC/X are all conviction
signals — the move is already large in ATR terms, volatility is compressing,
the stop is tight. When the base book is scraping, those flags are the only
thing separating a good trade from a coin flip, so loading up on them is
worth a lot. When the book is already compounding, the same loading mostly
buys concentration, and the cost shows up in drawdown.

## Verdict

**NOT REPLICATED (2/4 against a pre-registered 4/4).** The arm does not
transfer at the strength Bybit showed.

What survives:

- The selection is **not an artefact** — it is emphatic where the base edge
  is thin, and it reproduces with zero threshold changes on a second venue.
- Bybit's headline drawdown *improvement* **does not** transfer; on binance
  the arm consistently costs drawdown. That part of the earlier write-up
  should not be relied on.

What does not survive:

- The claim that this is a general, uniformly beneficial risk-budget change.
  It is regime-dependent, and the regime it likes is the one the live account
  spends most of its time *not* in.

## Status

**NOT ADOPTED**, and the bar is now higher than before this run, not lower.
The remaining blockers are unchanged and now include an unsatisfied
independent replication: `v18_streak_halt.py` still has no size state, the
forward gate is still untouched, and the one venue where the arm looks
strong is the already-inspected one.

## Files
- `live_stuff/tests/exp_smzx_binance_replication.py` → `_smzx_binance_replication.json`
- `live_stuff/docs/SMZX_LEVERAGE_AUDIT.md` — the bybit result this audits

## Run note

The combined two-era run died mid-OOS with no traceback — the binance 1m
slice is ~119MB per era and both eras plus their window tables did not fit in
one process. The harness now takes the era as an argument and merges into the
same JSON (`is`, then `oos --append`). Both halves are complete; the numbers
above are from those two runs.
