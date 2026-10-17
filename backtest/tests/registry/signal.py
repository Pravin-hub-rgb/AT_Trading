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
                     "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                     "pivot_rule": "leg",
                     "exit_fs_max_gap_h": 4.0},
        "swing": "sw10",
        # See the FS_EXIT ladder in exp_fs_exit.py.
        "pins": {"n": 422, "net": 138.22,
                 "dd_net": 72.23, "oos_n": 254, "oos_net": -17.78, "oos_dd_net": 46.97},
    },
    # ===== MODE CENSUS SURVIVORS (2026-10-14, exp_mode_census.py) =====
    # exp_mode_census.py swept all 26 mode branches in unified.py across 5
    # books, 135 cells, 0 errors, and found a mode beating the shipped
    # atr_high in both eras on EVERY book. With 26 modes against 5 books a
    # winner per book is what chance produces, so the census promoted nothing
    # and pointed at exp_mode_stability.py instead. Only 2 of the 5 survived
    # that, and they are the 2 registered here.
    #
    # WHAT DID NOT SURVIVE, so it is not redone:
    #   garch on fsent_champ_long       +175.92 IS / +40.98 OOS - FAILED
    #   garch on fsent_champ_long_mcloff +171.56 IS / +36.04 OOS - FAILED
    #   session on fsent_champ_long_htffs IS -124.91        - FAILED
    # garch routes on chop_thresh (unified.py:1051-1053). Sweeping it on
    # fsent_champ_long: 42 -> -49.29 IS, 50 -> +83.19, 58 -> +175.92,
    # 66 -> +3.11, 74 -> -10.78. The gain exists at 58 and nowhere else, and
    # 58 is the value 86 of the shipped books already use - the knob measured
    # DEAD under atr_high in exp_knob_liveness.py. garch is the same dead
    # threshold reached by a different branch, not a new edge. Do not
    # re-register garch on the strength of its IS number.
    #
    # HOW TO READ THE TWO BELOW. session/union were not chosen by looking at
    # IS and then confirmed; they were the only two whose effect survived
    # having the thing that causes it removed.

    "fsent_champ_short_session": {
          "desc": "champ_short routed by SESSION (Asia B2 / London-NY FLIP) instead of atr_high",
          "engine": "patched",
          "params": {"mode": "session",
                       "sl_buf_atr": 0.01,
                       "cooldown_bars": 8,
                       "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # THE STRONGEST SURVIVOR. Session routing is Asia(0,3) -> B2,
          # London/NY(1,2) -> FLIP, at unified.py:1028-1031.
          #
          # STABILITY: the engine already contains the exact inverse routing,
          # session_flip (unified.py:1032-1035). Inverting the routing kills
          # the gain in BOTH eras - IS 589.36 -> 535.84, OOS 267.29 -> 149.01.
          # That is the point of registering this: the routing is the
          # mechanism, not a threshold that happens to sit at a good number.
          # session_flip is NOT registered - it is the control.
          #
          # OOS +267.29 against the shipped +195.01 is +72.28R on the same book,
          # and it is a genuine reroute - trade count 508 vs 569 IS, 294 vs 280
          # OOS - not the same trades relabelled.
          "pins": {"n": 501, "net": 582.58, "dd_net": 18.71, "wr_net": 0.377,
                  "gross_win": 0.403, "oos_n": 291, "oos_net": 269.46, "oos_dd_net": 18.41,
                  "oos_wr_net": 0.375, "oos_gross_win": 0.388, "n_all": 792,
                  "net_all": 852.04, "dd_net_all": 18.71},
          "pins_legacy": {"n": 508, "net": 589.36, "dd_net": 18.71, "oos_n": 294,
                         "oos_net": 267.29, "oos_dd_net": 19.46},
      },

    # fsent_champ_long_htf15_union WAS REGISTERED HERE AND WAS REMOVED AGAIN.
    # Do not put it back on the strength of its IS and OOS nets.
    #
    # It looked like a winner: IS 505.24 -> 575.97, OOS 254.81 -> 321.38, both
    # eras positive, and it was already past the stability harness as "SKIPPED,
    # nothing to sweep" rather than failed. The nets are real. The book is not.
    #
    # The census ranked modes on NET, and net pays for volume. union takes both
    # the B2 and the FLIP 1h window wherever either exists, so it simply takes
    # more trades. It did not get better - it got more:
    #                      IS trades   IS R/trade   OOS trades   OOS R/trade
    #   htf15 shipped            500        1.010          281          0.907
    #   + union                  786        0.733          451          0.713
    #   per-trade quality fell 27% in both eras while the count rose 57% and
    #   60%. Profit factor 3.13 -> 2.40. That is dilution, not edge.
    #
    # Year by year, which is where it shows (exp_mode_yearly.py):
    #              trades/yr   2020     2021     2022     2023
    #   htf15 shipped    136   164.44    99.41   109.87   131.51
    #   + union          214   141.25   223.53   198.91    12.28
    # 2023 paid 12.28R across a whole year. OOS trades per year went 140 -> 225.
    #
    # THE LESSON, because the mistake was in the selection rule and not in the
    # engine: a mode has to beat the shipped mode on net AND on R-per-trade AND
    # without adding trades. Under that rule union fails on both counts, and so
    # does every mode on 4 of the 5 census books. Re-run the census with the
    # three-part test before ranking anything again - see
    # exp_mode_strict.py.

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
          "pins": {"n": 487, "net": 459.41, "dd_net": 25.08, "wr_net": 0.382,
                  "gross_win": 0.427, "oos_n": 275, "oos_net": 221.05, "oos_dd_net": 10.16,
                  "oos_wr_net": 0.418, "oos_gross_win": 0.433, "n_all": 762,
                  "net_all": 680.46, "dd_net_all": 25.08},
          "pins_legacy": {"n": 497, "net": 466.92, "dd_net": 25.08, "oos_n": 281,
                         "oos_net": 215.32, "oos_dd_net": 11.2},
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
          "desc": "CANDIDATE, NOT ADOPTED - blocked on drawdown against the owner's 20R budget, not on the invented 11.88R gate (withdrawn 2026-10-08 as mine, not the framework's). fsent_champ_long with mode='atr_low' - the atr_high inversion: decisive windows when 15m bars are QUIET, not big. Only the mode changes; every other knob identical. This is the strongest of the four on the framework's own buckets: it WINS bucket 1 outright in both eras - IS 599t / +517.64R[as of 2026-10-15 (exp_repin_all.py, net lens)]/ expectancy 1.125 / PF 3.22 against the base 528t / +533.4R / 1.010 / 3.09, and OOS 261t / +187.96R/ 0.891 / 2.96 against 311t / +239.6R / 0.770 / 2.69 - on MORE trades than the base, so more evidence and not less. Its out-of-sample tail is also the healthiest in the set (top 5% contributes 71.2% against the base's 81.1%; removing the top 10% still leaves -4.6% against -11.7%; removing the top 5% leaves 26.3% against 16.3%) and its DD expansion is 0.51, i.e. half its out-of-sample drawdown is in-sample. It is blocked purely on bucket 2 and bucket 9: 28.9R max DD in sample against the owner's 20R budget, 82 trades to make the drawdown, 460 trades underwater against the base's 286, and a 16-trade losing streak against the base's 11. Its own threshold swept 0.20-0.60 and the OOS gain peaks sharply at 0.35 (+41.1R) and is NEGATIVE everywhere else - one point, not a region, which is exactly the grid-peak failure P69 warns about. This is the one candidate worth keeping open, and the open question is whether a 20R budget can stretch to 29R - the owner's call, not the registry's. See method/OWNER_SCORECARD_MODES.md.",
          "engine": "patched",
          "params": {"mode": "atr_low", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 599, "net": 517.64, "dd_net": 48.01, "wr_net": 0.396,
                  "gross_win": 0.424, "oos_n": 261, "oos_net": 187.96, "oos_dd_net": 14.47,
                  "oos_wr_net": 0.398, "oos_gross_win": 0.414, "n_all": 860,
                  "net_all": 705.6, "dd_net_all": 48.01},
          "pins_legacy": {"n": 612, "net": 515.49, "dd_net": 48.76, "oos_n": 269,
                         "oos_net": 192.64, "oos_dd_net": 14.16},
    },
    "fsent_champ_long_mode_fd": {
          "desc": "CANDIDATE, NOT ADOPTED. fsent_champ_long with mode='fd' - fractional-dimension regime: low FD=trend->flip, high FD=range->B2. Closest drawdown of the four (13.4R IS / 12.2R OOS) but still worse than base, and fails out of sample on both second lanes.",
          "engine": "patched",
          "params": {"mode": "fd", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 481, "net": 439.67, "dd_net": 25.94, "wr_net": 0.37,
                  "gross_win": 0.416, "oos_n": 270, "oos_net": 203.08, "oos_dd_net": 13.92,
                  "oos_wr_net": 0.396, "oos_gross_win": 0.411, "n_all": 751,
                  "net_all": 642.75, "dd_net_all": 25.94},
          "pins_legacy": {"n": 488, "net": 447.88, "dd_net": 25.94, "oos_n": 276,
                         "oos_net": 191.21, "oos_dd_net": 13.92},
    },
    "fsent_champ_long_mode_flip_quality": {
          "desc": "CANDIDATE, NOT ADOPTED - DISQUALIFIED 2026-10-08 as a regime proxy. fsent_champ_long with mode='flip_quality' - B2/flip by chop AND a HTF-magnitude floor, so it filters the chop branch. It held the base drawdown exactly (13.4R IS / 11.9R OOS) and was ahead on all three books of its family in the lane test (+4.8R / +4.8R / +54.0R), which is why it was the closest of the four. Period control then disqualified it: the mode is IN-SAMPLE INERT on all three books. In IS the arm and the base take the SAME trades - 0 new, 0 dropped on fsent_utcsat_long and fsent_champ_short, and on this book the entire +1.41R is ONE dropped trade - so all three IS cells are non-estimable and every R of the mode's effect is out of sample. Out of sample b after a half-year fixed effect is +0.2122 against an MDE of 0.8569: inside the noise floor, 96% of the raw gap explained by the calendar. The one powered cell is fsent_champ_short OOS (b +1.3963, t 2.016) - the FS-short mirror, a different architecture with 23.9R drawdown, and the source of the whole +54.01R - and one cell of one architecture on one era cannot carry the other five. The earlier 3-of-3 lane result was real and was not sufficient; being drawdown-neutral is not the same as being useful. Two corrections recorded on 2026-10-08: the 'fails on both second lanes (-7.0R, -4.1R)' sentence was measured on champion_multi_sw10/utcsat_multi_sw10, a DIFFERENT architecture (pivot_rule=origin, no FS side, no exp_mltf), and the first period-control harness labelled survivors as cohort=1, which produced a meaningless t of 7.672. Remains registered and pinned so the measurements are re-derivable. The branch also READS chop_thresh, which is not in this book's config, so it was never the base plus a mode string. See method/FLIP_QUALITY_PERIOD_CONTROL.md, method/MODE_CONFIRM2_RIGHT_LANES.md.",
          "engine": "patched",
          "params": {"mode": "flip_quality", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 478, "net": 454.16, "dd_net": 25.08, "wr_net": 0.379,
                  "gross_win": 0.425, "oos_n": 259, "oos_net": 190.92, "oos_dd_net": 10.16,
                  "oos_wr_net": 0.402, "oos_gross_win": 0.417, "n_all": 737,
                  "net_all": 645.07, "dd_net_all": 25.08},
          "pins_legacy": {"n": 488, "net": 461.66, "dd_net": 25.08, "oos_n": 265,
                         "oos_net": 186.82, "oos_dd_net": 11.2},
    },
    # fsent_sig_multi is the sig book's WHOLE filter set with max_positions 1 -> 0.
    # It is the only candidate in this file whose out-of-sample effect survives the
    # period control: 99% of the raw gap survives a half-year fixed effect in BOTH
    # eras, and it is ahead in 12 of 12 half-year cells. See
    # method/SIG_MULTI_STUDY.md for the full gates, and the caveat below.
    "fsent_champ_long_mcloff_htf15": {
          "desc": "CANDIDATE, NOT ADOPTED - the best NON-degenerate arm found, and the two findings that actually changed the picture, stacked. It is fsent_champ_long_mcloff (max_consecutive_losses=0) on the htf15 1h swing series. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 525t / +538.40R / DD 28.38R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 41.1%, OOS 295t / +272.92R / DD 11.05R / WR 38.1%. It beats the parent in BOTH eras by more than mcloff alone (+82.80R IS, +37.76R OOS) and beats mcloff in both eras as well (+49.59R IS, +6.44R OOS), for 1.00R of extra in-sample drawdown. ZERO negative half-years out of 12. WHY THIS IS THE RECOMMENDATION AND NOT htf15 OR htfesmcl4: it does not use exp_htf_fs_entry, so it keeps the flip/decisive/b2 regime buckets distinct and is NOT the degenerate all-fs_entered configuration that the completion sweep's highest arms all turn out to be. The 12-arm joint grid over max_consecutive_losses x HTF leg length x HTF FS entry produced a +1321.41R arm, and that arm collapses the regime distinction - see method/HTF_FS_ENTRY_REJECTED.md. This one reaches +616.17R while staying honest about what a regime is. PERIOD CONTROL, run on this exact combination on 2026-10-09: SURVIVES with b > 0 in 2 of 2 eras - b = +0.77 (t = 1.72, MDE 0.88) IS and b = +0.62 (t = 1.60, MDE 0.76) OOS, cluster bootstraps +0.80 and +0.64 - but it is UNDERPOWERED, and this is the honest cost of the extra swing. fsent_champ_long_mcloff on its own is the only arm in the family whose control is powered in BOTH eras, at t = 3.37 and t = 3.97. Adding the htf15 swing buys +49.59R IS and dilutes the cohort variance at the same time, so the recommendation on EVIDENCE remains mcloff and the recommendation on RETURN is this one. Still NOT adopted: no arm in the family has forward evidence, and 12 observations of a half-year table is not a guarantee. See method/RESEARCH_COMPLETE.md and method/GRID_PERIOD_AND_KNOB_GUARD.md. PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0115 in sample, p = 0.1445 out of sample, gap +82.80 IS and +37.76 OOS - significant in sample, NOT out of sample - the era that matters. Significance means this arm's choice of trades is unlikely to be a reshuffle of the parent's; it does NOT mean the book is statistically better in absolute terms, which the same audit shows it is not (the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades, and the corrected absolute null is M = 771.09R IS / 384.36R OOS against the 381.7 / 205.5 quoted in BASE_BOOK_NULL.md, which was measured on a different book). See method/NULL_AUDIT_P5.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "htf15",
          "pins": {"n": 525, "net": 538.4, "dd_net": 28.38, "wr_net": 0.408,
                  "gross_win": 0.451, "oos_n": 295, "oos_net": 272.92, "oos_dd_net": 11.05,
                  "oos_wr_net": 0.427, "oos_gross_win": 0.437, "n_all": 820,
                  "net_all": 811.32, "dd_net_all": 28.38},
          "pins_legacy": {"n": 535, "net": 539.77, "dd_net": 28.38, "win": 0.452,
                         "oos_n": 302, "oos_net": 270.17, "oos_dd_net": 11.05,
                         "oos_win": 0.434},
    },
    "fsent_champ_long_causalfloor": {
          "desc": "CANDIDATE, NOT ADOPTED. **The name is historical and wrong - this is NOT a causality fix, and nothing about it is a fix at all.** It is fsent_champ_long with one number changed: exp_window_floor_s, the wait between a window opening and the LTF entry being allowed, from the shipped 2700 seconds to 7200 seconds. That is the whole mechanism: a longer wait, not a corrected one. It came out of a sweep of that one parameter, 7200 was the best value found, and a value chosen by a sweep carries selection pressure - it was not derived from a rule.  IT WAS ORIGINALLY REGISTERED AS A CAUSALITY FIX AND THAT WAS WRONG. The first description claimed the shipped gate let an LTF entry run up to 900 seconds before its 1h window candle closed, and that this book removed those trades. That claim was withdrawn on 2026-10-10 - the six trades it pointed at sit exactly on the boundary, where the 15m bar closes at the same instant the 1h window closes, which is legal. method/WINDOW_FLOOR_LEAK.md, which carried the finding, was deleted with it; this text is the correction. Read method/WITHDRAWN_WINDOW_LOOKAHEAD.md before believing anything here about causality.  MEASURED against the parent (528 / +533.37 / 13.42 IS, 311 / +239.59 / 11.88 OOS): IS 513 / +529.84R / DD 13.62R / WR 39.6%, OOS 308 / +248.90R / DD 11.88R / WR 38.0%. It earns LESS in sample and about the same out of sample - it gives up trades to buy a smaller drawdown, and on this evidence it does not buy enough.  The book does have ZERO negative half-years where the parent has one, but that is NOT a regime discovery and must not be read as one: across 155 half-year cells the 6 negative ones are indistinguishable from the 149 positive ones in loss concentration (35.2% vs 36.1%) and losing-streak length (8.3 vs 8.1). The same expectancy is landing slightly red, not a condition that can be filtered. That finding lives in method/PERIOD_2025H1_WHAT_HAPPENED.md.  FOR THE RECORD, since it bounds every causality claim in this family: a slack audit on 2026-10-10 (exp_window_slack_audit.py, 29 books, both eras, 22154 trades) measured the gap between each trade's decision instant and the close of its 1h window candle. The gate at unified.py:1034 is permissive by 900 seconds in principle, but ZERO trades anywhere in the family landed in that band - the distribution is 21992 trades at 900s or more of clearance, 147 exactly on the boundary, and none between. The shipping book is clean at 311 of 311. The 15 apparent violations are all fsent_champ_long_mode_union and are a REPORTING defect in that book's window_start field, not lookahead - see method/WINDOW_SLACK_AUDIT.md.  PAIRED PERMUTATION vs the shipping book (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.7256 in sample, p = 0.0230 out of sample, gap -3.52 IS / +9.31 OOS - out of sample only, and negative in sample. Significance here means this arm's choice of trades is unlikely to be a reshuffle of the parent's. It does NOT mean the book is better in absolute terms; the same audit shows it is not. See method/NULL_AUDIT_P5.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_window_floor_s": 7200},
          "swing": "sw10",
          "pins": {"n": 475, "net": 458.55, "dd_net": 24.47, "wr_net": 0.377,
                  "gross_win": 0.423, "oos_n": 270, "oos_net": 220.15, "oos_dd_net": 10.16,
                  "oos_wr_net": 0.419, "oos_gross_win": 0.433, "n_all": 745,
                  "net_all": 678.7, "dd_net_all": 24.47},
          "pins_legacy": {"n": 483, "net": 466.98, "dd_net": 24.47, "win": 0.429,
                         "oos_n": 277, "oos_net": 216.05, "oos_dd_net": 11.2,
                         "oos_win": 0.43},
    },
    "fsent_champ_long_mode_chop": {
          "desc": "REGISTERED FOR COMPLETENESS, NOT A CANDIDATE - and the interesting thing about it is how close it is to doing nothing. mode='chop' instead of mode='atr_high': the regime classifier that decides whether a bar belongs to the decisive or the flip bucket now reads a chop threshold (chop_thresh=58.0) instead of an ATR percentile band. EVERY ONE of the other 31 fsent books is mode='atr_high', so this axis had never been registered anywhere in the family and the 2026-10-09 HTF-FS rejection only ever spoke to the ATR classifier. MEASURED in sample it is the shipping book exactly: 528 / +533.37 / DD 13.42, identical n, net and drawdown to fsent_champ_long. Out of sample it diverges slightly - 294 / +244.45 / DD 11.88 against the parent's 311 / +239.59 / 11.88 - so the two classifiers agree on every bar of the in-sample era and part company on 17 trades out of sample. CONCLUSION WORTH KEEPING: the regime classifier is NOT a live axis on this book. Swapping ATR for chop moves the number by less than half a percent of the net, and in sample not at all, so no result in this family should be attributed to the classifier rather than to the things that actually move it. Registered because an axis that was never measured should not stay that way, and because 'we never tested the chop classifier' is exactly the sentence that let the 2026-09 HTF-FS test be read as a general result. PAIRED PERMUTATION vs the shipping book (exp_null_audit.py, 4000 draws, seed 20261010): p = 1.0000 in sample, p = 0.7603 out of sample, gap +0.00R IS and +4.86R OOS. p = 1.0000 is not a rounding curiosity and is worth reading carefully: the in-sample trade list is BYTE-IDENTICAL to the shipping book's, so the permutation is comparing the parent against itself and 1.0000 is the correct answer rather than a null result. It is the precise form of the claim above - the chop classifier and the ATR classifier select the same bars on every in-sample bar, so this is not a small effect, it is no effect at all on half the data.",
          "engine": "patched",
          "params": {"mode": "chop", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 485, "net": 455.08, "dd_net": 25.08, "wr_net": 0.379,
                  "gross_win": 0.425, "oos_n": 259, "oos_net": 190.92, "oos_dd_net": 10.16,
                  "oos_wr_net": 0.402, "oos_gross_win": 0.417, "n_all": 744, "net_all": 646,
                  "dd_net_all": 25.08},
          "pins_legacy": {"n": 495, "net": 462.58, "dd_net": 25.08, "win": 0.43, "oos_n": 265,
                         "oos_net": 186.82, "oos_dd_net": 11.2, "oos_win": 0.411},
    },
    "fsent_champ_long_htffs": {
          "desc": "CANDIDATE, NOT ADOPTED - the strongest arm in this family on the owner's own rule, and the first one that adds return without adding a negative half-year. ONE parameter from the shipping book: exp_htf_fs_entry='flip', so the HTF flip-bucket window opens on the swing's FS print instead of on the break, while the decisive and b2 buckets keep their breaks. That is the selective form of the arm rejected on 2026-10-09 - 'all' was rejected partly because it collapsed flip/decisive/b2 into one fs_both set and the book stopped distinguishing regimes; this keeps two of the three intact. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 751t / +756.98R / DD 22.45R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 42.3%, OOS 388t / +313.35R / DD 14.74R / WR 36.9%. That is +364.57R in sample and +60.84R out of sample on 242 more trades. THE OWNER'S RULE: drawdown 19.78R is inside the 29R budget, and the negative half-year count is UNCHANGED at 1 - this arm does not bring back the 2025-H1 cell that htf_fs='all' re-broke, which is the specific failure that sank the earlier test. PERIOD CONTROL PASSES BOTH WAYS: with a calendar-year fixed effect b = +1.34 at t = +3.24, and with the stricter half-year fixed effect b = +1.40 at t = +3.40, better in 5 of 6 years. It is also the largest gain the half-year test has ever survived in this family. CAUSALITY IS CLEAN, measured in HTF_FS_ENTRY_REJECTED.md: window_start minus its own FS print is exactly 0.0h at min, median and max in both eras, and zero entries precede their window_start - an FS-anchored window opens precisely at the print, not before it. WHAT IT COSTS: the same objection that applies to every FS-entered window applies here - 95% of the gain sits in 197 windows the book was not trading before, trades per window roughly doubles, and the drawdown goes from 13.42R to 19.78R. The return is real and survives a period control, but it is bought with breadth rather than with a better read of the existing windows, and it is bought with 46% more drawdown than the parent. Nothing is adopted: the 2021-22 era is reused old data, not a holdout. PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0272 in sample, p = 0.5956 out of sample, gap +364.57R IS and +60.84R OOS - significant IN SAMPLE ONLY. The in-sample result is the strongest of its shape in this family and the out-of-sample one is not distinguishable from a reshuffle of the parent. So the honest ranking is unchanged by this arm: fsent_champ_long_mcloff remains the only book that clears in BOTH eras (0.0312 / 0.0117), and htf15_htffs' in-sample p of 0.0105 is the single lowest in-sample figure measured anywhere in the family paired with an out-of-sample figure of 0.4904. That pattern - very strong in sample, flat out of it - is exactly what the forward window exists to distinguish, and it is the reason +364R is not a recommendation.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_htf_fs_entry": "flip"},
          "swing": "sw10",
          "pins": {"n": 751, "net": 756.98, "dd_net": 22.45, "wr_net": 0.397,
                  "gross_win": 0.426, "oos_n": 388, "oos_net": 313.35, "oos_dd_net": 14.74,
                  "oos_wr_net": 0.381, "oos_gross_win": 0.394, "n_all": 1139,
                  "net_all": 1070.33, "dd_net_all": 22.45},
          "pins_legacy": {"n": 754, "net": 757.99, "dd_net": 22.45, "win": 0.426,
                         "oos_n": 389, "oos_net": 313.35, "oos_dd_net": 14.74,
                         "oos_win": 0.396},
    },
    "fsent_champ_long_htf15_htffs": {
          "desc": "CANDIDATE, NOT ADOPTED - FAILS THE DRAWDOWN BUDGET, and is registered with that stated first because it is the arm that looks best on a net column and is disqualified by a single number. fsent_champ_long_htf15 with exp_htf_fs_entry='flip'. MEASURED: IS 754t / +764.85R / DD 29.76R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 42.8%, OOS 395t / +346.08R / DD 14.74R / WR 37.9%. WHY IT IS NOT THE PICK: in-sample drawdown 29.62R is OVER the owner's 29R ceiling, before any consideration of the return. It also re-creates a negative half-year that its own parent does not have (htf15 has 0, this has 1), so it fails the zero-negative rule twice over. The period control passes - b = +1.05 at t = +3.29 on the half-year fixed effect, better in 5 of 6 years - so the gain itself is not a period artifact; it is the risk it carries that disqualifies it. Registered because it is the highest in-sample net measured anywhere in the fsent family, +925.79R, and burying the number that beats every other one while omitting the ceiling it breaches is the failure mode this family has been guarding against all cycle. PAIRED PERMUTATION vs the shipping book (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0105 in sample, p = 0.4904 out of sample, gap +392.43R IS and +64.58R OOS. THE STRONGEST IN-SAMPLE RESULT IN THE ENTIRE FAMILY, and not significant out of sample. Stating that pair next to each other is the point: a p of 0.0105 on its own is the number a person would quote, and the 0.4904 beside it is the number that decides. It is disqualified on the drawdown ceiling before either of them is consulted, but if that ceiling were lifted it would still be an in-sample-only result.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_htf_fs_entry": "flip"},
          "swing": "htf15",
          "pins": {"n": 754, "net": 764.85, "dd_net": 29.76, "wr_net": 0.398,
                  "gross_win": 0.428, "oos_n": 395, "oos_net": 346.08, "oos_dd_net": 14.74,
                  "oos_wr_net": 0.395, "oos_gross_win": 0.408, "n_all": 1149,
                  "net_all": 1110.92, "dd_net_all": 29.76},
          "pins_legacy": {"n": 756, "net": 765.86, "dd_net": 29.76, "win": 0.429,
                         "oos_n": 396, "oos_net": 346.07, "oos_dd_net": 14.74,
                         "oos_win": 0.409},
    },
    "fsent_sig_multi_htffs": {
          "desc": "CANDIDATE, NOT ADOPTED - the best risk profile of the three FS-entered arms and it still fails the owner's rule on the negative cell. fsent_sig_multi with exp_htf_fs_entry='flip'. MEASURED: IS 415t / +505.72R / DD 19.40R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 45.2%, OOS 224t / +201.65R / DD 7.33R / WR 46.8%. Out-of-sample drawdown 7.99R and win rate 46.8% are the best numbers on this entry anywhere in the family, and the period control is positive (b = +0.42 at t = +1.81 half-year, better in 3 of 6 years) though the weakest of the three. WHY IT IS NOT THE PICK: it adds a negative half-year that sig_multi does not have - sig_multi is one of only two books in this family with ZERO negative cells, and this arm gives that up. Trading the single best-behaved shape in the family for a wider one is a bad exchange at this ratio, and the owner does not trade there. Registered with that named, because the out-of-sample numbers on it are the best in the family and the reason they are not adopted is not that they are bad - it is that the rule they break is the one the book was chosen for. PAIRED PERMUTATION vs the shipping book (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.5091 in sample, p = 0.9708 out of sample, gap +132.95R IS and -5.11R OOS - NOT significant in either era, and the out-of-sample gap is NEGATIVE. Worth being blunt about the ordering here, because the risk numbers point the other way: this arm has the best out-of-sample drawdown (7.99R) and the best out-of-sample win rate (46.8%) anywhere in the family, and it is the one whose edge is least distinguishable from its parent. Good risk profile is not evidence of edge, and a book can be quietly pleasant to hold and still be indistinguishable from reshuffling its parent's trades.",
          "engine": "patched",
          "params": {'mode': 'atr_high', 'atr_high_thresh': 0.65, 'atr_low_thresh': 0.35, 'sl_buf_atr': 0.01, 'chop_thresh': 58.0, 'cooldown_bars': 8, 'max_consecutive_losses': 3, 'max_positions': 0, 'ext_stop_r': 3.0, 'exp_partial_r': 0.0, 'exp_fs_entry_side': 'short', 'exp_bias_momentum_min': 0.8, 'exp_trail_skip_n': 2, 'exp_fs_small_swing': 6.0, 'exp_skip_weekend': 1, 'window_end': 'exit', 'exp_htf_fs_entry': 'flip'},
          "swing": "sw10",
          "pins": {"n": 415, "net": 505.72, "dd_net": 19.4, "wr_net": 0.439,
                  "gross_win": 0.451, "oos_n": 224, "oos_net": 201.65, "oos_dd_net": 7.33,
                  "oos_wr_net": 0.464, "oos_gross_win": 0.469, "n_all": 639,
                  "net_all": 707.37, "dd_net_all": 19.4},
          "pins_legacy": {"n": 417, "net": 511.52, "dd_net": 19.4, "win": 0.451, "oos_n": 225,
                         "oos_net": 197.73, "oos_dd_net": 8.98, "oos_win": 0.46},
    },
    "fsent_sig_multi_acc": {
          "desc": "CANDIDATE, NOT ADOPTED - and the name is the point. This book was found BY ACCIDENT while testing a lean max_positions=1 serial base: the owner asked for a base with very few filters to test hypotheses on, ten knobs were censused, and exp_mltf=1 was the only one that improved both eras. It was registered under the serial framing until the concurrency was checked, at which point it was found to run UP TO 7 SIMULTANEOUS POSITIONS. It is a multi book and the _acc suffix keeps that provenance visible so nobody later reads it as a serial finding. NOT A DISCOVERY: unified.py:41 already documents exp_mltf as the entire multi edge ('With the gate on, the same config is +137.72R IS but -13.26R OOS over 230 trades. Turning it off gives +325.78R IS / +70.15R OOS'). What was added here is a confirmation that it also works on a thin base, and the note below that the sweep almost produced a false serial result. max_positions IS INERT WHEN exp_mltf IS ON - measured byte-identical, same trade-set sha ad4399fcf1 IS and bc92bc0329 OOS at max_positions 1 and at 0, with 7 concurrent in sample and 5 out of sample at BOTH settings. So the value is written as 0 to match observed behaviour rather than 1 to match the base it was derived from. That is the same class of finding as chop_thresh being inert under mode=atr_high: a config key that states an intention the code does not carry out. THIN BASE - it is fsent_sig_sw10_short with exp_mltf and NOTHING else, so it lacks all five filters its siblings carry (exp_bias_momentum_min 0.8, exp_fs_small_swing 6.0, exp_skip_weekend 1, exp_trail_skip_n 2, and htffs also exp_htf_fs_entry flip). MEASURED on the registry net lens: IS 472t / +441.93R / DD 12.67R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 41.3%, OOS 301t / +226.33R / DD 12.17R / WR 40.7%. AGAINST ITS SIBLINGS, NOT A CLEAN WIN, and the awkward parts are recorded rather than buried. vs fsent_sig_multi: better in both nets (+75.41R IS, +38.14R OOS) and better IS drawdown (12.67 against 13.43), but WORSE out-of-sample drawdown by 4.57R (12.18 against 7.61) and a lower net win rate (0.386 against 0.445). vs fsent_sig_multi_htffs: better out of sample (+23.18R) but 63.15R WORSE in sample. Ranked across the 42 exp_mltf multi books: IS net 21st, OOS net 11th, IS drawdown 3rd of 42 - the best in-sample drawdown in that set - and OOS drawdown 11th. THE ONE THING IT IS BEST AT: it is the only arm in the entire ten-knob census that REPAIRS a negative half-year instead of adding one - 2022-H2 goes -2.94R to +16.94R out of sample - and it posts zero negative half-years in both eras (8 of 8 IS, 4 of 4 OOS) while its own parent posts one. TAIL DEPENDENCE IS BETTER THAN THE PARENT'S, which is the opposite of every other candidate in this series: removing the ten largest out-of-sample trades leaves the parent at 9.39R, 8% of itself, and this at 104.22R, 47% of the ratio. THE ONE AXIS THAT WORSENS: in-sample max losing streak 9 to 12, out-of-sample unchanged at 11. WHY IT IS NOT THE PICK: the serial gate it was supposed to be is inoperative, the family already has two multi books with more filters on it, and its case rests on breadth that the siblings already have. Registered because the thin-base confirmation is a real measurement and because the sweep that produced it is worth keeping.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "chop_thresh": 58.0,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 7.5,
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          "pins": {"n": 472, "net": 441.93, "dd_net": 12.67, "wr_net": 0.386,
                  "gross_win": 0.413, "oos_n": 301, "oos_net": 226.33, "oos_dd_net": 12.17,
                  "oos_wr_net": 0.399, "oos_gross_win": 0.412, "n_all": 773,
                  "net_all": 668.27, "dd_net_all": 12.67},
          "pins_legacy": {"n": 477, "net": 448.37, "dd_net": 12.67, "win": 0.386,
                         "oos_n": 305, "oos_net": 220.91, "oos_dd_net": 12.18,
                         "oos_win": 0.393},
    },
    "fsent_champ_long_mcloff": {
          "desc": "CANDIDATE, NOT ADOPTED - and the best-EVIDENCED one in the registry. It changes ONE INTEGER: max_consecutive_losses from 3 to 0, which turns the loss-run cutoff OFF. The autopsy of the parent's negative half-year found 2025-H1 was not a disaster but a coin flip that landed red: 60 trades, net -0.69R, mean -0.011R per trade, 20 winners making +29.6R against 40 losers making -30.3R. In that exact situation the cutoff is not protecting the book, it is cutting winners - it stops the book right before the recovery trade that follows every streak. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 524t / +502.69R / DD 23.30R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 39.7%, OOS 293t / +216.03R / DD 11.05R / WR 37.1%. IT DOMINATES THE PARENT ON RETURN IN BOTH ERAS (+33.21R IS, +31.32R OOS) on 47 and 26 MORE trades, for 1.71R and 2.28R of extra drawdown. ZERO negative half-years out of 12. PERIOD CONTROL IS THE REASON TO TRUST IT - this is the only arm in the whole family whose effect is SIGN HOLDS and POWERED in BOTH eras: b = +1.21 (t = 3.37, MDE 0.70) IS and b = +1.86 (t = 3.97, MDE 0.92) OOS, cluster-bootstrap b_boot +1.28 and +1.92. Compare fsent_champ_long_htf15 (underpowered), fsent_champ_long_biasmom05 (b NEGATIVE and significant at t = -9.63 OOS) and htf_fs=all (underpowered). Still NOT adopted: the period control compares this arm to champ_long, NOT to absolute zero, and a book that is meaningfully better than its parent can still be negative in some unseen half-year. The cutoff also has a real purpose under position sizing, which is a risk decision and not a signal decision. Forward evidence does not exist for it yet. See method/MAXCONSEC_LOSSES_FINDING.md. PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0312 in sample, p = 0.0117 out of sample, gap +33.22 IS and +31.32 OOS - the only book in the family significant in BOTH eras. Significance means this arm's choice of trades is unlikely to be a reshuffle of the parent's; it does NOT mean the book is statistically better in absolute terms, which the same audit shows it is not (the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades, and the corrected absolute null is M = 771.09R IS / 384.36R OOS against the 381.7 / 205.5 quoted in BASE_BOOK_NULL.md, which was measured on a different book). See method/NULL_AUDIT_P5.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 524, "net": 502.69, "dd_net": 23.3, "wr_net": 0.395,
                  "gross_win": 0.437, "oos_n": 293, "oos_net": 216.03, "oos_dd_net": 11.05,
                  "oos_wr_net": 0.41, "oos_gross_win": 0.423, "n_all": 817,
                  "net_all": 718.72, "dd_net_all": 23.3},
          "pins_legacy": {"n": 533, "net": 504.12, "dd_net": 23.3, "win": 0.439, "oos_n": 300,
                         "oos_net": 213.27, "oos_dd_net": 11.05, "oos_win": 0.42},
    },
    "fsent_champ_long_htfesmcl4": {
          "desc": "CANDIDATE, NOT ADOPTED - the largest-return arm measured in this family, and registered because the owner asked for every arm to be visible rather than pre-filtered. It stacks the HTF-side FS entry (exp_htf_fs_entry=all) with max_consecutive_losses=4, which is the one setting that clears the 2022-H2 cell that the FS entry alone re-broke. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 762t / +771.87R / DD 20.02R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 43.0%, OOS 425t / +339.08R / DD 15.04R / WR 37.8%. ZERO negative half-years out of 12. THREE REASONS IT IS NOT THE RECOMMENDATION DESPITE THE NET. (1) In-sample drawdown 27.74R is at the owner's 29R budget ceiling, against 15.13R for fsent_champ_long_mcloff on less than half the return. (2) PERIOD CONTROL IS UNDERPOWERED OUT OF SAMPLE - b = +0.027 with t = 0.05 and MDE 1.16, i.e. the out-of-sample effect is indistinguishable from nothing, and the cluster bootstrap goes NEGATIVE at -0.03. (3) The FS entry collapses the flip/decisive/b2 regime buckets into one fs_entered set, so this arm stops distinguishing regimes - see method/HTF_FS_ENTRY_REJECTED.md. It buys +384R of in-sample return mostly by admitting 528 new trades rather than by improving the ones it had. Registered as the high-return end of the range so the owner can see what the ceiling costs. PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0285 in sample, p = 0.5311 out of sample, gap +384.44 IS and +86.63 OOS - significant in sample, NOT out of sample. Significance means this arm's choice of trades is unlikely to be a reshuffle of the parent's; it does NOT mean the book is statistically better in absolute terms, which the same audit shows it is not (the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades, and the corrected absolute null is M = 771.09R IS / 384.36R OOS against the 381.7 / 205.5 quoted in BASE_BOOK_NULL.md, which was measured on a different book). See method/NULL_AUDIT_P5.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 4,
                       "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_htf_fs_entry": "all"},
          "swing": "sw10",
          "pins": {"n": 762, "net": 771.87, "dd_net": 20.02, "wr_net": 0.391,
                  "gross_win": 0.419, "oos_n": 425, "oos_net": 339.08, "oos_dd_net": 15.04,
                  "oos_wr_net": 0.381, "oos_gross_win": 0.393, "n_all": 1187,
                  "net_all": 1110.95, "dd_net_all": 20.02},
          "pins_legacy": {"n": 763, "net": 770.53, "dd_net": 20.02, "win": 0.417,
                         "oos_n": 425, "oos_net": 339.08, "oos_dd_net": 15.04,
                         "oos_win": 0.393},
    },
    "fsent_champ_long_biasmom05": {
          "desc": "CANDIDATE, NOT ADOPTED - the HTF-side sibling of fsent_champ_long_htf15, and the one that fixes the negative half-year WITHOUT adding drawdown. Where htf15 lengthens the 1h leg, this arms the other HTF knob: exp_bias_momentum_min=0.5, a floor on the RATIO of this HTF leg's magnitude to the previous one, so the book only takes entries while the 1h leg is growing rather than shrinking. It is the closest existing knob to 'the HTF window opens on strength' - it is literally the 1h leg's own measure deciding whether its window counts. MEASURED against the parent 528 / +533.37 / 13.42 IS and 311 / +239.59 / 11.88 OOS: IS 456t / +459.33R / DD 22.78R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 39.5%, OOS 251t / +182.78R / DD 7.87R / WR 37.6%. THE POINT OF THIS BOOK IS ITS DRAWDOWN: in-sample max DD is 13.42R, EXACTLY the parent's, and out-of-sample is 13.47R against the parent's 11.88R - a 1.6R cost. Every other arm that removes the negative half-year pays for it in drawdown; this one does not. It costs return instead: -31.9R IS and -22.5R OOS, on 40 and 24 fewer trades. It is the low-drawdown branch of the owner's rule, against htf15's high-return branch (IS DD 17.28R, OOS 16.86R, but IS +567.57R / OOS +254.88R). Both are registered so the choice is visible rather than averaged. ZERO negative half-years out of 12, same as htf15. NOTE: this knob is ON the sig books at 0.8 and OFF on the champ books, and 0.8 was chosen there - see fsent_sig_multi. It was never swept on the champ architecture, which is why 0.5 and 1.0 were only measured here for the first time. Still NOT adopted: no period control has been run on this arm, the negative-cell removal has not been shown to survive a half-year fixed effect, and the OOS window is 2021-22, which is not a holdout - see method/OOS_IS_NOT_A_HOLDOUT.md. See method/HTF_SWEEP_OWNER_RULE.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_bias_momentum_min": 0.5},
          "swing": "sw10",
          "pins": {"n": 456, "net": 459.33, "dd_net": 22.78, "wr_net": 0.39,
                  "gross_win": 0.43, "oos_n": 251, "oos_net": 182.78, "oos_dd_net": 7.87,
                  "oos_wr_net": 0.422, "oos_gross_win": 0.438, "n_all": 707,
                  "net_all": 642.11, "dd_net_all": 22.78},
          "pins_legacy": {"n": 462, "net": 460.72, "dd_net": 22.78, "win": 0.433,
                         "oos_n": 255, "oos_net": 182.27, "oos_dd_net": 8.91,
                         "oos_win": 0.439},
    },
    "fsent_champ_long_htf15": {
          "desc": "CANDIDATE, NOT ADOPTED - the only arm found so far that fixes the shipping book's one negative half-year WITHOUT losing return, and it does so by moving a knob almost nobody has touched: the HTF swing length. THIS IS THE ONE FROM THE OWNER'S OWN RULE. Asked on 2026-10-09 for something that never goes negative - 'kabhi negative nahi hona chahiye' - the sweep of the HTF plane (1h swings, min_bars 10 -> 3..40) found that fsent_champ_long's single negative half-year, 2025-H1 at -0.7R, disappears at min_bars 13 and the net RISES from +773.0R to +796.5R (14) and +822.4R (15). MEASURED: IS 490t / +502.76R / DD 26.26R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 41.2%, OOS 274t / +256.61R / DD 10.32R / WR 37.1%. Against the parent that is +34.2R IS and +15.3R OOS on 8 and 31 fewer trades. WHY THIS IS NOT A GRID PEAK: the region around it is a genuine plateau, not a spike. min_bars 12 gives +783.5R but still 1 negative cell; 13 gives +787.6R with 0; 14 +796.5R with 0; 15 +822.4R with 0; 16 +746.1R with 0; 18 falls back to +708.7R with 1 negative again. By contrast min_bars 30 posts the single best number in the whole sweep at +847.3R with 0 negative - and is a SPIKE: 24 gives +645.4R with 2 negatives, 28 gives +659.6R with 2, 32 gives +696.3R with 0, 34 gives +562.5R. A 200R peak with a 60R trough either side is not an edge, so 30 is rejected and 15 is kept. WHAT CHANGED MECHANICALLY: the HTF plane is engine slot 2 and its swing series feeds the leg ratio, the bias-momentum breaks, the bias flips and _sw_ts_dir_mag, which is the flip/decisive classification every trade is tagged with. A longer 1h leg means fewer, larger HTF windows - 1601 swings at min_bars 10 down to 1479 at 15 - so the regime the router sees is coarser and it sits on fewer regime flips. That is why it is a genuinely different book rather than a re-tuned one. NOTE ON REGISTRATION: the HTF swing length is NOT an engine parameter, it is the registry's `swing` FIELD selecting a precomputed series, so this book needs the `htf15` series added to run_experiment.get_data - it is there, built at min_bars=15 on the 1h flow candles. A book that wanted a different HTF length would need its own series there, not a params edit. STILL NOT ADOPTED: period control gives b=+0.5681 IS and +0.3723 OOS, both positive with 97-98% of the raw gap surviving the half-year fixed effect, so it is not a regime proxy - but both cells are UNDERPOWERED against their own MDEs (1.0372 and 0.8050), so the magnitude is not established. In-sample drawdown rises 13.42R -> 17.28R and OOS 11.88R -> 16.86R, which fits the owner's 29R budget but is a real cost. And the OOS window is 2021-22, which is not a holdout - see method/OOS_IS_NOT_A_HOLDOUT.md. See method/HTF_SWEEP_OWNER_RULE.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long"},
          "swing": "htf15",
          "pins": {"n": 490, "net": 502.76, "dd_net": 26.26, "wr_net": 0.396,
                  "gross_win": 0.445, "oos_n": 274, "oos_net": 256.61, "oos_dd_net": 10.32,
                  "oos_wr_net": 0.423, "oos_gross_win": 0.434, "n_all": 764,
                  "net_all": 759.37, "dd_net_all": 26.26},
          "pins_legacy": {"n": 500, "net": 505.24, "dd_net": 26.26, "win": 0.446,
                         "oos_n": 281, "oos_net": 254.81, "oos_dd_net": 11.28,
                         "oos_win": 0.434},
    },
    "fsent_champ_long_tskip4": {
          "desc": "CANDIDATE, NOT ADOPTED - fsent_champ_long with exp_trail_skip_n=4, and the first result in this repo whose edge was CONFIRMED BY MECHANISM rather than by a net that survived OOS. exp_trail_skip_n drops the first N trailing-stop events outright (unified.py:1493, _trail_skip_rem -= 1; _tr_ok = False). WHAT IT ACTUALLY DOES, and this is the part worth reading: it does NOT improve exits on the same trades, it CONVERTS trail exits into stop exits. On the parent, 497 of 497 trades exit on the trail and ZERO hit the stop; at skip_n=5 it inverts to 185 trail and 244 SL. So the knob is turning trailing stops off for the first few moves, and positions that would have closed early at a small profit instead ride until the stop. EVERY one of those converted trades exits at exactly -1.000R - median and 10th percentile identical - so they are ordinary losses, not oversized ones, and they are the same weak trades the trail was closing for scraps. THE PURGE TEST IS WHY THIS IS DIFFERENT FROM THE FOUR HYPOTHESES THAT DIED BEFORE IT. At the pin there is nothing to purge, because almost nothing exits on the stop. Above skip_n=4 the stop population is large, and removing every stop-exit trade RAISES the net on all three books tested (+616 -> +860 on long, +724 -> +959 on htf15, +1505 -> +1834 on htffs). A right-tail bet loses exactly that way, because its gain lives in the trades the filter removes. Here the survivors go from -0.20 to +2.31 median R. That is selection, not variance. MEASURED, on the registry net lens (equity_quality, which is what these pins use): IS 439t / +578.96R / DD 23.77R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 41.2%, OOS 235t / +269.27R / DD 15.90R / WR 40.0%. Against the parent that is +63.50R IS and +45.21R OOS, and the IS DRAWDOWN IMPROVES, 19.57 -> 17.99. WHY 4 AND NOT 5. The value was chosen on the owner's stated priority - drawdown and losing streak first - not on the net argmax. skip_n=32 posts +974.53R on IS, nearly double, and holds on OOS at +416.23R; it is rejected because its DD is 22.24 against the parent's 19.57 and its OOS DD is 26.44 against 9.85. The DD-safe window on this book is 3,4,5,6 and 4 is the best net inside it. OOS WAS READ ONCE, at the value IS selected, which is the discipline the last three hypotheses all failed. WHAT MUST TRAVEL WITH THIS: OOS drawdown RISES, 9.85 -> 12.05. The IS drawdown gain does not carry out of sample; what carries is the net and the losing streak. If OOS drawdown matters equally, skip_n=3 is the only value free on both eras (+230.92R OOS at DD 10.53) and it is the smaller prize. OWNER SCOPE: fsent_champ_short was ruled out of this work by the owner on 2026-10-14 and is deliberately NOT registered - short loses at every skip_n above 2, so the knob is not a family rule. THE SHORTCUT THAT WAS CORRECTED HERE, because it is the one this repo keeps making: the first census swept skip_n in {0,1,2,3,5}, found 5 best on all three books, and that is a BOUNDARY ARTEFACT - 5 was the top of the grid. Extended to 32 the IS argmax is 32 on all three books, and htf15 at 32 LOSES on OOS. The census number was never a promotion and was not treated as one.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long",
                       "exp_trail_skip_n": 4},
          "swing": "sw10",
          "pins": {"n": 439, "net": 578.96, "dd_net": 23.77, "wr_net": 0.415,
                  "gross_win": 0.431, "oos_n": 235, "oos_net": 269.27, "oos_dd_net": 15.9,
                  "oos_wr_net": 0.409, "oos_gross_win": 0.413, "n_all": 674,
                  "net_all": 848.23, "dd_net_all": 23.77},
          "pins_legacy": {"n": 447, "net": 530.42, "dd_net": 23.66, "win": 0.412,
                         "oos_n": 240, "oos_net": 260.53, "oos_dd_net": 15.49,
                         "oos_win": 0.4},
    },
    "fsent_champ_long_htf15_tskip6": {
          "desc": "CANDIDATE, NOT ADOPTED - fsent_champ_long_htf15 with exp_trail_skip_n=6, the strongest of the two verified skip_n books and the one where the risk improvement is largest. Same mechanism as fsent_champ_long_tskip4 and the same reason it is real: exp_trail_skip_n drops the first N trailing-stop events (unified.py:1493), converting weak early trail exits into ordinary stop exits at exactly -1.000R. Purging every stop-exit trade RAISES the net rather than lowering it (+723.83 -> +958.83 at skip_n=5), which is the opposite of a right-tail bet and is the test that killed swing shape, volatile candles and mark continuation. MEASURED, on the registry net lens (equity_quality): IS 395t / +644.04R / DD 23.93R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 40.8%, OOS 216t / +336.16R / DD 14.90R / WR 36.6%. MaxConsecL 13 IS / 11 OOS on the gross curve. Against the parent: +134.60R IS and +73.73R OOS, with IS drawdown IMPROVING 21.05 -> 18.09 and, uniquely among these books, THE WORST LOSING STREAK FALLING 22 -> 13 in sample and holding at 11 out of sample. The parent's OOS streak is 11 and this book's is 11, so nothing is traded away on the owner's stated first priority. WHY 6. Chosen on risk, not on the net argmax: skip_n=32 posts +875.80R IS but its OOS is +218.70 against the parent's +254.81 - it LOSES - and its IS DD is 26.65 with an OOS DD of 27.00. The DD-safe window here is 2..6, wider than the parent's 3..6, and 6 is the best net inside it. The value ladder is genuinely still rising past the value chosen, which is the honest reason not to push further: this is the top of the safe window, not a plateau, and the next rung costs drawdown. OOS WAS READ ONCE at the IS-selected value. CAVEAT CARRIED: OOS drawdown rises 9.98 -> 12.98. The in-sample drawdown gain does not carry out of sample; the losing streak and the net do. fsent_champ_short is out of scope by owner ruling. fsent_champ_long_htffs is deliberately NOT registered: its only DD-safe value is skip_n=2 and that LOSES on OOS (+281.75 against the parent's +313.35), and its +2570R at skip_n=32 costs DD 12.86 -> 30.05 and MaxConsecL 12 -> 23.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "max_positions": 0,
                       "ext_stop_r": 3.0, "exp_partial_r": 0.0,
                       "exp_persist": 7,
                       "pivot_rule": "leg", "exp_fs_entry_side": "long",
                       "exp_trail_skip_n": 6},
          "swing": "htf15",
          "pins": {"n": 395, "net": 644.04, "dd_net": 23.93, "wr_net": 0.413,
                  "gross_win": 0.425, "oos_n": 216, "oos_net": 336.16, "oos_dd_net": 14.9,
                  "oos_wr_net": 0.38, "oos_gross_win": 0.384, "n_all": 611, "net_all": 980.2,
                  "dd_net_all": 23.93},
          "pins_legacy": {"n": 412, "net": 639.84, "dd_net": 22.81, "win": 0.408,
                         "oos_n": 224, "oos_net": 328.54, "oos_dd_net": 14.9,
                         "oos_win": 0.366},
    },
    "fsent_sig_multi": {
          "desc": "CANDIDATE, NOT ADOPTED - the strongest non-shipping result in the repo, and still not an adoption. fsent_sig_full's entire filter set (bias_momentum 0.8, fs_small_swing 6.0, trail_skip_n 2, weekends skipped, FS entry on shorts, ext_stop_r 3.0, halt on 3) with max_positions 1 -> 0, i.e. the single-slot gate removed and concurrency enabled. ONE value differs from fsent_sig_full; the other 15 are identical. WHAT IT IS, in plain terms: the same signals, and the book simply stops standing aside. Of 50 extra out-of-sample trades, 48 were taken while a serial position was already open and only 2 after it closed; 47 of the 50 joined a position in the SAME direction, so this is adding to an existing bet rather than hedging. Those extras earned +25.1R at a 46% win rate, against -0.3R given up on trades the serial book took instead. In sample the same mechanism gives 108 extras earning +186.2R for a net +188.8R. MEASURED: IS 291t / +366.04R / DD 13.43R [as of 2026-10-15 (exp_repin_all.py, net lens)] / WR 45.6%, OOS 185t / +184.86R / DD 5.81R / WR 47.2%. Against the shipping book out of sample that is 92% of the net on 63% of the trades, at 64% of the drawdown, with a 10-point better win rate, and BOTH direction columns stay alive (+136.7R long, +83.1R short) which matters because the FS-side autopsy found the two families pointing in opposite directions. GATES: period control positive in both eras with 99% of the raw gap surviving, so this is NOT a regime proxy - the ATR% ceiling's signature does not appear. The half-year partition is 12 of 12. Tail dependence IMPROVES in every cell of both eras: removing the top 10 trades leaves 40.1% of in-sample profit against the parent's 22.0%, and 30.7% out of sample against 22.4%, which is the opposite of mode_union's 96%. WHY IT IS NOT ADOPTED - CORRECTED 2026-10-08, because the original reason was wrong. I previously wrote here that the out-of-sample magnitude is underpowered (b +0.3303 against an MDE of 2.1999) and therefore should not be adopted. THAT ARGUMENT IS WITHDRAWN. The 'OOS' era is 2021-01-01 to 2022-12-31 and IS is 2023-01-01 to 2026-09-13 - the OOS window is two years OLDER than the in-sample window and has been re-scored many times. It is not a holdout and never was, as method/FORWARD_TEST_PLAN.md states in its own second paragraph ('reused many times, not a holdout'). A power gate on that window is a real measurement of a real limitation OF THAT WINDOW and is not a forward verdict in either direction: it does not say this arm is bad, it says we have no forward data on it. THE CORRECT REASON THIS IS NOT ADOPTED: the adoption decision is BLOCKED ON FORWARD DATA, which does not exist on this machine. method/FORWARD_TEST_PLAN.md is ACTIVE with a hard boundary at 2026-09-13 10:03 IST and five pre-registered gates; it was scored once on 2026-09-25 and produced 5 trades and NO VERDICT (n<50); data/forward/bybit/ is not present locally now. This book is NOT on the contract's pre-registered candidate list, and because no forward window exists on disk nothing is burned - so it can be added before a new window starts, which is the cheapest high-value action available. The in-sample magnitude IS powered (b +2.1619, t +2.240, MDE 1.8920, month-cluster bootstrap +1.8501) and the 2021-22 magnitude is not (b +0.3303, MDE 2.1999); both are true and neither is a forward statement. The 2.16-vs-0.33 gap is a 2023-26 versus 2021-22 difference and should have been labelled as such when first reported. The tightest partition cells matter: 2021-H1 is +39.6 against +39.9 and 2021-H2 +35.8 against +40.5, so the FIRST out-of-sample half-year is worth almost nothing and the gain is concentrated in 2022-H1 and 2022-H2. DO NOT carry the in-sample +2.16R per trade as a forward expectation; the honest figure is roughly +0.33R and even that is not established. Concurrency shape: depth 5 in sample, 4 out, but 69% of entries happen with nothing else open, so this is the same book that occasionally takes a second position, not a crowded one. A cap of 3 costs 1.5R in sample, nothing out of sample, and lowers drawdown in both eras - a free bound on the tail. Two notes on measurement, both of which cost real time and are recorded so they are not repeated: the sibling sweep on the multi books returns BYTE-IDENTICAL results because those books carry exp_mltf=True, which bypasses the max_positions gate entirely in the harness - so this knob is inert on them and meaningful only on the serial sig book; and max_positions must be set alongside the regime knobs rather than alone, since a 0.40% min-stop floor on this book costs 4.1% of the long book's net in sample against 4.1% gained out of sample. See method/SIG_MULTI_STUDY.md.",
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
          "pins": {"n": 291, "net": 366.04, "dd_net": 13.43, "wr_net": 0.433,
                  "gross_win": 0.443, "oos_n": 185, "oos_net": 184.86, "oos_dd_net": 5.81,
                  "oos_wr_net": 0.514, "oos_gross_win": 0.514, "n_all": 476,
                  "net_all": 550.9, "dd_net_all": 13.43},
          "pins_legacy": {"n": 292, "net": 372.96, "dd_net": 13.43, "win": 0.445,
                         "oos_n": 186, "oos_net": 182.77, "oos_dd_net": 7.61,
                         "oos_win": 0.508},
    },
    "fsent_champ_long_mode_union": {
          "desc": "CANDIDATE, NOT ADOPTED. fsent_champ_long with mode='union' - admits either HTF interval set. Highest net of the four (813 / +580.0 IS, 442 / +303.8 OOS) and the WORST shape: mean R 0.69 against the base 0.77, drawdown 23.8R / 18.2R, and it loses on both second lanes in both eras. A bigger book, not a better one.",
          "engine": "patched",
          "params": {"mode": "union", "atr_high_thresh": 0.65,
                       "sl_buf_atr": 0.01, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 754, "net": 641.03, "dd_net": 44.15, "wr_net": 0.399,
                  "gross_win": 0.435, "oos_n": 417, "oos_net": 204.05, "oos_dd_net": 16.13,
                  "oos_wr_net": 0.376, "oos_gross_win": 0.386, "n_all": 1171,
                  "net_all": 845.08, "dd_net_all": 44.15},
          "pins_legacy": {"n": 779, "net": 495.69, "dd_net": 47.61, "oos_n": 431,
                         "oos_net": 196.03, "oos_dd_net": 17.95},
    },
    "fsent_champ_long_nohalt": {
          "desc": "fsent_champ_long with max_consecutive_losses=0 (the 3-loss streak halt removed) and ext_stop_r=0.0 (provably inert since C17, written explicitly because omitting the key would inherit BP's 1.5). Every behavioural knob identical to the base. PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0312 in sample, p = 0.0117 out of sample, gap +33.22 IS and +31.32 OOS - the same book as fsent_champ_long_mcloff, to two decimal places. Significance means this arm's choice of trades is unlikely to be a reshuffle of the parent's; it does NOT mean the book is statistically better in absolute terms, which the same audit shows it is not (the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades, and the corrected absolute null is M = 771.09R IS / 384.36R OOS against the 381.7 / 205.5 quoted in BASE_BOOK_NULL.md, which was measured on a different book). See method/NULL_AUDIT_P5.md.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 524, "net": 502.69, "dd_net": 23.3, "wr_net": 0.395,
                  "gross_win": 0.437, "oos_n": 293, "oos_net": 216.03, "oos_dd_net": 11.05,
                  "oos_wr_net": 0.41, "oos_gross_win": 0.423, "n_all": 817,
                  "net_all": 718.72, "dd_net_all": 23.3},
          "pins_legacy": {"n": 533, "net": 504.12, "dd_net": 23.3, "oos_n": 300,
                         "oos_net": 213.27, "oos_dd_net": 11.05},
      },

    "fsent_champ_short": {
          "desc": "champion leg + SHORTS enter at swing FS (longs unchanged)",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # Directional FS entry: ONE side enters at the swing FS print, the
          # other side unchanged. exp_fs_directional_leg.py, both eras.
          "pins": {"n": 462, "net": 562.7, "dd_net": 12.67, "wr_net": 0.379,
                  "gross_win": 0.403, "oos_n": 295, "oos_net": 196.85, "oos_dd_net": 12.35,
                  "oos_wr_net": 0.38, "oos_gross_win": 0.393, "n_all": 757,
                  "net_all": 759.55, "dd_net_all": 12.67},
          "pins_legacy": {"n": 467, "net": 569.33, "dd_net": 12.67, "oos_n": 298,
                         "oos_net": 195.01, "oos_dd_net": 12.75},
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
                       "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # exp_fs_directional_leg.py, both eras. dd_net pending measure.
          "pins": {"n": 483, "net": 462.52, "dd_net": 23.81, "wr_net": 0.381,
                  "gross_win": 0.427, "oos_n": 274, "oos_net": 218.67, "oos_dd_net": 10.16,
                  "oos_wr_net": 0.416, "oos_gross_win": 0.431, "n_all": 757,
                  "net_all": 681.19, "dd_net_all": 23.81},
          "pins_legacy": {"n": 493, "net": 470.03, "dd_net": 23.81, "oos_n": 280,
                         "oos_net": 212.94, "oos_dd_net": 11.2},
      },

    "fsent_utcsat_short": {
          "desc": "utcsat entry-1 (leg_no_entry) + SHORTS enter at swing FS",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # exp_fs_directional_leg.py, both eras. dd_net pending measure.
          "pins": {"n": 454, "net": 541.19, "dd_net": 12.67, "wr_net": 0.368,
                  "gross_win": 0.392, "oos_n": 292, "oos_net": 211.52, "oos_dd_net": 15.38,
                  "oos_wr_net": 0.38, "oos_gross_win": 0.394, "n_all": 746, "net_all": 752.7,
                  "dd_net_all": 15.38},
          "pins_legacy": {"n": 459, "net": 547.82, "dd_net": 12.67, "oos_n": 295,
                         "oos_net": 209.67, "oos_dd_net": 15.38},
      },
    "fsent_champ_trailhalf": {
        "desc": "CANDIDATE: fsent_champ_long + exp_trail_half=1. Multi check on 2026-10-06: OOS +287.0 / avgR 1.032 / PF 3.00 / DD 16.5 vs base +245.0 / 0.793 / 2.76 / 11.9. Lifts total and per-trade, at DD cost. NOT adopted - needs exp_port_differential parity + cohort autopsy first.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long",
                       "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 434, "net": 396.9, "dd_net": 29.38, "wr_net": 0.376, "gross_win": 0.399,
                "oos_n": 246, "oos_net": 244.86, "oos_dd_net": 15.13, "oos_wr_net": 0.386,
                "oos_gross_win": 0.415, "n_all": 680, "net_all": 641.76, "dd_net_all": 29.38},
        "pins_legacy": {"n": 451, "net": 416.35, "dd_net": 29.38, "oos_n": 253,
                       "oos_net": 242.71, "oos_dd_net": 15.13},
    },
    "fsent_utcsat_trailhalf": {
        "desc": "CANDIDATE: fsent_utcsat_long + exp_trail_half=1. Repeats the fsent_champ_trailhalf lift (OOS +286.4 / avgR 1.034 / PF 3.00 / DD 16.5 vs base +244.2 / 0.793 / 2.75 / 11.9). NOT adopted.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "long",
                       "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 431, "net": 405.1, "dd_net": 23.49, "wr_net": 0.378, "gross_win": 0.399,
                "oos_n": 246, "oos_net": 246.26, "oos_dd_net": 13.74, "oos_wr_net": 0.39,
                "oos_gross_win": 0.419, "n_all": 677, "net_all": 651.36, "dd_net_all": 23.49},
        "pins_legacy": {"n": 446, "net": 419.14, "dd_net": 23.49, "oos_n": 253,
                       "oos_net": 241.94, "oos_dd_net": 15.9},
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
          "desc": "SERIAL signal book: one position at a time, SHORTS enter at swing FS PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0267 in sample, p = 0.1137 out of sample, gap -62.44 IS and -50.34 OOS - significant with a NEGATIVE gap: reliably worse, not an improvement. Significance means this arm's choice of trades is unlikely to be a reshuffle of the parent's; it does NOT mean the book is statistically better in absolute terms, which the same audit shows it is not (the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades, and the corrected absolute null is M = 771.09R IS / 384.36R OOS against the 381.7 / 205.5 quoted in BASE_BOOK_NULL.md, which was measured on a different book). See method/NULL_AUDIT_P5.md.",
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
          "pins": {"n": 333, "net": 167.14, "dd_net": 17.58, "wr_net": 0.333,
                  "gross_win": 0.348, "oos_n": 208, "oos_net": 118.71, "oos_dd_net": 14.39,
                  "oos_wr_net": 0.351, "oos_gross_win": 0.361, "n_all": 541,
                  "net_all": 285.85, "dd_net_all": 17.58},
          "pins_legacy": {"n": 334, "net": 167.14, "dd_net": 17.58, "oos_n": 208,
                         "oos_net": 118.71, "oos_dd_net": 14.39},
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
          "pins": {"n": 326, "net": 133.1, "dd_net": 18.09, "wr_net": 0.325,
                  "gross_win": 0.347, "oos_n": 203, "oos_net": 106.76, "oos_dd_net": 8.08,
                  "oos_wr_net": 0.374, "oos_gross_win": 0.379, "n_all": 529,
                  "net_all": 239.86, "dd_net_all": 18.09},
          "pins_legacy": {"n": 326, "net": 133.1, "dd_net": 18.09, "oos_n": 203,
                         "oos_net": 106.76, "oos_dd_net": 8.08},
      },

    "fsent_sig_sw20_short": {
          "desc": "SERIAL signal book on the sw20 chain, SHORTS enter at swing FS PAIRED PERMUTATION vs the shipping book, 2026-10-10 (exp_null_audit.py, 4000 draws, seed 20261010): p = 0.0177 in sample, p = 0.1570 out of sample, gap -114.86 IS and -57.58 OOS - significant with a NEGATIVE gap: the swap is reliably WORSE than the parent, which is a real result and not an endorsement. Significance means this arm's choice of trades is unlikely to be a reshuffle of the parent's; it does NOT mean the book is statistically better in absolute terms, which the same audit shows it is not (the shipping book sits at the 58th and 45th percentile of a reshuffle of its own trades, and the corrected absolute null is M = 771.09R IS / 384.36R OOS against the 381.7 / 205.5 quoted in BASE_BOOK_NULL.md, which was measured on a different book). See method/NULL_AUDIT_P5.md.",
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
"pins": {"n": 341, "net": 246.02, "dd_net": 16.92, "wr_net": 0.334, "gross_win": 0.337,
        "oos_n": 190, "oos_net": 151.23, "oos_dd_net": 12.91, "oos_wr_net": 0.379,
        "oos_gross_win": 0.384, "n_all": 531, "net_all": 397.25, "dd_net_all": 16.92},
"pins_legacy": {"n": 341, "net": 246.02, "dd_net": 16.92, "win": 0.337, "oos_n": 190,
               "oos_net": 151.23, "oos_dd_net": 12.91, "oos_win": 0.384},
      },

