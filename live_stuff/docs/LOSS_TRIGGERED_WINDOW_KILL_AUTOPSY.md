# Stage 63 — Loss-Triggered HTF Window Kill

## Scope and design

Bybit BTCUSDT perpetual only. The tested thesis was:

> After N completed losses, the current parent HTF window is invalidated. Do not wait for its original 3R/16-day exit; resume from the next parent HTF window.

Frozen matrix:

- completed-loss thresholds: N = 2, 3, 4, 5;
- count losses inside the current window, or globally across windows;
- soft action: block new entries only;
- hard action: also close active same-window positions at the causal trigger timestamp;
- references: pure/literal v18 single + multi, current fullstack single, champion multi, UTC-Saturday multi;
- periods: IS 2023–2026 and reused OOS 2021–2022;
- 18 policies × 7 references × 2 periods = 252 path-true ledgers.

All custom arms disable the built-in three-loss halt, so the fair control is `no_builtin_halt`, not only the shipped baseline.

## Causality and identity

- Default-off identity passed: shipped `340 trades / +225.3R`, patched-off `340 / +225.3R`.
- A loss enters the streak only when its exit occurred by the candidate entry instant.
- The trigger runs at a later candidate and never rewrites prior trade history.
- A killed window cannot accept another entry; a different parent-window key resumes normally.
- Hard and soft are identical when no position is open when the next eligible candidate discovers the trigger. Across all arms, hard closed only 40 IS and 27 OOS positions.

## Primary result

Relative to `no_builtin_halt`, **zero custom policies improved net R in both IS and OOS for any of the seven references.**

| Reference | Both-period-positive custom policies |
|---|---:|
| Pure v18 single | 0 |
| Pure v18 multi | 0 |
| Literal v18 single | 0 |
| Literal v18 multi | 0 |
| Fullstack wage10 single | 0 |
| Champion multi | 0 |
| UTC-Saturday multi | 0 |

Individual OOS gains are genuine path-true effects, but every one has an IS or fair-control contradiction.

## Current multi references

### Champion multi

| Reference/control | IS net | OOS net | IS trades | OOS trades |
|---|---:|---:|---:|---:|
| Shipped baseline | +325.8R | +70.2R | 500 | 279 |
| No built-in halt | +308.5R | +60.5R | 557 | 320 |
| Window soft N2 | +67.1R | +94.7R | 352 | 215 |
| Window soft N3 | +141.3R | +60.7R | 445 | 259 |
| Window soft N4 | +164.1R | +70.3R | 496 | 294 |
| Window soft N5 | +200.0R | +65.6R | 528 | 303 |
| Global soft N3 | +42.1R | +88.3R | 342 | 219 |

- Window N2 improves OOS by `+34.3R` versus no-halt, but costs `−241.4R` in IS.
- Global N3 improves OOS by `+27.8R`, but costs `−266.4R` in IS.

### UTC-Saturday multi

| Reference/control | IS net | OOS net | IS trades | OOS trades |
|---|---:|---:|---:|---:|
| Shipped baseline | +359.0R | +60.2R | 454 | 253 |
| No built-in halt | +324.1R | +68.6R | 506 | 283 |
| Window soft N2 | +127.6R | +86.6R | 346 | 203 |
| Window soft N3 | +155.8R | +70.1R | 421 | 237 |
| Window soft N4 | +171.2R | +82.0R | 461 | 260 |
| Window soft N5 | +224.6R | +72.9R | 486 | 268 |
| Global soft N3 | +71.1R | +93.5R | 327 | 206 |

- Window N2 improves OOS by `+18.0R` versus no-halt, but costs `−196.4R` in IS.
- Global N3 improves OOS by `+24.9R`, but costs `−253.0R` in IS.


## Pure-v18 controls

### Pure single

- Best IS custom arm: global soft N5, `+161.7R`, only `−0.8R` versus no-halt.
- Its OOS result is `−20.1R`, or `−9.2R` versus no-halt.
- Window N4 gains `+1.9R` in OOS but costs `−28.6R` in IS.

### Pure multi

- Window N4 reduces IS DD (`31.5R → 25.5R`) but costs `−81.2R` net.
- Global soft N2 gains `+22.8R` in OOS but costs `−212.3R` in IS.
- No window-local threshold preserves both eras.

## Why DD can improve while total R collapses

The rule blocks the rest of the current HTF campaign after consecutive losses. Those later entries are often recovery/re-entry attempts. Blocking them removes losses, but also removes later winners and runners.

- Pure multi window N4 improves DD by about `6R`, but loses `81R` net in IS.
- Current multi N2 often improves OOS DD while removing `100–236` entries and large chunks of total R.

This is not a free risk trim; it changes v18 into a lower-frequency, lower-expectancy version of itself.

## Hard versus soft

Most hard and soft ledgers were identical because no same-window position remained active when the trigger was discovered. Hard closed only 40 IS and 27 OOS positions across the full matrix. A few arms differed by a few R in either direction, but hard action did not resolve the IS/OOS contradiction.

The rule is therefore primarily a **new-entry block**, not an effective portfolio liquidation mechanism.

## Verdict

```text
Loss-triggered HTF-window kill: REJECTED as a universal or current multi replacement.
```

Reasons:

1. zero policies improve both periods versus the fair no-halt control across seven references;
2. current multi OOS gains are real but accompanied by very large IS losses;
3. later same-window entries often contain recovery and runner contribution;
4. hard closing changes little because triggers usually occur after the cohort has exited.

Keep the raw matrix for research history. Do not add a production flag and do not re-test this N2–N5 family under renamed thresholds.

## Files

Harness:

```text
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\exp_thesis_loss_window_kill.py
```

Canonical results:

```text
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_loss_window_kill_results_is.json
C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_loss_window_kill_results_oos.json
```

The JSON files retain `"stage": 48` as a legacy internal label. The canonical research stage is Stage 63 because Stage 48 is already assigned to `retest_fill`.
