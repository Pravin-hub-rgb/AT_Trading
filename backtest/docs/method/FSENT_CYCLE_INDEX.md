# consolidated index — the fsent cycle and what came before it

Date: 2026-10-09.

## START HERE

**`FSENT_MASTER_STUDY.md`** — the complete record. Candidate leaderboard, full
experiment ledger, period-control ranking, negative-cell autopsy, corrections log,
and what is still open. Everything below is evidence behind it.

---

## this cycle, in the order it happened

| # | doc | the finding |
|---|---|---|
| 1 | `FS_CAUSALITY_AND_HTF_EXPERIMENTS.md` | **0 lookahead violations**, 6 books, both eras — after the audit's own timezone bug produced 184 false ones first |
| 2 | `HTF_FS_ENTRY_REJECTED.md` | HTF window opening on FS: **+55% net, fails the rule.** Withdrawn period-control number now marked in place |
| 3 | `MAXCONSEC_LOSSES_FINDING.md` | the negative cell is **−0.69R on 60 trades**; the cause was **`max_consecutive_losses=3`**; turning it off dominates the parent in both eras |
| 4 | `FSENT_MASTER_STUDY.md` | the consolidated record |

## the candidates

| doc | book |
|---|---|
| `HTF_SWEEP_OWNER_RULE.md` | `fsent_champ_long_htf15` |
| — (in MASTER, §3.3) | `fsent_champ_long_biasmom05` — **period control fails** |
| — (in MASTER, §3.4) | `fsent_champ_long_htfesmcl4` — the ceiling, 27.74R dd |
| — (in MASTER, §7) | `fsent_champ_long_mcloff` — **same book as `nohalt`** |
| `SIG_MULTI_STUDY.md`, `SIG_MULTI_REGISTERED.md` | `fsent_sig_multi` |
| `REGIME_ROBUSTNESS_12_CELLS.md` | the 12-cell comparison, HTF/LTF definitions |
| `OWNER_SCORECARD_MODES.md` | the owner framework: net is not the ranking metric |
| `PRUNE_BOOKS.md`, `BOOK_ARCHIVE.md` | 85 retired keys, 156 live books |

## the rules that must not bend

| doc | the rule |
|---|---|
| `OOS_IS_NOT_A_HOLDOUT.md` | 2021-22 is **reused old data**, not forward evidence |
| `FORWARD_TEST_PLAN.md` | n≥50 provisional, n≥150 verdict, n≥300 publishable |
| `FLIP_QUALITY_PERIOD_CONTROL.md` | the instrument that killed `flip_quality` — reuse it, don't reinvent it |
| `C17_WINDOW_END_CAUSALITY.md` | `window_end` as a knowable instant, not the exit bar |
| `RESEARCH_POLICY_CORRECTION.md` | a clean backtest table is not evidence |

## the instruments

| doc | what it does |
|---|---|
| `exp_flip_period.py` | the P87 period control — OLS + cohort + half-year fixed effects, cluster-robust SE, bootstrap, MDE |
| `exp_fs_causality.py` | C1/C2/C3 lookahead audit, exact join by `swing_no`, TZ self-test |
| `exp_mcl_arms.py` | period control + pins for a list of arms |
| `exp_htf_fs_entry.py` | HTF-FS autopsy incl. the window-structure split |
| `exp_negcell_brainstorm.py` | 12-knob sweep scored on negative half-years |
| `exp_origin_lookahead.py` | broad lookahead / key / swing-loader gate |

## before this cycle

The wider history is in `STRATEGY_STATE_OF_PLAY.md`, `OPEN_RESEARCH_QUEUE.md`,
`MASTER_LEADERBOARD.md` and `EXPERIMENT_LOG.md`. This cycle does not supersede
them; it resolves one branch of the queue — *find a replacement for
`fsent_champ_long` that never has a negative half-year* — down to two candidates
and a list of what is still unproven.