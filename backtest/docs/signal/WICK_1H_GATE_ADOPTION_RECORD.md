# WICK 1h GATE - ADOPTION RECORD (decision record, nothing adopted yet)

**Written 2026-09-27.** Purpose: so that whoever picks this up after the
forward gate clears does not have to rediscover it, and - more importantly -
does not re-run the mistakes that cost this gate its first two investigations.

**STATUS: RESEARCH COMPLETE. NOT ADOPTED. Single blocker: forward gate 5/50.**

Related records: `method/CAPITAL_STAGE_PLAN.md` (a13), `method/CHECKLIST.md` 24.96/24.97,
`method/EXPERIMENT_LOG.md` rows 101/102, `AGENT_COORDINATION.md` (corrected-status
section), `method/BLEED_AUTOPSY.md` 5.3 (the original Stage B post-process claim),
`method/WICK_GATE_RULING_BRIEF.md` (plain-language version, outcome line added).

---

## 1. What the gate is, exactly

Pinned to source so it cannot drift. Do not paraphrase this section.

```
predicate : SHORT trades only
feature   : wick_atr12, on the 1-HOUR plane
formula   : wick_atr12 = (sum over 12 bars ending at j of
                         (high-max(open,close)) + (min(open,close)-low))
            / ATR14_1h[j]
            rounded to 3 dp
window    : 12 CLOSED 1h bars ending at j  (== 12 hours)
cutoff    : j = bisect_right(ts_1h, cutoff - 3600) - 1
            where cutoff = entry_ts + 900  (the entry 15m bar's close)
            => the last 1h bar that had CLOSED before the entry
guard     : feature is None unless j >= 50  (50+ 1h bars of history needed)
threshold : wick_atr12 < 6.026   (STRICT '<' - see section 5)
action    : GRAY - do not place the order; the engine still runs the trade
```

Source of truth: `exp_regime_structure_autopsy.py` - `compute_features()`
(the `j = bisect...` line and the `f["wick_atr12"] = ...` line) and
`wick_feats()` (the per-bar wick arithmetic). Feature values are reused from
`_regime_structure_is.json` / `_regime_structure_oos.json`; the independent
recompute in `exp_wick1h_audit.py` / `exp_wick1h_deep.py` reproduces them
from the engine.

**A gate on a 1-hour value is applied to a 15-minute entry.** That is
intentional - the HTF parent plane is the context - but it is exactly what got

## 2. Scope: champion + utcsat ONLY, age10 default-off

| config | params that differ from the others | trades/yr | verdict |
|---|---|---|---|
| `champion_multi_sw10` | exp_mltf, exp_persist=7 | 136 / 139 | **IN SCOPE** |
| `utcsat_multi_sw10` | exp_mltf, exp_persist=7, exp_skip_utc_sat=1 | 124 / 127 | **IN SCOPE** |
| `age10_dirmatch_swingpause_single_sw10` | exp_require_dir_match=1, exp_swingpause=1, exp_max_swing_age=10, **no exp_mltf** | 35 / 38 | **OUT OF SCOPE** |

age10 is a structurally different strategy (single not multi; dir-match and
swingpause filters; 3.5x fewer trades; IS book avgR +3.35 vs +0.65 / +0.79).
A threshold mined on the multi books has no business on it.

**This is also why "all 6 cells" is not the gate here.** Stage B pre-registered
4 cells (champion/utcsat x IS/OOS) and this gate clears **4/4 on those exact
terms**. Do not retrofit an all-6 requirement onto it - and equally, do not
claim all-6.

---

## 3. The evidence

| claim | value | where |
|---|---|---|
| Stage B parity | **4/4 exact to 1e-3**, now a hard assert | `exp_wick1h_deep.py` |
| Gray cascade | **0.00 in all cells** | `_wick1h_deep.json` |
| Gray seq-identical | **6/6** | `_gray_wick1h.json` |
| Cohort robust (ex-best) | **6/6 cells still negative** | `_wick1h_deep.json` |
| Stable window (champ+uts, both eras) | **5.0-5.4 \| 5.6-6.4** (hole at 5.5) | `_wick1h_deep.json` |
| Upper cliff | **6.4 -> 6.5** (champIS +24.59, utsIS +34.13 together) | `_wick1h_deep.json` |
| Flip points | IS 6.4 / 6.4 / 6.1 · OOS 7.2 / 7.2 / 6.6 | `_wick1h_deep.json` |
| Live gray dNet | **+28.1 / +25.7 / +19.8 / +23.8** (champ IS, uts IS, champ OOS, uts OOS) | `_gray_wick1h.json` |
| Live == post-process | **exact in 4/4** | `_gray_wick1h.json` |
| Path-true skip (contrast) | IS **-39.0 / -12.6**, OOS +7.5 / +24.0 | `_gray_wick1h.json` |

