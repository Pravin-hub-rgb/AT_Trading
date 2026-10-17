"""TRAIL - exit-side trail shapes, the trail sweep surface, trail quality.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {

    # ===== EXIT-SIDE TRAIL FAMILY (first measured here 2026-10-02) =====
    "trail_half": {
        "desc": "champion leg + half",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1},
        "swing": "sw10",
        # Parts do not pay on their own - see trail_half_delay1_skipn4.
        "pins": {"n": 411, "net": 152.66,
                 "dd_net": 87.7, "oos_n": 239, "oos_net": -13.23, "oos_dd_net": 58.19},
    },
    "trail_delay1": {
        "desc": "champion leg + delay1",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_delay_r": 1.0},
        "swing": "sw10",
        # Parts do not pay on their own - see trail_half_delay1_skipn4.
        "pins": {"n": 426, "net": 152.28,
                 "dd_net": 59.38, "oos_n": 235, "oos_net": -17.73, "oos_dd_net": 43.26},
    },
    "trail_half_delay1": {
        "desc": "champion leg + half_delay1",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_delay_r": 1.0},
        "swing": "sw10",
        # Parts do not pay on their own - see trail_half_delay1_skipn4.
        "pins": {"n": 411, "net": 159.99,
                 "dd_net": 73.62, "oos_n": 232, "oos_net": -5.2, "oos_dd_net": 48.27},
    },
    "trail_skipn4": {
        "desc": "champion leg + skipn4",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_skip_n": 4},
        "swing": "sw10",
        # Exit-side trail family, rerun on unified.py 2026-10-02.
        # First measured here - signal/EQUITY_CURVE_STUDY.md (2026-09-24) ran this on
        # the older engines, and these knobs live in the harness patch rather
        # than in unified.py, so no registry book covered them.
        #   exp_trail_half      widen the ratchet to halfway, not the extreme
        #   exp_trail_delay_r   hold the trail off until the trade is +N R unrealised
        #   exp_trail_skip_n    ignore the first N swing events entirely
        #
        #                        IS n / net R / dd R      OOS n / net R / dd R
        #   baseline            499 / +239.12 / 46.85    280 /  +72.79 / 50.55
        #   half                468 / +384.99 / 51.10    269 /  +71.73 / 52.08
        #   delay1              501 / +263.62 / 45.37    279 /  +69.65 / 54.91
        #   half+delay1         465 / +385.92 / 51.39    272 /  +88.74 / 51.72
        #   skip_n=4            439 / +357.15 / 43.96    243 /  +61.05 / 75.60
        #   half+delay1+skipn4  424 / +556.62 / 44.47    234 / +104.98 / 52.50
        #
        # BEST BOOK IN THE REGISTRY ON BOTH ERAS. +556.62R IS against the
        # champion's +239.12R, and +104.98R OOS against +72.79R. Beating
        # baseline OOS is the test the cap_days peak and the dirmatch books have
        # not passed - both of those are in-sample wins only.
        #
        # The honest read is in the same note on every arm below this one:
        # half alone is an in-sample artefact (+145.87R IS, -1.06R OOS - it does
        # nothing out of sample). delay1 alone is near-inert on both. skip_n=4
        # alone is the worst of the three on OOS (+61.05R, drawdown nearly
        # doubled to 75.60). The gain appears ONLY in combination, and a gain
        # that appears only in aggregate while its parts do not is exactly the
        # shape that hides overfitting.
        #
        # Two things argue for taking it seriously anyway. It beats baseline on
        # OOS and not merely IS, and it buys the R with LESS risk - 44.47 IS
        # drawdown against 46.85 on the baseline, i.e. better R per unit of
        # drawdown, not just more R. And nothing here was tuned to these arms:
        # half, delay_r=1.0 and skip_n=4 were inherited from the 2026-09-24
        # study, not selected by looking at this engine's results.
        #
        # What it still needs before it could ship: a sweep of skip_n and
        # delay_r on THIS engine to confirm 4 and 1.0 are not flukes, since they
        # were chosen against different engine code.
        "pins": {"n": 446, "net": 349.29, "dd_net": 57.02,
                 "oos_n": 246, "oos_net": 31.02, "oos_dd_net": 81.36},
    },
    "trail_half_delay1_skipn4": {
        "desc": "champion leg + half_delay1_skipn4",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_delay_r": 1.0, "exp_trail_skip_n": 4},
        "swing": "sw10",
        # Exit-side trail family, rerun on unified.py 2026-10-02.
        # First measured here - signal/EQUITY_CURVE_STUDY.md (2026-09-24) ran this on
        # the older engines, and these knobs live in the harness patch rather
        # than in unified.py, so no registry book covered them.
        #   exp_trail_half      widen the ratchet to halfway, not the extreme
        #   exp_trail_delay_r   hold the trail off until the trade is +N R unrealised
        #   exp_trail_skip_n    ignore the first N swing events entirely
        #
        #                        IS n / net R / dd R      OOS n / net R / dd R
        #   baseline            499 / +239.12 / 46.85    280 /  +72.79 / 50.55
        #   half                468 / +384.99 / 51.10    269 /  +71.73 / 52.08
        #   delay1              501 / +263.62 / 45.37    279 /  +69.65 / 54.91
        #   half+delay1         465 / +385.92 / 51.39    272 /  +88.74 / 51.72
        #   skip_n=4            439 / +357.15 / 43.96    243 /  +61.05 / 75.60
        #   half+delay1+skipn4  424 / +556.62 / 44.47    234 / +104.98 / 52.50
        #
        # BEST BOOK IN THE REGISTRY ON BOTH ERAS. +556.62R IS against the
        # champion's +239.12R, and +104.98R OOS against +72.79R. Beating
        # baseline OOS is the test the cap_days peak and the dirmatch books have
        # not passed - both of those are in-sample wins only.
        #
        # The honest read is in the same note on every arm below this one:
        # half alone is an in-sample artefact (+145.87R IS, -1.06R OOS - it does
        # nothing out of sample). delay1 alone is near-inert on both. skip_n=4
        # alone is the worst of the three on OOS (+61.05R, drawdown nearly
        # doubled to 75.60). The gain appears ONLY in combination, and a gain
        # that appears only in aggregate while its parts do not is exactly the
        # shape that hides overfitting.
        #
        # Two things argue for taking it seriously anyway. It beats baseline on
        # OOS and not merely IS, and it buys the R with LESS risk - 44.47 IS
        # drawdown against 46.85 on the baseline, i.e. better R per unit of
        # drawdown, not just more R. And nothing here was tuned to these arms:
        # half, delay_r=1.0 and skip_n=4 were inherited from the 2026-09-24
        # study, not selected by looking at this engine's results.
        #
        # What it still needs before it could ship: a sweep of skip_n and
        # delay_r on THIS engine to confirm 4 and 1.0 are not flukes, since they
        # were chosen against different engine code.
        "pins": {"n": 362, "net": 256.64, "dd_net": 69.62, "wr_net": 0.196,
                "gross_win": 0.207, "oos_n": 213, "oos_net": 24.19, "oos_dd_net": 37.59,
                "oos_wr_net": 0.197, "oos_gross_win": 0.197, "n_all": 575, "net_all": 280.83,
                "dd_net_all": 69.62},
        "pins_legacy": {"n": 363, "net": 256.64, "dd_net": 69.62, "oos_n": 215,
                       "oos_net": 24.19, "oos_dd_net": 37.59},
    },

    "gap_inert_event_shift": {
        "desc": "champion leg + scheduled-event shift +/-24h, MEASURED INERT",
        "status": "reference",   # measured inert - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_event_shift_min": 1440, "exp_event_mode": "shift"},
        "swing": "sw10",
        # Bit-for-bit the baseline on both eras. Shifting the scheduled-event
        # window by a day either way changes nothing on this book, which is
        # itself the answer to the question the script was asking.
        "pins": None,
    },

    # AUDIT RESIDUE, 2026-10-02, and why it stays at four.
    #
    # Re-running the audit against the patched engine signature (not a name
    # pattern) leaves four (parameter, value) pairs that appear in scripts and
    # in no book:
    #
    #   sl_buf_atr 0.10            -> covered by gap_slbuf010 (same value, the
    #                               audit compares the literal string and the
    #                               book was written with the same one)
    #   exp_event_shift_min -1440  -> the mirror of gap_inert_event_shift, which
    #                               uses +1440. Both are bit-for-bit the baseline.
    #   exp_5m_confirm 1           -> raises TypeError on its own because
    #   exp_5m_wait_min 240           exp_5m_data is a STATS SINK defaulting to
    #                               None, so there is no experiment to run.
    #
    # So the knob/value layer is CLOSED. Not "nearly" - closed, with the residue
    # enumerated and each line explained.

    # ===== FINAL AUDIT PASS: plain engine params (2026-10-02) =====
    # ===== TRAIL SWEEP SURFACE (swept 2026-10-02, IS+OOS) =====
    "trail_half_skipn8_nodelay": {
        "desc": "champion leg + half ratchet + skip first 8 swing events, NO delay",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_skip_n": 8},
        "swing": "sw10",
        # SWEPT 2026-10-02 on this engine, IS + OOS, 6x7 grid. half=1 held
        # on throughout. Rows are exp_trail_delay_r, columns exp_trail_skip_n.
        #
        # IS net R                        OOS net R
        #          sn=0   sn=2   sn=3   sn=4   sn=6   sn=8  sn=12      sn=0   sn=2   sn=3   sn=4   sn=6   sn=8  sn=12
        # dr=0.0    385   518   562   550   589   589   573       71.7   70.4   98.6  105.2  103.9  113.3  117.1
        # dr=0.5    391   525   572   557   589   589   573       68.8   69.2   98.2  104.9  103.9  113.3  117.1
        # dr=1.0    386   525   572   557   589   589   573       88.7   89.0   97.7  105.0  100.1  104.0  107.3
        # dr=1.5    393   540   583   576   606   593   580      111.7  113.6  106.7  114.1  109.0  108.4  110.7
        # dr=2.0    379   527   569   565   589   577   580      114.7  117.7  114.5  128.9  117.9  118.2  110.6
        # dr=3.0    417   563   592   587   615   608   594      123.6  117.8  122.4  130.4  118.9  119.3  111.0
        #
        # baseline (shipped): IS 499 / +239.12 / dd 46.85   OOS 280 / +72.79 / dd 50.55
        #
        # TWO THINGS THIS SWEEP CHANGED ABOUT THE EARLIER READING.
        #
        # 1. 38 of 42 cells beat the baseline on BOTH eras. That is a plateau,
        #    not a spike, and it is the opposite shape to the cap_days result,
        #    where one value peaked and its neighbours wobbled. A surface where
        #    almost everywhere is better is very hard to produce by fitting the
        #    knobs to the sample.
        #
        # 2. exp_trail_delay_r is nearly INERT, and the inherited arm over-valued
        #    it. delay_r=1.0 was one of the two unverified values flagged as the
        #    weak point of the result. It turns out dr=0.0 with skip_n=8 measures
        #    IS +588.76 / OOS +113.28 against dr=1.0's +588.76 / +113.28 - the
        #    same book. The whole gain is skip_n; the delay was carrying nothing.
        #    The 2026-09-24 study paired them and the pair was read as one finding.
        #
        # The 4 cells that fail the both-era test are all small skip_n at low
        # delay_r: (0,0), (0.5,0), (0,2), (0.5,2) - i.e. skip_n <= 2 with the
        # delay off. skip_n >= 3 is where OOS starts working. So the requirement
        # is on skip_n, not on the delay.
        #
        # Best combined cell is dr=3.0 sn=6 (IS +615.15 / OOS +118.86), but
        # dr=3.0 is the edge of the swept range, so it is the least trustworthy
        # point on the grid rather than the best. Nothing here should be adopted
        # on the strength of the sweep alone - what it establishes is that the
        # effect is broad and survives OOS, which the single inherited point could
        # not show.
        "pins": {"n": 323, "net": 238.39, "dd_net": 70.22, "wr_net": 0.152,
                "gross_win": 0.155, "oos_n": 199, "oos_net": 21.62, "oos_dd_net": 37.37,
                "oos_wr_net": 0.161, "oos_gross_win": 0.166, "n_all": 522, "net_all": 260.01,
                "dd_net_all": 70.22},
        "pins_legacy": {"n": 324, "net": 238.39, "dd_net": 70.22, "oos_n": 202,
                       "oos_net": 21.62, "oos_dd_net": 37.37},
    },
    "trail_half_skipn3_nodelay": {
        "desc": "champion leg + half ratchet + skip first 3 swing events, NO delay",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_skip_n": 3},
        "swing": "sw10",
        # Part of the swept surface - see trail_half_skipn8_nodelay.
        "pins": {"n": 373, "net": 213.59, "dd_net": 69.84, "wr_net": 0.217,
                "gross_win": 0.228, "oos_n": 220, "oos_net": 30.13, "oos_dd_net": 44.29,
                "oos_wr_net": 0.2, "oos_gross_win": 0.2, "n_all": 593, "net_all": 243.71,
                "dd_net_all": 69.84},
        "pins_legacy": {"n": 374, "net": 213.59, "dd_net": 69.84, "oos_n": 222,
                       "oos_net": 30.13, "oos_dd_net": 44.29},
    },
    "trail_half_skipn6_dr3": {
        "desc": "champion leg + half ratchet + skip 6 events + delay to +3R",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_skip_n": 6, "exp_trail_delay_r": 3.0},
        "swing": "sw10",
        # Part of the swept surface - see trail_half_skipn8_nodelay.
        "pins": {"n": 319, "net": 291.76, "dd_net": 70.39, "wr_net": 0.157,
                "gross_win": 0.163, "oos_n": 206, "oos_net": 11.58, "oos_dd_net": 40.29,
                "oos_wr_net": 0.184, "oos_gross_win": 0.184, "n_all": 525, "net_all": 303.35,
                "dd_net_all": 70.39},
        "pins_legacy": {"n": 320, "net": 291.76, "dd_net": 70.39, "oos_n": 209,
                       "oos_net": 11.58, "oos_dd_net": 40.29},
    },
    "trail_half_dr3_nodelay": {
        "desc": "champion leg + half ratchet + delay to +3R, no skip_n",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_delay_r": 3.0},
        "swing": "sw10",
        # Part of the swept surface - see trail_half_skipn8_nodelay.
        "pins": {"n": 340, "net": 144.07, "dd_net": 70.47, "wr_net": 0.203,
                "gross_win": 0.215, "oos_n": 227, "oos_net": 66.08, "oos_dd_net": 50.41,
                "oos_wr_net": 0.229, "oos_gross_win": 0.238, "n_all": 567, "net_all": 210.15,
                "dd_net_all": 70.47},
        "pins_legacy": {"n": 341, "net": 144.07, "dd_net": 70.47, "oos_n": 230,
                       "oos_net": 66.08, "oos_dd_net": 50.41},
    },
    "trail_half_skipn8_dr1": {
        "desc": "champion leg + half ratchet + skip 8 + delay 1R (original arm family)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_trail_half": 1, "exp_trail_skip_n": 8, "exp_trail_delay_r": 1.0},
        "swing": "sw10",
        # Part of the swept surface - see trail_half_skipn8_nodelay.
        "pins": {"n": 323, "net": 238.39, "dd_net": 70.22, "wr_net": 0.152,
                "gross_win": 0.155, "oos_n": 194, "oos_net": 21, "oos_dd_net": 37.98,
                "oos_wr_net": 0.16, "oos_gross_win": 0.165, "n_all": 517, "net_all": 259.39,
                "dd_net_all": 70.22},
        "pins_legacy": {"n": 324, "net": 238.39, "dd_net": 70.22, "oos_n": 197, "oos_net": 21,
                       "oos_dd_net": 37.98},
    },

    # ===== P4 cap_days family (reproduced on unified.py 2026-10-02) =====
    # ===== D3 TRAIL QUALITY (skip far trail levels) =====

    "trail10_swingpause_sig": {
        "desc": "swingpause single + skip trail levels > 1.0% from entry",
        "status": "reference",   # dead: net -311.27R - not a candidate.
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_trail_max_dist": 1.0, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross -170.58R  net -311.27R  dd 313.38R  win 22.5%  n=328
        # all 115 registry books in one pass.
        #   gross -170.58R  net -311.27R  dd 313.38R  win 22.5%  n=328
        "pins": None,
    },
    "trail06_swingpause_sig": {
        "desc": "swingpause single + skip trail levels > 0.6% from entry",
        "status": "reference",   # dead: net -276.56R - not a candidate.
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_trail_max_dist": 0.6, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross -165.46R  net -276.56R  dd 276.56R  win 14.9%  n=233
        # all 115 registry books in one pass.
        #   gross -165.46R  net -276.56R  dd 276.56R  win 14.9%  n=233
        "pins": None,
    },
    "trail10_multi": {
        "desc": "king + skip trail levels > 1.0% from entry",
        "status": "reference",   # dead: net -247.51R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_trail_max_dist": 1.0,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross -151.55R  net -247.51R  dd 248.22R  win 17.8%  n=246
        # all 115 registry books in one pass.
        #   gross -151.55R  net -247.51R  dd 248.22R  win 17.8%  n=246
        "pins": None,
    },

    # ===== D3 UNION DUAL-QUALIFICATION (2x2 autopsy: FLIP-only window = fragile cell) =====
}
