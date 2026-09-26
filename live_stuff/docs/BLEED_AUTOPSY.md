# Stage B - Bleed Autopsy (net-negative bucket hunt + removal test)

**Date:** 2026-09-26 | **Status:** COMPLETE + causality-audited - **FINAL: 2/4 removal PASS**
(ORIGINAL "4/4 PASS" + chain HEADLINE RETRACTED - lookahead leak found post-run, fixed same session)
**Harness:** `live_stuff/tests/exp_bleed_autopsy.py` (closed-only enrich, fixed in place) -> `_bleed_autopsy_results.json` (= 2/4)
**Audit:** `verify_bleed_causality.py` -> `_bleed_autopsy_CLOSEDONLY.json` (byte-identical to the fixed main JSON, excl. elapsed)
**Identity:** gate IDENTICAL both scopes | **Smoke:** PASS 351t / +211.7R | **Engine:** untouched (post-process)

## 1. Goal (user round, pre-registered)

Find a bucket whose **net R is NEGATIVE in all 4 cells** (champion/utcsat x IS/OOS); remove it;
the baseline must then be **strictly better: net up, trades down, avg/trade up** - ideally in all
4 cells. Follow-up: is there an unexplored LTF-vs-HTF split? Answer: all prior studies score at
the **LTF trade list**; the **HTF chain-state plane** (chain running-R, streak, age, direction
continuity, 4h context) was never bucketed - that is this stage's hunting ground, plus
time-of-day/weekday (user approved) and 8 dir-masked Z1 survivors.

## 2. Phase-0 (why new features were mandatory)

Mined all **74 existing Z1 buckets** (`_regime_structure_{is,oos}.json`): **ZERO 4/4-negative,
ZERO 3/4-negative with n>=15.** Neg-count histogram {0: 48, 1: 9, 2: 16, 3: 1}. Best era-flips
(pool direction hides the bleed): `wick_atr12|<=6.03` (IS +11.4/+17.6, OOS -28.2/-30.4),
`flips96|4-5` (IS +18.2/+7.7, OOS -28.0/-27.3), `vol7_prev7|>1.06` (IS +75.6/+71.3, OOS
-11.5/-24.1). Lesson: the negative pocket was direction-conditioned, so Z1 features are carried
forward **masked by trade direction**.

## 3. Method

**30 features**, all causal at `obs_ts = entry_ts + 900` (j<50 -> None):

- **Chain state (new plane):** chain_len (1/2/3/>=4), chain_same (dir matches current), chain_r_so_far
  (<0 / 0 / 0-3 / >3), chain_wl_streak (<=-2 / -1 / 0 / +1 / +2 / >=+3), chain_age_h, last_swing_age_h, flip_age_h
- **4h context (synthesized):** h4_dir, h4_agree, h4_flip_age, h4_range_pos
- **Structure/regime:** struct (up/mixed/down), swing_ret_pct, atr_pct, atr_pct_rank, day_range_pos, chop_side_dur
- **Time (user approved):** hour6 (UTC blocks), weekday (UTC Mon=1..Sun=7)
- **LTF state:** prev_streak, prev_net_cum20, entries_24h
- **Dir-masked Z1 edges (IS-pooled, applied unchanged):** wick_atr12 / flips96 / vol7_prev7 /
  range48_pct each x {long, short} - edges lifted from `_regime_structure_is.json`

Buckets: fixed bins, IS-pooled terciles (Q1-Q4 labels), or masked edges. Tercile edges printed
in the run (e.g. chain_age_h Q1<=8.5 / Q2<=17.5 / Q3<=35.75).

**FIND rule (pre-registered in harness docstring):** bucket qualifies iff
`n >= 15 AND share <= 35% AND sumNet < 0` in **ALL 4 cells**.

**REMOVAL PASS (pre-registered):** for each qualifier, drop its trades and re-score;
pass iff `dNet > 0 AND avgNet/trade >= baseline AND n < baseline AND curve_better`
in **ALL 4 cells**. Removal is direct post-process only (no chain re-timing - Study 1:
direct dominates IS).

