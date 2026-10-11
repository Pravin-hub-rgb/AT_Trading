"""RISK - decay gates, window caps, risk width, entry quality, baselines.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {
    # ===== P36 DECAY GATE (engine knob, measured 2026-10-02 IS+OOS) =====
    "decayA_c": {
        "desc": "champion leg + decay off (control)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg"},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 500, "net": 247.21,
                 "dd_net": 43.47, "oos_n": 289, "oos_net": 72.95, "oos_dd_net": 55.18},
    },
    "decayA_u": {
        "desc": "utcsat + decay off (control)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 458, "net": 261.85,
                 "dd_net": 46.31, "oos_n": 259, "oos_net": 102.43, "oos_dd_net": 22.86},
    },
    "decayB_c": {
        "desc": "champion leg + decay block when BUYING decay >= 0.75",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 1},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 308, "net": 242.86,
                 "dd_net": 32.62, "oos_n": 151, "oos_net": 90.22, "oos_dd_net": 26.5},
    },
    "decayB_u": {
        "desc": "utcsat + decay block when BUYING decay >= 0.75",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 1},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 269, "net": 291.39,
                 "dd_net": 29.05, "oos_n": 133, "oos_net": 92.02, "oos_dd_net": 23.56},
    },
    "decayC_c": {
        "desc": "champion leg + decay block when SELLING decay >= 0.75",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 2},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 301, "net": 84.74,
                 "dd_net": 44.66, "oos_n": 173, "oos_net": 68.75, "oos_dd_net": 34.79},
    },
    "decayC_u": {
        "desc": "utcsat + decay block when SELLING decay >= 0.75",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 2},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 270, "net": 117.79,
                 "dd_net": 36.96, "oos_n": 148, "oos_net": 69.14, "oos_dd_net": 20.33},
    },
    "decayD_c": {
        "desc": "champion leg + decay block long on buying decay, short on selling decay",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 3},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 352, "net": 204.23, "dd_net": 33.05,
                 "oos_n": 178, "oos_net": 44.55, "oos_dd_net": 49.32},
    },
    "decayD_u": {
        "desc": "utcsat + decay block long on buying decay, short on selling decay",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 3},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 320, "net": 222.72,
                 "dd_net": 37.68, "oos_n": 165, "oos_net": 75.16, "oos_dd_net": 29.82},
    },
    "decayE_c": {
        "desc": "champion leg + decay block long on SELLING decay, short on buying decay (crossed)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 4},
        "swing": "sw10",
        # P36 DECAY GATE, measured as an ENTRY-TIME engine gate on 2026-10-02.
        # Before this the decay rules existed only in exp_decay_*.py as a post-hoc
        # filter over trades the engine had already booked, which is why no registry
        # book existed for them. They are now real knobs (exp_decay_mode/thr/legs).
        #
        # Decay = of the last N CONFIRMED 15m legs in a direction, the fraction whose
        # start level broke. An up-leg defends its start low. Causal: a leg is read
        # only once confirmed at or before the entry bar.
        #
        # Rule          IS n / net / dd              OOS n / net / dd
        # A off       499 / +239.12 / 46.85       280 /  +72.79 / 50.55
        # B <-buying  303 / +263.90 / 30.18       146 /  +70.97 / 16.32
        # C <-selling 299 / +154.64 / 34.02       166 /  +58.98 / 35.42
        # D own side  353 / +194.24 / 33.05       176 /  +45.26 / 48.53
        # E crossed   245 / +254.21 / 28.76       139 /  +95.96 / 15.13  <- best OOS
        # F allow x   206 /  -43.62 / 66.80       135 /  -29.30 / 37.55
        # G allow own 148 /  +40.92 / 57.57       108 /   -5.13 / 22.61
        # H allow eith261 /  +17.03 / 59.13       146 /  -21.82 / 41.72
        #
        # Same shape on utcsat_multi_sw10: E crossed OOS +94.53 / dd 17.18 against
        # the +66.90 / 24.64 baseline. E wins on BOTH books out of sample.
        #
        # Two things worth keeping in view. First, IS and OOS disagree about which
        # rule is best - B is the best IS rule on both books and is roughly flat OOS,
        # while E is mid-pack IS and the best OOS by a wide margin. Second, every
        # ALLOW rule is bad, and F is the exact mirror of E differing only in sign,
        # so the decay signal is directional: it tells you which side NOT to take.
        # It is not a standalone entry signal.
        "pins": {"n": 258, "net": 169.18,
                 "dd_net": 40.22, "oos_n": 140, "oos_net": 97.44, "oos_dd_net": 16.07},
    },
    "decayE_u": {
        "desc": "utcsat + decay block long on SELLING decay, short on buying decay (crossed)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 4},
        "swing": "sw10",
        # P36 DECAY GATE, measured as an ENTRY-TIME engine gate on 2026-10-02.
        # Before this the decay rules existed only in exp_decay_*.py as a post-hoc
        # filter over trades the engine had already booked, which is why no registry
        # book existed for them. They are now real knobs (exp_decay_mode/thr/legs).
        #
        # Decay = of the last N CONFIRMED 15m legs in a direction, the fraction whose
        # start level broke. An up-leg defends its start low. Causal: a leg is read
        # only once confirmed at or before the entry bar.
        #
        # Rule          IS n / net / dd              OOS n / net / dd
        # A off       499 / +239.12 / 46.85       280 /  +72.79 / 50.55
        # B <-buying  303 / +263.90 / 30.18       146 /  +70.97 / 16.32
        # C <-selling 299 / +154.64 / 34.02       166 /  +58.98 / 35.42
        # D own side  353 / +194.24 / 33.05       176 /  +45.26 / 48.53
        # E crossed   245 / +254.21 / 28.76       139 /  +95.96 / 15.13  <- best OOS
        # F allow x   206 /  -43.62 / 66.80       135 /  -29.30 / 37.55
        # G allow own 148 /  +40.92 / 57.57       108 /   -5.13 / 22.61
        # H allow eith261 /  +17.03 / 59.13       146 /  -21.82 / 41.72
        #
        # Same shape on utcsat_multi_sw10: E crossed OOS +94.53 / dd 17.18 against
        # the +66.90 / 24.64 baseline. E wins on BOTH books out of sample.
        #
        # Two things worth keeping in view. First, IS and OOS disagree about which
        # rule is best - B is the best IS rule on both books and is roughly flat OOS,
        # while E is mid-pack IS and the best OOS by a wide margin. Second, every
        # ALLOW rule is bad, and F is the exact mirror of E differing only in sign,
        # so the decay signal is directional: it tells you which side NOT to take.
        # It is not a standalone entry signal.
        "pins": {"n": 223, "net": 177.32,
                 "dd_net": 27.58, "oos_n": 122, "oos_net": 105.88, "oos_dd_net": 15.43},
    },
    "decayF_c": {
        "desc": "champion leg + decay ALLOW crossed only (mirror of E)",
        "status": "reference",   # dead: net -43.62R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 5},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": None,
    },
    "decayF_u": {
        "desc": "utcsat + decay ALLOW crossed only (mirror of E)",
        "status": "reference",   # dead: net -21.96R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 5},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": None,
    },
    "decayG_c": {
        "desc": "champion leg + decay ALLOW own side only",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 7},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 154, "net": 42.27, "dd_net": 57.96,
                 "oos_n": 112, "oos_net": -18.25, "oos_dd_net": 34.73},
    },
    "decayG_u": {
        "desc": "utcsat + decay ALLOW own side only",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 7},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 145, "net": 52.88, "dd_net": 43.38,
                 "oos_n": 97, "oos_net": 9.54, "oos_dd_net": 17.49},
    },
    "decayH_c": {
        "desc": "champion leg + decay ALLOW either broken",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg",
                    "exp_decay_mode": 8},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 266, "net": 23.63, "dd_net": 54.02,
                 "oos_n": 148, "oos_net": -24.44, "oos_dd_net": 44.42},
    },
    "decayH_u": {
        "desc": "utcsat + decay ALLOW either broken",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_skip_utc_sat": 1,
                    "exp_decay_mode": 8},
        "swing": "sw10",
        # Part of the P36 decay grid - see decayE_*.
        "pins": {"n": 250, "net": 43.24, "dd_net": 45.9,
                 "oos_n": 134, "oos_net": -32.59, "oos_dd_net": 39.49},
    },

    # ===== TRAIL SWEEP SURFACE (swept 2026-10-02, IS+OOS) =====
    # ===== P4 cap_days family (reproduced on unified.py 2026-10-02) =====
    "cap1d": {
        "desc": "cap_days 1 days",
        "status": "reference",   # dead: net -49.73R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 1},
        "swing": "sw10",
        "pins": None,
    },
    "cap4d": {
        "desc": "cap_days 4 days",
        "status": "reference",   # dead: net -35.21R - not a candidate.
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 4},
        "swing": "sw10",
        "pins": None,
    },
    "cap8d": {
        "desc": "cap_days 8 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 8},
        "swing": "sw10",
        "pins": {"n": 474, "net": 165.56, "dd_net": 41.02,
                 "oos_n": 277, "oos_net": 49.57, "oos_dd_net": 58.4},
    },
    "cap12d": {
        "desc": "cap_days 12 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 12},
        "swing": "sw10",
        "pins": {"n": 484, "net": 136.52,
                 "dd_net": 42.67, "oos_n": 284, "oos_net": 70.39, "oos_dd_net": 56.83},
    },
    "cap16d": {
        "desc": "cap_days 16 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 16},
        "swing": "sw10",
        # cap_days family, reproduced on unified.py 2026-10-02.
        # method/CAPS_P49.md reported this direction but could not be reproduced here:
        # cap_days=16 was hardcoded at all three HTF window call sites, so there
        # was no knob to turn. It is now exp_cap_days, default still 16.
        #
        # Champion, cap_days -> n / net R / dd R:
        #    1   236 /  -49.73 /  84.28      16  499 / +239.12 / 46.85
        #    4   385 /  -35.21 /  57.45      20  498 / +269.60 / 46.03
        #    8   472 / +185.83 /  47.32      24  510 / +248.83 / 46.68
        #   12   471 / +153.72 /  46.71      32  522 / +375.53 / 48.39
        #                                     48  556 / +351.27 / 54.25
        #                                    999  592 / +360.87 / 54.25
        # utcsat: 16 -> 453 / +279.47 / 35.54   999 -> 537 / +336.98 / 42.82
        #
        # P49's direction reproduces: removing the cap is positive on both books
        # and ADDS trades (+93 champion, +84 utcsat) rather than removing them,
        # which is the opposite of what a brake does. The cap was only ever
        # truncating windows that were still open and still working.
        #
        # NOT an adoption, for the reasons P49 itself gives and which still hold.
        # The sweep is not monotone - 12 is worse than 8, and 32 is the peak while
        # 999 is lower. A non-monotone curve means any single good value is partly
        # noise. The finding is the direction, not a number. Note also that the
        # peak here is 32 (+375.53R), not "off" - so the honest reading is that
        # 16 is simply too tight, not that no cap is best.
        "pins": {"n": 500, "net": 247.21,
                 "dd_net": 43.47, "oos_n": 289, "oos_net": 72.95, "oos_dd_net": 55.18},
    },
    "cap20d": {
        "desc": "cap_days 20 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 20},
        "swing": "sw10",
        "pins": {"n": 512, "net": 279.74,
                 "dd_net": 42.02, "oos_n": 296, "oos_net": 83.47, "oos_dd_net": 43.93},
    },
    "cap24d": {
        "desc": "cap_days 24 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 24},
        "swing": "sw10",
        "pins": {"n": 515, "net": 303.49, "dd_net": 43.49,
                 "oos_n": 301, "oos_net": -6.51, "oos_dd_net": 54.76},
    },
    "cap32d": {
        "desc": "cap_days 32 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 32},
        "swing": "sw10",
        "pins": {"n": 524, "net": 368.35,
                 "dd_net": 39.37, "oos_n": 292, "oos_net": 59.75, "oos_dd_net": 58.01},
    },
    "cap48d": {
        "desc": "cap_days 48 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 48},
        "swing": "sw10",
        "pins": {"n": 543, "net": 350.74,
                 "dd_net": 39.37, "oos_n": 304, "oos_net": 62.98, "oos_dd_net": 57.24},
    },
    "cap999_nocap": {
        "desc": "cap_days no cap (999)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 999},
        "swing": "sw10",
        # cap_days family, reproduced on unified.py 2026-10-02.
        # method/CAPS_P49.md reported this direction but could not be reproduced here:
        # cap_days=16 was hardcoded at all three HTF window call sites, so there
        # was no knob to turn. It is now exp_cap_days, default still 16.
        #
        # Champion, cap_days -> n / net R / dd R:
        #    1   236 /  -49.73 /  84.28      16  499 / +239.12 / 46.85
        #    4   385 /  -35.21 /  57.45      20  498 / +269.60 / 46.03
        #    8   472 / +185.83 /  47.32      24  510 / +248.83 / 46.68
        #   12   471 / +153.72 /  46.71      32  522 / +375.53 / 48.39
        #                                     48  556 / +351.27 / 54.25
        #                                    999  592 / +360.87 / 54.25
        # utcsat: 16 -> 453 / +279.47 / 35.54   999 -> 537 / +336.98 / 42.82
        #
        # P49's direction reproduces: removing the cap is positive on both books
        # and ADDS trades (+93 champion, +84 utcsat) rather than removing them,
        # which is the opposite of what a brake does. The cap was only ever
        # truncating windows that were still open and still working.
        #
        # NOT an adoption, for the reasons P49 itself gives and which still hold.
        # The sweep is not monotone - 12 is worse than 8, and 32 is the peak while
        # 999 is lower. A non-monotone curve means any single good value is partly
        # noise. The finding is the direction, not a number. Note also that the
        # peak here is 32 (+375.53R), not "off" - so the honest reading is that
        # 16 is simply too tight, not that no cap is best.
        "pins": {"n": 575, "net": 366.94,
                 "dd_net": 39.37, "oos_n": 315, "oos_net": 111.41, "oos_dd_net": 55},
    },
    "utcsat_cap16d": {
        "desc": "cap_days 16 days",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 16, "exp_skip_utc_sat": 1},
        "swing": "sw10",
        "pins": {"n": 458, "net": 261.85,
                 "dd_net": 46.31, "oos_n": 259, "oos_net": 102.43, "oos_dd_net": 22.86},
    },
    "utcsat_cap999_nocap": {
        "desc": "cap_days no cap (999)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg", "exp_cap_days": 999, "exp_skip_utc_sat": 1},
        "swing": "sw10",
        # cap_days family, reproduced on unified.py 2026-10-02.
        # method/CAPS_P49.md reported this direction but could not be reproduced here:
        # cap_days=16 was hardcoded at all three HTF window call sites, so there
        # was no knob to turn. It is now exp_cap_days, default still 16.
        #
        # Champion, cap_days -> n / net R / dd R:
        #    1   236 /  -49.73 /  84.28      16  499 / +239.12 / 46.85
        #    4   385 /  -35.21 /  57.45      20  498 / +269.60 / 46.03
        #    8   472 / +185.83 /  47.32      24  510 / +248.83 / 46.68
        #   12   471 / +153.72 /  46.71      32  522 / +375.53 / 48.39
        #                                     48  556 / +351.27 / 54.25
        #                                    999  592 / +360.87 / 54.25
        # utcsat: 16 -> 453 / +279.47 / 35.54   999 -> 537 / +336.98 / 42.82
        #
        # P49's direction reproduces: removing the cap is positive on both books
        # and ADDS trades (+93 champion, +84 utcsat) rather than removing them,
        # which is the opposite of what a brake does. The cap was only ever
        # truncating windows that were still open and still working.
        #
        # NOT an adoption, for the reasons P49 itself gives and which still hold.
        # The sweep is not monotone - 12 is worse than 8, and 32 is the peak while
        # 999 is lower. A non-monotone curve means any single good value is partly
        # noise. The finding is the direction, not a number. Note also that the
        # peak here is 32 (+375.53R), not "off" - so the honest reading is that
        # 16 is simply too tight, not that no cap is best.
        "pins": {"n": 518, "net": 340.79,
                 "dd_net": 34.74, "oos_n": 278, "oos_net": 134.92, "oos_dd_net": 28.93},
    },

    # ===== OPTIMAL LANES (from exp37, fine fills, corrected engine) =====
    # ===== ENTRY-1 VARIANTS (leg_no_entry pivot rule) =====
    # champion_multi_sw10_entry1 - the proposed ENTRY-1 variant
    # leg_no_entry + exp_ltf_no_entry=0: causal SL, exclude entry bar from leg extreme
    "champion_multi_sw10_entry1": {
        "desc": "Champion multi sw10 - ENTRY-1 variant, leg_no_entry pivot, no LTF entry-bar skip. "
                "Causal SL, entry bar excluded from leg extreme. 500 trades on IS.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg_no_entry",
                    "exp_ltf_no_entry": 0},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=500 net=325.75. Full sweep incl. gross/dd/win-rate:
        #   gross +445.19R  net +325.75R  dd 27.72R  win 30.0%  n=500
        # MEASURED 2026-10-02: 500 / +445.19 gross, +325.75 net. The pin was first
        # written with the gross figure in the net field, which the runner does not
        # check against - it silently passed because n matched and net was not
        # compared against gross.
        # pin was n=500 net=325.75; now n=500 net=325.75 (win rate 30.0%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 499, "net": 283.7,
                 "dd_net": 43.69, "oos_n": 289, "oos_net": 74.76, "oos_dd_net": 53.01},
    },

    # champion_multi_sw10_leg_no_entry - NEW variant with LTF entry-bar skip
    # leg_no_entry + exp_ltf_no_entry=1: causal SL, exclude entry bar, AND skip LTF entry bar
    "champion_multi_sw10_leg_no_entry": {
        "desc": "Champion multi sw10 - NEW variant, leg_no_entry pivot with LTF entry-bar skip. "
                "Causal SL, entry bar excluded from leg extreme, skip LTF entry bar on signal.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg_no_entry",
                    "exp_ltf_no_entry": 1},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=500 net=325.75. Full sweep incl. gross/dd/win-rate:
        #   gross +445.19R  net +325.75R  dd 27.72R  win 30.0%  n=500
        # MEASURED 2026-10-02: 500 / +325.7 net, identical to champion_multi_sw10_entry1.
        # Its exp_ltf_no_entry=1 does nothing on its own - without exp_causal_sl=1 the
        # LTF leg reads sig["swing_start_px"], which pivot_rule already sets. This is
        # therefore the same book as entry1 under a second name. The version that
        # actually differs on both legs is champion_multi_sw10_entry_both.
        # pin was n=500 net=325.75; now n=500 net=325.75 (win rate 30.0%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # KNOB SATURATION: champion_multi_sw10_entry1 differs in config but lands on the same
        # 500 trades / +325.75R / 27.72R drawdown. The differing knob does not bind
        # in this range - saturated, not equivalent. Kept as its own entry so the
        # knob stays visible; do not read the tie as "same book".
        # exp_ltf_no_entry 1 vs 0.
        "pins": {"n": 499, "net": 283.7,
                 "dd_net": 43.69, "oos_n": 289, "oos_net": 74.76, "oos_dd_net": 53.01},
    },

    # ===== BASELINES (no partial, for delta measurement) =====
    # ===== BASELINES (no partial, for delta measurement) =====

    "baseline_no_partial_sw20": {
        "desc": "Champion config without partial exits sw20 (baseline, +122.3 post trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "window_end": "exit"},
        "swing": "sw20",
        # pin was n=372 net=122.3; now n=496 net=232.38 (win rate 31.9%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=496 net=232.38. Full sweep incl. gross/dd/win-rate:
        #   gross +348.67R  net +232.38R  dd 61.58R  win 31.9%  n=496
        "pins": {"n": 497, "net": 236.65, "dd_net": 56.34,
                 "oos_n": 275, "oos_net": -11.82, "oos_dd_net": 61.17},
    },
    "baseline_no_partial_sw10": {
        "desc": "Champion config without partial exits sw10 (baseline, +137.7 post trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=395 net=137.7; now n=502 net=238.45 (win rate 30.3%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=502 net=238.45. Full sweep incl. gross/dd/win-rate:
        #   gross +354.08R  net +238.45R  dd 53.86R  win 30.3%  n=502
        "pins": {"n": 506, "net": 267.7,
                 "dd_net": 46.54, "oos_n": 300, "oos_net": 65.74, "oos_dd_net": 60.07},
    },

    # ===== D3 COOLDOWN FAMILY (loss-reactive window skip / swing pause) =====
    # ===== D3 RISK-WIDTH FAMILY (skip stale/stretched breaks) =====

    "rmax15_swingpause_sig_sw10": {
        "desc": "swingpause single + skip entries with stop width over 1.5% of price — DEAD (cascade)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_risk_max_pct": 1.5, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=310 net=91.7; now n=376 net=187.78 (win rate 26.9%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=376 net=187.78. Full sweep incl. gross/dd/win-rate:
        #   gross +290.57R  net +187.78R  dd 57.54R  win 26.9%  n=376
        "pins": {"n": 314, "net": 132.0, "dd_net": 49.01, "win": 0.236,
                 "oos_n": 156, "oos_net": -51.65, "oos_dd_net": 56.81, "oos_win": 0.128},
    },
    "rmax10_swingpause_sig_sw10": {
        "desc": "swingpause single + skip entries with stop width over 1.0% of price — DEAD",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_risk_max_pct": 1.0, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=255 net=195.5; now n=294 net=228.59 (win rate 23.8%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=294 net=228.59. Full sweep incl. gross/dd/win-rate:
        #   gross +323.62R  net +228.59R  dd 47.91R  win 23.8%  n=294
        "pins": {"n": 258, "net": 180.04, "dd_net": 53.09, "win": 0.202,
                 "oos_n": 91, "oos_net": -31.84, "oos_dd_net": 45.17, "oos_win": 0.11},
    },
    "rmax15_multi_sw10": {
        "desc": "king + skip entries with stop width over 1.5% of price — DEAD (cascade)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_risk_max_pct": 1.5, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=406 net=259.4; now n=407 net=255.56 (win rate 27.5%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=407 net=255.56. Full sweep incl. gross/dd/win-rate:
        #   gross +371.60R  net +255.56R  dd 50.19R  win 27.5%  n=407
        "pins": {"n": 412, "net": 266.92, "dd_net": 49.35,
                 "oos_n": 170, "oos_net": -3.58, "oos_dd_net": 46.67},
    },

    # ===== D3 LTF REGIME FAMILY (chop15 transition band + ATR blow-off) =====
    # ===== SHIPPED BASELINE (identity gate reference) =====
    #
    # REMOVED 2026-10-02: "_shipped_coarse_618" (pins 340 / +225.3R) and
    # "_shipped_fine_58" (pins 351 / +211.7R). Deleted rather than re-anchored,
    # and that is the point.
    #
    # These were observations, not specs. Nothing independent said "the engine
    # should print 340 on the coarse basis"; they recorded what one module
    # printed once, through an import that has since been repointed from
    # v18_streak_halt to unified. Re-anchoring them to whatever unified prints
    # today would leave a check that can never fail - the same failure this
    # registry already had once, when a pin agreed with a stale module and was
    # believed. A missing anchor is visible. A tautological one is not.
    #
    # The identity gate's actual contract is patched == shipped. That is
    # enforced directly in run_experiment.py against unified and needs no
    # registry row to do its job.
    #
    # What legitimately survives as a spec, and is NOT here: v18's
    # COUNT_BAND=(348,358), an independent band that is still checked.
    #
    # History: docs/signal/ANCHOR_BASIS_AUDIT.md records why the single original pin
    # {351, +225.3R} was split into two - n came from the fine+chop58 run while
    # gross came from the coarse+chop61.8 run. exp_crosslane.py still listed both
    # rows as reference lanes and was updated alongside this removal.

    # ===== ENTRY-QUALITY FILTERS (Phase 2: skip bad setups before they happen) =====
    # ===== ENTRY-QUALITY FILTERS (Phase 2: skip bad setups before they happen) =====
    # Based on entry autopsy (Phase 1b): B2+doji is worst combo (48t, 18.8% WR,
    # +0.11 avgR). Swing age >50 bars = 0% WR. Candle strength <0.3 has best
    # separation but tiny sample. Each filter tested on both king configs.

    "b2doji_utcsat_multi_sw10": {
        "desc": "king multi + skip B2 entries with doji candle (body/range < 0.3)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_entry_skip_b2_doji": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +393.87R  net +295.70R  dd 36.16R  win 31.0%  n=422
        # all 115 registry books in one pass.
        #   gross +393.87R  net +295.70R  dd 36.16R  win 31.0%  n=422
        "pins": {"n": 422, "net": 237.83,
                 "dd_net": 42.07, "oos_n": 228, "oos_net": 96.85, "oos_dd_net": 23.46},
    },
    "b2doji_swingpause_sig_sw10": {
        "desc": "king single + skip B2 entries with doji candle (body/range < 0.3)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_entry_skip_b2_doji": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +285.02R  net +188.71R  dd 46.29R  win 29.2%  n=414
        # all 115 registry books in one pass.
        #   gross +285.02R  net +188.71R  dd 46.29R  win 29.2%  n=414
        "pins": {"n": 332, "net": 97.58, "dd_net": 61.98, "win": 0.274,
                 "oos_n": 210, "oos_net": -12.36, "oos_dd_net": 32.81, "oos_win": 0.233},
    },
    "age50_utcsat_multi_sw10": {
        "desc": "king multi + skip entries on swings older than 50 bars",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_entry_swing_age_max": 50, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +366.64R  net +261.40R  dd 37.95R  win 28.8%  n=434
        # all 115 registry books in one pass.
        #   gross +366.64R  net +261.40R  dd 37.95R  win 28.8%  n=434
        "pins": {"n": 439, "net": 173.74,
                 "dd_net": 47.17, "oos_n": 254, "oos_net": 94.56, "oos_dd_net": 28.71},
    },
    "age50_swingpause_sig_sw10": {
        "desc": "king single + skip entries on swings older than 50 bars",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_entry_swing_age_max": 50, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +237.63R  net +137.14R  dd 48.05R  win 27.0%  n=429
        # all 115 registry books in one pass.
        #   gross +237.63R  net +137.14R  dd 48.05R  win 27.0%  n=429
        "pins": {"n": 352, "net": 137.77, "dd_net": 48.08, "win": 0.241,
                 "oos_n": 215, "oos_net": -18.71, "oos_dd_net": 46.94, "oos_win": 0.237},
    },
    "combined_b2age_utcsat_multi_sw10": {
        "desc": "king multi + B2+doji skip + swing age 50 skip (combined entry quality)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_entry_skip_b2_doji": 1,
                    "exp_entry_swing_age_max": 50, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +363.28R  net +265.38R  dd 36.00R  win 29.7%  n=407
        "pins": {"n": 402, "net": 176.33,
                 "dd_net": 47.62, "oos_n": 224, "oos_net": 91.48, "oos_dd_net": 26.16},
    },

    # ===== KINGSWEEP: persist / htf_rr / ext_stop_r / wage / curfew / partial_r =====
}
