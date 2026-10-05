# 1m path context, SCALE-MATCHED — the correction. Still fails, but now for a
# real reason instead of a units bug.

Date: 2026-09-28. Harness: `exp_1m_ctx_scaled.py` → `_1m_ctx_scaled.json`
Controls exact both eras (500t +325.8R / 279t +70.2R). In-memory patch, no
shared file edited.

## The bug this fixed

The previous run (`method/ONE_MIN_PATH_CONTEXT.md`) reported −325.8R by graying
**658 of 660** signals. The probe showed `ctx_extend` had median **8.7**
against thresholds of 0.5/1.0 — so nothing was ever being *decided*.

Cause: I measured a 15m-scale distance and divided it by 1m-scale
volatility. BTC's 15m range is several 1m ATRs wide, so the ratio was ~9
**by construction**.

## The corrected features

| feature | definition | scale |
|---|---|---|
| `ctx_pos_15m` | 1m close's position inside the signal 15m bar's own range | scale-free, 0..1 |
| `ctx_ext_15m` | (close − low_60min) / **ATR_15** | numerator and denominator both 15m |

The probe confirms the fix landed — this is the whole point of printing it:

| | old `ext` median | new `pos` median | new `ext` median |
|---|---|---|---|
| IS | 8.691 | **0.485** | **0.688** |
| OOS | 11.081 | **0.538** | **0.940** |

Graying moved from 658/660 to 175–352/660. The gate now actually decides
something, so its results are readable.

## Result: 0/10, but the closest arm is informative

| arm | IS dNet | OOS dNet | grayed (IS) |
|---|---|---|---|
| pos_0.25–0.75 | −246.4 | −49.9 | 352/660 |
| pos_hi_0.75 | −139.3 | −43.3 | 177/660 |
| pos_lo_0.25 | −102.8 | −32.2 | 175/660 |
| ext_2–4 | −299.8 | −83.4 | 530/660 |
| **ext_hi_4** | **−27.6** | **−9.7** | 17/660 |

Every arm loses in both eras. Same sign 10/10, so this is a clean close
rather than an era-flip.

**`ext_hi_4` is worth naming because it is a real (if weak) effect, not
noise:** rejecting trades whose 1m close sits more than 4× the 15m ATR above
the 60-minute low costs only −27.6R IS / −9.7R OOS while graying just 17
and 23 signals. It is *nearly* free and it is still a loss. That is the
honest shape of the answer: the feature is not measuring nothing, it is
measuring something too small to pay for itself.

## Verdict

- **The corrected path-context family is DEAD.** 0/10, same sign, controls
  green. Do not re-cut these features.
- **And with it, the last open 1m idea.** Together with the net-cost result
  (0/196 trigger cells) and the fill replication failure, the 1m timeframe
  has now been tested as a **trigger**, a **book**, an **exit/fill**, an
  **add-on gate**, and a **feature**. All closed.
- `ext_hi_4` at −27.6R/−9.7R is the strongest 1m result of the entire
  session, and it is still negative. That is the cleanest possible statement
  of why 1m is not the place to look.

The likely structural reason, stated once so it need not be re-derived:
the 15m book's edge is a property of the 15m swing *structure*, and no
re-framing of 1m data recovers information that structure did not already
contain. 1m is finer, not more informative.

**NOTHING ADOPTED.** Production untouched, all flags default-off.

