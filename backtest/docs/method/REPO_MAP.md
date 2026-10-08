# Repository map: 25 router branches no book uses, and 53 registry keys the engine rejects

Date: 2026-10-08. Harness: `exp_repo_map.py`. Nothing adopted; this is an
inventory.

## Why a map and not another experiment

This session produced nine findings and adopted nothing. Each was a single knob,
book or threshold, checked against a framework the repo already had. What nobody
had was the thing a map gives: **which parts of the space were never touched at
all**, as distinct from which parts were tested and closed. The repo's closed-ideas
list is long and does not separate those two things.

## Books

| | |
|---|---:|
| registered in `experiment_registry` | 230 |
| pinned (have an exact expectation) | 189 |
| `status: reference` (must never pin) | 41 |
| named in `registry/signal.py` | 25 |

**11 groups of books carry byte-identical param sets.** These are one result shown
twice, not two results, and quoting them as agreement is a mistake this repo has
already made once:

    fsent_sig_sw10_short, fsent_sig_sw20_short, fsent_sig_sw20_short_wr
    fsswing_sig_sw10, fsswing_sig_sw20
    champion_multi_sw10_leg, decayA_c
    baseline_no_partial_sw10, baseline_no_partial_sw20
    swingpause_sig_sw10, swingpause_sig_sw20
    chopband_swingpause_sig_sw10, chopband_swingpause_sig_sw20

## The first gap: 53 registry keys the engine does not accept

`exp_max_concurrent` was added to `unified.py` yesterday and the map found it
still listed as a book-set key alongside 52 others. This is not a display bug —
**the registry carries keys that no longer exist in the engine.** They are inert
by omission rather than by design, and nothing detects that: the results DB only
compares books that still have pins, and a key the engine ignores does not move a
pin.

53 of them, including `b3_k`, `exp31_lb`, `exp_atr_ratio_max`,
`exp_campaign_*`, `exp_cohort_*`, `exp_curfew_*`, `exp_event_mode`,
`exp_geom_b1_*`.

**This is the cheapest finding on the map and nobody had it.** Not one is a
strategy idea. It is a hygiene gap: the registry claims a configuration the engine
cannot honour, and the only reason it was found is that this map happened to
count keys against the signature.

## The second gap: 25 of 27 router branches have no book

| branch | uses chop_thresh? |
|---|---|
| `atr_low` | no |
| `b2_vs_flip_chop` | **yes** |
| `chop` | **yes** |
| `chop_and_atr_low` | **yes** |
| `chop_or_atr_low` | **yes** |
| `decisive_vs_flip_chop` | **yes** |
| `dynamic_chop` | **yes** |
| `entropy` / `entropy_inv` | **yes** |
| `fd` / `fd_inv` | **yes** |
| `flip_quality` | **yes** |
| `garch` / `garch_inv` | **yes** |
| `hmm` / `hmm_inv` | **yes** |
| `htf_dir`, `ltf_dir` | no |
| `htf_mag` / `htf_mag_inv` | **yes** |
| `session` / `session_flip` | no |
| `soft_atr`, `soft_chop`, `soft_ensemble` | **yes** |

Live books use only `mode="atr_high"` (215 books, chop-inert) and `mode="union"`
(2 books). Everything else is unreachable **by the current registry**, including
19 of the 20 branches that read `chop_thresh`.

The session's own finding — that `chop` and `atr` are different variables
disagreeing on a quarter to a third of bars — was measured by grafting `chop`'s
condition onto `atr_high`. **Eighteen of the branches that already implement
exactly that, in the engine, have never been run against a book.**

That is the largest untouched region in the repository, and it is untouched by
accident rather than by decision.

## Parameters no book sets (reachable, unexercised)

    exp_bm_causal, exp_fs_gray, exp_max_concurrent, soft_width

`exp_max_concurrent` is the one added yesterday and measured this session.
The other three have never been set by any book.

## Queue state

5 open, 19 done. All five are blocked on data, a size channel, a validator, or an
owner decision — none is a knob that could be swept today.

## What this map does not claim

It does not propose experiments. "A mode has no book" is a fact about the
registry, not an argument that the mode would work — and this session has
produced nine consecutive examples of a measurement worth making that changed
nothing. The `entropy`, `garch` and `hmm` families are the obvious next thing to
look at **because they are a fixed cost to test and not because any evidence
points at them.**

**Nothing adopted. No registry entry changed, no key removed.**