## 4. Phase-1 qualifiers: 4 of 114 buckets x 4 cells

| qualifier | IS champ net | IS uts net | OOS champ net | OOS uts net | bucket n (4 cells) | share |
|---|---|---|---|---|---|---|
| chain_r_so_far \| <0 | -19.7 | -20.1 | -16.4 | -10.0 | 82/57/45/34 | 16.4/12.6/16.1/13.4% |
| chain_wl_streak \| -1 | -12.9 | -17.2 | -11.7 | -9.5 | 73/52/35/29 | 14.6/11.5/12.5/11.5% |
| wick_atr12@short \| <=6.03 | -28.1 | -25.7 | -19.8 | -23.8 | 74/62/35/36 | 14.8/13.7/12.5/14.2% |
| flips96@short \| 4-5 | -8.2 | -14.0 | -12.8 | -11.6 | 37/37/17/16 | 7.4/8.1/6.1/6.3% |

All also n>=15 and share<=35% in every cell. (Closest miss: `wick_atr12@short|6.03-6.90` era-flips,
2/4 negative - pass-2 pair stage never ran because phase-1 produced qualifiers.)

**Numbers above are the CORRECTED closed-only enrich (canonical).** Chain rows differ from the
original leaky run (which showed -42.0/-30.6/-19.5/-13.0 and n 80/58/43/32): the leak inflated
the chain buckets' negativity; see the audit in section 9.9. Masked rows are byte-identical
under both enriches (no trade state involved).

## 5. Removal results: 2/4 PASS (corrected closed-only; original leaky run showed 4/4)

Baselines: is|champion n500 net+325.8 avg+0.652 DD27.7 calmar3.202 | is|utcsat 454 +358.9
+0.791 21.2 4.619 | oos|champion 279 +70.2 +0.251 53.2 0.659 | oos|utcsat 253 +60.2 +0.238
29.4 1.025.

### 5.1 Remove `chain_r_so_far < 0` (chain already losing) - **FAIL (HEADLINE RETRACTED)**

Original (leaky) run showed PASS 4/4 with dNet +42.0/+30.6/+19.5/+13.0 - **that result is
retracted** (lookahead leak, section 9.9). Under the corrected closed-only enrich:

| cell | n | net R | dNet | avgNet | maxDD | calmar | curve |
|---|---|---|---|---|---|---|---|
| is champ | 500->418 | +325.8->+345.5 | +19.7 | +0.652->+0.827 | 27.7->27.7 | 3.202->3.404 | True |
| is uts | 454->397 | +358.9->+379.1 | +20.1 | +0.791->+0.955 | **21.2->26.2** | 4.619->**3.940** | **False -> FAIL** |
| oos champ | 279->234 | +70.2->+86.6 | +16.4 | +0.251->+0.370 | 53.2->40.5 | 0.659->1.068 | True |
| oos uts | 253->219 | +60.2->+70.2 | +10.0 | +0.238->+0.320 | 29.4->25.2 | 1.025->1.390 | True |

**FAIL on is|utcsat:** net still rises (+20.1) but drawdown actively worsens (+5.0R) and
calmar drops 4.619->3.940, so the pre-registered all-4-cells rule fails. Not a rounding
loss. The bucket itself stays 4/4-negative descriptively (nets -19.7/-20.1/-16.4/-10.0)
-> FIND survives, REMOVAL does not. Trades cut 15-16%.

### 5.2 Remove `chain_wl_streak = -1` (prior same-chain trade lost) - **FAIL (retracted)**

| cell | n | net R | dNet | avgNet | maxDD | calmar | curve |
|---|---|---|---|---|---|---|---|
| is champ | 500->427 | +338.7 | +12.9 | +0.652->+0.793 | 27.7->27.7 | 3.202->3.337 | True |
| is uts | 454->402 | +376.2 | +17.2 | +0.791->+0.936 | **21.2->26.2** | 4.619->**3.910** | **False -> FAIL** |
| oos champ | 279->244 | +81.9 | +11.7 | +0.251->+0.336 | 53.2->43.3 | 0.659->0.946 | True |
| oos uts | 253->224 | +69.7 | +9.5 | +0.238->+0.311 | 29.4->24.9 | 1.025->1.401 | True |

