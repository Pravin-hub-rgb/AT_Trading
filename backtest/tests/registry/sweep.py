"""SWEEP - the grid sweeps: final audit, script-grid, knob-gap.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {
    # ===== FINAL AUDIT PASS: plain engine params (2026-10-02) =====
    "gap_slbuf025": {
        "desc": "champion leg + sl_buf_atr 0.25",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "sl_buf_atr": 0.25},
        "swing": "sw10",
        # FINAL AUDIT PASS 2026-10-02. The previous audit filtered on the
        # knob NAME PATTERN (exp_*) and so missed every plain engine parameter -
        # b3_k, chop_thresh, cooldown_bars, sl_buf_atr, htf_rr,
        # max_consecutive_losses and exp31_lb. Fixed by filtering on the actual
        # signature of the patched engine instead of a regex, which is the only
        # correct way to ask "is this a knob". 18 real pairs surfaced that way.
        #
        # The notable one: sl_buf_atr=0.25 is BETTER out of sample (+82.53R at
        # dd 31.78, against the shipped 0.01 giving +72.79 at dd 50.55) while
        # being worse in sample (+188.41 against +239.12). That is a stop-buffer
        # value the whole project has been treating as settled, measured by one
        # script, never pinned.
        #
        # MEASURED INERT on both eras - wired but not binding on this book:
        #   chop_thresh at 52.0 and 61.0. It does not bind because mode=atr_high
        #     selects the HTF interval set by ATR, not by chop - chop_thresh is
        #     read only in mode=chop. Every book in the registry is atr_high, so
        #     chop_thresh has been a decorative parameter on all 192 of them.
        #   exp31_lb at 50 and 60, htf_rr=3.0 (the shipped value).
        # The b3_k ladder is a fifth sibling of the decay conclusion: b3_k=2
        # gives IS +41.78 / OOS +25.70 on 167 and 79 trades. Small, low drawdown
        # on both sides, and nowhere near the champion - the arm is real and weak.
        "pins": {"n": 497, "net": 188.41, "dd_net": 44.69,
                 "oos_n": 279, "oos_net": 82.53, "oos_dd_net": 31.78},
    },
    "gap_slbuf010": {
        "desc": "champion leg + sl_buf_atr 0.10",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "sl_buf_atr": 0.10},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 497, "net": 214.36, "dd_net": 45.99,
                 "oos_n": 278, "oos_net": 62.66, "oos_dd_net": 51.65},
    },
    "gap_cd15": {
        "desc": "champion leg + cooldown_bars 15",
        "engine": "patched",
        "params": {
                    "mode": "atr_high",
                    "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0,
                    "cooldown_bars": 15,
                    "max_consecutive_losses": 3,
                    "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0,
                    "exp_mltf": True,
                    "exp_persist": 7,
                    "window_end": "exit",
                    "pivot_rule": "leg",
                },
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 488, "net": 298.14, "dd_net": 46.85,
                 "oos_n": 273, "oos_net": 74.67, "oos_dd_net": 46.67},
    },
    "gap_cd5": {
        "desc": "champion leg + cooldown_bars 5",
        "engine": "patched",
        "params": {
                    "mode": "atr_high",
                    "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0,
                    "cooldown_bars": 5,
                    "max_consecutive_losses": 3,
                    "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0,
                    "exp_mltf": True,
                    "exp_persist": 7,
                    "window_end": "exit",
                    "pivot_rule": "leg",
                },
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 502, "net": 238.56, "dd_net": 46.47,
                 "oos_n": 284, "oos_net": 68.59, "oos_dd_net": 52.83},
    },
    "gap_mcl5": {
        "desc": "champion leg + max_consecutive_losses 5",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "max_consecutive_losses": 5},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 523, "net": 240.02, "dd_net": 43.35,
                 "oos_n": 302, "oos_net": 72.73, "oos_dd_net": 54.16},
    },
    "gap_b3k2": {
        "desc": "champion leg + b3_k 2",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "b3_k": 2},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 167, "net": 41.78, "dd_net": 19.07,
                 "oos_n": 79, "oos_net": 25.70, "oos_dd_net": 15.92},
    },
    "gap_b3k4": {
        "desc": "champion leg + b3_k 4",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "b3_k": 4},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 207, "net": 67.39, "dd_net": 19.78,
                 "oos_n": 107, "oos_net": 14.21, "oos_dd_net": 17.11},
    },
    "gap_b3k6": {
        "desc": "champion leg + b3_k 6",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "b3_k": 6},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 220, "net": 62.40, "dd_net": 26.06,
                 "oos_n": 122, "oos_net": 19.81, "oos_dd_net": 18.85},
    },
    "gap_b3k8": {
        "desc": "champion leg + b3_k 8",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "b3_k": 8},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 233, "net": 55.36, "dd_net": 26.53,
                 "oos_n": 128, "oos_net": 18.60, "oos_dd_net": 20.03},
    },
    "gap_b3k10": {
        "desc": "champion leg + b3_k 10",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "b3_k": 10},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 241, "net": 65.65, "dd_net": 23.72,
                 "oos_n": 135, "oos_net": 20.27, "oos_dd_net": 21.12},
    },
    "gap_inert_chop52": {
        "desc": "champion leg + chop_thresh 52, MEASURED INERT under atr_high",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "chop_thresh": 52.0},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_chop61": {
        "desc": "champion leg + chop_thresh 61, MEASURED INERT under atr_high",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "chop_thresh": 61.0},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_lb50": {
        "desc": "champion leg + exp31_lb 50, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp31_lb": 50},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_lb60": {
        "desc": "champion leg + exp31_lb 60, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp31_lb": 60},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_htfrr3": {
        "desc": "champion leg + htf_rr 3.0 (shipped value, control)",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "htf_rr": 3.0},
        "swing": "sw10",
        # Part of the final audit pass - see gap_slbuf025.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },

    # ===== TAIL OF SCRIPT-GRID SWEEP (2026-10-02) =====
    # ===== TAIL OF SCRIPT-GRID SWEEP (2026-10-02) =====
    "gap_campaign4": {
        "desc": "champion leg + campaign max total 4",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_campaign_max_total": 4, "exp_campaign_max_addons": 4, "exp_campaign_block_mixed": 1},
        "swing": "sw10",
        # TAIL OF THE SCRIPT-GRID SWEEP. Two of the knobs these scripts set
        # do not exist in the engine at all - see the note on
        # gap_missing_regime_persist below, which is recorded as evidence rather
        # than as a book because a book with a knob the engine does not accept
        # would be a lie.
        "pins": {"n": 369, "net": 100.55, "dd_net": 44.08,
                 "oos_n": 216, "oos_net": 109.33, "oos_dd_net": 19.25},
    },
    "gap_campaign1": {
        "desc": "champion leg + campaign max total 1",
        "status": "reference",   # dead: net -34.78R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_campaign_max_total": 1, "exp_campaign_max_addons": 1, "exp_campaign_block_mixed": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 183, "net": -34.78, "dd_net": 46.27,
                 "oos_n": 96, "oos_net": 16.28, "oos_dd_net": 25.11},
    },
    "gap_campaign_markneg": {
        "desc": "champion leg + campaign requires -0.5R marked",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_campaign_max_total": 2, "exp_campaign_max_addons": 2, "exp_campaign_require_marked_r": -0.5},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 273, "net": 6.43, "dd_net": 51.84,
                 "oos_n": 150, "oos_net": 83.41, "oos_dd_net": 10.08},
    },
    "gap_inert_cohort1": {
        "desc": "champion leg + cohort gate n=1, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cohort_swingpause": 1, "exp_cohort_loss_n": 1, "exp_cohort_rearm": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    # exp_regime_persist (3, 5) and exp_window_quality (0.1, 0.2) are set by
    # test_combos.py but ARE NOT PARAMETERS of the engine. Passing them raises
    # TypeError: simulate_htf_ltf_streak_halt() got an unexpected keyword
    # argument. So that script either measures something else, or measured these
    # on an engine that had them and they were lost in the unification. Not
    # recorded as books - a book whose knob the engine rejects is a fiction, and
    # the knob-wiring gate would be right to flag it. Listed here instead so the
    # fact is not lost.

    # ===== SCRIPT-GRID SWEEP: knob/value pairs with no book (2026-10-02) =====
    # ===== SCRIPT-GRID SWEEP: knob/value pairs with no book (2026-10-02) =====
    "gap_bm_min09": {
        "desc": "champion leg + bias-momentum threshold 0.9",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_bias_momentum_min": 0.9},
        "swing": "sw10",
        # SCRIPT-GRID SWEEP 2026-10-02, second pass over the audit.
        # The first pass asked which KNOBS had no book. This one asks which
        # (knob, value) PAIRS a script actually ran but no book recorded - a
        # finer net, because a knob can have one book and still have had three
        # values tested by hand.
        #
        # 39 such pairs across 14 knobs, from exp_la11_extensions,
        # exp_thesis_window_budget, exp_thesis_campaign_policy, test_combos,
        # exp_forward_eval and others. All measured here, both eras.
        #
        # THE STANDOUT: exp_bias_momentum_min=0.9. A bias-momentum threshold
        # sweep that four scripts ran (test_bm_monthly_dist,
        # test_bm_single_headtohead and two more) and that no book captured.
        #   IS  370 trades / +328.26R / dd 29.02
        #   OOS 196 trades / +106.62R / dd 21.41
        # Against the champion's +239.12 / +72.79 at drawdown 46.85 / 50.55,
        # that is more R on both sides at roughly half the drawdown. It is the
        # best both-era result found today that is NOT already a book.
        #
        # Also better on both eras: exp_window_entry_cap=3 (IS +27.63 but OOS
        # +110.07 at dd 16.69 - IS is worse, OOS far better),
        # exp_campaign_max_total=3 (OOS +105.95 at dd 20.23), wage_h=28
        # (OOS +87.58), exp_window_r_cap=3 (OOS +80.16).
        #
        # INERT on both eras - measured, recorded so nobody re-runs them:
        #   exp_window_win_kill_n at 2 and 3, exp_loss_streak_*, exp_cohort_*,
        #   exp_curfew_a=4.0 with exp_curfew_b=4.0 (equal bounds = no window),
        #   exp_persist=1.
        # The curfew pair is a good example of why these were worth running:
        # a=4.0/b=4.0 is a degenerate band that closes instantly, and the
        # a=4.0/b=8.0 version of the same knob is active. Same knob, one value
        # inert and one not - you cannot tell that from reading the knob.
        "pins": {"n": 370, "net": 328.26, "dd_net": 29.02,
                 "oos_n": 196, "oos_net": 106.62, "oos_dd_net": 21.41},
    },
    "gap_bm_min07": {
        "desc": "champion leg + bias-momentum threshold 0.7",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_bias_momentum_min": 0.7},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 414, "net": 266.50, "dd_net": 41.29,
                 "oos_n": 224, "oos_net": 84.81, "oos_dd_net": 32.89},
    },
    "gap_bm_min06": {
        "desc": "champion leg + bias-momentum threshold 0.6",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_bias_momentum_min": 0.6},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 445, "net": 284.52, "dd_net": 43.68,
                 "oos_n": 245, "oos_net": 82.81, "oos_dd_net": 32.65},
    },
    "gap_campaign3": {
        "desc": "champion leg + campaign max total 3",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_campaign_max_total": 3, "exp_campaign_max_addons": 3, "exp_campaign_block_mixed": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 328, "net": 30.12, "dd_net": 37.79,
                 "oos_n": 188, "oos_net": 105.95, "oos_dd_net": 20.23},
    },
    "gap_entry_cap3": {
        "desc": "champion leg + 3 entries per window",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_window_entry_cap": 3},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 330, "net": 27.63, "dd_net": 38.85,
                 "oos_n": 188, "oos_net": 110.07, "oos_dd_net": 16.69},
    },
    "gap_entry_cap2": {
        "desc": "champion leg + 2 entries per window",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_window_entry_cap": 2},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 273, "net": 6.43, "dd_net": 51.84,
                 "oos_n": 150, "oos_net": 83.41, "oos_dd_net": 10.08},
    },
    "gap_r_cap3": {
        "desc": "champion leg + window R cap 3.0",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_window_r_cap": 3.0},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 459, "net": 198.53, "dd_net": 46.85,
                 "oos_n": 270, "oos_net": 80.16, "oos_dd_net": 49.35},
    },
    "gap_r_cap1": {
        "desc": "champion leg + window R cap 1.0",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_window_r_cap": 1.0},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 448, "net": 162.70, "dd_net": 46.85,
                 "oos_n": 246, "oos_net": 66.10, "oos_dd_net": 48.53},
    },
    "gap_wage28": {
        "desc": "champion leg + wage window 28h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_wage_h": 28},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 341, "net": 223.08, "dd_net": 30.47,
                 "oos_n": 208, "oos_net": 87.58, "oos_dd_net": 26.23},
    },
    "gap_wage32": {
        "desc": "champion leg + wage window 32h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_wage_h": 32},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 331, "net": 214.48, "dd_net": 31.77,
                 "oos_n": 202, "oos_net": 76.96, "oos_dd_net": 26.04},
    },
    "gap_wage24": {
        "desc": "champion leg + wage window 24h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_wage_h": 24.0},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 364, "net": 240.58, "dd_net": 31.33,
                 "oos_n": 218, "oos_net": 76.29, "oos_dd_net": 34.05},
    },
    "gap_persist1": {
        "desc": "champion leg + exp_persist 1",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "window_end": "exit",
                    "pivot_rule": "leg", "exp_persist": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 502, "net": 238.45, "dd_net": 53.86,
                 "oos_n": 294, "oos_net": 78.35, "oos_dd_net": 46.46},
    },
    "gap_curfew_16_20": {
        "desc": "champion leg + curfew 16h/20h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_curfew_a": 16.0, "exp_curfew_b": 20.0},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 470, "net": 231.33, "dd_net": 49.95,
                 "oos_n": 274, "oos_net": 61.84, "oos_dd_net": 46.58},
    },
    "gap_campaign_mark05": {
        "desc": "champion leg + campaign requires +0.5R marked",
        "status": "reference",   # dead: net -4.69R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_campaign_max_total": 2, "exp_campaign_max_addons": 2, "exp_campaign_require_marked_r": 0.5},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 267, "net": -4.69, "dd_net": 49.81,
                 "oos_n": 148, "oos_net": 47.93, "oos_dd_net": 10.08},
    },
    "gap_inert_winkill2": {
        "desc": "champion leg + win-kill at 2, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_window_win_kill_n": 2, "exp_window_win_kill_scope": "window", "exp_window_win_kill_action": "close"},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_winkill3": {
        "desc": "champion leg + win-kill at 3, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_window_win_kill_n": 3, "exp_window_win_kill_scope": "window", "exp_window_win_kill_action": "close"},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_lossstreak": {
        "desc": "champion leg + loss-streak halt at 3, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_loss_streak_n": 3, "exp_loss_streak_mode": "halt", "exp_loss_streak_action": "halt"},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_cohort2": {
        "desc": "champion leg + cohort gate, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cohort_swingpause": 1, "exp_cohort_loss_n": 2, "exp_cohort_rearm": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_curfew44": {
        "desc": "champion leg + curfew 4h/4h, MEASURED INERT (degenerate band)",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_curfew_a": 4.0, "exp_curfew_b": 4.0},
        "swing": "sw10",
        # Part of the 2026-10-02 script-grid sweep - see gap_bm_min09.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },

    # ===== KNOB-GAP SWEEP: live knobs with no book (2026-10-02) =====
    # ===== KNOB-GAP SWEEP: live knobs with no book (2026-10-02) =====
    "gap_cooldown20": {
        "desc": "champion leg + cooldown_bars 20",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "cooldown_bars": 20},
        "swing": "sw10",
        # KNOB-GAP SWEEP 2026-10-02. An exhaustive audit found 41 knobs that are
        # LIVE in the engine (harness-patched or a real signature parameter) and
        # are exercised by at least one exp_*.py, but which NO registry book sets.
        # The trail family was exactly this shape and had never been measured, so
        # the whole class was measured rather than only remembered knobs.
        #
        #   ACTIVE, beats champion on BOTH eras:
        #     cooldown_bars=20    IS +278.45 dd 46.85   OOS  +87.36 dd 38.17
        #     skip_decisive=1     IS +239.12 dd 46.85   OOS +104.12 dd 29.03
        #     window_r_cap=2.0    IS +163.31 dd 46.85   OOS  +77.92 dd 50.33
        #
        #   ACTIVE but worse on at least one era: trail_delay_prevbar,
        #   pivot_trail, profit_stage5, campaign_max2, loss_kill1,
        #   window_entry_cap, ma_trail, curfew_a4_b8, cooldown4.
        #
        #   INERT - bit-for-bit the baseline on BOTH eras: exp_geom_b1_min,
        #   exp_geom_mag_min_atr, exp_geom_start_dist_max_atr, exp_geom_b1_max,
        #   exp_loss_streak_*, exp_window_win_kill_*, exp_cohort_*,
        #   chop_thresh=65.0. Wired but not binding on this book at these values.
        #   Recorded as measured-and-inert so nobody re-runs them.
        #
        #   skip_decisive is the odd one: bit-for-bit the baseline IN SAMPLE and
        #   +104.12R against +72.79R OUT of sample. The knob only fires on bars
        #   present in 2021-22 and absent from 2023-26. An IS-only reading would
        #   have called it inert and thrown away the best OOS number here.
        "pins": {"n": 484, "net": 278.45, "dd_net": 46.85,
                 "oos_n": 270, "oos_net": 87.36, "oos_dd_net": 38.17},
    },
    "gap_skip_decisive": {
        "desc": "champion leg + skip decisive signals",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_skip_decisive": 1},
        "swing": "sw10",
        # KNOB-GAP SWEEP 2026-10-02. An exhaustive audit found 41 knobs that are
        # LIVE in the engine (harness-patched or a real signature parameter) and
        # are exercised by at least one exp_*.py, but which NO registry book sets.
        # The trail family was exactly this shape and had never been measured, so
        # the whole class was measured rather than only remembered knobs.
        #
        #   ACTIVE, beats champion on BOTH eras:
        #     cooldown_bars=20    IS +278.45 dd 46.85   OOS  +87.36 dd 38.17
        #     skip_decisive=1     IS +239.12 dd 46.85   OOS +104.12 dd 29.03
        #     window_r_cap=2.0    IS +163.31 dd 46.85   OOS  +77.92 dd 50.33
        #
        #   ACTIVE but worse on at least one era: trail_delay_prevbar,
        #   pivot_trail, profit_stage5, campaign_max2, loss_kill1,
        #   window_entry_cap, ma_trail, curfew_a4_b8, cooldown4.
        #
        #   INERT - bit-for-bit the baseline on BOTH eras: exp_geom_b1_min,
        #   exp_geom_mag_min_atr, exp_geom_start_dist_max_atr, exp_geom_b1_max,
        #   exp_loss_streak_*, exp_window_win_kill_*, exp_cohort_*,
        #   chop_thresh=65.0. Wired but not binding on this book at these values.
        #   Recorded as measured-and-inert so nobody re-runs them.
        #
        #   skip_decisive is the odd one: bit-for-bit the baseline IN SAMPLE and
        #   +104.12R against +72.79R OUT of sample. The knob only fires on bars
        #   present in 2021-22 and absent from 2023-26. An IS-only reading would
        #   have called it inert and thrown away the best OOS number here.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 223, "oos_net": 104.12, "oos_dd_net": 29.03},
    },
    "gap_window_r_cap2": {
        "desc": "champion leg + window R cap 2.0",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_window_r_cap": 2.0},
        "swing": "sw10",
        # KNOB-GAP SWEEP 2026-10-02. An exhaustive audit found 41 knobs that are
        # LIVE in the engine (harness-patched or a real signature parameter) and
        # are exercised by at least one exp_*.py, but which NO registry book sets.
        # The trail family was exactly this shape and had never been measured, so
        # the whole class was measured rather than only remembered knobs.
        #
        #   ACTIVE, beats champion on BOTH eras:
        #     cooldown_bars=20    IS +278.45 dd 46.85   OOS  +87.36 dd 38.17
        #     skip_decisive=1     IS +239.12 dd 46.85   OOS +104.12 dd 29.03
        #     window_r_cap=2.0    IS +163.31 dd 46.85   OOS  +77.92 dd 50.33
        #
        #   ACTIVE but worse on at least one era: trail_delay_prevbar,
        #   pivot_trail, profit_stage5, campaign_max2, loss_kill1,
        #   window_entry_cap, ma_trail, curfew_a4_b8, cooldown4.
        #
        #   INERT - bit-for-bit the baseline on BOTH eras: exp_geom_b1_min,
        #   exp_geom_mag_min_atr, exp_geom_start_dist_max_atr, exp_geom_b1_max,
        #   exp_loss_streak_*, exp_window_win_kill_*, exp_cohort_*,
        #   chop_thresh=65.0. Wired but not binding on this book at these values.
        #   Recorded as measured-and-inert so nobody re-runs them.
        #
        #   skip_decisive is the odd one: bit-for-bit the baseline IN SAMPLE and
        #   +104.12R against +72.79R OUT of sample. The knob only fires on bars
        #   present in 2021-22 and absent from 2023-26. An IS-only reading would
        #   have called it inert and thrown away the best OOS number here.
        "pins": {"n": 449, "net": 163.31, "dd_net": 46.85,
                 "oos_n": 256, "oos_net": 77.92, "oos_dd_net": 50.33},
    },
    "gap_loss_kill1": {
        "desc": "champion leg + kill window after 1 loss",
        "status": "reference",   # dead: net -29.83R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_window_loss_kill_n": 1, "exp_window_loss_kill_scope": "window", "exp_window_loss_kill_action": "close"},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 213, "net": -29.83, "dd_net": 38.88,
                 "oos_n": 123, "oos_net": 113.16, "oos_dd_net": 30.00},
    },
    "gap_campaign_max2": {
        "desc": "champion leg + campaign stacking capped at 2",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_campaign_max_total": 2, "exp_campaign_max_addons": 2, "exp_campaign_block_mixed": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 272, "net": 7.48, "dd_net": 50.78,
                 "oos_n": 149, "oos_net": 80.52, "oos_dd_net": 11.88},
    },
    "gap_ma_trail": {
        "desc": "champion leg + MA trail period 20",
        "status": "reference",   # dead: net -67.38R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_ma_trail_period": 20},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 554, "net": -67.38, "dd_net": 105.97,
                 "oos_n": 313, "oos_net": -52.02, "oos_dd_net": 53.65},
    },
    "gap_pivot_trail": {
        "desc": "champion leg + pivot trail",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_pivot_trail": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 514, "net": 133.69, "dd_net": 44.89,
                 "oos_n": 296, "oos_net": -4.57, "oos_dd_net": 41.79},
    },
    "gap_window_entry_cap1": {
        "desc": "champion leg + 1 entry per window",
        "status": "reference",   # dead: net -33.79R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_window_entry_cap": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 183, "net": -33.79, "dd_net": 45.28,
                 "oos_n": 96, "oos_net": 17.29, "oos_dd_net": 25.11},
    },
    "gap_profit_stage5": {
        "desc": "champion leg + profit stage at 5R",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_profit_stage_r": 5.0, "exp_profit_stage_distance_r": 0.25},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 501, "net": 53.68, "dd_net": 43.32,
                 "oos_n": 282, "oos_net": 15.29, "oos_dd_net": 44.80},
    },
    "gap_trail_prevbar": {
        "desc": "champion leg + trail delay prev-bar variant",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_trail_delay_prevbar": 1, "exp_trail_delay_r": 1.0},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 501, "net": 263.62, "dd_net": 45.37,
                 "oos_n": 279, "oos_net": 69.65, "oos_dd_net": 54.91},
    },
    "gap_curfew_a4_b8": {
        "desc": "champion leg + curfew 4h/8h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_curfew_a": 4.0, "exp_curfew_b": 8.0},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 470, "net": 209.93, "dd_net": 45.74,
                 "oos_n": 269, "oos_net": 81.76, "oos_dd_net": 48.07},
    },
    "gap_cooldown4": {
        "desc": "champion leg + cooldown_bars 4",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "cooldown_bars": 4},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 502, "net": 238.56, "dd_net": 46.47,
                 "oos_n": 285, "oos_net": 70.69, "oos_dd_net": 50.73},
    },
    "gap_inert_geom": {
        "desc": "champion leg + geometry gates, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_geom_b1_min": 96, "exp_geom_mag_min_atr": 4.0, "exp_geom_start_dist_max_atr": 1.0, "exp_geom_b1_max": 1},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_kill": {
        "desc": "champion leg + streak gates, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "cooldown_bars": 8,
                    "pivot_rule": "leg", "exp_window_win_kill_n": 1, "exp_window_win_kill_scope": "window", "exp_window_win_kill_action": "close"},
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },
    "gap_inert_chop65": {
        "desc": "champion leg + chop_thresh 65, MEASURED INERT under atr_high",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {
                    "mode": "atr_high",
                    "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35,
                    "sl_buf_atr": 0.01,
                    "chop_thresh": 65.0,
                    "cooldown_bars": 8,
                    "max_consecutive_losses": 3,
                    "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0,
                    "exp_mltf": True,
                    "exp_persist": 7,
                    "window_end": "exit",
                    "pivot_rule": "leg",
                },
        "swing": "sw10",
        # Part of the 2026-10-02 knob-gap sweep - see gap_cooldown20.
        "pins": {"n": 499, "net": 239.12, "dd_net": 46.85,
                 "oos_n": 280, "oos_net": 72.79, "oos_dd_net": 50.55},
    },

    # ===== FS-EXIT (engine knob, measured 2026-10-03 IS+OOS) =====
}