Rough annual value: (28.1 + 19.8) / 5.67y = **~8.5R/yr on champion**,
**~11.9R/yr on utcsat** OOS. The real win is not the R, it is that gray avoids
the cascade: **~67R on is/champion** versus skipping the trade outright.

Threshold status: **6.026 is a VALIDATED CANDIDATE, NOT FROZEN.** It sits
inside the 14-step stable window with ~0.37 of headroom below the cliff. It
was originally mined by Stage B; nothing here re-freezes it.

**Do NOT use 6.1.** It is the single all-6 point (age10 -0.29R on n=22) and it
was chosen after the fact to make age10 pass. Data snooping, not a derivation.

confused for two stages. See section 5.


## 4. Why gray, and not a skip

A normal removal frees the `busy_until` slot, which shifts `cooldown_bars` and
the loss streak. Stage B measured that cascade at **-78.6R, 280% of the direct
effect**; the path-true rerun turned a +28.1R post-process "pass" into
**-50.5R**.

A gray trade is still run to completion, so all chain state updates exactly as
if the trade had been taken, and only the P&L is suppressed. That is why
cascade is 0.00 and live dNet lands exactly on the post-process number.

**Consequence for the engine change:** the trade must be booked with `r = 0`
while still setting `busy_until`, the cooldown, and the streak. Gating the
cooldown is a BUG - it shifts the timeline and manufactures a fake cascade. See
`method/CAPITAL_STAGE_PLAN.md` (a11) and commit a3ca96b; the bug shipped in three
harnesses and produced a spurious -44R that I initially wrote up as a
structural property of gray mode.

Also: **costs are real.** The harness still deducts fee/slippage/funding on a
gray trade; live you do not pay them. That gap is `cost_relief` in
`_gray_wick1h.json` (+17.6R on is/champion) and is the difference between
`harness_d_net` and `live_d_net`. Compare live numbers, not harness numbers.

---

## 5. Mistakes that cost this gate two investigations - read before running

1. **The 15m predicate.** `exp_wick_short_pathtrue`, `exp_cascade_tax_test`
   and their children used 12 x **15m** bars with ATR15. Same name, different
   formula, different cohort (112 vs 74 trades on is/champion), OPPOSITE sign.
   Every "wick gate is dead" verdict in this repo was measured on that one. It
   is still dead - reconciled at -70.1 / -70.2 live on OOS - but that is not
   Stage B's gate. **Check the timeframe before believing any wick number.**
2. **`<=` instead of `<`.** Stage B's `bucket_of` is strict. Using `<=` added
   exactly one trade per IS cell and made parity fail. Parity is now asserted.
3. **A control failure is an abort, not a footnote.** An earlier run reported
   every verdict while its parity control was failing.
4. **Nested thresholds are one cohort, not N observations.** 4.5 / 5.0 / 5.5
   contain each other; they do not independently confirm anything.
5. **Windows must be reported as blocks.** This window is 5.0-5.4 | 5.6-6.4,
   with a hole at 5.5. Quoting it as a single range hides the hole.
6. **Verify before writing.** I attributed a stale number to another agent's
   document that did not contain it, and mis-transcribed a 6/6 robustness
   figure as 5/6. Both were caught by the other agent.

---

## 6. What happens next, and the adoption procedure

1. **Wait for the forward gate: 5/50 -> 50/50 trades.** This is the only
   outstanding blocker. It accrues passively; nothing needs running.
2. **When it clears, the ruling is the user's.** RESEARCH_POLICY: report raw
   P&L and caveats, no automatic gate.
3. **Only then does the engine owner implement it** - a gray flag on
   `v18_streak_halt.py` (short side, `wick_atr12 < 6.026`, book `r = 0`, keep
   every state update). Default-off until the user says so.
4. **age10 stays off** unless a separate pre-registered study is run for the
   single-book case. Do not reuse 6.026 there.

Evidence is complete; the remaining uncertainty is forward performance, not
backtest interpretation.

---

## 7. Number to remember

```
+28.1 / +25.7 / +19.8 / +23.8 R   (champ IS, uts IS, champ OOS, uts OOS)
0.00 cascade · 6/6 seq-identical · 6/6 ex-best · 4/4 parity asserted
window 5.0-5.4 | 5.6-6.4 · cliff 6.4->6.5 · 6.026 validated, not frozen
forward gate 5/50  <- the only thing between this and adoption
```