**FAIL on the same cell** (is|utcsat, DD 21.2->26.2). Both chain removals die of one cause:
the leaky enrich had flattered the chain features (the leak made them look better at
identifying losers than they really are - section 9.9).

### 5.3 Remove `wick_atr12@short <= 6.03` (short trades, low opposing-wick days) - **PASS (HEADLINE)**

| cell | n | net R | dNet | avgNet | maxDD | calmar | curve |
|---|---|---|---|---|---|---|---|
| is champ | 500->426 | +353.8 | **+28.1** | +0.831 | 23.0 | 4.190 | True |
| is uts | 454->392 | +384.6 | **+25.7** | +0.981 | 20.1 | 5.224 | True |
| oos champ | 279->244 | +89.9 | **+19.8** | +0.369 | 36.7 | 1.224 | True |
| oos uts | 253->217 | +84.0 | **+23.8** | +0.387 | 19.8 | 2.124 | True |

Bucket avgNet -0.38/-0.41/-0.57/-0.66 - the Z1 era-flip candidate that only bleeds when
conditioned on shorts. Best OOS DD improvement (uts 29.4->19.8).

### 5.4 Remove `flips96@short = 4-5` (short trades, 4-5 swing flips in 96h) - **PASS**

| cell | n | net R | dNet | avgNet | maxDD | calmar | curve |
|---|---|---|---|---|---|---|---|
| is champ | 500->463 | +333.9 | **+8.2** | +0.721 | 25.1 | 3.621 | True |
| is uts | 454->417 | +373.0 | **+14.0** | +0.894 | 18.7 | 5.428 | True |
| oos champ | 279->262 | +82.9 | **+12.8** | +0.317 | 47.6 | 0.871 | True |
| oos uts | 253->237 | +71.8 | **+11.6** | +0.303 | 25.0 | 1.438 | True |

Smallest effect (share only 6-8%) but PASS 4/4.

**Sections 5.3/5.4 (masked): all 8 cells - maxDD down AND calmar up, net-up AND trades-down
AND avg-up (the user's strict target), BYTE-IDENTICAL under both enriches** (pure market
structure from `z1_compute`, no trade state - immune to the leak). **Sections 5.1/5.2
(chain): FAIL** - 3/4 cells each pass, is|utcsat curve worsens (DD 21.2->26.2).

## 6. Reading

1. **The bleed lives on the SHORT side and inside already-losing chains.** 3 of 4 buckets are
   short-conditioned or chain-state; the 4h/weekday/time buckets produced NO 4/4-negative
   (weekday: Mon n=0 across all cells - entries never land Monday UTC; descriptive curiosity only).
2. **Direction-conditioning rescues two Z1 era-flips:** pooled `wick_atr12|<=6.03` and
   `flips96|4-5` flip eras (2/4 negative); masked to shorts they are 4/4-negative in both eras.
   The pooled era-flip was averaging long-positive against short-negative.
3. **Headline after the audit = `wick_atr12@short <= 6.03`** (best OOS DD reduction:
   champion 53.2->36.7, utcsat 29.4->19.8; dNet +28.1/+25.7/+19.8/+23.8; removal immune to
   the leak). The chain plane remains interesting DESCRIPTIVELY - both chain buckets stay
   4/4-negative after the fix - but their removals fail the equity rule. The leaky version
   was partly right by accident: folding still-open trades' outcomes made the chain features
   look better at identifying losers than they really are.

## 7. Caveats

