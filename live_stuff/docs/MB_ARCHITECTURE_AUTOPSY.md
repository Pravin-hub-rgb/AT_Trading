# Stage 40 — 15m MB20/MB30/MB40/MB50 Architecture

**Date:** 2026-09-25  
**Instrument:** BTCUSDT, Bybit linear perpetual only  
**Periods:** IS 2023–2026; reused validation/OOS 2021–2022  
**Production changes:** none

## Purpose

This was the requested `15m MB50 → MB20/MB30/MB40/MK50` architecture test. Only the 15m swing chain was rebuilt. The following stayed frozen:

- 1h HTF chain: `min_bars=20`;
- all strategy parameters;
- 1m fine structural exits;
- costs/funding;
- portfolio and halt rules.

MB50 is the exact identity architecture control:

```text
mb50_exact_trade_match = true
```

This was a path-true architecture comparison: changing the 15m chain changes signals, entries, busy/concurrency state, and later trade sequence.

## Swing counts

| 15m minBars | Swing count |
|---:|---:|
| 20 | 5,150 |
| 30 | 4,174 |
| 40 | 3,413 |
| 50 | 2,900 |

## IS results

| Reference | MB50 baseline net | MB20 | MB30 | MB40 | Best alternative |
|---|---:|---:|---:|---:|---:|
| Pure single | +101.1R | -51.5R | +3.4R | +50.8R | MB40, -50.3R vs MB50 |
| Pure multi | +272.5R | +206.8R | +262.1R | +213.1R | MB30, -10.5R |
| Literal single | +196.8R | -59.7R | +26.4R | -12.7R | MB30, -170.4R |
| Literal multi | +279.4R | +286.4R | **+321.9R** | +241.2R | MB30, **+42.4R** |
| Fullstack single | +310.7R | +47.3R | +94.3R | +90.4R | MB30, -216.4R |
| Champion multi | +325.8R | +264.5R | +279.6R | +249.3R | MB20, -61.3R |
| UTC-Saturday multi | +358.9R | +225.6R | +268.7R | +245.0R | MB20, -133.3R |

### IS trade-quality examples

#### Literal multi

| Architecture | Trades | Net R | Avg net R | Win rate | Gross PF | Max net DD |
|---|---:|---:|---:|---:|---:|---:|
| MB50 | 443 | +279.4R | +0.631R | 31.4% | 2.43 | 34.7R |
| MB30 | 653 | +321.9R | +0.493R | 31.9% | 2.32 | 53.5R |

MB30 increased total R by `+42.4R`, but average R/trade fell from `+0.631R` to `+0.493R`, and drawdown rose from `34.7R` to `53.5R`. It is a different, higher-churn strategy rather than a clean quality improvement.

#### Champion multi

| Architecture | Trades | Net R | Avg net R | Win rate | Gross PF | Max net DD |
|---|---:|---:|---:|---:|---:|---:|
| MB50 | 500 | +325.8R | +0.652R | 30.0% | 2.38 | 27.7R |
| MB20 | 932 | +264.5R | +0.284R | 31.3% | 1.93 | 49.5R |
| MB30 | 741 | +279.6R | +0.377R | 29.0% | 2.02 | 66.1R |
| MB40 | 592 | +249.3R | +0.421R | 31.2% | 2.07 | 55.9R |

All MB alternatives reduced total R, average R/trade, PF, and drawdown performance for champion multi.

## OOS results

| Reference | MB50 baseline net | MB20 delta | MB30 delta | MB40 delta | Interpretation |
|---|---:|---:|---:|---:|---|
| Pure single | +8.3R | -8.5R | +20.9R | +17.2R | OOS improvement, IS failure |
| Pure multi | +44.3R | +14.7R | +22.6R | +36.5R | OOS improvement, IS failure |
| Literal single | +4.2R | -36.6R | -28.7R | -10.8R | All alternatives fail |
| Literal multi | +72.3R | +3.6R | -24.2R | -17.3R | MB20 only, no IS confirmation |
| Fullstack single | +16.9R | +11.7R | -17.7R | +3.5R | Configuration-specific |
| Champion multi | +70.2R | **+21.5R** | -41.3R | +9.9R | MB20 only, IS failure |
| UTC-Saturday multi | +60.2R | -12.6R | -2.3R | -40.2R | All alternatives fail |

## Interpretation

The architecture change is not a small entry filter. Changing 15m `minBars` changes:

- swing count;
- number of HTF/LTF opportunities;
- signal timing;
- trade count;
- concurrency interaction;
- trail-event path;
- runner distribution.

The best OOS cells are not reliable evidence because the same architecture generally loses on IS:

- pure multi: MB40 `+36.5R` OOS but `-59.5R` IS;
- champion multi: MB20 `+21.5R` OOS but `-61.3R` IS;
- pure single: MB30 `+20.9R` OOS but `-97.7R` IS.

The literal-multi MB30 result is the only notable both-period positive cell in this batch, but its average R/trade and drawdown deteriorate. It remains architecture-specific, not a universal replacement.

## Canonical files

- Harness: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\exp_thesis_mb_architecture.py`
- IS result: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_mb_architecture_results_is.json`
- OOS result: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\tests\_thesis_mb_architecture_results_oos.json`
- Checklist: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\docs\CHECKLIST.md`
- Experiment log: `C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff\docs\EXPERIMENT_LOG.md`

## Verdict

**Complete and negative as a universal architecture replacement.** MB50 remains the stable architecture. MB20/MB30/MB40 remain descriptive alternatives; no production change is authorized.
