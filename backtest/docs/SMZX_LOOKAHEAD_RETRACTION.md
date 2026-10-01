# RETRACTION — sMZX "SELECTION" was substantially a LOOK-AHEAD detector

**This corrects `SMZX_LEVERAGE_AUDIT.md`, which overstated the case. The user
caught the flaw: M2 is forward-looking, and M2 is the load-bearing flag.**

## I was wrong about what the shuffle test could prove

I ran sMZX against a 50-draw matched-count random size reassignment, the real
flags beat 49-50 of 50, and I called it SELECTION — real skill, not a
leverage trap. The shuffle test does satisfy this repo's standing rule that
no sizing dNet is quoted without a matched-count null. But it **cannot
distinguish skill from look-ahead**, and I treated it as if it could.

A feature that encodes the trade's own future outcome will beat a random
null every time. The test was blind to exactly the failure mode that
mattered.

## The flaw, in the repo's own words

`cur_mag_atr = |seg.end_px − seg.start_px| / atr15` uses the swing segment's
**END** price. `backend_check_wd_days.py:108` asserts
`fs_at_idx >= seg.end_idx` — a swing's FS/SUS confirmation lands at or after
the end bar. The entry fires at **B2 or flip, before the swing ends**, so
`end_px` does not exist at decision time.

`CAPITAL_STAGE_PLAN.md` had already recorded all of this and I did not check
it before building on the number:

- send-time replacement agrees on only **77.5%** of trades (bar: 95%),
  worst cell 72.0%;
- the send-time reader fires on **0–6 trades out of 76–500** where the
  backtest flags 12–133;
- `mag_so_far` → **0/6** ("the threshold is unreachable mid-swing");
  `ramp_so_far` → **0/6** ("flags 100% — pure leverage, the M1 trap");
- **"A send-time replacement for M2 was searched for and does not exist."**
  **"none of them is deployable as measured."**

## The decomposition (bybit, champion + utcsat, IS + OOS)

Each family alone, each with the same shuffle null. `dNet` is vs the flat
book; the bracket is what the same average size applied FLAT would have
given, so it is the size-adjusted comparison.

| Arm | is/champ | is/utcsat | oos/champ | oos/utcsat | cells passing |
|---|---|---|---|---|---|
| **M2 only** (forward-looking) | +152.7 (100th, 0/50) | +147.5 (98th, 1/50) | +29.1 (96th, 2/50) | +31.3 (96th, 2/50) | **4/4** |
| ZC only | +106.5 (84th, 8/50) | +112.3 (84th, 8/50) | +32.2 (88th, 6/50) | +40.4 (96th, 2/50) | 1/4 |
| X only | +23.9 (58th, 21/50) | +23.4 (58th, 21/50) | +36.6 (100th, 0/50) | +39.5 (100th, 0/50) | 2/4 |
| **M2-free ZC+X** | +133.6 (80th, 10/50) | +138.1 (92nd, 4/50) | +86.4 (100th, 0/50) | +99.3 (100th, 0/50) | **3/4** |
| all M2+ZC+X (sMZX) | +346.5 (100th, 0/50) | +341.2 (98th, 1/50) | +130.4 (100th, 0/50) | +146.6 (100th, 0/50) | 4/4 |

### What this actually says

1. **M2 alone is 4/4 and is the strongest single flag** — and it is the one
   that cannot be computed at entry time. A flag that knows how big the swing
   eventually turned out to be *is* a statement about the trade's future.
   That it beats a random null 50/50 is exactly what look-ahead predicts, and
   nothing more.
2. **X alone "passes" in OOS on 7 and 9 trades** — 2.5% and 3.6% coverage.
   That is small-n noise, not selection. It should not be read as a signal.
3. **The M2-free residue (ZC×X) is real but weak and inconsistent** — 3/4,
   and it fails is/champion (80th percentile, 10 of 50 shuffles beat it). It
   is genuinely live-computable, which is what makes it the only thing here
   worth keeping.

## Corrected verdicts

- **sMZX as published is not a deployable edge.** Its headline (+346.5 IS)
  is dominated by a forward-looking flag. The statistic was real; the
  *interpretation* — that a live trader could reproduce it — was wrong.
- **The M2-free ZC×X residue is the only live-computable candidate**, and it
  is materially weaker and less consistent than sMZX's headline suggests.
  Note `exp_zx_causal_combo.py` had already closed the ZCX family unadopted
  for exactly this reason; the shuffle null here is the missing test the
  standing rule demanded, and it agrees with that closure rather than
  overturning it.
- **The binance replication (2/4) should be read with this in mind.** A weak
  cross-venue result on an arm containing a non-transferable feature is
  unsurprising, not surprising.

## Standing rules this earns

1. **A matched-count null is necessary but not sufficient.** For any feature
   that touches future bars, the null must be accompanied by an explicit
   causality audit of the feature's inputs. Check the feature definition
   against the engine's bar-availability assertions **before** running the
   arm, not after.
2. **Before quoting any `cur_mag_atr` sizing number, state that M2 is
   forward-looking** and that no send-time replacement exists. Carry that
   caveat inline in the harness docstring, not in a separate plan doc.

## Status

**NOT ADOPTED** — unchanged, and the case is now weaker than it looked an
hour ago. `SMZX_LEVERAGE_AUDIT.md` should be read subject to this retraction.
Production untouched, `sMZX` was never wired to anything.

## Files
- `backtest/tests/exp_smzx_lookahead_split.py` → `_smzx_lookahead_decomposition.json`
- `backtest/docs/CAPITAL_STAGE_PLAN.md` — the pre-existing M2 look-ahead
  findings this run was supposed to have read first