- **The leak (found post-run, now fixed):** original `enrich_sequential` folded each trade's
  final net R in ENTRY order; with `exp_mltf` concurrent positions, 178 trades read state
  containing an unclosed trade (203 prior-open observations). Same bug class the loss-streak
  work already fixed ("only trades exited by the candidate entry timestamp may contribute").
  Chain results above are POST-FIX; masked results are byte-identical. Audit: section 9.9.
- **Overlap:** `chain_wl_streak = -1` is largely a subset of `chain_r_so_far < 0` - ONE family;
  stacking both removals is UNTESTED (would double-count most of the same trades). Now
  descriptive-only anyway (both removals FAIL the equity rule).
- **Combinations UNTESTED:** removing multiple qualifiers together = future work (pairs showed
  diminishing dNet in Stage A lessons).
- **Selection:** 114 buckets x 4 cells scanned; the 4/4-negative FIND rule is strict (a lucky
  bucket must go negative in both eras AND both lanes) but selection risk is not zero. Rules were
  pre-registered in the harness docstring before the run.
- **Post-process, no chain re-timing** (Study 1: direct dominates IS; chain shift small).
- **OOS luck caveat** (Study 2 / LOG 74): the weak OOS baseline makes OOS deltas easier to
  achieve - applies to all four removals' OOS lifts.
- **Cosmetic:** h4_flip_age terciles degenerate on integer data (quartile edges 1/1/2 -> empty
  "<=1"/"1-1" labels; buckets still complete); `weekday` Mon bucket n=0.

## 8. Verdict

**FINAL: 2/4 pre-registered removal PASS.**

- **PASS / recommended candidate: `wick_atr12@short <= 6.03`** (headline - best OOS DD
  reduction 53.2->36.7 and 29.4->19.8) and **`flips96@short 4-5`** - both byte-identical
  under the leaky and closed-only enriches (no trade state involved).
- **RETRACTED: `chain_r_so_far < 0` and `chain_wl_streak = -1`.** The original 4/4 PASS
  relied on a lookahead leak in `enrich_sequential`; corrected run fails is|utcsat
  (DD 21.2->26.2, calmar 4.619->3.940/3.910, curve False). Descriptive FIND survives
  (both buckets still 4/4-negative) - recorded, NOT deployable.

No gate/sizing engine change made; harness fixed in place (closed-only). Adoption =
user's call (RESEARCH_POLICY). Comparison vs X/Y/Z/M2 sizing candidates: deferred to
end-of-session side-by-side (they are sizing lifts, this is a removal - different lever).

## 9. Harness reference (`live_stuff/tests/exp_bleed_autopsy.py`)

### 9.1 Reproduce

```
$env:PYTHONIOENCODING='utf-8'
& "C:\Users\Pravin\AppData\Local\Programs\Python\Python312\python.exe" -u exp_bleed_autopsy.py
   (workdir live_stuff/tests; runtime ~64s; needs pandas -> Python312, NOT the default 3.10)
```

Gates printed by the run itself: `[identity-gate] shipped 340t/+225.3R vs patched-off
340t/+225.3R -> IDENTICAL` (both scopes), final `REMOVAL PASS: 2 / 4 tested` (post-fix;
the pre-fix run printed 4/4 - retracted), then `wrote ... _bleed_autopsy_results.json`.
After logging: `test_smoke.py` PASS 351t/+211.7R (Python312).

**Imports (reuse, no copies):**

| source | what is reused |
|---|---|
| `experiment_registry` | `BP`, `EXPERIMENTS` (lane params: champion_multi_sw10, utcsat_multi_sw10) |
| `run_experiment.net_r` | per-trade net R (fees 0.055%/side + funding) for running-R / streak state |
| `test_experiments_craze.build_module` | patched v18 engine factory (identity gate) |
| `exp_boundary_state_autopsy` | `load_scope(scope)` (IS/OOS datasets), `obs_ts` (entry_ts+900) |
| `exp_equity_quality` | `equity_quality`, `arm_scores`, `curve_better` (calmar/ulcer/sortino bundle) |
| `exp_regime_structure_autopsy` | `build_arrays` (1h OHLC+TR), `bucket_of`, `compute_features` (z1, for masked), `_chop_series_1h(lb=14)` |
| `_regime_structure_is.json` | Z1 survivor edges/labels for the 8 dir-masked features |

