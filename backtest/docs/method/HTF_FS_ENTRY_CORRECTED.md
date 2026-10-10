# HTF-side FS entry — corrected, and extended to the chop classifier

**Run 2026-10-10. `exp_htf_fs_grid.py` → `_htf_fs_grid.json` · `exp_period_control_recheck.py`**
**Supersedes the period-control section of `HTF_FS_ENTRY_REJECTED.md` (2026-10-09).**

Two gaps closed, and in the course of closing them the original rejection was
found to rest on a broken test.

---

## 1. Two modes that did not exist

The owner asked twice whether the HTF side opens on FS, the way the LTF side
does. It had been tested — but the knob could not express what was being asked
for.

`exp_htf_fs_entry` had three values: `""`, `"flip"`, `"all"`. Reading the code:

```python
_hfs_on = _hfs in ("flip", "all")
_fb_flip = ("fs_both" if _hfs_on and _hfs == "all" else "flip")
```

`"flip"` set `_hfs_on` true and then tested `_hfs == "all"`, which was false — so
all three buckets fell through to their shipped values. **The mode named for the
bucket it moves moved nothing.** It "measured identical to off" because it *was*
off. Replaced with a direct table:

| mode | flip | decisive | b2 |
|---|---|---|---|
| `""` | break | break | break |
| `"flip"` | **FS** | break | break |
| `"dec"` | break | **FS** | break |
| `"b2"` | break | break | **FS** |
| `"all"` | FS | FS | FS |

`dec` is the exact analogue of what the LTF side does with
`exp_fs_entry_side` — one bucket on FS, the rest on break.

---

## 2. Every registered fsent book is `mode="atr_high"`

There is no `mode="chop"` book anywhere in the registry. So the 2026-10-09
rejection only ever spoke to the ATR classifier, and the classifier is not an
inert bystander — its whole job is deciding which bucket a bar belongs to.

**`fsent_champ_long_mode_chop`: IS 528 / +533.37 / DD 13.42 — identical n, net and
drawdown to the shipping book.** Out of sample it moves to 294 / +244.45.

The paired permutation returns **p = 1.0000 in sample** — not a small effect, no
effect at all, because the in-sample trade list is byte-identical to the parent's
and the test is literally the parent against itself.

**So the regime classifier is not a live axis on this book.** Nothing in this
family should be attributed to it.

---

## 3. The 2026-10-09 period control was reading the wrong number

That doc rejected `all` partly on "htf_fs better in 2 of 6 years… the gain does
not survive a half-year fixed effect."

`exp_period_control_recheck.py` reproduces that figure **exactly** — and then
shows why.

The expression was:

```python
ea = sum(arms["off"]["per_h"][c][0] for c in hs) / len(hs)
```

`per_h[c]` is the list of per-trade R values in that half-year. `[0]` is **the
first trade of the half-year.** The line below it, for the negative-cell check,
correctly used `sum(per_h[c])`. So the year comparison averaged one trade per
half-year while everything around it averaged the whole half-year.

| year | off `ea[0]` | all `eb[0]` | old verdict | off sum | all sum | correct verdict |
|---|---:|---:|---|---:|---:|---|
| 2021 | +0.7 | +1.0 | yes | +39.2 | +62.0 | yes |
| 2022 | −0.7 | −0.8 | **no** | +80.6 | +89.0 | **yes** |
| 2023 | −0.4 | −1.2 | **no** | +86.2 | +162.2 | **yes** |
| 2024 | −0.9 | −1.1 | **no** | +57.1 | +145.8 | **yes** |
| 2025 | +0.8 | −0.4 | no | +68.8 | +64.5 | no |
| 2026 | +1.9 | +4.4 | yes | +54.6 | +76.4 | yes |

**first-trade-only: 2 of 6 · half-year net: 5 of 6**

Six single trades decided a family-wide rejection.

**The gain is broad.** Half-year fixed effect **b = +1.39, t = +3.42**; year
fixed effect **b = +1.34, t = +3.26**.

---

## 4. Results, 4 books × 5 modes

Baselines:

| book | regime | n | net | dd IS | dd OOS | neg |
|---|---|---:|---:|---:|---:|---:|
| `champ_long` | atr_high | 839 | +773.0 | 13.42 | 11.88 | 1 |
| `htf15` | atr_high | 800 | +822.5 | 17.28 | 16.86 | 0 |
| `sig_multi` | atr_high | 523 | +704.4 | 13.39 | 7.64 | 0 |
| `chop_sw10` | **chop** | 822 | +777.8 | 13.42 | 11.88 | 1 |

Arms:

