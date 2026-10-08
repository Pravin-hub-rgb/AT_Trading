"""RETIRED books — removed from EXPERIMENTS on 2026-10-08, definitions untouched.

THE OWNER'S RULE, IN TWO BARS
=============================
    "any book jisme IS ya OOS negative hai usko hata"
    "OOS 50R se low hai to hata"

Applied literally, no exceptions:

    BAR 1   IS < 0  OR  OOS < 0                 -> 32 books
    BAR 2   0 <= OOS < 50                       -> 52 books
    ALIAS   one alias pointing at a retired bar-1 book -> 1 key

85 keys out, 236 entries down to 151.

WHY A LIST AND NOT DELETIONS
============================
Book configs live in six family modules and deleting them in place would touch
all six for no benefit. This module holds KEYS and `registry/__init__.py`
subtracts them from the merged dict after the merge. Two consequences worth
stating:

  * The definitions never move, so a retired book is still fully runnable. See
    `archived()` below — nothing had to be copied, so nothing can drift.
  * The registry's public surface is unchanged. `book()`, `shortlisted()`,
    `alias_of()` and every harness keep working; retired keys simply stop
    resolving, which is the same observable behaviour as deletion.

THE ARCHIVE IS THE OWNER'S POINT, SO IT IS A READER, NOT A COPY
===============================================================
"ye book se hat rahi hai, archive mai hongi he — jaise kabhi experiment karna ho
toh waha kaam aaye, harness ka code wagera"

`archived()` returns the FULL config and pins for every retired book, read live
from the family modules at call time. That is better than a snapshot for this
purpose in three ways: there is one source of truth, so it cannot go stale; a
retired book's harness code is still runnable by passing the returned config; and
restoring is one line. `exp_archive_list.py` dumps it to markdown and JSON.

THE SPLIT INSIDE BAR 1, because it is not what it looks like
============================================================
"Is negative OR OOS negative" as one undifferentiated rule throws away two
different findings.

  ERA_FITTED (28) - IS positive, OOS negative.
      IS average R per trade 0.089 to 0.711; OOS average R per trade negative on
      every one. OOS trade counts 91 to 301, so not a small-sample artifact.

  BOTH_NEGATIVE (1) - `skipwinhalt_sig_sw10`, IS -1.50R over 280 trades, OOS
      -4.24R over 162. Nothing worth keeping.

  INVERSE (3) - IS negative, OOS strongly POSITIVE:

          book                  IS avgR   OOS avgR   OOS net   OOS dd
          gap_campaign_max2     -0.0566    +0.4927    +74.89    13.59
          gap_campaign_markneg  -0.0602    +0.4979    +76.67    13.59
          gap_entry_cap2        -0.0602    +0.4979    +76.67    13.59

      Out of sample these are among the healthiest books in the registry by
      drawdown. They were shown these numbers in plain text and the owner
      answered that a book negative in either era comes out, which is a decision
      to hold — a book with a -16R in-sample expectancy has not earned trust
      because one window suited it. But the reason they leave is the RULE, not a
      measurement, and that is recorded so the judgement can be revisited rather
      than rediscovered. `archived()` still returns them, pins intact.
"""
from . import trail as _trail, sweep as _sweep, signal as _signal, \
    risk as _risk, d3 as _d3, kingsweep as _kingsweep

# ---- BAR 1: IS < 0 or OOS < 0 (32 books) -----------------------------------
ERA_FITTED = {
    "cap24d", "rmax15_multi_sw10", "opt_ml_cd0_mb10", "baseline_no_partial_sw20",
    "champion_multi_sw20", "fliponly_multi_sw10",
    "wage12_swingpause_sig_nowknd_sw10", "chopband_swingpause_sig_sw10",
    "rmax10_swingpause_sig_sw10", "atrr_swingpause_sig_sw10",
    "atrr_cd0_swingpause_sig_sw10", "fliponly_swingpause_sig_sw10",
    "utc_wknd_swingpause_sig_sw10", "wage12_swingpause_sig_sw20",
    "age50_swingpause_sig_sw10", "rmax15_swingpause_sig_sw10",
    "chopband_atrr_swingpause_sig_sw10", "swingpause_sig_sw20",
    "atrr_swingpause_sig_sw20", "swingpause_sig_sw10",
    "chopband_atrr_swingpause_sig_sw20", "b2doji_swingpause_sig_sw10",
    "champion_sig_sw20", "bm05_swingpause_sig_sw10", "champion_sig_sw10",
    "decayH_u", "decayG_c", "decayH_c",
}
BOTH_NEGATIVE = {"skipwinhalt_sig_sw10"}
INVERSE = {"gap_campaign_max2", "gap_campaign_markneg", "gap_entry_cap2"}

