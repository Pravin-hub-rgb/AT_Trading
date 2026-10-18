# The admission gate as a percentile rather than a fixed 3.0R

## Why this knob and not `htf_rr`

The `htf_rr` decomposition split the change in book net into an entry-set
term worth 2-3x the HTF term, and eight state-variable signals were tested
against the smaller one. All eight flipped between eras. The larger half
runs through the admission gate:

```python
# unified.py:1212-1216
ext = (close - window_open) * dir / htf_risk
if ext > ext_stop_r: continue
```

`ext` is in units of the window's own risk, which depends on where the swing
started. So a fixed 3.0R is a different effective strictness in each
regime - and 2021-22 measured 3.5x more volatile than 2023-26.

The gate itself is earning its place. The gate diagnostic found trades
nearest it are the weakest on every book and both eras (+0.12R to +0.60R
per trade against +0.85R to +3.32R for fresh entries). The open question is
its level, not its existence.

## Percentile sweep — net R

### IS

| book | base 3.0R | pct=0.0 | pct=0.5 | pct=0.7 | pct=0.85 | pct=0.92 | pct=0.96 | pct=0.99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 107 | +538 | +538 | +182 | +387 | +469 | +512 | +532 | +539 |
| 110 | +644 | +644 | +249 | +374 | +566 | +625 | +643 | +651 |
| 106 | +757 | +757 | +435 | +608 | +711 | +710 | +742 | +753 |
| 109 | +765 | +765 | +471 | +578 | +713 | +723 | +753 | +760 |
| 108 | +772 | +772 | +447 | +625 | +708 | +721 | +755 | +768 |
| sigm_htffs | +506 | +506 | +334 | +447 | +485 | +491 | +494 | +506 |
| sigm | +366 | +366 | +223 | +332 | +373 | +363 | +353 | +368 |
| htf15 | +503 | +503 | +161 | +357 | +448 | +480 | +498 | +503 |

### OOS

| book | base 3.0R | pct=0.0 | pct=0.5 | pct=0.7 | pct=0.85 | pct=0.92 | pct=0.96 | pct=0.99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 107 | +273 | +273 | +118 | +192 | +245 | +257 | +274 | +273 |
| 110 | +336 | +336 | +125 | +243 | +345 | +319 | +339 | +339 |
| 106 | +313 | +313 | +179 | +250 | +264 | +311 | +298 | +313 |
| 109 | +346 | +346 | +209 | +243 | +346 | +360 | +356 | +352 |
| 108 | +339 | +339 | +150 | +233 | +262 | +319 | +328 | +344 |
| sigm_htffs | +202 | +202 | +89 | +88 | +170 | +191 | +196 | +203 |
| sigm | +185 | +185 | +83 | +143 | +157 | +189 | +198 | +182 |
| htf15 | +257 | +257 | +99 | +192 | +248 | +260 | +263 | +259 |

### Fixed-level sweep — the same knob the other way, for reference

**IS**

| book | 1.5 | 2.5 | 3.0 | 4.0 | 6.0 | off |
|---|---:|---:|---:|---:|---:|---:|
| 107 | +483 | +540 | - | - | - | +538 |
| 110 | +571 | +649 | - | - | - | +644 |
| 106 | +680 | +754 | - | - | - | +757 |
| 109 | +684 | +762 | - | - | - | +765 |
| 108 | +686 | +769 | - | - | - | +772 |
| sigm_htffs | +516 | +506 | - | - | - | +506 |
| sigm | +368 | +367 | - | - | - | +366 |
| htf15 | +465 | +505 | - | - | - | +503 |

**OOS**

| book | 1.5 | 2.5 | 3.0 | 4.0 | 6.0 | off |
|---|---:|---:|---:|---:|---:|---:|
| 107 | +219 | +274 | - | - | - | +273 |
| 110 | +305 | +336 | - | - | - | +336 |
| 106 | +263 | +313 | - | - | - | +313 |
| 109 | +344 | +352 | - | - | - | +346 |
| 108 | +264 | +346 | - | - | - | +339 |
| sigm_htffs | +179 | +200 | - | - | - | +202 |
| sigm | +167 | +185 | - | - | - | +185 |
| htf15 | +223 | +260 | - | - | - | +257 |

---

## The bar

A setting counts only if it beats the registered gate in **both eras**
on aggregate. One era agreeing is what `exp_trail_skip_n=16` did and what
the whole `htf_rr` sweep did.

| setting | sum IS | sum OOS | beats 3.0R in both? |
|---|---:|---:|---|
| registered 3.0R | +4851 | +2251 | - |
| pct=0.5 | +2502 | +1051 | no |
| pct=0.7 | +3708 | +1583 | no |
| pct=0.85 | +4474 | +2036 | no |
| pct=0.92 | +4625 | +2206 | no |
| pct=0.96 | +4771 | +2251 | no |
| pct=0.99 | +4847 | +2265 | no |

Nothing here is adopted. A percentile level chosen from this table on
IS alone would be the same mistake in a new place. What this tells us is
whether a regime-invariant gate is even worth having, which is a question
about the mechanism rather than about the best number.