| book | mode | Δn | Δnet | dd IS | neg | yr | t_year | t_half |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `champ_long` | dec | +7 | +2.9 | 13.42 | 1 | 2/6 | 2.23 | 2.09 |
| `champ_long` | **flip** | **+346** | **+425.4** | 19.78 | 1 | 5/6 | 3.24 | **3.40** |
| `champ_long` | b2 | +0 | +0.0 | 13.42 | 1 | 0/6 | 0.00 | 0.00 |
| `champ_long` | all | +352 | +427.0 | 19.78 | 1 | 5/6 | 3.26 | 3.42 |
| `htf15` | dec | +6 | −7.6 | 17.28 | 0 | 0/6 | −2.05 | −1.95 |
| `htf15` | **flip** | +354 | +407.5 | **29.62** | **1** | 5/6 | 2.80 | 3.29 |
| `htf15` | b2 | +0 | +0.0 | 17.28 | 0 | 0/6 | 0.00 | 0.00 |
| `htf15` | all | +361 | +399.8 | 29.62 | 1 | 5/6 | 2.73 | 3.22 |
| `sig_multi` | dec | +26 | +35.7 | 14.19 | 0 | 4/6 | 2.45 | 2.00 |
| `sig_multi` | **flip** | +131 | +196.4 | 17.82 | **1** | 3/6 | 1.60 | 1.81 |
| `sig_multi` | b2 | +0 | +0.0 | 13.39 | 0 | 0/6 | 0.00 | 0.00 |
| `sig_multi` | all | +163 | +243.9 | 17.69 | 1 | 3/6 | 2.04 | 2.29 |
| `chop_sw10` | dec | −1 | +1.0 | 13.42 | 1 | 1/6 | 1.41 | 1.41 |
| `chop_sw10` | **flip** | +370 | +421.1 | 19.78 | 1 | 5/6 | 3.19 | **3.46** |
| `chop_sw10` | b2 | +0 | +0.0 | 13.42 | 1 | 0/6 | 0.00 | 0.00 |
| `chop_sw10` | all | +369 | +422.1 | 19.78 | 1 | 5/6 | 3.21 | 3.47 |

**`b2` is exactly inert on all four books** — these books do not read the b2
bucket. **`dec` is nearly inert** (−1 to +26 trades). All the action is in
**`flip`**, and `flip ≈ all` precisely because the other two buckets are empty.

---

## 5. Registered, including the losers

The owner's standing instruction for this family: register everything, even the
arms that lose, because the net is what they are judging.

| book | IS | OOS | verdict |
|---|---|---|---|
| `fsent_champ_long_htffs` | 770 / **+897.94** / 19.78 | 415 / +300.43 / 14.35 | **in-budget, no new negative cell** |
| `fsent_champ_long_htf15_htffs` | 761 / **+925.79** / **29.62** | 393 / +304.17 / 14.35 | **over the 29R ceiling** |
| `fsent_sig_multi_htffs` | 434 / +666.32 / 17.82 | 220 / +234.48 / 7.99 | best OOS risk, worst evidence |
| `fsent_champ_long_mode_chop` | 528 / +533.37 / 13.42 | 294 / +244.45 / 11.88 | inert |

**Paired permutation vs the shipping book:**

| book | p IS | p OOS | gap IS | gap OOS |
|---|---:|---:|---:|---:|
| `htf15_htffs` | **0.0105** | 0.4904 | +392.43 | +64.58 |
| `htffs` | 0.0272 | 0.5956 | +364.57 | +60.84 |
| `sig_multi_htffs` | 0.5091 | 0.9708 | +132.95 | **−5.11** |
| `mode_chop` | 1.0000 | 0.7603 | +0.00 | +4.86 |

**No new book clears in both eras.** `htf15_htffs` at p = 0.0105 is the single
strongest in-sample figure in the family — paired with 0.4904 out of sample.
`fsent_champ_long_mcloff` remains the only book significant in both (0.0312 /
0.0117).

`sig_multi_htffs` is worth stating plainly: it has the best out-of-sample
drawdown (7.99R) and win rate (46.8%) anywhere in the family, and it is the arm
whose edge is least distinguishable from its parent's, with a *negative*
out-of-sample gap. **Good risk profile is not evidence of edge.**

---

## 6. What survives and what does not

**`fsent_champ_long_htffs` is the strongest arm in this family on the owner's own
rule**: +364.57R in sample and +60.84R out, drawdown 19.78R inside the 29R
budget, and it does **not** bring back the negative half-year that sank `all`.
Causality is clean — windows open exactly at their own FS print, 0.0h at min,
median and max.

It is still not adopted, because p = 0.5956 out of sample. That is the same shape
as `htfesmcl4` and `htf15_htffs`, and it is the entire reason the forward window
exists: the return is real and broad in the historical data and indistinguishable
from a reshuffle of the parent on the era that was not used to find it.

## Reproduce

```
python backtest/tests/exp_htf_fs_grid.py            # the 4x5 grid
python backtest/tests/exp_period_control_recheck.py # first-trade vs half-year net
python backtest/tests/exp_null_audit.py             # paired permutation
python backtest/tests/exp_register_htffs.py         # pins for the four books
```