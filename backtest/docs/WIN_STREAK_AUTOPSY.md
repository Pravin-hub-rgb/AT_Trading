# Stage 64 — Completed-Win-Streak Policy Autopsy

## Scope

- Instrument: `BTCUSDT_BYBIT` linear perpetual only
- Periods: IS 2023–2026 and reused OOS 2021–2022
- References: pure v18 single/multi, literal v18 single/multi, fullstack single, champion multi, UTC-Saturday multi
- No production or live-trading changes
- Causal policy: only completed winners with `exit_ts <= candidate entry timestamp` contribute to the streak

This study tested completed winning-streak controls that were not the same as the existing same-window re-win autopsy.

Policies:

- global completed-win streak N = 2/3/4/5
- current-parent-window completed-win streak N = 2/3/4/5
- skip the next eligible signal once
- soft-close the current window (block later entries in that window)
- hard-close active positions in that window
- resume normally when the next parent window begins

The fair control for custom policies is `no_builtin_halt`, because the custom policy replaces the built-in loss-halt behavior. The shipped baseline is retained as a separate reference.

## Key result

The strongest branch was `global_soft_n3`:

- after three completed global wins, invalidate the current HTF window for new entries;
- do not close positions already open;
- continue with the next parent HTF window.

For the current multi references, this improved both periods versus `no_builtin_halt`:

| Reference | IS control | IS N3 | IS delta | OOS control | OOS N3 | OOS delta |
|---|---:|---:|---:|---:|---:|---:|
| Champion multi | +308.5R | +313.4R | **+4.9R** | +60.5R | +88.4R | **+27.9R** |
| UTC-Saturday multi | +324.1R | +325.4R | **+1.3R** | +68.6R | +77.9R | **+9.3R** |

The improvement is not universal across all seven references. Pure/literal/single references were mixed or negative, so this remains an open research candidate rather than a production rule.

## Current multi detail

### Champion multi — IS

| Policy | Trades | Gross R | Net R | Net R/trade | Win rate | Avg winner | Avg loss | PF | Net max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Shipped baseline | 500 | +445.2R | +325.8R | +0.652R | 30.0% | +5.114R | -0.919R | 2.38 | 27.7R |
| No-built-in-halt control | 557 | +439.8R | +308.5R | +0.554R | 29.3% | +4.904R | -0.912R | 2.22 | 32.6R |
| `global_soft_n3` | 542 | +441.9R | +313.4R | +0.578R | 29.9% | +4.868R | -0.912R | 2.27 | 31.7R |

`global_soft_n3` triggered 8 times and blocked 17 entries in IS.

### Champion multi — OOS

| Policy | Trades | Gross R | Net R | Net R/trade | Win rate | Avg winner | Avg loss | PF | Net max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Shipped baseline | 279 | +105.7R | +70.2R | +0.251R | 28.0% | +3.649R | -0.890R | 1.59 | 53.2R |
| No-built-in-halt control | 320 | +103.0R | +60.5R | +0.189R | 28.1% | +3.439R | -0.898R | 1.50 | 59.9R |
| `global_soft_n3` | 296 | +128.0R | +88.4R | +0.299R | 29.4% | +3.625R | -0.897R | 1.68 | 46.3R |

`global_soft_n3` triggered 6 times and blocked 32 entries in OOS.

### UTC-Saturday multi — IS

| Policy | Trades | Gross R | Net R | Net R/trade | Win rate | Avg winner | Avg loss | PF | Net max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Shipped baseline | 454 | +466.5R | +359.0R | +0.791R | 30.8% | +5.391R | -0.918R | 2.62 | 21.2R |
| No-built-in-halt control | 506 | +440.8R | +324.1R | +0.640R | 29.8% | +5.080R | -0.919R | 2.35 | 30.1R |
| `global_soft_n3` | 476 | +437.0R | +325.4R | +0.684R | 30.0% | +5.202R | -0.921R | 2.42 | 29.2R |

