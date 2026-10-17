# What max_consecutive_losses=0 buys, and what it costs

Turning the halt off does not alter the trades the book already had.
 It adds trades the cutoff had been suppressing. Those extra trades are
 the whole question - do they earn like the rest, or does the net rise
 for some other reason while they do not?

## 106 `fsent_champ_long_htffs`

| era | trades | net | R/trade | net % | max DD | DD % | streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| IS registered | 753 | +758.0 | +1.0066 | - | 22.45 | - | 13 |
| IS at 0 | 802 | +810.5 | +1.0106 | +6.9% | 24.42 | +8.8% | 14 |
| OOS registered | 389 | +313.4 | +0.8055 | - | 14.74 | - | 10 |
| OOS at 0 | 423 | +353.9 | +0.8366 | +12.9% | 12.82 | -13.0% | 11 |

### IS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 753 | +758.0 | +1.0066 | 39.7% | 3.04 |
| **NEW trades added by turning the halt off** | 73 | +34.9 | +0.4775 | 26.0% | 1.77 |
| trades removed by turning the halt off | 24 | -17.7 | -0.7357 | 8.3% | 0.23 |

The new trades earn materially worse than the book's own rate, so the net improvement is NOT coming from them.

### OOS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 389 | +313.4 | +0.8055 | 38.0% | 2.73 |
| **NEW trades added by turning the halt off** | 45 | +28.0 | +0.6226 | 31.1% | 2.03 |
| trades removed by turning the halt off | 11 | -12.5 | -1.1382 | 0.0% | 0.00 |

The new trades earn materially worse than the book's own rate, so the net improvement is NOT coming from them.

## 108 `fsent_champ_long_htfesmcl4`

| era | trades | net | R/trade | net % | max DD | DD % | streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| IS registered | 762 | +770.5 | +1.0112 | - | 20.02 | - | 17 |
| IS at 0 | 802 | +810.5 | +1.0106 | +5.2% | 24.42 | +22.0% | 14 |
| OOS registered | 425 | +339.1 | +0.7978 | - | 15.04 | - | 11 |
| OOS at 0 | 441 | +350.1 | +0.7939 | +3.3% | 12.82 | -14.8% | 11 |

### IS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 762 | +770.5 | +1.0112 | 39.0% | 3.04 |
| **NEW trades added by turning the halt off** | 49 | +29.2 | +0.5951 | 38.8% | 2.05 |
| trades removed by turning the halt off | 9 | -10.8 | -1.2019 | 0.0% | 0.00 |

The new trades earn materially worse than the book's own rate, so the net improvement is NOT coming from them.

### OOS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 425 | +339.1 | +0.7978 | 38.1% | 2.69 |
| **NEW trades added by turning the halt off** | 23 | +3.8 | +0.1649 | 34.8% | 1.35 |
| trades removed by turning the halt off | 7 | -7.2 | -1.0355 | 0.0% | 0.00 |

The new trades earn materially worse than the book's own rate, so the net improvement is NOT coming from them.

## 109 `fsent_champ_long_htf15_htffs`

| era | trades | net | R/trade | net % | max DD | DD % | streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| IS registered | 756 | +765.9 | +1.0130 | - | 29.76 | - | 13 |
| IS at 0 | 807 | +810.1 | +1.0039 | +5.8% | 22.35 | -24.9% | 14 |
| OOS registered | 396 | +346.1 | +0.8739 | - | 14.74 | - | 10 |
| OOS at 0 | 429 | +393.8 | +0.9178 | +13.8% | 12.82 | -13.0% | 11 |

### IS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 756 | +765.9 | +1.0130 | 39.8% | 3.02 |
| **NEW trades added by turning the halt off** | 72 | +28.2 | +0.3922 | 29.2% | 1.65 |
| trades removed by turning the halt off | 21 | -16.0 | -0.7632 | 9.5% | 0.25 |

The new trades earn materially worse than the book's own rate, so the net improvement is NOT coming from them.

### OOS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 396 | +346.1 | +0.8739 | 39.4% | 2.88 |
| **NEW trades added by turning the halt off** | 44 | +35.2 | +0.8011 | 34.1% | 2.41 |
| trades removed by turning the halt off | 11 | -12.4 | -1.1303 | 0.0% | 0.00 |

The new trades earn at close to the book's own rate, so the higher net is attributable to this change.

## 110 `fsent_champ_long_htf15_tskip6`

| era | trades | net | R/trade | net % | max DD | DD % | streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| IS registered | 412 | +639.8 | +1.5530 | - | 22.81 | - | 13 |
| IS at 0 | 435 | +634.0 | +1.4575 | -0.9% | 27.33 | +19.8% | 15 |
| OOS registered | 224 | +328.5 | +1.4667 | - | 14.90 | - | 11 |
| OOS at 0 | 241 | +383.9 | +1.5932 | +16.9% | 17.00 | +14.1% | 10 |

### IS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 412 | +639.8 | +1.5530 | 40.8% | 3.26 |
| **NEW trades added by turning the halt off** | 44 | -17.4 | -0.3957 | 18.2% | 0.60 |
| trades removed by turning the halt off | 21 | -11.6 | -0.5519 | 23.8% | 0.40 |

The new trades earn materially worse than the book's own rate, so the net improvement is NOT coming from them.

### OOS - the extra trades the cutoff had been suppressing

| group | n | net | R/trade | win rate | PF |
|---|---:|---:|---:|---:|---:|
| all trades as registered | 224 | +328.5 | +1.4667 | 36.6% | 3.09 |
| **NEW trades added by turning the halt off** | 30 | +40.8 | +1.3592 | 43.3% | 3.33 |
| trades removed by turning the halt off | 13 | -14.6 | -1.1258 | 0.0% | 0.00 |

The new trades earn at close to the book's own rate, so the higher net is attributable to this change.
