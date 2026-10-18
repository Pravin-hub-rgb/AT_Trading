# Is ext_stop_r removing winners or losers?

## Why this run exists

The `htf_rr` decomposition found that raising the target from 3.0 to 4.0
loses more on the LTF entry set than it gains on the HTF booking. On 106 IS:
751 entries become 726 and book net moves −48.1R. That arithmetic says the
25 disappearing entries were worth **+48.1R, about +1.9R each**.

So on IS the gate is not blocking bad trades. It is blocking good ones. On
OOS the sign flips and it appears to be blocking bad ones. That relocates
the question: the knob whose value changes is not `htf_rr`, it is
`ext_stop_r`.

```python
# unified.py:1214-1216
ext = (close - window_open) * dir / htf_risk
if ext > ext_stop_r: continue
```

## The measurement, and why it is normalised differently

`ext` is in units of the HTF trade's risk, which depends on where the swing
started — not comparable across eras, and 2021-22 is 3.5x more volatile than
2023-26. So the diagnostic measures chase in ATR units instead:

```
chase = (entry_price - window_open_price) * dir / ATR_at_entry
```

Numerator and denominator both scale with volatility, so this is era-invariant
by construction. Same fix the earlier volatility bucketing needed, where a
raw ATR level was comparing two different populations.

## Result — net R per trade by how late the entry was

### 107 IS — 382 entries, 1 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 27 | +0.9 | +0.033 |
| 0.5-1 | 21 | +13.4 | +0.636 |
| 1-2 | 33 | +13.6 | +0.411 |
| 2-3 | 38 | +77.8 | +2.047 |
| 3-4.5 | 50 | +58.2 | +1.165 |
| 4.5-6 | 34 | +38.8 | +1.141 |
| >6 | 179 | +277.2 | +1.549 |

### 107 OOS — 194 entries, 36 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 12 | +13.4 | +1.120 |
| 0.5-1 | 7 | +8.2 | +1.171 |
| 1-2 | 17 | +31.5 | +1.850 |
| 2-3 | 11 | +40.0 | +3.640 |
| 3-4.5 | 17 | +1.0 | +0.061 |
| 4.5-6 | 15 | +9.1 | +0.609 |
| >6 | 115 | +141.8 | +1.233 |

### 110 IS — 292 entries, 1 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 18 | +2.0 | +0.110 |
| 0.5-1 | 21 | +12.0 | +0.571 |
| 1-2 | 28 | +10.5 | +0.376 |
| 2-3 | 32 | +106.7 | +3.333 |
| 3-4.5 | 43 | +55.3 | +1.286 |
| 4.5-6 | 23 | +89.9 | +3.908 |
| >6 | 127 | +257.2 | +2.025 |

### 110 OOS — 144 entries, 26 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 7 | +14.6 | +2.082 |
| 0.5-1 | 3 | +9.7 | +3.232 |
| 1-2 | 16 | +23.9 | +1.491 |
| 2-3 | 7 | +52.1 | +7.440 |
| 3-4.5 | 11 | -2.2 | -0.199 |
| 4.5-6 | 11 | +22.7 | +2.066 |
| >6 | 89 | +210.5 | +2.365 |

### 109 IS — 561 entries, 0 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 18 | +70.4 | +3.911 |
| 0.5-1 | 18 | +0.3 | +0.015 |
| 1-2 | 37 | +17.5 | +0.474 |
| 2-3 | 24 | +45.5 | +1.895 |
| 3-4.5 | 54 | +29.4 | +0.544 |
| 4.5-6 | 38 | +23.2 | +0.611 |
| >6 | 372 | +390.8 | +1.050 |

### 109 OOS — 290 entries, 4 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 12 | +6.5 | +0.544 |
| 0.5-1 | 6 | -0.6 | -0.105 |
| 1-2 | 18 | -2.9 | -0.163 |
| 2-3 | 18 | +20.3 | +1.130 |
| 3-4.5 | 30 | +7.7 | +0.257 |
| 4.5-6 | 20 | +12.4 | +0.620 |
| >6 | 186 | +169.2 | +0.910 |

### 106 IS — 553 entries, 0 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 21 | +69.7 | +3.321 |
| 0.5-1 | 18 | +0.9 | +0.052 |
| 1-2 | 33 | +24.1 | +0.731 |
| 2-3 | 23 | +36.1 | +1.569 |
| 3-4.5 | 54 | +32.3 | +0.598 |
| 4.5-6 | 37 | +30.4 | +0.822 |
| >6 | 367 | +376.2 | +1.025 |

### 106 OOS — 285 entries, 4 unassigned to any window

| chase (ATR units) | trades | net R | R per trade |
|---|---:|---:|---:|
| <0.5 | 11 | +9.4 | +0.858 |
| 0.5-1 | 6 | -0.6 | -0.105 |
| 1-2 | 19 | -6.1 | -0.319 |
| 2-3 | 21 | +18.9 | +0.901 |
| 3-4.5 | 29 | +3.4 | +0.116 |
| 4.5-6 | 19 | +9.9 | +0.519 |
| >6 | 180 | +149.8 | +0.832 |

---

## How to read it

**Declining R per trade with rising chase** means the gate has a real job
and the question is only where to put it. **Flat or rising** means the gate
has no job and any threshold is arbitrary — in which case loosening it on
IS, where it removes winners, is the obvious direction and `htf_rr` should
not be made conditional at all.

Either way this does not adopt a threshold. A level chosen from this curve
on IS alone is 110's `skip_n=16`, and the objection from the external review
applies unchanged. The value here is establishing whether the gate is
load-bearing at all, which nothing so far has done.