`global_soft_n3` triggered 9 times and blocked 40 entries in IS.

### UTC-Saturday multi — OOS

| Policy | Trades | Gross R | Net R | Net R/trade | Win rate | Avg winner | Avg loss | PF | Net max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Shipped baseline | 253 | +92.6R | +60.2R | +0.238R | 29.6% | +3.381R | -0.904R | 1.58 | 29.4R |
| No-built-in-halt control | 283 | +106.7R | +68.6R | +0.242R | 29.7% | +3.419R | -0.907R | 1.59 | 34.2R |
| `global_soft_n3` | 273 | +114.7R | +77.9R | +0.285R | 30.4% | +3.457R | -0.907R | 1.67 | 33.6R |

`global_soft_n3` triggered 5 times and blocked 17 entries in OOS.

## Other policy behavior

- `global_soft_n2` often improved the current multi OOS cells but removed more trades and was not consistent in IS.
- `global_soft_n4/n5` had fewer triggers and were close to the no-halt control.
- `window_soft_n2` was the strongest same-window branch in some references, but it was not stable across the full matrix.
- `skip` policies were less consistent than soft window invalidation.
- `hard` policies did not provide a meaningful advantage over the corresponding soft policy because the trigger was usually discovered after existing positions had already exited naturally.

## Mechanism interpretation

A completed-win streak does not prove that the current HTF direction is invalid. The result suggests a narrower portfolio mechanism:

> After several completed wins, a global streak may indicate that the current window has already received enough successful exposure, and later entries in that same window have lower marginal value.

This is different from a loss streak. A loss-triggered window kill often removes later recovery and runner trades. A win-triggered soft kill removes only later entries in a window after the campaign has already delivered several wins; existing positions remain eligible to continue.

The evidence is strongest for the current multi references, but it is not universal enough to claim that all v18 variants should use it.

## Default-stacking follow-up (completed)

The direct interaction test is recorded in `WIN_STREAK_STACKING_AUTOPSY.md`:

- Champion shipped default + `global_soft_n3`: IS `+325.8R -> +331.7R`, OOS `+70.2R -> +90.0R`; R/trade, PF and drawdown improve; OOS 10R+ remains 6.
- UTC-Saturday default + global N3: only `+1.5R` IS / `+0.6R` OOS.
- UTC-Saturday default + `window_soft_n3`: `+3.2R` IS, neutral OOS, 4 IS / 0 OOS blocks, complete runner preservation.
- The global rule is not universal and is negative on pure multi, literal multi, and fullstack single.

Updated verdict:

```text
Champion-specific global soft N3: strongest current research candidate
UTC-Saturday-specific window soft N3: conservative current research candidate
Universal default: rejected
Production change in this study: none
```

## Validation and files

- Identity gate: `340 trades / +225.3R` shipped versus patched-off; exact match.
- Streak state uses completed exits only and no future trade result.
- No retroactive trade rewriting in soft mode.
- Canonical original sweep harness: `backtest/tests/exp_thesis_win_streak.py`
- Original IS/OOS: `backtest/tests/_thesis_win_streak_results_{is,oos}.json`
- Direct default-stacking harness: `backtest/tests/exp_thesis_win_streak_stack.py`
- Stacking IS/OOS: `backtest/tests/_thesis_win_streak_stack_results_{is,oos}.json`
- Full stacking report: `backtest/docs/WIN_STREAK_STACKING_AUTOPSY.md`
- No production engine or live-trading code changed.

## Verdict

```text
Champion-specific default + global_soft_n3: strongest current research candidate
UTC-Saturday-specific default + window_soft_n3: conservative alternative
Universal win-streak default: rejected
Hard close: no meaningful incremental benefit
Production change in this study: none
```

Do not run another N2-N5 rename sweep. The next evidence should be a genuinely untouched future Bybit period, with the candidate fixed in advance as champion-global N3 and the king-window N3 control.

