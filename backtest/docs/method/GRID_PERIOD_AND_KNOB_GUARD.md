# Grid period control + the inert-knob guard

Date: 2026-10-09. Harness: `exp_grid_period.py`.
Closes items 1 and 4 of `RESEARCH_COMPLETE.md`.

---

# PART 1 — period control on the grid arms

A grid arm is chosen **by search**, so it owes the same instrument as everything
else before it can be called a candidate. The two factors had each been tested
separately; the combination had not.

P87 instrument, half-year fixed effects, cluster-robust SE, 4000-draw bootstrap,
MDE printed with every result.

| arm | IS b (t) | OOS b (t) | verdict |
|---|---|---|---|
| **`mcloff` alone** | **+1.21 (3.37)** | **+1.86 (3.97)** | **SURVIVES + POWERED** |
| `mcloff_htf15` | +0.77 (1.72) | +0.62 (1.60) | survives, **underpowered** |
| `mcl4_htf15` | +0.49 (1.01) | +0.60 (1.27) | survives, underpowered |
| `cap21` | +2.63 (0.86) | +0.94 (1.16) | survives, underpowered |
| `bias_flip` | +0.25 (0.31) | +0.69 (0.90) | survives, underpowered |
| `partial_r15` | **−3.78** (−1.32) | +0.24 (0.26) | **does NOT survive** |
| `mcloff_htf15` vs `mcloff` | — | — | identical set — the swing contributes nothing once `mcl` is fixed |

## the finding: the extra swing buys return and spends power

`mcloff_htf15` beats `mcloff` by **+49.59R in sample** and both clear every
half-year. But `mcloff` alone is the **only arm in the family whose control is
powered in both eras**, at t = 3.37 and t = 3.97. Stacking the htf15 swing on top
**dilutes the cohort variance** and drops it to t = 1.72 / 1.60.

**So there are two different recommendations and they are not the same book:**

- **on evidence** → `fsent_champ_long_mcloff`, powered in both eras
- **on return** → `fsent_champ_long_mcloff_htf15`, +49.59R more, not powered

Both are registered with both facts written down. **The default should be
`mcloff`**, because a book whose advantage clears the MDE is worth more than one
whose advantage does not, and the extra 49R is a point estimate on 859 trades.

## `bias_flip` is the most balanced gain, and it contradicts a September decision

`window_end="bias_flip"`: **+191.77R IS and +190.21R OOS** — almost identical
gains in both eras, which is rarer than anything else in this family — and it
survives the control in 2 of 2.

The engine's own comment at the `window_end` definition records it as **NOT
adopted**, tested 2026-09-08, rejected because it added a cohort with t = 1.21
and 2023 was flat in R at 85% more churn. Those are not contradictory — "not
significant" and "consistent across eras" can both be true — but **the tension is
now on the record rather than settled**, and the September rejection was made
without a period control in the P87 form.

`partial_r15` fails outright: b = −3.78 in sample. Its +473R at the family-lowest
10.35R drawdown is bought by scaling **out** of trades, and the survivors'
contribution goes sharply negative.

---

# PART 2 — the inert-knob guard

Three knobs in a shipped champ book's params **cannot change a single trade**.
They read like live risk controls. They are not.

| knob | in a shipped book? | verdict |
|---|---|---|
| **`chop_thresh`** | yes | **INERT** — no trade changes at 40 or 90 |
| **`atr_low_thresh`** | yes | **INERT** — only read in `atr_low` mode, which is not this book |
| **`exp_ltf_no_entry`** | no | **INERT** — identical at 0 and 1 |
| `cooldown_bars` | yes | live |
| `max_consecutive_losses` | yes | live |
| `ext_stop_r` | yes | live |
| `exp_persist` | yes | live |
| `sl_buf_atr` | yes | live |
| `exp_partial_r` | yes | live |
| `pivot_rule` | yes | live |
| `exp_cap_days` | no | live |
| `exp_causal_sl` | no | live (**and setting it to 1 gives ddIS 205.83**) |
| `exp_htf_fs_entry` | no | live |
| `exp_min_sl_pct` | no | live |
| `exp_no_opposite` | no | live |
| `exp_skip_utc_sat` / `_sun` | no | live |
| `window_end` | no | live |

**3 inert, 15 live.**

## why this matters beyond tidiness

`chop_thresh: 58.0` sits in the shipping book's params. Anyone reading that
config — a future maintainer, an auditor, a model — has every reason to believe a
chop filter is running at 58. **It is not running at all.** That is the failure
mode this guard exists to prevent, and it is why the guard is a harness rather
than a note: a note can be forgotten, a harness fails.

**Nothing was deleted.** Removing keys from a shipped book's params changes its
serialised identity and every pin derived from it, for no behavioural gain. The
guard makes the claim checkable instead.

## and one dangerous knob with no guard on it

`exp_causal_sl=1` is live and **produces ddIS 205.83** on the shipping book —
a 16× drawdown increase from one boolean. It is default-off and nothing in the
config path warns about it.

---

# What is now closed, and what is not

| item | state |
|---|---|
| period control on the grid arms | **done** — all six, MDE printed |
| dead knobs | **done** — three inert, guard written |
| which book to recommend | **two answers, on two axes** — `mcloff` on evidence, `mcloff_htf15` on return |
| `window_end=bias_flip` vs the September rejection | **on the record, unresolved** |
| `exp_causal_sl=1` warning | **not added** — a warning is a product decision, not a research one |
| forward evidence | **still none for any arm** |

---

*Shipping book unchanged: 528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS,
one negative half-year, `max_consecutive_losses=3` untouched.*