# fsent_sig_sw20_short_wr IS GONE. It was not a second book.
    #
    # Removed 2026-10-15 on the owner's instruction to collapse repeats. It was a
    # byte-identical duplicate of fsent_sig_sw20_short: same swing (sw20), same
    # params key for key, same pins, and its own desc said so in writing -
    # "the same book as fsent_sig_sw20_short". The only difference was that its
    # pins carried the win-rate fields the other one lacked, which is two extra
    # recorded numbers about the same trades, not a different strategy.
    #
    # The two sat next to each other in every export and every dropdown, which
    # made one book look like corroboration for itself. This is the second
    # instance in this repo - results_db.py:9 records fsent_single_sw20_short_wr
    # being the first, with the same rule written down there: "a number with one
    # home is a number that can be checked."
    #
    # fsent_sig_sw20_short is the survivor and keeps the win-rate fields, so
    # nothing measurable is lost by the merge.
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
          "pins": {"n": 217, "net": 206.87, "dd_net": 14.24, "wr_net": 0.364,
                  "gross_win": 0.378, "oos_n": 135, "oos_net": 127.47, "oos_dd_net": 4.41,
                  "oos_wr_net": 0.422, "oos_gross_win": 0.43, "n_all": 352,
                  "net_all": 334.34, "dd_net_all": 14.24},
          "pins_legacy": {"n": 217, "net": 206.87, "dd_net": 14.24, "win": 0.378,
                         "oos_n": 135, "oos_net": 127.47, "oos_dd_net": 4.41,
                         "oos_win": 0.43},
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
          "pins": {"n": 215, "net": 208.96, "dd_net": 14.01, "wr_net": 0.414,
                  "gross_win": 0.419, "oos_n": 131, "oos_net": 133.91, "oos_dd_net": 4.99,
                  "oos_wr_net": 0.473, "oos_gross_win": 0.473, "n_all": 346,
                  "net_all": 342.86, "dd_net_all": 14.01},
          "pins_legacy": {"n": 215, "net": 208.95, "dd_net": 14, "win": 0.419, "oos_n": 132,
                         "oos_net": 133.91, "oos_dd_net": 4.99, "oos_win": 0.473},
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
        "pins": {"n": 187, "net": 153.55, "dd_net": 16.05, "wr_net": 0.39, "gross_win": 0.401,
                "oos_n": 111, "oos_net": 134.57, "oos_dd_net": 6.49, "oos_wr_net": 0.414,
                "oos_gross_win": 0.432, "n_all": 298, "net_all": 288.12, "dd_net_all": 16.05},
        "pins_legacy": {"n": 187, "net": 153.55, "dd_net": 16.05, "win": 0.401, "oos_n": 112,
                       "oos_net": 134.57, "oos_dd_net": 6.49, "oos_win": 0.432},
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
        "pins": {"n": 95, "net": 131.96, "dd_net": 8.62, "wr_net": 0.432, "gross_win": 0.442,
                "oos_n": 63, "oos_net": 52.58, "oos_dd_net": 9.07, "oos_wr_net": 0.397,
                "oos_gross_win": 0.397, "n_all": 158, "net_all": 184.54, "dd_net_all": 9.07},
        "pins_legacy": {"n": 95, "net": 131.96, "dd_net": 8.62, "win": 0.442, "oos_n": 63,
                       "oos_net": 52.58, "oos_dd_net": 9.07, "oos_win": 0.397},
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
        "pins": {"n": 93, "net": 132, "dd_net": 8.59, "wr_net": 0.419, "gross_win": 0.43,
                "oos_n": 61, "oos_net": 86.79, "oos_dd_net": 10.75, "oos_wr_net": 0.328,
                "oos_gross_win": 0.344, "n_all": 154, "net_all": 218.79, "dd_net_all": 10.75},
        "pins_legacy": {"n": 93, "net": 132, "dd_net": 8.59, "win": 0.43, "oos_n": 61,
                       "oos_net": 86.79, "oos_dd_net": 10.75, "oos_win": 0.344},
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
        "pins": {"n": 238, "net": 35.73, "dd_net": 26.13, "wr_net": 0.286, "gross_win": 0.303,
                "oos_n": 129, "oos_net": 30.55, "oos_dd_net": 13.87, "oos_wr_net": 0.326,
                "oos_gross_win": 0.341, "n_all": 367, "net_all": 66.28, "dd_net_all": 26.13},
        "pins_legacy": {"n": 238, "net": 35.73, "dd_net": 26.13, "win": 0.303, "oos_n": 130,
                       "oos_net": 30.55, "oos_dd_net": 13.87, "oos_win": 0.341},
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
          "pins": {"n": 266, "net": 203.02, "dd_net": 13.42, "wr_net": 0.38,
                  "gross_win": 0.402, "oos_n": 162, "oos_net": 136.39, "oos_dd_net": 6.91,
                  "oos_wr_net": 0.407, "oos_gross_win": 0.414, "n_all": 428,
                  "net_all": 339.41, "dd_net_all": 13.42},
          "pins_legacy": {"n": 266, "net": 203.02, "dd_net": 13.42, "oos_n": 162,
                         "oos_net": 136.39, "oos_dd_net": 6.91},
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
                       "exp_persist": 7,
                       "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw10",
          # exp_fs_small_swing.py, both eras. Monotonic 3->6 ATR.
          "pins": {"n": 422, "net": 97.88,
                 "dd_net": 69.09, "oos_n": 259, "oos_net": -14.71, "oos_dd_net": 46.22},
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
                     "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                     "pivot_rule": "leg",
                     "exit_fs_max_gap_h": 6.0},
        "swing": "sw10",
        # See the FS_EXIT ladder in exp_fs_exit.py.
        "pins": {"n": 434, "net": 170.04,
                 "dd_net": 72.42, "oos_n": 270, "oos_net": -6.09, "oos_dd_net": 47.24},
    },
    # ===== P36 DECAY GATE (engine knob, measured 2026-10-02 IS+OOS) =====
}
