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
        "pins": {"n": 419, "net": 140.16, "dd_net": 39.47, "wr_net": 0.243,
                "gross_win": 0.258, "oos_n": 249, "oos_net": 2.04, "oos_dd_net": 42.09,
                "oos_wr_net": 0.249, "oos_gross_win": 0.257, "n_all": 668, "net_all": 142.2,
                "dd_net_all": 42.09},
        "pins_legacy": {"n": 419, "net": 140.16, "dd_net": 39.47, "oos_n": 249,
                       "oos_net": 2.04, "oos_dd_net": 42.09},
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
        "pins": {"n": 422, "net": 159.98,
                 "dd_net": 40.05, "oos_n": 250, "oos_net": -28.75, "oos_dd_net": 49.25},
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
        "pins": {"n": 410, "net": 117.24,
                 "dd_net": 70.1, "oos_n": 242, "oos_net": -14.73, "oos_dd_net": 40.31},
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
        "pins": {"n": 427, "net": 149.89,
                 "dd_net": 69.46, "oos_n": 256, "oos_net": -39.44, "oos_dd_net": 56.53},
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
        "pins": {"n": 466, "net": 128.37,
                 "dd_net": 67.76, "oos_n": 271, "oos_net": -3.03, "oos_dd_net": 41.26},
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
        "pins": {"n": 169, "net": 43.03, "dd_net": 19.07,
                 "oos_n": 81, "oos_net": 23.59, "oos_dd_net": 17.02},
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
        "pins": {"n": 210, "net": 69.57, "dd_net": 18.99,
                 "oos_n": 109, "oos_net": 12.1, "oos_dd_net": 17.11},
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
        "pins": {"n": 222, "net": 65.59, "dd_net": 24.1,
                 "oos_n": 124, "oos_net": 17.7, "oos_dd_net": 18.85},
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
        "pins": {"n": 236, "net": 59.18, "dd_net": 24.57,
                 "oos_n": 131, "oos_net": 16.5, "oos_dd_net": 20.03},
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
        "pins": {"n": 247, "net": 65.73, "dd_net": 22.87,
                 "oos_n": 138, "oos_net": 16.3, "oos_dd_net": 21.12},
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": {"n": 328, "net": 39,
                 "dd_net": 67.55, "oos_n": 193, "oos_net": -21.89, "oos_dd_net": 42.5},
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
        "pins": None,
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
        "pins": {"n": 278, "net": -16.73, "dd_net": 66.45,
                 "oos_n": 154, "oos_net": 76.67, "oos_dd_net": 13.59},
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
        "pins": None,
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
        "pins": {"n": 302, "net": 165.01, "dd_net": 39.39, "wr_net": 0.285,
                "gross_win": 0.295, "oos_n": 186, "oos_net": 8.08, "oos_dd_net": 28.19,
                "oos_wr_net": 0.263, "oos_gross_win": 0.269, "n_all": 488, "net_all": 173.09,
                "dd_net_all": 39.39},
        "pins_legacy": {"n": 302, "net": 165.01, "dd_net": 39.39, "oos_n": 186,
                       "oos_net": 8.08, "oos_dd_net": 28.19},
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
        "pins": {"n": 353, "net": 116.85, "dd_net": 49.03, "wr_net": 0.266,
                "gross_win": 0.278, "oos_n": 213, "oos_net": 10.52, "oos_dd_net": 28.3,
                "oos_wr_net": 0.268, "oos_gross_win": 0.277, "n_all": 566, "net_all": 127.37,
                "dd_net_all": 49.03},
        "pins_legacy": {"n": 353, "net": 116.86, "dd_net": 49.03, "oos_n": 213,
                       "oos_net": 10.52, "oos_dd_net": 28.3},
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
        "pins": {"n": 381, "net": 161.73, "dd_net": 50.14, "wr_net": 0.268,
                "gross_win": 0.278, "oos_n": 230, "oos_net": 4.64, "oos_dd_net": 35.26,
                "oos_wr_net": 0.248, "oos_gross_win": 0.257, "n_all": 611, "net_all": 166.38,
                "dd_net_all": 50.14},
        "pins_legacy": {"n": 381, "net": 161.73, "dd_net": 50.14, "oos_n": 230,
                       "oos_net": 4.64, "oos_dd_net": 35.26},
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
        "pins": {"n": 291, "net": -40.62,
                 "dd_net": 68.96, "oos_n": 172, "oos_net": -0.18, "oos_dd_net": 33.98},
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
        "pins": {"n": 292, "net": -45.48,
                 "dd_net": 71.49, "oos_n": 172, "oos_net": -0.22, "oos_dd_net": 34.01},
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
        "pins": {"n": 278, "net": -16.73, "dd_net": 66.45,
                 "oos_n": 154, "oos_net": 76.67, "oos_dd_net": 13.59},
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
        "pins": {"n": 408, "net": 84.74,
                 "dd_net": 98.98, "oos_n": 249, "oos_net": -31.6, "oos_dd_net": 49.28},
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
        "pins": {"n": 397, "net": 81.72,
                 "dd_net": 88.67, "oos_n": 233, "oos_net": -59.35, "oos_dd_net": 66.14},
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
        "pins": {"n": 294, "net": 141.72,
                 "dd_net": 62.49, "oos_n": 185, "oos_net": -0.14, "oos_dd_net": 52.86},
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
        "pins": {"n": 283, "net": 129.72, "dd_net": 60.27, "wr_net": 0.261,
                "gross_win": 0.279, "oos_n": 180, "oos_net": 0.84, "oos_dd_net": 54.42,
                "oos_wr_net": 0.228, "oos_gross_win": 0.233, "n_all": 463, "net_all": 130.56,
                "dd_net_all": 60.27},
        "pins_legacy": {"n": 283, "net": 129.72, "dd_net": 60.27, "oos_n": 180,
                       "oos_net": 0.83, "oos_dd_net": 54.42},
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
        "pins": {"n": 308, "net": 149.33,
                 "dd_net": 62.78, "oos_n": 191, "oos_net": -18.76, "oos_dd_net": 54.64},
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
        "pins": {"n": 420, "net": 123.59,
                 "dd_net": 71.72, "oos_n": 264, "oos_net": -40.33, "oos_dd_net": 72.73},
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
        "pins": {"n": 479, "net": 234.9, "dd_net": 46.3,
                 "oos_n": 280, "oos_net": 48.77, "oos_dd_net": 56.54},
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
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
        "pins": {"n": 404, "net": 124.34, "dd_net": 55.77, "wr_net": 0.243,
                "gross_win": 0.255, "oos_n": 237, "oos_net": 22.24, "oos_dd_net": 41.05,
                "oos_wr_net": 0.232, "oos_gross_win": 0.236, "n_all": 641, "net_all": 146.57,
                "dd_net_all": 55.77},
        "pins_legacy": {"n": 404, "net": 124.34, "dd_net": 55.77, "oos_n": 237,
                       "oos_net": 22.23, "oos_dd_net": 41.05},
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
        "pins": {"n": 421, "net": 127.39,
                 "dd_net": 71.11, "oos_n": 188, "oos_net": -25.28, "oos_dd_net": 48.2},
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
        "pins": {"n": 397, "net": 81.72,
                 "dd_net": 88.67, "oos_n": 243, "oos_net": -45.06, "oos_dd_net": 62.04},
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
        "pins": None,
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
        "pins": {"n": 277, "net": -15.67, "dd_net": 65.4,
                 "oos_n": 152, "oos_net": 74.89, "oos_dd_net": 13.59},
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
        "pins": None,
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
        "pins": {"n": 523, "net": 136.08, "dd_net": 47.86,
                 "oos_n": 303, "oos_net": 0.92, "oos_dd_net": 47.66},
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
        "pins": None,
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
        "pins": {"n": 506, "net": 55.66, "dd_net": 39.71,
                 "oos_n": 290, "oos_net": 9.54, "oos_dd_net": 48.61},
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
        "pins": {"n": 426, "net": 152.28,
                 "dd_net": 59.38, "oos_n": 235, "oos_net": -17.73, "oos_dd_net": 43.26},
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
        "pins": {"n": 405, "net": 71.25,
                 "dd_net": 77.36, "oos_n": 244, "oos_net": -35.11, "oos_dd_net": 54.8},
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
        "pins": {"n": 427, "net": 151.81,
                 "dd_net": 69.46, "oos_n": 256, "oos_net": -42.24, "oos_dd_net": 56.53},
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
        "pins": None,
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
        "pins": None,
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
        "pins": None,
    },

    # ===== FS-EXIT (engine knob, measured 2026-10-03 IS+OOS) =====
}