### 9.2 Pipeline (6 phases, one process, both scopes)

1. **Load Z1 edges; build engine** (`build_module()` - identity asserted inside).
2. **Per scope:** `load_scope` -> `build_arrays` -> chop series -> `build_ctx`:
   confirmed sw10 swings -> `conf` rows {ts, dir(+-1), dur, ext, ret} sorted by confirm
   ts (+ `conf_ts/conf_dir/conf_dur` parallel lists for bisect); `h4_series` aggregates
   completed 4h buckets (epoch//14400) -> keys/ohlc/dirs.
3. **Per lane:** engine run -> `ltf_trades` sorted by entry_ts; `compute_new` per trade
   (causal snapshot at `obs_ts`); `enrich_sequential` computes the path-dependent state
   **CLOSED-ONLY (post-audit fix): a prior trade contributes only when `exit_ts <= cutoff`**
   - `chain_r_so_far` (net R of closed trades sharing `_ckey` = first-confirm ts of the
   chain), `chain_wl_streak` (signed streak over closed same-chain trades), `prev_streak`,
   `prev_net_cum20` (last 20 closed), `entries_24h` (rolling 86400s, entry times).
   `z1_compute` per trade for masked bases. (Original entry-order fold = the leak, 9.7 #5.)
4. **Edges:** tercile4 = quartiles of IS rule-lane pools (>=40 values) applied unchanged
   to both eras; masked = Z1 JSON edges; `payload["features"]` records every kind/edges/
   labels (reproducible from JSON alone).
5. **Bucket matrix** (n / sumR / sumNet / share per label x 4 cells) -> printed ->
   **FIND** (`find_rule`) -> `qualifiers_phase1`.
6. **REMOVAL** per qualifier (`removal_test`: drop membership trades, re-score, assert
   excl+keep == total) -> PASS/FAIL table; **PASS-2 pairs** (`removal_pair`, intersection
   skip, `cells_ref`) ONLY if phase-1 empty - this run: phase-1 had 4, so JSON has NO
   `pass2`/`removals_pass2` keys.

### 9.3 Causality rules

- cutoff = `obs_ts(trade)` = entry_ts + 900; features read the last **closed** 1h bar
  (`ts <= cutoff - 3600`); `j < 50` -> whole feature dict `{"ok": False}` (warmup).
- `chain_state`: bisect on confirm ts <= cutoff; chain = maximal same-dir run of
  confirmed swings (`key` = confirm ts of run start). State keying by ts (not idx) so
  IS/OOS chains cannot bleed into each other.
- `enrich_sequential` is CLOSED-ONLY (post-audit fix): state reads only trades with
  `exit_ts <= cutoff`, and is updated AFTER the current trade's features are read. The
  original entry-order version leaked still-open trades' final R (9.7 #5, section 9.9).
- 4h: only completed buckets (`bmax = (cutoff - 14400) // 14400`); `day_range_pos` is
  None unless the last closed bar is in the same UTC day as cutoff; time features from
  `time.gmtime` (UTC) - weekday Mon=1..Sun=7, hour6 = tm_hour//6.
- Masked: value taken only when trade direction matches (+1 long / -1 short), else None
  (bucket skipped, not defaulted).

### 9.4 Feature table (30 features -> 114 buckets)

| feature | family | kind | buckets / edges (IS-pooled quartiles where t4) |
|---|---|---|---|
| chain_len | chain | fixed | 1 / 2 / 3 / >=4 |
| chain_same | chain | fixed | 0 / 1 (chain dir vs trade dir) |
| chain_r_so_far | chain | fixed | <0 / 0 / 0-3 / >3 |
| chain_wl_streak | chain | fixed | <=-2 / -1 / 0 / +1 / +2 / >=+3 |
| chain_age_h | chain | t4 | <=8.5 / 8.5-17.5 / 17.5-35.75 / >35.75 |
| last_swing_age_h | chain | t4 | <=4.5 / 4.5-10.25 / 10.25-17.25 / >17.25 |
| flip_age_h | chain | t4 | <=8.5 / 8.5-17.5 / 17.5-35.75 / >35.75 |
| h4_dir | 4h | fixed | short / long |
| h4_agree | 4h | fixed | 0 / 1 |
| h4_flip_age | 4h | t4 | <=1 / 1-1 / 1-2 / >2 (degenerate labels, see quirks) |
| h4_range_pos | 4h | t4 | <=26.3 / 26.3-52.8 / 52.8-76.5 / >76.5 |
| struct | structure | fixed | down / mixed / up (last 2 up + 2 down swing exts) |
| swing_ret_pct | structure | t4 | <=0.909 / 0.909-1.536 / 1.536-2.707 / >2.707 |
| atr_pct | regime | t4 | <=0.425 / 0.425-0.601 / 0.601-0.766 / >0.766 |
| atr_pct_rank | regime | t4 | <=20 / 20-39 / 39-63.5 / >63.5 (rolling 200-bar pct) |
| day_range_pos | regime | t4 | <=26.8 / 26.8-53.9 / 53.9-81 / >81 |
| chop_side_dur | regime | t4 | <=2 / 2-5 / 5-11 / >11 (side = chop vs 55/61.8 bands) |
| hour6 | time | fixed | 0-6 / 6-12 / 12-18 / 18-24 (UTC) |
| weekday | time | fixed | Mon..Sun (UTC) |
| prev_streak | ltf | fixed | <=-2 / -1 / 0 / +1 / +2 / >=+3 (global, prior trades) |
| prev_net_cum20 | ltf | t4 | <=-3.88 / -3.88-7.78 / 7.78-29.27 / >29.27 |
| entries_24h | ltf | fixed | 0 / 1 / 2 / >=3 |
| wick_atr12@long/@short | masked | masked | <=6.03 / 6.03-6.90 / >6.90 (Z1 edges) |
| flips96@long/@short | masked | masked | <=1 / 2-3 / 4-5 / >=6 (Z1 edges) |
| vol7_prev7@long/@short | masked | masked | <=0.85 / 0.85-1.06 / >1.06 (Z1 edges) |
| range48_pct@long/@short | masked | masked | <=3.45 / 3.45-5.37 / >5.37 (Z1 edges) |

Bucket counts: fixed 45 + t4 11x4=44 + masked 26 = **114**.

### 9.5 Rules (code-level)

- `find_rule` (line ~321): all 4 cells -> `n >= 15 AND share <= 35.0+1e-9 AND sumNet < 0`.
- `removal_test` cell_ok (line ~501): `(d_net > 0) AND avg_net >= base_avg AND
  n < base_n AND curve_better(d)`; overall PASS = AND over 4 cells.
- `curve_better` = equity-quality arm scores positive (from `exp_equity_quality`).

### 9.6 JSON schema (`_bleed_autopsy_results.json`)

```
stage/instrument, find_rule, removal_rule, years{is:3.67, oos:2.0}
cells            : {}            (placeholder - not populated; trades live in memory only)
features         : {name: {kind, edges, labels}}          <- reproducibility record
qualifiers_phase1: [{name, label, cells: {"scope|lane": [n, share, sumNet]}}]   (4)
removals_phase1  : [{name, label, rule:"phase1", pass, cells: {"scope|lane":
                     {excl, n, base_n, net, base_net, d_net, avg_net, base_avg,
                      max_dd, base_max_dd, calmar, base_calmar, curve_better, cell_pass}}}]
removal_pass_count: 2
matrix           : {"scope|lane|feature": {label: {n, sumR, sumNet, net, share}}}
elapsed_sec      : 64.2
(no pass2 / removals_pass2 keys - phase-1 non-empty, PASS-2 never ran)
```

### 9.7 Bugs fixed (4 build-time + 1 post-run critical)

1. `KeyError: conf_dur` - `z1_compute` needs `ctx["conf_dur"]`; first `build_ctx` draft
   omitted it -> added (parallel to conf_dir).
2. FIND-rule rounding bug - `sumNet` was rounded to 1dp before the `< 0` test, so a
   -0.04 bucket became -0.0 (falsy) -> aggregation now keeps full precision (rounding
   only for display/net fields).
3. `d_net` display typo `round(x or 0.1)` -> `round(x or 0.0, 1)` (0.0 must stay 0.0).
4. `cells_ref` never populated for `removal_pair` -> `cells_ref.update(cells)` after the
   scope loop (PASS-2 path; unused in the reported run but required for correctness).
5. **LOOKAHEAD LEAK (post-run, critical - found by `verify_bleed_causality.py`):**
   `enrich_sequential` folded each trade's FINAL net R at entry order; with `exp_mltf=True`
   concurrent positions, a prior-by-entry trade could still be OPEN at the current cutoff,
   so its outcome entered `chain_r_so_far` / `chain_wl_streak` / `prev_streak` /
   `prev_net_cum20` as future information (audit: 203 prior-open observations across 178
   trades). Same bug class the loss-streak work already fixed. Effect: chain removals
   PASS 4/4 -> FAIL under closed-only; masked candidates byte-identical. Fixed in place
   (see 9.9); `removal_pass_count` 4 -> 2.
(An earlier malformed draft of the file was overwritten wholesale before first execution.)

### 9.8 Known quirks / cosmetic

- `h4_flip_age` integer data makes quartile edges 1/1/2 -> labels "<=1" and "1-1" are
  empty (n=0); buckets still partition the book completely - label cosmetics only.
- `weekday` Mon bucket is n=0 in all 4 cells (engine never enters Monday-UTC day) -
  descriptive curiosity, no rule touched it.
- `day_range_pos` is None for trades whose last closed 1h bar sits in the prior UTC day
  (bucket skipped; ~1 bar wide edge effect).
- `payload["cells"]` is an empty dict by design; per-cell detail lives in
  `removals_phase1` + `matrix`.

### 9.9 Causality audit (`verify_bleed_causality.py` -> `_bleed_autopsy_CLOSEDONLY.json`)

Post-run audit monkey-patched a **closed-only** enrich (only trades with `exit_ts <= cutoff`
contribute) and re-ran the ENTIRE pipeline - same rules, edges, FIND/REMOVAL code:

- **Leak size:** `prior_open_at_cutoff: 203` observations; `trades_with_leak: 178` (trades
  whose state contained an unclosed trade).
- **Chain bucket nets:** leaky -42.0/-30.6/-19.5/-13.0 -> closed -19.7/-20.1/-16.4/-10.0
  (FIND survives; membership shifts n 80/58/43/32 -> 82/57/45/34).
- **Removal verdicts:**

| qualifier | leaky (original) | closed-only (correct) |
|---|---|---|
| chain_r_so_far <0 | PASS 4/4 | **FAIL** - is\|uts DD 21.2->26.2, calmar 4.619->3.940, curve False |
| chain_wl_streak -1 | PASS 4/4 | **FAIL** - is\|uts DD 21.2->26.2, calmar 4.619->3.910 |
| wick_atr12@short <=6.03 | PASS 4/4 | PASS 4/4 (byte-identical) |
| flips96@short 4-5 | PASS 4/4 | PASS 4/4 (byte-identical) |

- **Harness now CONTAINS the closed-only enrich**; a fresh run of `exp_bleed_autopsy.py`
  reproduces `_bleed_autopsy_CLOSEDONLY.json` byte-for-byte (verified - only `elapsed_sec`
  differs between JSONs), and `_bleed_autopsy_results.json` was regenerated with
  `removal_pass_count: 2`. The leaky JSON is superseded (its numbers survive only in this
  doc's retracted tables + the audit JSON's comparison column).
