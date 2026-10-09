"""SIGNAL - one-position books: FS exit, directional entry, serial, the signal book.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {
    # ===== FS-EXIT (engine knob, measured 2026-10-03 IS+OOS) =====
    # Enter exactly as the book does, then close the position when its own
    # swing confirms - but only when that confirmation lands within a few
    # hours of the entry. Causal: fs_at_idx >= seg.end_idx and the book enters
    # at a B2/flip break which sits before that, so the exit only ever reads
    # a confirmation that already happened.
    #
    # The band is a plateau at 2-6h, not a knife edge - every arm in it beats
    # the control on BOTH eras. Exiting on ANY FS is far worse than doing
    # nothing (+133.26 IS / +57.90 OOS vs +239.12 / +72.79), because the
    # long-gap swings are where the runners live.
    "fsexit4_c": {
        "desc": "champion leg + exit at own-swing FS when it lands within 4h",
        "engine": "patched",
"params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                     "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                     "chop_thresh": 58.0, "cooldown_bars": 8,
                     "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                     "exp_partial_r": 0.0, "exp_mltf": True,
                     "exp_persist": 7, "window_end": "exit",
                     "pivot_rule": "leg",
                     "exit_fs_max_gap_h": 4.0},
        "swing": "sw10",
        # See the FS_EXIT ladder in exp_fs_exit.py.
        "pins": {"n": 507, "net": 298.0, "dd_net": 40.91,
                 "oos_n": 295, "oos_net": 68.92, "oos_dd_net": 48.72},
    },
    # ===== DIRECTIONAL FS ENTRY (engine knob exp_fs_entry_side) =====
    # ===== DIRECTIONAL FS ENTRY (engine knob exp_fs_entry_side) =====
    # Measured 2026-10-04 by exp_fs_directional_leg.py on CAUSAL leg-family
    # books, both eras. Only the ENTRY TRIGGER changes on one side; the other
    # side, the LTF cascade and every risk knob are untouched. Do not confuse
    # with the closed FS-EXIT work in closed/CLOSED_DO_NOT_REPEAT.md: same FS print,
    # but used to DELAY an entry instead of to close a position.
    "fsent_champ_long": {
          "desc": "champion leg + LONGS enter at swing FS (shorts unchanged)",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # Directional FS entry: ONE side enters at the swing FS print, the
          # other side unchanged. exp_fs_directional_leg.py, both eras.
          #
          # ext_stop_r = 0.0. It ran at 3.0 until 2026-10-07 and was removed
          # because it no longer does anything, not because it was found harmful.
          # Measured, both eras: 3.0 and 0.0 produce a BYTE-IDENTICAL trade list
          # and an identical equity curve, and every field of the equity lens
          # (ulcer, sortino, calmar, uw_pct, max_dd_dur, max_uw, max_streak,
          # pos_month_pct, worst_month) compares equal. See
          # method/EQUITY_LENS_EXT_AND_NOHALT.md, harness exp_equity_lens.py.
          #
          # WHY IT STOPPED MATTERING - C17, same day. ext_stop_r=3.0 and
          # htf_rr=3.0 are the same level, 1h_entry + 3 x |1h_entry - 1h_sl|,
          # so the HTF window gate already removed everything beyond it. What the
          # knob was still blocking was the straddle: a 15m bar that opened before
          # the 1m exit and closed after it, so its close crossed 3R on a thesis
          # that had already died. C17 fixed that gate and the straddle cannot
          # occur, which left the knob blocking zero signals. The threshold was
          # never re-tuned after that - 3.0 was simply the top of a dead plateau,
          # and 4.0 measures identically to it.
          #
          # WRITE 0.0, NEVER OMIT THE KEY. BP carries ext_stop_r=1.5, so deleting
          # the field would not mean "off", it would inherit 1.5 - which is a live
          # filter blocking 122 IS and 86 OOS signals on this book. That silent
          # default is the one way this line can be broken by accident.
          #
          # RE-TESTED AND REJECTED, do not redo it. A coarse sweep made 2.0 look
          # like a +16R in-sample lift. A 19-point fine sweep found NO threshold
          # that beats 0.0 in both eras, and the cohort autopsy showed the filter
          # removes a cohort worth -1.5R in IS and +9.6R in OOS - it deletes
          # profitable trades out of sample. The in-sample move was re-sequencing,
          # not selection. Closed in method/EXT_STOP_R_RIDGE.md.
          "pins": {"n": 528, "net": 533.37, "dd_net": 13.42,
                   "oos_n": 311, "oos_net": 239.59, "oos_dd_net": 11.88},
      },

    # SINGLE-VARIANT ABLATION of fsent_champ_long: the 3-loss streak halt off.
    # The point of registering it rather than folding it into the base is
    # attribution.
    #
    # FOUR KEYS REMOVED 2026-10-07 - chop_thresh, atr_low_thresh, exp_mltf,
    # window_end. All four were measured INERT on this book (exp_knob_binds.py)
    # and all four omit cleanly: this book's own value equalled the BP default in
    # every case except exp_mltf, where BP has no value at all. Verified by
    # removing all four and re-running: trade lists byte-identical on both eras,
    # 528 / +533.37 IS and 311 / +239.59 OOS.
    #
    # chop_thresh - mode="atr_high" routes on atr_high_thresh alone and never
    # reads chop_thresh. Removed because BP's default is ALSO 58.0, so there is
    # nothing to inherit differently. That is NOT a registry-wide fact: 13
    # registry books omit `mode`, inherit BP's "b2_vs_flip_chop", and DO read it,
    # carrying +105R to +163R on the four sampled; one is named
    # lb30_chop55_persist2. See docs/method/KNOB_BINDS_AUDIT.md. If `mode` on
    # this book ever changes to a chop-reading mode, this key must come back, and
    # the audit that says so is the mode census in exp_knob_binds.py.
    # atr_low_thresh - same mode-gating, same reasoning, BP default 0.35.
    # exp_mltf is BACK, and the reason it left is worth recording because it was my
    # error. It was removed 2026-10-07 in a cleanup of the four inert keys, on the
    # grounds that it is INERT at max_positions=0 and that BP carries no value for
    # it. Both halves of that are true and together they were misleading: the
    # engine default for the key is 0, so omitting it happened to reproduce the
    # pinned trade lists exactly, which made removal look safe.
    #
    # It is NOT dead. It is the multi-timeframe gate and this book is a MULTI
    # position book, so the knob matters the moment anyone flips the book to
    # max_positions=1. Measured, post-C17, this book's config:
    #
    #   max_positions=1, exp_mltf off   IS 355 / +166.31   OOS 220 / +66.99
    #   max_positions=1, exp_mltf on    IS 528 / +533.37   OOS 311 / +239.59
    #
    # A 69% loss of return if the book is made serial without restoring this key.
    # At the shipped max_positions=0 the key is genuinely inert - restoring it
    # changes nothing, trade lists byte-identical both eras - so it costs one line
    # and removes a live trap.
    #
    # THE LESSON, which is the generalisable part: "INERT" from exp_knob_binds.py
    # is scoped to the config it was measured on, and that config includes
    # max_positions. Deleting a key whose inertness depends on ANOTHER setting is
    # only safe if the other setting cannot change. Three of the four keys removed
    # that day were safe because their BP default was identical; this one was safe
    # only because max_positions=0 happened to be true today. Do not generalise
    # from "it omitted cleanly" to "it is unnecessary".
    # window_end - value-collapsed: at ext_stop_r=0.0 both "exit" and "r_touch"
    # resolve to the same code path. It reappears if ext_stop_r ever goes above
    # htf_rr. BP default is "exit".
    #
    # ext_stop_r is set to 0.0 explicitly rather than dropped, for two reasons.
    # It is provably inert since C17: 3.0 and 0.0 produce byte-identical trade
    # lists AND an identical equity curve, both eras (exp_equity_lens.py Q1), so
    # this change is not what makes the book differ. And omitting the key would
    # NOT mean "off" - BP carries ext_stop_r=1.5, and 1.5 is a live filter that
    # blocks 122 IS / 86 OOS signals. Write 0.0, never nothing.
    #
    # ===== GOVERNANCE: why the MAIN book keeps the 3-loss halt =====
    # fsent_champ_long runs max_consecutive_losses=3. Removing it measured
    # CHEAPER on both eras, and we kept it anyway. Written here so the next
    # reader does not have to rediscover it from git log, and so nobody
    # "fixes" the main book by deleting the halt because a table said so.
    #
    # What the measurement says (current engine, post-C17; artifacts
    # _fsent_ablation.md "no_streak3", _strip.md "no_halt_only",
    # _halt_sweep.md rows persist=7/ext=0.0 at halt=0 vs halt=3):
    #
    #   halt off : IS 575 / +566.6   OOS 337 / +270.9   PF 2.77   biggest drop 14.2
    #   halt on  : IS 528 / +533.4   OOS 311 / +239.6   PF 2.69   biggest drop 11.9
    #   delta    : +33.2R in sample, +31.3R out of sample
    #
    # So the data disagrees with the decision, on both eras, by about 30R.
    # That is recorded, not hidden. What we accept in exchange:
    #   - longest run of losses in a row goes from 15 trades to 16
    #   - biggest drop from peak goes from 11.9R to 14.2R
    #   - 26 more trades out of sample, and a slightly busier book
    #
    # WHY WE KEEP IT ANYWAY - this is a governance call, not a data call.
    # The halt is a brake whose benefit is a worst-case bound, not an average.
    # Its cost is certain and measured. Its benefit is what it does in the one
    # stretch we have not lived through yet. Paying a certain ~30R for a bound
    # on the unbounded case is the trade we are making on purpose; if the
    # capital behind this book can absorb a 16-trade losing run, the cheaper
    # book below is the better one and this note is the thing to overturn.
    #
    # Do not "correct" the main book from the tables. The counter-book
    # fsent_champ_long_nohalt below is REGISTERED AND PINNED, with the halt off
    # at 575 / +566.6 IS and 337 / +270.9 OOS, so whoever overturns this
    # decision starts from a re-derivable measurement instead of prose to
    # reconstruct one from. That is what makes the decision revisable rather
    # than permanent by inertia: the counter-book is a book, not a claim.
    #
    # ===== THE RULE THAT FLIPS IT - owner's decision, 2026-10-07 =====
    # This is not "keep the halt until we feel richer". The trigger is ONE
    # measured number, so it cannot be argued into or out of by mood:
    #
    #   Halt stays ON while the live max-drawdown budget does NOT comfortably
    #   cover this book's own tail.
    #
    #   Current budget need: 14.16R OOS max_dd of fsent_champ_long_nohalt,
    #   which is the deepest drop measured on the halt-off book in either
    #   era. Base book sits at 11.88R.
    #
    #   When the budget can absorb 14.16R with room to spare, flip
    #   fsent_champ_long to the nohalt params. No further evidence is needed
    #   and no re-run is required: the counter-book's pins already hold that
    #   measurement.
    #
    # WHY THE TRIGGER IS NOT "more capital". More capital does not change
    # this book's behaviour - it takes MORE trades either way, so its max DD
    # is ~14R whether the account is small or large. Only the budget moves.
    # A rule keyed on "we can afford to lose more" silently re-decides itself
    # every time the owner's feeling about the account changes, which is
    # exactly the inertia this note exists to prevent.
    #
    # WHY NOT 16 CONSECUTIVE LOSSES AS THE TRIGGER. The 15 -> 16 OOS streak is
    # the real argument for the halt, but it is not a usable threshold: the
    # backtest has never seen a live losing run, so 16 is a lower bound on
    # the tail and not its size. Keying a capital decision to a number known
    # only from backtest would be pretending to a precision nobody has. The
    # max-dd budget is a number the owner actually sets and actually knows.
    #
    # ===== FOUR MODE CANDIDATES - registered and pinned, NOT promoted =====
    # Added 2026-10-08. exp_mode_sweep.py ran all 27 router branches against
    # this book for the first time; 25 of them had no book anywhere in the
    # registry. Four beat mode="atr_high" in BOTH eras and survived removing the
    # top 5 and top 10 trades:
    #
    #   book                        IS             OOS            IS dd  OOS dd
    #   fsent_champ_long (shipping) 528 / +533.4   311 / +239.6   13.4   11.9
    #   ..._mode_atr_low            641 / +721.3   315 / +280.7   28.9   14.6
    #   ..._mode_fd                 529 / +534.8   295 / +276.8   13.4   12.2
    #   ..._mode_flip_quality       527 / +534.8   294 / +244.4   13.4   11.9
    #   ..._mode_union              813 / +580.0   442 / +303.8   23.8   18.2
    #
    # NONE is adoptable, for two measured reasons, not for lack of evidence:
    #
    #   1. Drawdown, ON THE OWNER'S BUDGET. Corrected 2026-10-08: the earlier note
    #      here said "every one spends drawdown" and cited a rule requiring DD
    #      <= the base book's 11.88R. That rule was MINE and it is not in the
    #      owner's framework (docs/learn/finding optimal book.md), which treats
    #      drawdown as an input to a trade rather than a veto and names
    #      Net R / Max DD as the measure for that trade. It is withdrawn.
    #      The owner has since set a 20R drawdown budget, so the real test is
    #      against 20R, and it still bites:
    #        atr_low   28.9R IS  OVER   82 trades to make, 460 underwater
    #        union     23.8R IS  OVER   46 to make, 771 underwater
    #        fd/flip   13.4R IS  PASS   identical to base
    #      Note this reverses my own framing: union's OOS DD is 18.2R, which
    #      PASSED my invented 11.88R gate on the number I was citing, and it is
    #      still rejected - on the in-sample 23.8R, on 771 trades underwater,
    #      on Net R / Max DD being LAST of the five (24.37 IS vs base 39.80), and
    #      on the top 5% of trades carrying 95.0% of in-sample profit with only
    #      3.9% surviving their removal. See method/OWNER_SCORECARD_MODES.md.
    #   2. Lane test. The first version of this note used champion_multi_sw10 /
    #      utcsat_multi_sw10 as "the second lane" and all four failed there out
    #      of sample. Those books are a DIFFERENT architecture - pivot_rule=origin,
    #      no exp_fs_entry_side, no exp_mltf - so that was the wrong family to
    #      judge a change to THIS book on, and the shipping book was never tested
    #      anywhere in that run at all. Re-run on the family that does share the
    #      architecture - fsent_champ_long / fsent_utcsat_long / fsent_champ_short,
    #      all three netting about 239R OOS - only flip_quality held: ahead on all
    #      three (+4.8R / +4.8R / +54.0R) with drawdown flat or better on each.
    #      See method/MODE_CONFIRM2_RIGHT_LANES.md.
    #   3. PERIOD CONTROL, 2026-10-08 - all four are dead, including flip_quality.
    #      Step 2 measured NET on a total that the base and the arm share almost
    #      entirely. exp_flip_period.py fitted R = a + b*cohort + half-year
    #      fixed effect - the framework's own discriminator, the one every prior
    #      regime-conditional tweak in this repo failed - on the DISAGREEMENT set
    #      only (NEW trades vs DROPPED trades).
    #      The mode is IN-SAMPLE INERT on all three books. In IS the arm and the
    #      base take the SAME trades: 0 new, 0 dropped on utcsat_long and
    #      champ_short; on champ_long the entire +1.41R is ONE dropped trade. All
    #      three IS cells are therefore non-estimable - there is no disagreement
    #      to measure. Every R of the mode's effect is out of sample.
    #      On the two long books b is +0.2122 against an MDE of 0.8569: inside
    #      the noise floor, 96% of the raw gap explained by the calendar. The one
    #      powered cell is fsent_champ_short OOS (b +1.3963, t 2.016) - the
    #      FS-short mirror, a different architecture with 23.9R drawdown, and the
    #      source of the whole +54.01R. One cell of one architecture on one era
    #      cannot carry the other five.
    #      VERDICT: flip_quality is DISQUALIFIED as a regime proxy - the exact
    #      case this framework exists to catch. Its drawdown-neutral property is
    #      still true and still not sufficient: harmless is not useful. Step 2's
    #      3-of-3 was real and was not enough.
    #      See method/FLIP_QUALITY_PERIOD_CONTROL.md.
    #
    # Two bugs in the first version of that harness are recorded in the doc
    # because both flattered the arm: survivors were labelled cohort=1 (giving a
    # meaningless t of 7.672), and the half-year partition compared the base
    # against itself (printing 8 of 8 on a cell where both books were identical).
    #
    # So this whole table is now CLOSED. Four modes swept, four registered, four
    # rejected - three on drawdown, and flip_quality on era. Step 2's 3-of-3 was
    # a real measurement and was not sufficient, and neither was holding the
    # drawdown flat. The router is not where the next gain is; see
    # method/REPO_MAP.md for what the map says has never been touched.
    #
    # So the blockers below are per-candidate and were REVISED, not uniform. On
    # the correct family flip_quality is not lane-blocked at all; atr_low and fd
    # each hold on 1 of 3 and both spend drawdown on the two long books; union
    # fails all three on drawdown alone.
    #
    # mode="atr_low" is the interesting one and the reason it is worth keeping
    # registered: it is an INVERSION, not a tuning. atr_high takes decisive
    # windows when bars are big; atr_low takes them when bars are quiet. Same
    # variable, sign flipped, worth +187.9R in sample. Its own threshold was
    # swept 0.20-0.60 and the OOS gain peaks sharply at 0.35 (+41.1R) and is
    # NEGATIVE everywhere else - one point, not a region, which is exactly the
    # grid-peak failure P69 warns about.
    #
    # Registered so the measurements are re-derivable and the next round starts
    # from a pin instead of prose. Do not promote one from this table.
    # See method/MODE_CONFIRM_FOUR_CANDIDATES.md.
    "fsent_champ_long_mode_atr_low": {
          "desc": "CANDIDATE, NOT ADOPTED - blocked on drawdown against the owner's 20R budget, not on the invented 11.88R gate (withdrawn 2026-10-08 as mine, not the framework's). fsent_champ_long with mode='atr_low' - the atr_high inversion: decisive windows when 15m bars are QUIET, not big. Only the mode changes; every other knob identical. This is the strongest of the four on the framework's own buckets: it WINS bucket 1 outright in both eras - IS 641t / +721.3R / expectancy 1.125 / PF 3.22 against the base 528t / +533.4R / 1.010 / 3.09, and OOS 315t / +280.7R / 0.891 / 2.96 against 311t / +239.6R / 0.770 / 2.69 - on MORE trades than the base, so more evidence and not less. Its out-of-sample tail is also the healthiest in the set (top 5% contributes 71.2% against the base's 81.1%; removing the top 10% still leaves -4.6% against -11.7%; removing the top 5% leaves 26.3% against 16.3%) and its DD expansion is 0.51, i.e. half its out-of-sample drawdown is in-sample. It is blocked purely on bucket 2 and bucket 9: 28.9R max DD in sample against the owner's 20R budget, 82 trades to make the drawdown, 460 trades underwater against the base's 286, and a 16-trade losing streak against the base's 11. Its own threshold swept 0.20-0.60 and the OOS gain peaks sharply at 0.35 (+41.1R) and is NEGATIVE everywhere else - one point, not a region, which is exactly the grid-peak failure P69 warns about. This is the one candidate worth keeping open, and the open question is whether a 20R budget can stretch to 29R - the owner's call, not the registry's. See method/OWNER_SCORECARD_MODES.md.",
          "engine": "patched",
          "params": {"mode": "atr_low", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 641, "net": 721.30, "dd_net": 28.90,
                   "oos_n": 315, "oos_net": 280.70, "oos_dd_net": 14.60},
    },
    "fsent_champ_long_mode_fd": {
          "desc": "CANDIDATE, NOT ADOPTED. fsent_champ_long with mode='fd' - fractional-dimension regime: low FD=trend->flip, high FD=range->B2. Closest drawdown of the four (13.4R IS / 12.2R OOS) but still worse than base, and fails out of sample on both second lanes.",
          "engine": "patched",
          "params": {"mode": "fd", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 529, "net": 534.80, "dd_net": 13.40,
                   "oos_n": 295, "oos_net": 276.80, "oos_dd_net": 12.20},
    },
    "fsent_champ_long_mode_flip_quality": {
          "desc": "CANDIDATE, NOT ADOPTED - DISQUALIFIED 2026-10-08 as a regime proxy. fsent_champ_long with mode='flip_quality' - B2/flip by chop AND a HTF-magnitude floor, so it filters the chop branch. It held the base drawdown exactly (13.4R IS / 11.9R OOS) and was ahead on all three books of its family in the lane test (+4.8R / +4.8R / +54.0R), which is why it was the closest of the four. Period control then disqualified it: the mode is IN-SAMPLE INERT on all three books. In IS the arm and the base take the SAME trades - 0 new, 0 dropped on fsent_utcsat_long and fsent_champ_short, and on this book the entire +1.41R is ONE dropped trade - so all three IS cells are non-estimable and every R of the mode's effect is out of sample. Out of sample b after a half-year fixed effect is +0.2122 against an MDE of 0.8569: inside the noise floor, 96% of the raw gap explained by the calendar. The one powered cell is fsent_champ_short OOS (b +1.3963, t 2.016) - the FS-short mirror, a different architecture with 23.9R drawdown, and the source of the whole +54.01R - and one cell of one architecture on one era cannot carry the other five. The earlier 3-of-3 lane result was real and was not sufficient; being drawdown-neutral is not the same as being useful. Two corrections recorded on 2026-10-08: the 'fails on both second lanes (-7.0R, -4.1R)' sentence was measured on champion_multi_sw10/utcsat_multi_sw10, a DIFFERENT architecture (pivot_rule=origin, no FS side, no exp_mltf), and the first period-control harness labelled survivors as cohort=1, which produced a meaningless t of 7.672. Remains registered and pinned so the measurements are re-derivable. The branch also READS chop_thresh, which is not in this book's config, so it was never the base plus a mode string. See method/FLIP_QUALITY_PERIOD_CONTROL.md, method/MODE_CONFIRM2_RIGHT_LANES.md.",
          "engine": "patched",
          "params": {"mode": "flip_quality", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 527, "net": 534.80, "dd_net": 13.40,
                   "oos_n": 294, "oos_net": 244.40, "oos_dd_net": 11.90},
    },
    # fsent_sig_multi is the sig book's WHOLE filter set with max_positions 1 -> 0.
    # It is the only candidate in this file whose out-of-sample effect survives the
    # period control: 99% of the raw gap survives a half-year fixed effect in BOTH
    # eras, and it is ahead in 12 of 12 half-year cells. See
    # method/SIG_MULTI_STUDY.md for the full gates, and the caveat below.
    "fsent_champ_long_mcloff_htf15": {
          "desc": "CANDIDATE, NOT ADOPTED - the best NON-degenerate arm found, and the two findings that actually changed the picture, stacked. It is fsent_champ_long_mcloff (max_consecutive_losses=0) on the htf15 1h swing series. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 560t / +616.17R / DD 15.13R / WR 41.1%, OOS 299t / +277.35R / DD 13.64R / WR 38.1%. It beats the parent in BOTH eras by more than mcloff alone (+82.80R IS, +37.76R OOS) and beats mcloff in both eras as well (+49.59R IS, +6.44R OOS), for 1.00R of extra in-sample drawdown. ZERO negative half-years out of 12. WHY THIS IS THE RECOMMENDATION AND NOT htf15 OR htfesmcl4: it does not use exp_htf_fs_entry, so it keeps the flip/decisive/b2 regime buckets distinct and is NOT the degenerate all-fs_entered configuration that the completion sweep's highest arms all turn out to be. The 12-arm joint grid over max_consecutive_losses x HTF leg length x HTF FS entry produced a +1321.41R arm, and that arm collapses the regime distinction - see method/HTF_FS_ENTRY_REJECTED.md. This one reaches +616.17R while staying honest about what a regime is. PERIOD CONTROL, run on this exact combination on 2026-10-09: SURVIVES with b > 0 in 2 of 2 eras - b = +0.77 (t = 1.72, MDE 0.88) IS and b = +0.62 (t = 1.60, MDE 0.76) OOS, cluster bootstraps +0.80 and +0.64 - but it is UNDERPOWERED, and this is the honest cost of the extra swing. fsent_champ_long_mcloff on its own is the only arm in the family whose control is powered in BOTH eras, at t = 3.37 and t = 3.97. Adding the htf15 swing buys +49.59R IS and dilutes the cohort variance at the same time, so the recommendation on EVIDENCE remains mcloff and the recommendation on RETURN is this one. Still NOT adopted: no arm in the family has forward evidence, and 12 observations of a half-year table is not a guarantee. See method/RESEARCH_COMPLETE.md and method/GRID_PERIOD_AND_KNOB_GUARD.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_mltf": True, "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "htf15",
          "pins": {"n": 560, "net": 616.17, "dd_net": 15.13, "win": 0.411,
                   "oos_n": 299, "oos_net": 277.35, "oos_dd_net": 13.64,
                   "oos_win": 0.381},
    },
    "fsent_champ_long_mcloff": {
          "desc": "CANDIDATE, NOT ADOPTED - and the best-EVIDENCED one in the registry. It changes ONE INTEGER: max_consecutive_losses from 3 to 0, which turns the loss-run cutoff OFF. The autopsy of the parent's negative half-year found 2025-H1 was not a disaster but a coin flip that landed red: 60 trades, net -0.69R, mean -0.011R per trade, 20 winners making +29.6R against 40 losers making -30.3R. In that exact situation the cutoff is not protecting the book, it is cutting winners - it stops the book right before the recovery trade that follows every streak. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 575t / +566.58R / DD 15.13R / WR 39.7%, OOS 337t / +270.91R / DD 14.16R / WR 37.1%. IT DOMINATES THE PARENT ON RETURN IN BOTH ERAS (+33.21R IS, +31.32R OOS) on 47 and 26 MORE trades, for 1.71R and 2.28R of extra drawdown. ZERO negative half-years out of 12. PERIOD CONTROL IS THE REASON TO TRUST IT - this is the only arm in the whole family whose effect is SIGN HOLDS and POWERED in BOTH eras: b = +1.21 (t = 3.37, MDE 0.70) IS and b = +1.86 (t = 3.97, MDE 0.92) OOS, cluster-bootstrap b_boot +1.28 and +1.92. Compare fsent_champ_long_htf15 (underpowered), fsent_champ_long_biasmom05 (b NEGATIVE and significant at t = -9.63 OOS) and htf_fs=all (underpowered). Still NOT adopted: the period control compares this arm to champ_long, NOT to absolute zero, and a book that is meaningfully better than its parent can still be negative in some unseen half-year. The cutoff also has a real purpose under position sizing, which is a risk decision and not a signal decision. Forward evidence does not exist for it yet. See method/MAXCONSEC_LOSSES_FINDING.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_mltf": True, "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 575, "net": 566.58, "dd_net": 15.13, "win": 0.397,
                   "oos_n": 337, "oos_net": 270.91, "oos_dd_net": 14.16,
                   "oos_win": 0.371},
    },
    "fsent_champ_long_htfesmcl4": {
          "desc": "CANDIDATE, NOT ADOPTED - the largest-return arm measured in this family, and registered because the owner asked for every arm to be visible rather than pre-filtered. It stacks the HTF-side FS entry (exp_htf_fs_entry=all) with max_consecutive_losses=4, which is the one setting that clears the 2022-H2 cell that the FS entry alone re-broke. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 793t / +917.80R / DD 27.74R / WR 43.0%, OOS 437t / +326.22R / DD 14.20R / WR 37.8%. ZERO negative half-years out of 12. THREE REASONS IT IS NOT THE RECOMMENDATION DESPITE THE NET. (1) In-sample drawdown 27.74R is at the owner's 29R budget ceiling, against 15.13R for fsent_champ_long_mcloff on less than half the return. (2) PERIOD CONTROL IS UNDERPOWERED OUT OF SAMPLE - b = +0.027 with t = 0.05 and MDE 1.16, i.e. the out-of-sample effect is indistinguishable from nothing, and the cluster bootstrap goes NEGATIVE at -0.03. (3) The FS entry collapses the flip/decisive/b2 regime buckets into one fs_entered set, so this arm stops distinguishing regimes - see method/HTF_FS_ENTRY_REJECTED.md. It buys +384R of in-sample return mostly by admitting 528 new trades rather than by improving the ones it had. Registered as the high-return end of the range so the owner can see what the ceiling costs.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 4,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_mltf": True, "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_htf_fs_entry": "all"},
          "swing": "sw10",
          "pins": {"n": 793, "net": 917.8, "dd_net": 27.74, "win": 0.43,
                   "oos_n": 437, "oos_net": 326.22, "oos_dd_net": 14.2,
                   "oos_win": 0.378},
    },
    "fsent_champ_long_biasmom05": {
          "desc": "CANDIDATE, NOT ADOPTED - the HTF-side sibling of fsent_champ_long_htf15, and the one that fixes the negative half-year WITHOUT adding drawdown. Where htf15 lengthens the 1h leg, this arms the other HTF knob: exp_bias_momentum_min=0.5, a floor on the RATIO of this HTF leg's magnitude to the previous one, so the book only takes entries while the 1h leg is growing rather than shrinking. It is the closest existing knob to 'the HTF window opens on strength' - it is literally the 1h leg's own measure deciding whether its window counts. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 488t / +501.48R / DD 13.42R / WR 39.5%, OOS 287t / +217.13R / DD 13.47R / WR 37.6%. THE POINT OF THIS BOOK IS ITS DRAWDOWN: in-sample max DD is 13.42R, EXACTLY the parent's, and out-of-sample is 13.47R against the parent's 11.88R - a 1.6R cost. Every other arm that removes the negative half-year pays for it in drawdown; this one does not. It costs return instead: -31.9R IS and -22.5R OOS, on 40 and 24 fewer trades. It is the low-drawdown branch of the owner's rule, against htf15's high-return branch (IS DD 17.28R, OOS 16.86R, but IS +567.57R / OOS +254.88R). Both are registered so the choice is visible rather than averaged. ZERO negative half-years out of 12, same as htf15. NOTE: this knob is ON the sig books at 0.8 and OFF on the champ books, and 0.8 was chosen there - see fsent_sig_multi. It was never swept on the champ architecture, which is why 0.5 and 1.0 were only measured here for the first time. Still NOT adopted: no period control has been run on this arm, the negative-cell removal has not been shown to survive a half-year fixed effect, and the OOS window is 2021-22, which is not a holdout - see method/OOS_IS_NOT_A_HOLDOUT.md. See method/HTF_SWEEP_OWNER_RULE.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_mltf": True, "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_bias_momentum_min": 0.5},
          "swing": "sw10",
          "pins": {"n": 488, "net": 501.48, "dd_net": 13.42, "win": 0.395,
                   "oos_n": 287, "oos_net": 217.13, "oos_dd_net": 13.47,
                   "oos_win": 0.376},
    },
    "fsent_champ_long_htf15": {
          "desc": "CANDIDATE, NOT ADOPTED - the only arm found so far that fixes the shipping book's one negative half-year WITHOUT losing return, and it does so by moving a knob almost nobody has touched: the HTF swing length. THIS IS THE ONE FROM THE OWNER'S OWN RULE. Asked on 2026-10-09 for something that never goes negative - 'kabhi negative nahi hona chahiye' - the sweep of the HTF plane (1h swings, min_bars 10 -> 3..40) found that fsent_champ_long's single negative half-year, 2025-H1 at -0.7R, disappears at min_bars 13 and the net RISES from +773.0R to +796.5R (14) and +822.4R (15). MEASURED: IS 520t / +567.57R / DD 17.28R / WR 41.2%, OOS 280t / +254.88R / DD 16.86R / WR 37.1%. Against the parent that is +34.2R IS and +15.3R OOS on 8 and 31 fewer trades. WHY THIS IS NOT A GRID PEAK: the region around it is a genuine plateau, not a spike. min_bars 12 gives +783.5R but still 1 negative cell; 13 gives +787.6R with 0; 14 +796.5R with 0; 15 +822.4R with 0; 16 +746.1R with 0; 18 falls back to +708.7R with 1 negative again. By contrast min_bars 30 posts the single best number in the whole sweep at +847.3R with 0 negative - and is a SPIKE: 24 gives +645.4R with 2 negatives, 28 gives +659.6R with 2, 32 gives +696.3R with 0, 34 gives +562.5R. A 200R peak with a 60R trough either side is not an edge, so 30 is rejected and 15 is kept. WHAT CHANGED MECHANICALLY: the HTF plane is engine slot 2 and its swing series feeds the leg ratio, the bias-momentum breaks, the bias flips and _sw_ts_dir_mag, which is the flip/decisive classification every trade is tagged with. A longer 1h leg means fewer, larger HTF windows - 1601 swings at min_bars 10 down to 1479 at 15 - so the regime the router sees is coarser and it sits on fewer regime flips. That is why it is a genuinely different book rather than a re-tuned one. NOTE ON REGISTRATION: the HTF swing length is NOT an engine parameter, it is the registry's `swing` FIELD selecting a precomputed series, so this book needs the `htf15` series added to run_experiment.get_data - it is there, built at min_bars=15 on the 1h flow candles. A book that wanted a different HTF length would need its own series there, not a params edit. STILL NOT ADOPTED: period control gives b=+0.5681 IS and +0.3723 OOS, both positive with 97-98% of the raw gap surviving the half-year fixed effect, so it is not a regime proxy - but both cells are UNDERPOWERED against their own MDEs (1.0372 and 0.8050), so the magnitude is not established. In-sample drawdown rises 13.42R -> 17.28R and OOS 11.88R -> 16.86R, which fits the owner's 29R budget but is a real cost. And the OOS window is 2021-22, which is not a holdout - see method/OOS_IS_NOT_A_HOLDOUT.md. See method/HTF_SWEEP_OWNER_RULE.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_mltf": True, "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "htf15",
          "pins": {"n": 520, "net": 567.57, "dd_net": 17.28, "win": 0.412,
                   "oos_n": 280, "oos_net": 254.88, "oos_dd_net": 16.86,
                   "oos_win": 0.371},
    },
    "fsent_sig_multi": {
          "desc": "CANDIDATE, NOT ADOPTED - the strongest non-shipping result in the repo, and still not an adoption. fsent_sig_full's entire filter set (bias_momentum 0.8, fs_small_swing 6.0, trail_skip_n 2, weekends skipped, FS entry on shorts, ext_stop_r 3.0, halt on 3) with max_positions 1 -> 0, i.e. the single-slot gate removed and concurrency enabled. ONE value differs from fsent_sig_full; the other 15 are identical. WHAT IT IS, in plain terms: the same signals, and the book simply stops standing aside. Of 50 extra out-of-sample trades, 48 were taken while a serial position was already open and only 2 after it closed; 47 of the 50 joined a position in the SAME direction, so this is adding to an existing bet rather than hedging. Those extras earned +25.1R at a 46% win rate, against -0.3R given up on trades the serial book took instead. In sample the same mechanism gives 108 extras earning +186.2R for a net +188.8R. MEASURED: IS 329t / +484.59R / DD 13.39R / WR 45.6%, OOS 195t / +219.82R / DD 7.64R / WR 47.2%. Against the shipping book out of sample that is 92% of the net on 63% of the trades, at 64% of the drawdown, with a 10-point better win rate, and BOTH direction columns stay alive (+136.7R long, +83.1R short) which matters because the FS-side autopsy found the two families pointing in opposite directions. GATES: period control positive in both eras with 99% of the raw gap surviving, so this is NOT a regime proxy - the ATR% ceiling's signature does not appear. The half-year partition is 12 of 12. Tail dependence IMPROVES in every cell of both eras: removing the top 10 trades leaves 40.1% of in-sample profit against the parent's 22.0%, and 30.7% out of sample against 22.4%, which is the opposite of mode_union's 96%. WHY IT IS NOT ADOPTED - CORRECTED 2026-10-08, because the original reason was wrong. I previously wrote here that the out-of-sample magnitude is underpowered (b +0.3303 against an MDE of 2.1999) and therefore should not be adopted. THAT ARGUMENT IS WITHDRAWN. The 'OOS' era is 2021-01-01 to 2022-12-31 and IS is 2023-01-01 to 2026-09-13 - the OOS window is two years OLDER than the in-sample window and has been re-scored many times. It is not a holdout and never was, as method/FORWARD_TEST_PLAN.md states in its own second paragraph ('reused many times, not a holdout'). A power gate on that window is a real measurement of a real limitation OF THAT WINDOW and is not a forward verdict in either direction: it does not say this arm is bad, it says we have no forward data on it. THE CORRECT REASON THIS IS NOT ADOPTED: the adoption decision is BLOCKED ON FORWARD DATA, which does not exist on this machine. method/FORWARD_TEST_PLAN.md is ACTIVE with a hard boundary at 2026-09-13 10:03 IST and five pre-registered gates; it was scored once on 2026-09-25 and produced 5 trades and NO VERDICT (n<50); data/forward/bybit/ is not present locally now. This book is NOT on the contract's pre-registered candidate list, and because no forward window exists on disk nothing is burned - so it can be added before a new window starts, which is the cheapest high-value action available. The in-sample magnitude IS powered (b +2.1619, t +2.240, MDE 1.8920, month-cluster bootstrap +1.8501) and the 2021-22 magnitude is not (b +0.3303, MDE 2.1999); both are true and neither is a forward statement. The 2.16-vs-0.33 gap is a 2023-26 versus 2021-22 difference and should have been labelled as such when first reported. The tightest partition cells matter: 2021-H1 is +39.6 against +39.9 and 2021-H2 +35.8 against +40.5, so the FIRST out-of-sample half-year is worth almost nothing and the gain is concentrated in 2022-H1 and 2022-H2. DO NOT carry the in-sample +2.16R per trade as a forward expectation; the honest figure is roughly +0.33R and even that is not established. Concurrency shape: depth 5 in sample, 4 out, but 69% of entries happen with nothing else open, so this is the same book that occasionally takes a second position, not a crowded one. A cap of 3 costs 1.5R in sample, nothing out of sample, and lowers drawdown in both eras - a free bound on the tail. Two notes on measurement, both of which cost real time and are recorded so they are not repeated: the sibling sweep on the multi books returns BYTE-IDENTICAL results because those books carry exp_mltf=True, which bypasses the max_positions gate entirely in the harness - so this knob is inert on them and meaningful only on the serial sig book; and max_positions must be set alongside the regime knobs rather than alone, since a 0.40% min-stop floor on this book costs 4.1% of the long book's net in sample against 4.1% gained out of sample. See method/SIG_MULTI_STUDY.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_fs_entry_side": "short", "exp_bias_momentum_min": 0.8,
                       "exp_trail_skip_n": 2, "exp_fs_small_swing": 6.0,
                       "exp_skip_weekend": 1, "window_end": "exit"},
          "swing": "sw10",
          "pins": {"n": 329, "net": 484.59, "dd_net": 13.39, "win": 0.456,
                   "oos_n": 195, "oos_net": 219.82, "oos_dd_net": 7.64,
                   "oos_win": 0.472},
    },
    "fsent_champ_long_mode_union": {
          "desc": "CANDIDATE, NOT ADOPTED. fsent_champ_long with mode='union' - admits either HTF interval set. Highest net of the four (813 / +580.0 IS, 442 / +303.8 OOS) and the WORST shape: mean R 0.69 against the base 0.77, drawdown 23.8R / 18.2R, and it loses on both second lanes in both eras. A bigger book, not a better one.",
          "engine": "patched",
          "params": {"mode": "union", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 813, "net": 580.00, "dd_net": 23.80,
                   "oos_n": 442, "oos_net": 303.80, "oos_dd_net": 18.20},
    },
    "fsent_champ_long_nohalt": {
          "desc": "fsent_champ_long with max_consecutive_losses=0 (the 3-loss streak halt removed) and ext_stop_r=0.0 (provably inert since C17, written explicitly because omitting the key would inherit BP's 1.5). Every behavioural knob identical to the base.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 575, "net": 566.6, "dd_net": 15.1,
                   "oos_n": 337, "oos_net": 270.9, "oos_dd_net": 14.2},
      },

    "fsent_champ_short": {
          "desc": "champion leg + SHORTS enter at swing FS (longs unchanged)",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # Directional FS entry: ONE side enters at the swing FS print, the
          # other side unchanged. exp_fs_directional_leg.py, both eras.
          "pins": {"n": 533, "net": 600.6, "dd_net": 17.6,
                   "oos_n": 312, "oos_net": 239.53, "oos_dd_net": 23.87},
      },
    # Directional FS entry, continued: a second shipping-family book and the
    # highest-OOS book in the registry. Same knob, different base book.

    "fsent_utcsat_long": {
          "desc": "utcsat entry-1 (leg_no_entry) + LONGS enter at swing FS",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # exp_fs_directional_leg.py, both eras. dd_net pending measure.
          "pins": {"n": 525, "net": 465.0, "dd_net": 20.66,
                   "oos_n": 310, "oos_net": 238.76, "oos_dd_net": 11.88},
      },

    "fsent_utcsat_short": {
          "desc": "utcsat entry-1 (leg_no_entry) + SHORTS enter at swing FS",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # exp_fs_directional_leg.py, both eras. dd_net pending measure.
          "pins": {"n": 531, "net": 596.71, "dd_net": 17.6,
                    "oos_n": 311, "oos_net": 229.65, "oos_dd_net": 24.63},
      },
    "fsent_champ_trailhalf": {
        "desc": "CANDIDATE: fsent_champ_long + exp_trail_half=1. Multi check on 2026-10-06: OOS +287.0 / avgR 1.032 / PF 3.00 / DD 16.5 vs base +245.0 / 0.793 / 2.76 / 11.9. Lifts total and per-trade, at DD cost. NOT adopted - needs exp_port_differential parity + cohort autopsy first.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long",
                       "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 496, "net": 536.19, "dd_net": 31.68,
                 "oos_n": 282, "oos_net": 282.08, "oos_dd_net": 16.45},
    },
    "fsent_utcsat_trailhalf": {
        "desc": "CANDIDATE: fsent_utcsat_long + exp_trail_half=1. Repeats the fsent_champ_trailhalf lift (OOS +286.4 / avgR 1.034 / PF 3.00 / DD 16.5 vs base +244.2 / 0.793 / 2.75 / 11.9). NOT adopted.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "long",
                       "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 497, "net": 534.46, "dd_net": 31.29,
                 "oos_n": 281, "oos_net": 281.49, "oos_dd_net": 16.45},
    },

    "fsent_dirmatch_long": {
          "desc": "dirmatch multi + LONGS enter at swing FS",
                  "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "exp_require_dir_match": 1,
                       "window_end": "exit",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # Directional FS entry on the registry highest-OOS book.
          # exp_fs_directional_leg.py, both eras.
          "pins": None,

        # GRAVEYARD - proved look-ahead. Not a candidate, never a base.
        # Measured by exp_dirmatch_causality.py, not asserted.
        # LOOK-AHEAD, measured not asserted: exp_require_dir_match and its
        # companions read a swing field that is not settled at the entry bar.
        # exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which
        # adds the one missing check (has this swing confirmed by the entry bar)
        # and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to
        # +70.79; on fsent_dirmatch_short, the largest number in this repo, IS
        # +658.65 to +368.54. The edge was the unconfirmed label. Do not quote
        # these numbers and do not copy a base from them. The causal replacements
        # already exist as fsent_champ_long / fsent_champ_short.
        "status": "reference",
        "graveyard": "LOOK-AHEAD, measured not asserted: exp_require_dir_match and its companions read a swing field that is not settled at the entry bar. exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which adds the one missing check (has this swing confirmed by the entry bar) and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to +70.79; on fsent_dirmatch_short, the largest number in this repo, IS +658.65 to +368.54. The edge was the unconfirmed label. Do not quote these numbers and do not copy a base from them. The causal replacements already exist as fsent_champ_long / fsent_champ_short.",
        "graveyard_knobs": ['exp_require_dir_match'],
},

    "fsent_dirmatch_short": {
          "desc": "dirmatch multi + SHORTS enter at swing FS",
                  "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "exp_require_dir_match": 1,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # Directional FS entry on the registry highest-OOS book.
          # exp_fs_directional_leg.py, both eras.
          "pins": None,

        # GRAVEYARD - proved look-ahead. Not a candidate, never a base.
        # Measured by exp_dirmatch_causality.py, not asserted.
        # LOOK-AHEAD, measured not asserted: exp_require_dir_match and its
        # companions read a swing field that is not settled at the entry bar.
        # exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which
        # adds the one missing check (has this swing confirmed by the entry bar)
        # and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to
        # +70.79; on fsent_dirmatch_short, the largest number in this repo, IS
        # +658.65 to +368.54. The edge was the unconfirmed label. Do not quote
        # these numbers and do not copy a base from them. The causal replacements
        # already exist as fsent_champ_long / fsent_champ_short.
        "status": "reference",
        "graveyard": "LOOK-AHEAD, measured not asserted: exp_require_dir_match and its companions read a swing field that is not settled at the entry bar. exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which adds the one missing check (has this swing confirmed by the entry bar) and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to +70.79; on fsent_dirmatch_short, the largest number in this repo, IS +658.65 to +368.54. The edge was the unconfirmed label. Do not quote these numbers and do not copy a base from them. The causal replacements already exist as fsent_champ_long / fsent_champ_short.",
        "graveyard_knobs": ['exp_require_dir_match'],
},

    # ===== SERIAL SIGNAL BOOKS (max_positions=1) + the 40% win-rate arm =====
    # ===== SERIAL SIGNAL BOOKS (max_positions=1) + the 40% win-rate arm =====
    # The bare serial single book is LOSING out of sample: -16.3R OOS on
    # champion_single_sw10. One position at a time is the deployment shape here
    # because capital does not allow concurrent losers. Directional FS entry
    # turns that book positive in both eras. exp_fs_single.py, both eras.

    "fsent_sig_sw10_short": {
          "desc": "SERIAL signal book: one position at a time, SHORTS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short",
                       "max_positions": 1},
          "swing": "sw10",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 374, "net": 175.41, "dd_net": 16.620,
                   "oos_n": 239, "oos_net": 103.31, "oos_dd_net": 11.820},
      },

    "fsent_sig_sw10_long": {
          "desc": "SERIAL signal book: one position at a time, LONGS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "long",
                       "max_positions": 1},
          "swing": "sw10",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 353, "net": 121.23, "dd_net": 21.07,
                   "oos_n": 232, "oos_net": 74.15, "oos_dd_net": 13.33},
      },

    "fsent_sig_sw20_short": {
          "desc": "SERIAL signal book on the sw20 chain, SHORTS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short",
                       "max_positions": 1},
          "swing": "sw20",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 343, "net": 146.2, "dd_net": 30.8,
                   "oos_n": 203, "oos_net": 97.0, "oos_dd_net": 8.9},
      },

    "fsent_sig_sw20_short_wr": {
          "desc": "sw20 + SHORTS enter at swing FS - only >=40% win rate on the board",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short"},
          "swing": "sw20",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 343, "net": 146.2, "dd_net": 30.8, "win": 0.362,
                 "oos_n": 203, "oos_net": 97.0, "oos_dd_net": 8.9, "oos_win": 0.325},
      },
    # ===== SWING-SIZE EXIT AT FS (the owner proposal) =====
    # ===== SWING-SIZE EXIT AT FS (the owner proposal) =====
    # Enter at B2/flip as the book does; when the swing CONFIRMS, measure that
    # swing own leg |end_px - start_px| over ATR(20) and exit if it is small.
    # Both fields are settled at or before confirmed_at_idx and the FS bar has
    # closed, so this is knowable - unlike the same quantity read at the entry
    # bar, which is M2 and is closed as retrospective. exp_fs_small_swing.py.
    "fsent_sig_fs_mom": {
          "desc": "THE SIGNAL BOOK. One position at a time. Weekend + swingpause + shorts entering at the swing FS print + a momentum floor on the bias.",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_fs_entry_side": "short",
                       "exp_swingpause": 1,
                       "exp_skip_weekend": 1,
                       "exp_bias_momentum_min": 0.8,
                       "window_end": "exit"},
          "swing": "sw10",
          # Measured from the engine, both eras, by exp_pinrefresh.py.
          #
          # The pin this replaces read IS 285 / +208.16 and was WRONG - but the
          # params were not. That number is step 2 of _signal_combo.json, a
          # TWO-knob ladder: exp_fs_entry_side=short + exp_bias_momentum_min=0.8.
          # This book carries FOUR knobs - those two plus exp_swingpause=1 and
          # exp_skip_weekend=1, which that ladder never added. So the number
          # belonged to a different configuration and was copied here by
          # mistake. It is left in this comment rather than deleted, so that if
          # anyone finds +208.16 quoted as this book, this is where it came from
          # and why it is wrong.
          #
          # Which way the error ran is worth recording: the real book is BETTER
          # in sample (+262.29 against +208.16) and the OOS was never recorded
          # at all, so nothing downstream was harmed by believing the smaller
          # number. That is luck, not a property of the process - the identical
          # mistake in the other direction would have shipped an inflated book.
          "pins": {"n": 235, "net": 268.37, "dd_net": 8.96, "win": 0.426,
                   "oos_n": 153, "oos_net": 166.8, "oos_dd_net": 9.14,
                   "oos_win": 0.425},
      },
    "fsent_sig_full": {
          "desc": "Best exhaustive candidate on the one-position signal ladder: FS-short + momentum + no partial + trail skip + small-swing exit at FS + weekend skip.",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_fs_entry_side": "short",
                       "exp_bias_momentum_min": 0.8,
                       "exp_partial_r": 0.0,
                       "exp_trail_skip_n": 2,
                       "exp_fs_small_swing": 6.0,
                       "exp_skip_weekend": 1,
                       "window_end": "exit"},
          "swing": "sw10",
          "pins": {"n": 234, "net": 295.83, "dd_net": 10.78, "win": 0.44,
                   "oos_n": 152, "oos_net": 194.44, "oos_dd_net": 6.96, "oos_win": 0.477},
      },
    # ===== FS TWEAKS — registered as candidate books, measured 2026-10-06 =====
    # Same stack as fsent_sig_full (and its both-side mirror), one lever added
    # each time. Measured by _sig_fs_tweaks.py / _sig_fs_mirror.py, same
    # closed-trades basis as the pins. NOT adopted: the decay/trail-half cells
    # lift OOS R/trd and PF on ~half the trades, at the cost of total OOS net.
    # Family-level shape repeats on fsent_sig_fs_mom and fsent_sig_wk_pause_short.
    "fsent_sig_trail_delay1": {
        "desc": "fsent_sig_full + exp_trail_half=1 and exp_trail_delay_r=1.0. The one trail cell that lifts OOS R/trd (+1.46), by gating the ratchet and cutting n.",
        "engine": "patched",
        "params": { "max_positions": 1,
                   "mode": "atr_high",
                   "atr_high_thresh": 0.65,
                   "atr_low_thresh": 0.35,
                   "sl_buf_atr": 0.01,
                   "chop_thresh": 58.0,
                   "cooldown_bars": 8,
                   "max_consecutive_losses": 3,
                   "ext_stop_r": 3.0,
                   "exp_fs_entry_side": "short",
                   "exp_bias_momentum_min": 0.8,
                   "exp_partial_r": 0.0,
                   "exp_trail_skip_n": 2,
                   "exp_fs_small_swing": 6.0,
                   "exp_skip_weekend": 1,
                   "window_end": "exit",
                   "exp_trail_half": 1,
                   "exp_trail_delay_r": 1.0},
        "swing": "sw10",
        "pins": {"n": 199, "net": 418.51, "dd_net": 13.34, "win": 0.382,
                 "oos_n": 123, "oos_net": 182.01, "oos_dd_net": 7.54, "oos_win": 0.426},
    },
    "fsent_sig_decay_crossed": {
        "desc": "fsent_sig_full + P36 decay gate, mode 'crossed', thr 0.75, legs 4. Halves the book; OOS R/trd +1.91, PF 4.60, DD ~base — filter shape, half the trades.",
        "engine": "patched",
        "params": { "max_positions": 1,
                   "mode": "atr_high",
                   "atr_high_thresh": 0.65,
                   "atr_low_thresh": 0.35,
                   "sl_buf_atr": 0.01,
                   "chop_thresh": 58.0,
                   "cooldown_bars": 8,
                   "max_consecutive_losses": 3,
                   "ext_stop_r": 3.0,
                   "exp_fs_entry_side": "short",
                   "exp_bias_momentum_min": 0.8,
                   "exp_partial_r": 0.0,
                   "exp_trail_skip_n": 2,
                   "exp_fs_small_swing": 6.0,
                   "exp_skip_weekend": 1,
                   "window_end": "exit",
                   "exp_decay_mode": 4,
                   "exp_decay_thr": 0.75,
                   "exp_decay_legs": 4},
        "swing": "sw10",
        "pins": {"n": 104, "net": 195.59, "dd_net": 8.64, "win": 0.481,
                 "oos_n": 67, "oos_net": 130.28, "oos_dd_net": 7.39, "oos_win": 0.507},
    },
    "fsent_sig_half_crossed": {
        "desc": "fsent_sig_full + trail_half + decay_crossed. The sharpest shape: OOS avgR +2.27, PF 4.85, on n=62. NOT adopted — smallest sample of the three, OOS total well below base.",
        "engine": "patched",
        "params": { "max_positions": 1,
                   "mode": "atr_high",
                   "atr_high_thresh": 0.65,
                   "atr_low_thresh": 0.35,
                   "sl_buf_atr": 0.01,
                   "chop_thresh": 58.0,
                   "cooldown_bars": 8,
                   "max_consecutive_losses": 3,
                   "ext_stop_r": 3.0,
                   "exp_fs_entry_side": "short",
                   "exp_bias_momentum_min": 0.8,
                   "exp_partial_r": 0.0,
                   "exp_trail_skip_n": 2,
                   "exp_fs_small_swing": 6.0,
                   "exp_skip_weekend": 1,
                   "window_end": "exit",
                   "exp_trail_half": 1,
                   "exp_decay_mode": 4,
                   "exp_decay_thr": 0.75,
                   "exp_decay_legs": 4},
        "swing": "sw10",
        "pins": {"n": 97, "net": 340.9, "dd_net": 8.46, "win": 0.423,
                 "oos_n": 63, "oos_net": 142.09, "oos_dd_net": 7.26, "oos_win": 0.435},
    },
    "fsent_both_trail_half": {
        "desc": "fsent_sig_full stack with exp_fs_entry_side='both' + exp_trail_half. Best measured both-side tweak here, but OOS +96.9 on n=141 — the lane stays far below the short-only book. Keep as the ceiling on 'both'.",
        "engine": "patched",
        "params": { "max_positions": 1,
                   "mode": "atr_high",
                   "atr_high_thresh": 0.65,
                   "atr_low_thresh": 0.35,
                   "sl_buf_atr": 0.01,
                   "chop_thresh": 58.0,
                   "cooldown_bars": 8,
                   "max_consecutive_losses": 3,
                   "ext_stop_r": 3.0,
                   "exp_fs_entry_side": "both",
                   "exp_bias_momentum_min": 0.8,
                   "exp_partial_r": 0.0,
                   "exp_trail_skip_n": 2,
                   "exp_fs_small_swing": 6.0,
                   "exp_skip_weekend": 1,
                   "window_end": "exit",
                   "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 253, "net": 77.69, "dd_net": 31.43, "win": 0.296,
                 "oos_n": 142, "oos_net": 96.91, "oos_dd_net": 14.81, "oos_win": 0.34},
    },
    # ===== THE SIGNAL BOOK =====
    # ===== THE SIGNAL BOOK =====
    # One position at a time. weekend + swingpause + shorts entering at the swing
    # FS print. Both filters are period-level/structural, which is what survived
    # validation in signal/ANCHOR_BASIS_AUDIT.md; the per-trade indicators (chop15 band,
    # atr-ratio) were rejected there and are deliberately absent here.
    # Measured against the PURE BASELINE (same base knobs, zero filters), which
    # is OOS +41.1R - this book is what makes a one-position book viable.
    "fsent_sig_wk_pause_short": {
          "desc": "SIGNAL book: one position, weekend+pause, SHORTS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_skip_weekend": 1,
                       "exp_swingpause": 1,
                       "exp_fs_entry_side": "short",
                       "max_positions": 1},
          "swing": "sw10",
          # exp_fs_single.py / exp_fs_untested.py arm set, both eras.
          # peak concurrent positions verified = 1.
          "pins": {"n": 306, "net": 203.26, "dd_net": 10.6,
                   "oos_n": 180, "oos_net": 129.95, "oos_dd_net": 10.53},
      },
    "fsswing6_c": {
          "desc": "champion leg + exit at own-swing FS when its leg is under 6x ATR",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw10",
          # exp_fs_small_swing.py, both eras. Monotonic 3->6 ATR.
          "pins": {"n": 510, "net": 322.18, "dd_net": 41.77,
                   "oos_n": 290, "oos_net": 82.61, "oos_dd_net": 54.27},
      },
    # ===== SWING-SIZE EXIT AT FS, single plane =====
    # ===== SWING-SIZE EXIT AT FS, single plane =====
    # Enter at B2/flip as the book does; when the swing CONFIRMS, measure that
    # swing own leg |end_px - start_px| over ATR(20) and exit if it is small. Both
    # fields settle at or before confirmed_at_idx, so this is knowable at the FS
    # bar - unlike the same quantity read at the ENTRY bar, which is M2 and is
    # closed as retrospective. exp_fs_small_swing.py.
    "fsswing_sig_sw10": {
          "desc": "champion single sw10 + exit at FS when its swing leg is under 6x ATR",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw10",
          # Base params copied from the named single book verbatim.
          # exp_fs_small_swing.py, both eras.
          "pins": {"n": 404, "net": 42.54, "dd_net": 45.11, "win": 0.272,
                 "oos_n": 245, "oos_net": 11.21, "oos_dd_net": 34.62, "oos_win": 0.265},
      },
    "fsswing_sig_sw20": {
          "desc": "champion single sw20 + exit at FS when its swing leg is under 6x ATR",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw20",
          # Base params copied from the named single book verbatim.
          # exp_fs_small_swing.py, both eras.
          "pins": {"n": 382, "net": 99.19, "dd_net": 50.05, "win": 0.296,
                 "oos_n": 218, "oos_net": 0.42, "oos_dd_net": 35.97, "oos_win": 0.266},
      },
    "fsexit6_c": {
        "desc": "champion leg + exit at own-swing FS when it lands within 6h",
        "engine": "patched",
"params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                     "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                     "chop_thresh": 58.0, "cooldown_bars": 8,
                     "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                     "exp_partial_r": 0.0, "exp_mltf": True,
                     "exp_persist": 7, "window_end": "exit",
                     "pivot_rule": "leg",
                     "exit_fs_max_gap_h": 6.0},
        "swing": "sw10",
        # See the FS_EXIT ladder in exp_fs_exit.py.
        "pins": {"n": 516, "net": 310.62, "dd_net": 46.66,
                 "oos_n": 302, "oos_net": 75.7, "oos_dd_net": 45.81},
    },
    # ===== P36 DECAY GATE (engine knob, measured 2026-10-02 IS+OOS) =====
}
