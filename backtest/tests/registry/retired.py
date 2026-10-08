"""RETIRED books - removed from EXPERIMENTS on 2026-10-08, definitions untouched.

THE OWNER'S RULE
================
    "any book jisme IS ya OOS negative hai usko hata"

Applied literally: 32 books, both eras' pins, no exceptions. `IS<0 or OOS<0`.

WHY A LIST AND NOT 32 DELETIONS
================================
The book configs live in six family modules and deleting them in place would
touch all six for no benefit. Instead this module holds the KEYS, and
`registry/__init__.py` subtracts them from the merged dict after the merge. Two
consequences worth stating:

  * The definitions stay where they were, so any retired book is one line in
    RETIRED to bring back. That is the difference between retiring and deleting.
  * Nothing about the registry's public surface changes. `book()`,
    `shortlisted()`, `alias_of()` and every harness keep working; the retired
    keys simply stop resolving, which is the same observable behaviour as
    deleting them.

THE SPLIT INSIDE THE 32, because it is not what it looks like
============================================================
Applying "IS<0 or OOS<0" as one undifferentiated rule throws away two different
findings. Both are recorded here so the rule can be re-read later without
re-running anything.

  ERA_FITTED (28 books) - IS positive, OOS negative.
      IS average R per trade runs 0.089 to 0.711 and OOS average R per trade is
      negative on every one. This is the pattern the repo has found over and
      over: a book that worked and stopped. The OOS trade counts are large -
      91 to 301 - so this is not a small-sample artifact.

  BOTH_NEGATIVE (1 book) - `skipwinhalt_sig_sw10`, IS -1.50R over 280 trades and
      OOS -4.24R over 162. Nothing about it is worth keeping.

  INVERSE (3 books) - IS negative, OOS strongly POSITIVE. These are the awkward
      ones and the owner's rule removes them:

          book                     IS avgR    OOS avgR   OOS net   OOS dd
          gap_campaign_max2        -0.0566    +0.4927    +74.89    13.59
          gap_campaign_markneg     -0.0602    +0.4979    +76.67    13.59
          gap_entry_cap2           -0.0602    +0.4979    +76.67    13.59

      Out of sample these three are among the healthiest books in the registry by
      OOS drawdown - 13.59R - and their out-of-sample average R per trade of
      +0.49 sits above `fsent_champ_long_mode_atr_low`'s +0.891 only because
      that book runs 315 trades for +280R rather than 154 for +76R. They lose
      in sample and win out of it, which is the mirror image of era-fitting and
      the opposite verdict.

      They are retired because the owner was told this in plain numbers and
      answered "ek era mai negative hai toh hatana hai". That is a decision to
      hold, and holding it is right: a book with a -16R in-sample expectancy has
      not earned trust just because one window suited it. But the reason they
      leave is the owner's rule, not a measurement, and the pins are preserved
      here so the judgement can be revisited rather than rediscovered.

56 further books sit at 0 <= OOS < 60R and are NOT retired here - that is a
second bar the owner named but has not applied. See method/PRUNE_BOOKS.md.
"""
RETIRED = {
    # ---- ERA_FITTED: IS positive, OOS negative (28) ----
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
    # ---- BOTH_NEGATIVE (1) ----
    "skipwinhalt_sig_sw10",
    # ---- INVERSE: IS negative, OOS positive (3) — see the module docstring ----
    "gap_campaign_max2", "gap_campaign_markneg", "gap_entry_cap2",
    # ---- DANGLING ALIAS (1) ----
    # `swingpause_cd0_single_sw10` is a str-valued row aliasing
    # `swingpause_sig_sw10`, which is retired above. Registry helpers raise on an
    # alias whose target is missing, so retiring the target alone would turn this
    # into a KeyError the moment anything iterated the registry - the prune would
    # have broken the registry rather than shrunk it. Retiring the alias too is
    # the only consistent option; leaving it would resurrect the book by the back
    # door while claiming to remove it.
    "swingpause_cd0_single_sw10",
}

assert len(RETIRED) == 33, f"retired count drifted: {len(RETIRED)}"

# The registry's only two alias rows, checked here so this module cannot be
# edited into a state that breaks alias resolution. Asserted rather than
# documented because the failure mode is a KeyError at import time somewhere
# unrelated, which is expensive to trace back to a prune.
_ALIAS_TARGETS = {"swingpause_cd0_single_sw10": "swingpause_sig_sw10"}
for _a, _t in _ALIAS_TARGETS.items():
    if _t in RETIRED and _a not in RETIRED:
        raise AssertionError(
            f"alias {_a!r} targets retired book {_t!r} but the alias itself is not "
            "retired. Retiring a target without its aliases raises KeyError from "
            "registry.helpers when anything iterates EXPERIMENTS.")