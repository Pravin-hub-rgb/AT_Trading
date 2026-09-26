# WIN_STREAK_STACKING_AUTOPSY — Default-Halt Interaction

## Scope

- Instrument: `BTCUSDT_BYBIT` linear perpetual only
- Periods: IS 2023–2026 and reused OOS 2021–2022
- References: pure v18 single/multi, literal v18 single/multi, fullstack single, champion multi, UTC-Saturday king multi
- Identity gate: shipped `340 trades / +225.3R` versus patched-off, exact match
- Path-true test-only simulation; no production or live-loop change

This follow-up resolves the interaction question left open by Stage 64. Stage 64's custom policies disabled the built-in loss halt, so its primary comparison was `no_builtin_halt`. This study separately tests the direct stack on each shipped default.

## Frozen six-policy matrix

1. `shipped_default`
2. `default_global_soft_n3`
3. `default_window_soft_n3`
4. `no_builtin_halt`
5. `no_halt_global_soft_n3`
6. `no_halt_window_soft_n3`

`global_soft_n3` means: after three completed global wins, block new entries in the current parent HTF window; keep open positions; resume normally in the next parent HTF window.

## Current multi direct-default result

| Reference | Period | Shipped default | Default + global N3 | Delta | Default + window N3 | Delta |
|---|---|---:|---:|---:|---:|---:|
| Champion multi | IS | +325.8R | +331.7R | **+5.9R** | +328.9R | +3.2R |
| Champion multi | OOS | +70.2R | +90.0R | **+19.8R** | +70.2R | 0.0R |
| UTC-Saturday king | IS | +358.9R | +360.5R | **+1.5R** | +362.2R | **+3.2R** |
| UTC-Saturday king | OOS | +60.2R | +60.8R | **+0.6R** | +60.2R | 0.0R |

The direct stack therefore improves both current multi references in both periods, but the strength is configuration-specific.

## Champion multi detail

| Period | Policy | Trades | Gross R | Net R | Net R/trade | WR | Avg win | Avg loss | PF | Net max DD | 3R+ | 5R+ | 10R+ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IS | Shipped default | 500 | +445.2 | +325.8 | +0.652 | 30.0% | +5.114 | -0.919 | 2.38 | 27.7 | 63 | 45 | 17 |
| IS | Default + global N3 | 483 | +448.1 | +331.7 | +0.687 | 30.6% | +5.108 | -0.919 | 2.46 | 24.6 | 62 | 44 | 16 |
| OOS | Shipped default | 279 | +105.7 | +70.2 | +0.251 | 28.0% | +3.649 | -0.890 | 1.59 | 53.2 | 30 | 17 | 6 |
| OOS | Default + global N3 | 262 | +124.1 | +90.0 | +0.343 | 29.0% | +3.825 | -0.896 | 1.74 | 43.2 | 31 | 18 | 6 |

Champion triggers/blocks:

- IS: 8 triggers, 17 blocked entries
- OOS: 5 triggers, 30 blocked entries

The candidate improves net R/trade, PF, and drawdown in both periods. The tail is preserved except one IS 10R+ trade (`17 -> 16`); OOS 10R+ remains 6.

## UTC-Saturday king detail

| Period | Policy | Trades | Gross R | Net R | Net R/trade | WR | Avg win | Avg loss | PF | Net max DD | 3R+ | 5R+ | 10R+ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IS | Shipped default | 454 | +466.5 | +358.9 | +0.791 | 30.8% | +5.391 | -0.918 | 2.62 | 21.2 | 62 | 42 | 18 |
| IS | Default + global N3 | 425 | +463.1 | +360.5 | +0.848 | 31.1% | +5.553 | -0.921 | 2.72 | 20.9 | 59 | 41 | 17 |
| IS | Default + window N3 | 450 | +469.2 | +362.2 | +0.805 | 30.9% | +5.428 | -0.917 | 2.64 | 21.2 | 62 | 42 | 18 |
| OOS | Shipped default | 253 | +92.6 | +60.2 | +0.238 | 29.6% | +3.381 | -0.904 | 1.58 | 29.4 | 28 | 14 | 4 |
| OOS | Default + global N3 | 245 | +92.5 | +60.8 | +0.248 | 29.4% | +3.461 | -0.906 | 1.59 | 28.6 | 27 | 14 | 4 |
| OOS | Default + window N3 | 253 | +92.6 | +60.2 | +0.238 | 29.6% | +3.381 | -0.904 | 1.58 | 29.4 | 28 | 14 | 4 |

King interpretation:

- Global N3 is only a small historical improvement and removes 29 IS plus 8 OOS trades.
- Window N3 is the conservative king branch: +3.2R IS, neutral OOS, only 4 IS blocks and zero OOS blocks, and complete runner preservation.
- Global N3 is not compelling enough to prefer over the conservative king branch.

## Non-current references prove the rule is not universal

Direct default + global N3 deltas:

| Reference | IS delta | OOS delta |
|---|---:|---:|
| Pure v18 single | -3.0R | +10.3R |
| Pure v18 multi | -27.8R | +4.4R |
| Literal v18 single | +12.0R | +5.5R |
| Literal v18 multi | -9.8R | -21.8R |
| Fullstack single | -38.1R | -5.5R |

Conclusion: this cannot be added to every v18 configuration or treated as a universal engine default.

## Verdict

```text
Champion default + global_soft_n3:
  strongest current research candidate
  positive IS and reused OOS
  better R/trade, PF, and drawdown
  preserve OOS 10R+ tail; lose one IS 10R+ trade

UTC-Saturday default + window_soft_n3:
  conservative current research candidate
  +3.2R IS, neutral OOS
  minimal trade reduction and complete runner preservation

Universal default:
  rejected

Production change in this study:
  none
```

## Files

- Harness: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\exp_thesis_win_streak_stack.py`
- IS: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_win_streak_stack_results_is.json`
- OOS: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_win_streak_stack_results_oos.json`
- Updated Stage 64 report: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\docs\WIN_STREAK_AUTOPSY.md`