# ---- BAR 2: 0 <= OOS < 50R (52 books) ---------------------------------------
LOW_OOS = {
    "chopband_swingpause_sig_sw20", "fsswing_sig_sw20", "gap_pivot_trail",
    "lb30_persist5", "partial1_multi_sw10", "causalsl_swingpause_sig_sw10",
    "partial3_multi_sw10", "gap_profit_stage5", "decayG_u", "lb30_halt6_cd0",
    "fsswing_sig_sw10", "partial2_multi_sw10", "wage12_swingpause_sig_sw10",
    "gap_b3k4", "a4_w24_ext1.5", "opt_cd10_w24", "legskip2_multi_sw10",
    "utcsat_swingpause_sig_sw10", "lb30_w24_ext1.5", "opt_ml_cd10_mb10",
    "gap_b3k10", "gap_b3k8", "gap_b3k6", "bm05_multi_sw20",
    "lb30_chop55_persist2", "htfrr2_multi_sw10", "gap_b3k2",
    "wage24_swingpause_sig_sw10", "partial4_multi_sw10",
    "fullstack_wage10_cd0_sig_sw10", "nowknd_multi_sw10", "a4_w24_ext3.0",
    "fullstack_atrr_utcsat_multi_sw10", "wage8_swingpause_sig_sw10",
    "curfew624_swingpause_sig_sw10", "wage16_swingpause_sig_sw10",
    "trail_skipn4", "persist8_multi_sw10", "fullstack_swingpause_sig_sw10",
    "lb30_w24_ext2.0", "htfrr35_multi_sw10", "nowknd_swingpause_sig_sw10",
    "wage10_swingpause_wskip_sig_sw10", "lb30_w24_ext3.0",
    "partial5_multi_sw10", "nowknd_sig_sw10", "lb30_halt0",
    "lb30_w24_ext2.5", "decayD_c", "wage20_swingpause_sig_sw10",
    "gap_curfew_16_20", "cap8d",
}

# ---- ALIAS pointing at a bar-1 target (1 key) ------------------------------
# `swingpause_cd0_single_sw10` is a str-valued row aliasing `swingpause_sig_sw10`.
# registry/helpers raises KeyError when an alias targets a missing book, so
# retiring the target alone turns this into a KeyError the moment anything
# iterates the registry — the prune would break the registry instead of shrinking
# it. That is not hypothetical: the first version of this change did exactly that
# and the test caught it.
DANGLING_ALIAS = {"swingpause_cd0_single_sw10"}

RETIRED = ERA_FITTED | BOTH_NEGATIVE | INVERSE | LOW_OOS | DANGLING_ALIAS

assert len(ERA_FITTED) == 28, f"bar-1 era-fitted drifted: {len(ERA_FITTED)}"
assert len(BOTH_NEGATIVE) == 1, f"bar-1 both-negative drifted: {len(BOTH_NEGATIVE)}"
assert len(INVERSE) == 3, f"bar-1 inverse drifted: {len(INVERSE)}"
assert len(LOW_OOS) == 52, f"bar-2 drifted: {len(LOW_OOS)}"
assert len(DANGLING_ALIAS) == 1, f"alias count drifted: {len(DANGLING_ALIAS)}"
assert len(RETIRED) == 85, f"retired total drifted: {len(RETIRED)}"

# The registry's only two alias rows, asserted so this file cannot be edited into
# a state that breaks alias resolution. The failure mode otherwise is a KeyError
# at import time somewhere unrelated, which is expensive to trace back to a prune.
_ALIAS_TARGETS = {"swingpause_cd0_single_sw10": "swingpause_sig_sw10"}
for _a, _t in _ALIAS_TARGETS.items():
    if _t in RETIRED and _a not in RETIRED:
        raise AssertionError(
            f"alias {_a!r} targets retired book {_t!r} but the alias itself is not "
            "retired. Retiring a target without its aliases raises KeyError from "
            "registry.helpers when anything iterates EXPERIMENTS.")


def _merged():
    """Every book as the family modules define it, before RETIRED is applied."""
    m = {}
    for mod in (_trail, _sweep, _signal, _risk, _d3, _kingsweep):
        m.update(mod.BOOKS)
    return m


def archived():
    """Full config plus pins for every retired book, read live from the modules.

    This is the archive. Nothing was copied out of the family modules when a book
    was retired, so this cannot drift from them — it is the same dict object. A
    retired book stays runnable: take its config out of here and hand it to the
    harness, or restore the key in RETIRED and use the registry as normal.
    """
    m = _merged()
    return {k: m[k] for k in sorted(RETIRED) if k in m}


def bar_of(key):
    """Which rule retired this key. So a reader can tell an era-fitted book from
    a merely-quiet one without consulting the diff."""
    if key in ERA_FITTED:
        return "bar1_era_fitted"
    if key in BOTH_NEGATIVE:
        return "bar1_both_negative"
    if key in INVERSE:
        return "bar1_inverse_IS_neg_OOS_pos"
    if key in LOW_OOS:
        return "bar2_oos_under_50"
    if key in DANGLING_ALIAS:
        return "alias_of_retired"
    return None