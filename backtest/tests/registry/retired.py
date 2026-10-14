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

# ---- RE-RETIRED 2026-10-14, on the corrected chain -------------------------
# The bar-1 set above was measured on the chain that existed on 2026-10-08. The
# engine has since moved: B1 arming (77711a6), V13 (88ecd00), the volatile-B1
# colour rule and the same-bar duplicate-pivot fix (5d6cab2, d71304f). The chain
# went from 2753 swings / 7505 marks to 2840 / 7734, and every pin was re-measured
# (dd02cf1, 120 books, both eras).
#
# So bar 1 was re-applied to the NEW numbers rather than trusted. 69 books are
# negative in at least one era on the corrected chain and all 69 are still active
# in the registry - the 2026-10-08 retirement had not caught them because they
# were positive then. Applying the owner's rule literally, no exceptions:
#
#     IS < 0  OR  OOS < 0   ->  retire
#
#     OWNER 2026-10-14: "any of on IS or OOS is negative retire that 's it..
#                            no more discussion"
#
# 6 of the 69 are negative in BOTH eras and 63 are era-fitted (IS positive, OOS
# negative), which is the overfit shape this repo has already seen repeatedly.
# Three of them lose by less than 0.25R - gap_wage28 -0.14, gap_campaign3 -0.18,
# gap_entry_cap3 -0.22. They are retired anyway: the rule is the rule and an
# exception would become a loop of "is this one an exception".
#
# This set is kept separate from ERA_FITTED rather than merged into it, because
# ERA_FITTED's own assert counts 28 members measured on the old chain. Merging
# would make that assert lie. The two are unioned into RETIRED below.
RE_RETIRED_ANY_ERA_NEGATIVE = {
    "age50_utcsat_multi_sw10", "b2doji_utcsat_multi_sw10",
    "baseline_no_partial_sw10", "bm05_multi_sw10", "bm05_utcsat_multi_sw10",
    "cap12d", "cap16d", "cap20d", "cap32d", "cap48d", "causalsl_multi_sw10",
    "causalsl_utcsat_multi_sw10", "champion_multi_sw10",
    "champion_multi_sw10_entry1", "champion_multi_sw10_entry_both",
    "champion_multi_sw10_leg", "champion_multi_sw10_leg_no_entry",
    "chopband_multi_sw10", "combined_b2age_utcsat_multi_sw10",
    "curfew624_utcsat_multi_sw10", "decayA_c", "decayA_u", "decayB_c",
    "decayB_u", "decayC_c", "decayC_u", "decayE_c", "decayE_u",
    "ext25_utcsat_multi_sw10", "ext2_utcsat_multi_sw10",
    "ext35_utcsat_multi_sw10", "ext4_utcsat_multi_sw10", "fsexit4_c",
    "fsexit6_c", "fsswing6_c", "gap_campaign3", "gap_campaign4", "gap_cd15",
    "gap_cd5", "gap_cooldown4", "gap_curfew_a4_b8", "gap_entry_cap3",
    "gap_mcl5", "gap_persist1", "gap_r_cap1", "gap_r_cap3", "gap_skip_decisive",
    "gap_slbuf010", "gap_trail_prevbar", "gap_wage24", "gap_wage28",
    "gap_window_r_cap2", "htfrr25_multi_sw10", "htfrr4_multi_sw10",
    "persist3_multi_sw10", "persist4_multi_sw10", "persist5_multi_sw10",
    "persist6_multi_sw10", "skipwinhalt_multi_sw10", "trail_delay1",
    "trail_half", "trail_half_delay1", "utcsat_cap16d",
    "utcsat_chopband_multi_sw10", "utcsat_entry_minus_1", "utcsat_multi_sw10",
    "wage12_utcsat_multi_sw10", "wage24_multi_sw10", "wage24_utcsat_multi_sw10",
}

# A retired target with a live alias pointing at it raises KeyError from
# registry.helpers the moment anything iterates EXPERIMENTS. Checked explicitly
# rather than assumed - the 2026-10-08 pass had this exact bug and the test caught
# it. _ALIAS_TARGETS is defined below RETIRED, so it is read lazily here.
def _alias_targets_for_retirement():
    return {alias for alias, target in _ALIAS_TARGETS.items()
            if target in RE_RETIRED_ANY_ERA_NEGATIVE}

RETIRED = (ERA_FITTED | BOTH_NEGATIVE | INVERSE | LOW_OOS | DANGLING_ALIAS
           | RE_RETIRED_ANY_ERA_NEGATIVE)

assert len(ERA_FITTED) == 28, f"bar-1 era-fitted drifted: {len(ERA_FITTED)}"
assert len(BOTH_NEGATIVE) == 1, f"bar-1 both-negative drifted: {len(BOTH_NEGATIVE)}"
assert len(INVERSE) == 3, f"bar-1 inverse drifted: {len(INVERSE)}"
assert len(LOW_OOS) == 52, f"bar-2 drifted: {len(LOW_OOS)}"
assert len(DANGLING_ALIAS) == 1, f"alias count drifted: {len(DANGLING_ALIAS)}"
# 85 before the 2026-10-14 re-retirement. The 69 re-retired keys are all still
# active books, so the union - not the sum - is the number that matters; it is
# asserted below rather than assumed.
assert len(RE_RETIRED_ANY_ERA_NEGATIVE) == 69, (
    f"re-retired set drifted: {len(RE_RETIRED_ANY_ERA_NEGATIVE)}")
_retired_before_reretire = 85
assert len(RETIRED) > _retired_before_reretire, (
    f"re-retirement added nothing: {len(RETIRED)}")

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


def stale_pins():
    """Books whose pins no longer reproduce on the current engine.

    Returns {} right now on purpose: the measurement lives in
    `exp_archive_verify.py`, which can re-derive it on demand. It is NOT computed
    at import time because re-running 84 books takes minutes and this module is
    imported by the registry on every harness run. Hardcoding the answer here
    would be worse than not having it - it would go stale exactly like the pins.

    As of 2026-10-08: **36 of 168 archive cells do not reproduce**, and this is
    PRE-EXISTING, not caused by any recent change. Confirmed by stashing the
    engine work and re-running: identical 132/36 split before and after. The
    failures are the `lb30_*` / `opt_*` / `gap_b3k*` / `a4_w24_*` families, and
    several show the right trade count with the wrong net, which is the signature
    of pins written on an older cost model rather than pins written wrong.

    The honest reading is that these pins are STALE, not that the books are
    broken - the registry itself carries this drift (see `_registry_before.json`,
    which was already failing its own check on HEAD before the prune).
    """


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