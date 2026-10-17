"""KINGSWEEP - the kingsweep, the optimal lanes, and our champions.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {
    # ===== OPTIMAL LANES (from exp37, fine fills, corrected engine) =====

    "opt_ml_cd0_mb10": {
        "desc": "OPT mltf cd0 chop55 persist2 mb10 (exp37 C1, their OPTIMAL)",
        "engine": "patched",
        "params": {"chop_thresh": 55.0, "exp_persist": 2,
                    "cooldown_bars": 0, "exp_mltf": True},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +346.49R  net +215.50R  dd 60.37R  win 27.6%  n=510
        # all 115 registry books in one pass.
        #   gross +346.49R  net +215.50R  dd 60.37R  win 27.6%  n=510
        "pins": {"n": 526, "net": 250.89, "dd_net": 65.83,
                 "oos_n": 257, "oos_net": -5.97, "oos_dd_net": 61.8},
    },
    "opt_ml_cd10_mb10": {
        "desc": "OPT mltf cd10 chop55 persist2 mb10 (exp37 C2)",
        "engine": "patched",
        "params": {"chop_thresh": 55.0, "exp_persist": 2,
                    "cooldown_bars": 10, "exp_mltf": True},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +309.89R  net +198.09R  dd 44.56R  win 28.9%  n=446
        # all 115 registry books in one pass.
        #   gross +309.89R  net +198.09R  dd 44.56R  win 28.9%  n=446
        "pins": {"n": 452, "net": 229.38, "dd_net": 50.29,
                 "oos_n": 220, "oos_net": 15.8, "oos_dd_net": 47.71},
    },
    "lb30_chop55_persist2": {
        "desc": "lb30 chop55 persist2 mb10 (exp37 A4)",
        "engine": "patched",
        "params": { "cooldown_bars": 10,"exp31_lb": 30, "chop_thresh": 55.0,
                    "exp_persist": 2},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +356.19R  net +247.51R  dd 46.17R  win 30.3%  n=429
        # all 115 registry books in one pass.
        #   gross +356.19R  net +247.51R  dd 46.17R  win 30.3%  n=429
        "pins": {"n": 432, "net": 247.07, "dd_net": 45.77,
                 "oos_n": 227, "oos_net": 21.69, "oos_dd_net": 46.74},
    },
    "lb30_persist5": {
        "desc": "lb30 persist5 mb20 (exp37 A3/A5)",
        "engine": "patched",
        "params": { "max_consecutive_losses": 3,"exp31_lb": 30, "exp_persist": 5},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +368.99R  net +267.30R  dd 49.18R  win 32.4%  n=410
        # all 115 registry books in one pass.
        #   gross +368.99R  net +267.30R  dd 49.18R  win 32.4%  n=410
        "pins": {"n": 415, "net": 266.92, "dd_net": 48.33,
                 "oos_n": 198, "oos_net": 1.28, "oos_dd_net": 38.98},
    },
    "lb30_halt0": {
        "desc": "lb30 no halt (exp37 B0)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "max_consecutive_losses": 0},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +399.04R  net +276.86R  dd 60.28R  win 32.9%  n=484
        # all 115 registry books in one pass.
        #   gross +399.04R  net +276.86R  dd 60.28R  win 32.9%  n=484
        "pins": {"n": 485, "net": 280.55, "dd_net": 58.93,
                 "oos_n": 241, "oos_net": 42.34, "oos_dd_net": 50.9},
    },
    "lb30_halt6_cd0": {
        "desc": "lb30 halt6 cd0 (exp37 B3)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "max_consecutive_losses": 6,
                    "cooldown_bars": 0},
        "swing": "sw20",
        "pins": {"n": 547, "net": 136.85, "dd_net": 76.83,
                 "oos_n": 259, "oos_net": 9.73, "oos_dd_net": 78.79},
    },

    # ===== LB30 SWEPT EXT (fine fills) =====
    # ===== LB30 SWEPT EXT (fine fills) =====

    "lb30_w24_ext1.5": {
        "desc": "lb30 w24 ext1.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {"n": 336, "net": 335.44, "dd_net": 35.92,
                 "oos_n": 143, "oos_net": 15.01, "oos_dd_net": 40.73},
    },
    "lb30_w24_ext2.0": {
        "desc": "lb30 w24 ext2.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.0},
        "swing": "sw20",
        "pins": {"n": 379, "net": 343.38, "dd_net": 36.58,
                 "oos_n": 176, "oos_net": 32.84, "oos_dd_net": 41.00},
    },
    "lb30_w24_ext2.5": {
        "desc": "lb30 w24 ext2.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.5},
        "swing": "sw20",
        "pins": {"n": 404, "net": 313.85, "dd_net": 42.82,
                 "oos_n": 178, "oos_net": 43.34, "oos_dd_net": 41.06},
    },
    "lb30_w24_ext3.0": {
        "desc": "lb30 w24 ext3.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        "pins": {"n": 414, "net": 313.29, "dd_net": 42.27,
                 "oos_n": 183, "oos_net": 36.09, "oos_dd_net": 45.09},
    },

    # ===== A4 (fine fills) =====
    # ===== A4 (fine fills) =====

    "a4_w24_ext1.5": {
        "desc": "A4 w24 ext1.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {"n": 299, "net": 142.9, "dd_net": 47.02,
                 "oos_n": 145, "oos_net": 12.70, "oos_dd_net": 34.90},
    },
    "a4_w24_ext3.0": {
        "desc": "A4 w24 ext3.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +225.06R  net +133.69R  dd 48.14R  win 31.0%  n=368
        # all 115 registry books in one pass.
        #   gross +225.06R  net +133.69R  dd 48.14R  win 31.0%  n=368
        "pins": {"n": 367, "net": 132.46, "dd_net": 48.14,
                 "oos_n": 187, "oos_net": 28.37, "oos_dd_net": 38.40},
    },

    # ===== OPT MULTI (their champion, fine fills) =====
    # ===== OPT MULTI (their champion, fine fills) =====

    "opt_cd10_w24": {
        "desc": "OPT cd10 w24 ext1.5 (their champion multi, fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "cooldown_bars": 10, "ext_stop_r": 1.5},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +224.59R  net +144.13R  dd 47.02R  win 31.7%  n=300
        # all 115 registry books in one pass.
        #   gross +224.59R  net +144.13R  dd 47.02R  win 31.7%  n=300
        # KNOB SATURATION: a4_w24_ext1.5 differs in config but lands on the same
        # 300 trades / +144.13R / 47.02R drawdown. The differing knob does not bind
        # in this range - saturated, not equivalent. Kept as its own entry so the
        # knob stays visible; do not read the tie as "same book".
        # exp_mltf+cd10 vs neither.
        "pins": {"n": 299, "net": 142.9, "dd_net": 47.02,
                 "oos_n": 145, "oos_net": 12.70, "oos_dd_net": 34.90},
    },

    # ===== OUR CHAMPIONS (partial exits) =====
    # ===== OUR CHAMPIONS (partial exits) =====

    "champion_sig_sw20": {
        "desc": "Champion single sw20 (partial exit, +90.1 post trail-fix)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "window_end": "exit"},
        "swing": "sw20",
        # pin was n=372 net=90.1; now n=496 net=196.28 (win rate 31.9%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=496 net=196.28. Full sweep incl. gross/dd/win-rate:
        #   gross +312.57R  net +196.28R  dd 58.21R  win 31.9%  n=496
        "pins": {"n": 374, "net": 91.64, "dd_net": 51.62, "win": 0.291,
                 "oos_n": 215, "oos_net": -13.11, "oos_dd_net": 37.75, "oos_win": 0.26},
    },
    "champion_sig_sw10": {
        "desc": "Champion single sw10 (partial exit, +82.0 post trail-fix)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=396 net=82.0; now n=503 net=170.91 (win rate 30.4%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=503 net=170.91. Full sweep incl. gross/dd/win-rate:
        #   gross +286.91R  net +170.91R  dd 50.48R  win 30.4%  n=503
        "pins": {"n": 395, "net": 48.63, "dd_net": 48.5, "win": 0.261,
                 "oos_n": 238, "oos_net": -18.06, "oos_dd_net": 44.97, "oos_win": 0.235},
    },
    "champion_multi_sw20": {
        "desc": "Champion multi sw20 (partial exit, +208.4 post trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw20",
        # pin was n=487 net=208.4; now n=493 net=213.33 (win rate 31.8%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=493 net=213.33. Full sweep incl. gross/dd/win-rate:
        #   gross +329.42R  net +213.33R  dd 50.64R  win 31.8%  n=493
        "pins": {"n": 493, "net": 214.74, "dd_net": 45.4,
                 "oos_n": 270, "oos_net": -1.45, "oos_dd_net": 51.47},
    },
    "champion_multi_sw10": {
        "desc": "Champion multi sw10 - PRE-C16 retro book, origin SL pivot (LOOKAHEAD, research baseline only)",
        "engine": "patched",
        # pivot_rule belongs here, not at each call site. The engine default is
        # "leg" (Causal), so a harness that builds its kwargs from this registry
        # and does not override the rule silently measures the post-C16 leg book
        # and cannot meet the pins below. Every harness that filters these params
        # against the engine signature now inherits the retro rule automatically.
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "origin"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=500 net=325.78. Full sweep incl. gross/dd/win-rate:
        #   gross +445.22R  net +325.78R  dd 27.72R  win 30.0%  n=500
        # pin was n=500 net=325.78; now n=500 net=325.78 (win rate 30.0%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 420, "net": 125.82,
                 "dd_net": 63.57, "oos_n": 249, "oos_net": -45.2, "oos_dd_net": 62.26},
    },
    # =========================================================================
    # =========================================================================
    # THE CHAMPION BOOKS - one engine (unified.py), three stop-placement rules.
    # =========================================================================
    # =========================================================================
    # The engine is the same for all three. They differ in ONE thing: which
    # price the initial stop is placed on. Verified trade-for-trade identical
    # on every rule before v19_champion.py was archived.
    #
    #   pivot_rule       stop goes on                       n     gross    htf
    #   origin           the swing's declared origin       500   +445.22   355
    #   leg              leg extreme, entry bar INCLUDED   499   +355.72   350
    #   leg_no_entry     leg extreme, entry bar EXCLUDED   500   +445.19   355
    #
    # leg and leg_no_entry are both causal: each reads only bars that closed
    # before the entry. They differ only on bars where the entry itself
    # extended the extreme, so the entry bar's own high/low can set the stop
    # under "leg" and cannot under "leg_no_entry".
    #
    # Worth stating plainly because it cuts against the usual framing: the
    # origin pivot is NOT measurably lookahead. leg_no_entry sits within
    # 0.03R of it over 500 trades, with 497 of 500 stops identical. What C16
    # actually changed was the risk denominator, not knowledge of the future.
    # Its rule is still the right one to ship - "leg" is the structural
    # extreme rather than a structural pivot - but "lookahead" overstated it.
    #
    # champion_multi_sw10 (origin)      - research baseline, superseded
    # champion_multi_sw10_leg (leg)    - THE SHIPPING BOOK
    # champion_multi_sw10_entry1        - the proposed ENTRY-1 variant
    # champion_multi_sw10_entry_both - ENTRY-1 on BOTH legs.
    #
    # "entry-1" means the initial stop may not be placed using the entry bar's own
    # extreme. Applied to both halves:
    #   HTF  pivot_rule="leg_no_entry"   excludes the break bar from the leg scan
    #   LTF  exp_ltf_no_entry=1 + exp_causal_sl=1
    #
    # exp_causal_sl=1 is required, not decorative. With it at 0 the LTF leg reads
    # sig["swing_start_px"], which pivot_rule ALREADY sets - so pivot_rule reaches
    # the LTF leg on its own and exp_ltf_no_entry has nothing to act on. The flag
    # only bites when the LTF leg is on the _csl running-extreme path, which is
    # what exp_causal_sl=1 selects. Verified across the full 2x2x2 matrix:
    #
    #   pivot         ltf_no_entry  causal_sl    n    gross      net
    #   leg              0            0        499   +355.72  +239.12   CAUSAL
    #   leg_no_entry     0            0        500   +445.19  +325.75   ENTRY-1 (HTF only)
    #   leg              1            1        499   +277.31  +166.50   distinct
    #   leg_no_entry     1            1        500   +345.02  +232.06   THIS BOOK
    #
    # Both flags are no-ops unless causal_sl is 1, so the four remaining
    # combinations collapse onto existing books and are not registered.
    "champion_multi_sw10_entry_both": {
        "desc": "ENTRY-1 on both legs - HTF and LTF both exclude the entry bar from the stop",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg_no_entry",
                    "exp_ltf_no_entry": 1,
                    "exp_causal_sl": 1},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=495 net=215.09. Full sweep incl. gross/dd/win-rate:
        #   gross +322.18R  net +215.09R  dd 34.72R  win 29.7%  n=495
        # MEASURED 2026-10-02 via the registry path with this book's own params:
        # 495 trades, +322.18R gross. The 500 / +232.06 I first wrote came from a
        # hand-built config missing exp_mltf and exp_persist, so it was not this
        # book. Measured through the harness only - raw unified.py does not accept
        # exp_partial_r, which the harness injects, so raw and harness are
        # different code paths for the exp_causal_sl branch (t_c13).
        # pin was n=495 net=215.14; now n=495 net=215.09 (win rate 29.7%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 416, "net": 124.46,
                 "dd_net": 58.15, "oos_n": 247, "oos_net": -50.44, "oos_dd_net": 62.21},
    },

    "champion_multi_sw10_leg": {
        "desc": "Champion multi sw10 - POST-C16 CAUSAL book, leg SL pivot. THIS is the "
                "one that ships (what live_loop and the v19_c16 / v19_causal dropdown "
                "books run). Same params as champion_multi_sw10, differing only in "
                "pivot_rule.",
        "engine": "patched",
        # The two champion_multi_sw10* entries exist because pivot_rule split them on
        # 2026-10-01. The entry literally named champion_multi_sw10 is the PRE-C16
        # lookahead book; it kept the old name because twenty-odd harnesses reference
        # it by key and renaming it would break every one of them. Read pivot_rule,
        # not the name, when deciding which book a harness measures.
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=499 net=239.12. Full sweep incl. gross/dd/win-rate:
        #   gross +355.72R  net +239.12R  dd 46.85R  win 29.7%  n=499
        # dd pin REMOVED 2026-10-02. It read 15.36, stamped MEASURED 2026-10-01 in
        # the same session as the origin row above, whose dd of 17.83 reproduces
        # exactly on demand. Here n, net and partials all round-trip and only dd
        # was wrong - one field out of four, so a transcription slip rather than a
        # different run. It never matched any measurement taken since: not 32.04
        # (current IS, confirmed three ways), not 17.83 (origin), not 23.87 (h2 only).
        # Deliberately not re-anchored to 32.04: three computations agreeing makes a
        # measurement, not a spec, and pinning it would leave a check that restates its
        # own output. Removed instead, same as the _shipped_* anchors above. Do not
        # re-add from memory. n / net / partials / oos below are the book.
        # pin was n=499 net=239.12; now n=499 net=239.12 (win rate 29.7%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 421, "net": 127.39,
                 "dd_net": 71.11, "oos_n": 251, "oos_net": -31.05, "oos_dd_net": 49.28},
    },

    # ===== ENTRY-1 VARIANTS (leg_no_entry pivot rule) =====
    # ===== KINGSWEEP: persist / htf_rr / ext_stop_r / wage / curfew / partial_r =====
    # Goal: find optimal values for the 6 unvalidated params on the kings.

    # --- persist fine sweep on king multi (current=7, never validated in {3,4,5,6,8}) ---
    "persist3_multi_sw10": {
        "desc": "king multi + persist=3 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 3, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +344.06R  net +229.45R  dd 53.26R  win 29.1%  n=495
        # all 115 registry books in one pass.
        #   gross +344.06R  net +229.45R  dd 53.26R  win 29.1%  n=495
        "pins": {"n": 425, "net": 137.59,
                 "dd_net": 60.94, "oos_n": 267, "oos_net": -28.98, "oos_dd_net": 50.61},
    },
    "persist4_multi_sw10": {
        "desc": "king multi + persist=4 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 4, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +347.93R  net +231.70R  dd 46.85R  win 29.5%  n=501
        # all 115 registry books in one pass.
        #   gross +347.93R  net +231.70R  dd 46.85R  win 29.5%  n=501
        "pins": {"n": 421, "net": 125.98,
                 "dd_net": 70.95, "oos_n": 262, "oos_net": -34.49, "oos_dd_net": 52.19},
    },
    "persist5_multi_sw10": {
        "desc": "king multi + persist=5 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 5, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +354.53R  net +239.00R  dd 46.85R  win 29.5%  n=498
        # all 115 registry books in one pass.
        #   gross +354.53R  net +239.00R  dd 46.85R  win 29.5%  n=498
        "pins": {"n": 421, "net": 127.39,
                 "dd_net": 71.11, "oos_n": 262, "oos_net": -31.3, "oos_dd_net": 51.45},
    },
    "persist6_multi_sw10": {
        "desc": "king multi + persist=6 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 6, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +355.72R  net +239.12R  dd 46.85R  win 29.7%  n=499
        # all 115 registry books in one pass.
        #   gross +355.72R  net +239.12R  dd 46.85R  win 29.7%  n=499
        # KNOB SATURATION: champion_multi_sw10_leg differs in config but lands on the same
        # 499 trades / +239.12R / 46.85R drawdown. The differing knob does not bind
        # in this range - saturated, not equivalent. Kept as its own entry so the
        # knob stays visible; do not read the tie as "same book".
        # pivot_rule unset vs leg.
        "pins": {"n": 421, "net": 127.39,
                 "dd_net": 71.11, "oos_n": 256, "oos_net": -29.52, "oos_dd_net": 48.65},
    },
    "persist8_multi_sw10": {
        "desc": "king multi + persist=8 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 8, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +355.72R  net +239.12R  dd 46.85R  win 29.7%  n=499
        # all 115 registry books in one pass.
        #   gross +355.72R  net +239.12R  dd 46.85R  win 29.7%  n=499
        # KNOB SATURATION: persist6_multi_sw10 differs in config but lands on the same
        # 499 trades / +239.12R / 46.85R drawdown. The differing knob does not bind
        # in this range - saturated, not equivalent. Kept as its own entry so the
        # knob stays visible; do not read the tie as "same book".
        # exp_persist 8 vs 6.
        "pins": {"n": 503, "net": 288.52, "dd_net": 43.2,
                 "oos_n": 289, "oos_net": 31.68, "oos_dd_net": 55.21},
    },

    # --- htf_rr re-sweep on king multi (current=3.0, swept pre-fix only) ---
    "htfrr2_multi_sw10": {
        "desc": "king multi + htf_rr=2.0 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 2.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +397.50R  net +292.86R  dd 35.68R  win 29.6%  n=423
        # all 115 registry books in one pass.
        #   gross +397.50R  net +292.86R  dd 35.68R  win 29.6%  n=423
        "pins": {"n": 431, "net": 245.36, "dd_net": 32.96,
                 "oos_n": 236, "oos_net": 23.56, "oos_dd_net": 47.17},
    },
    "htfrr25_multi_sw10": {
        "desc": "king multi + htf_rr=2.5 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 2.5,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +324.69R  net +221.11R  dd 34.27R  win 27.9%  n=419
        # all 115 registry books in one pass.
        #   gross +324.69R  net +221.11R  dd 34.27R  win 27.9%  n=419
        "pins": {"n": 378, "net": 75.64,
                 "dd_net": 79.63, "oos_n": 210, "oos_net": -24.72, "oos_dd_net": 50.19},
    },
    "htfrr35_multi_sw10": {
        "desc": "king multi + htf_rr=3.5 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 3.5,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +303.14R  net +202.29R  dd 41.04R  win 28.1%  n=406
        # all 115 registry books in one pass.
        #   gross +303.14R  net +202.29R  dd 41.04R  win 28.1%  n=406
        "pins": {"n": 416, "net": 242.56, "dd_net": 40.74,
                 "oos_n": 232, "oos_net": 33.8, "oos_dd_net": 50.66},
    },
    "htfrr4_multi_sw10": {
        "desc": "king multi + htf_rr=4.0 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 4.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +321.93R  net +222.36R  dd 38.81R  win 29.2%  n=397
        # all 115 registry books in one pass.
        #   gross +321.93R  net +222.36R  dd 38.81R  win 29.2%  n=397
        "pins": {"n": 330, "net": 100.91,
                 "dd_net": 58.03, "oos_n": 191, "oos_net": -47.62, "oos_dd_net": 59.89},
    },

    # --- ext_stop_r sweep on utcsat king (current=3.0, never swept on king) ---
    "ext2_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=2.0 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 2.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +402.41R  net +301.86R  dd 41.77R  win 32.6%  n=417
        # all 115 registry books in one pass.
        #   gross +402.41R  net +301.86R  dd 41.77R  win 32.6%  n=417
        "pins": {"n": 356, "net": 147.07,
                 "dd_net": 46.75, "oos_n": 213, "oos_net": -38.53, "oos_dd_net": 52.88},
    },
    "ext25_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=2.5 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 2.5,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +385.83R  net +281.30R  dd 36.18R  win 30.8%  n=442
        # all 115 registry books in one pass.
        #   gross +385.83R  net +281.30R  dd 36.18R  win 30.8%  n=442
        "pins": {"n": 382, "net": 138.04,
                 "dd_net": 46.98, "oos_n": 223, "oos_net": -37.46, "oos_dd_net": 49.32},
    },
    "ext35_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=3.5 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.5,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +384.11R  net +279.16R  dd 35.54R  win 30.4%  n=454
        # all 115 registry books in one pass.
        #   gross +384.11R  net +279.16R  dd 35.54R  win 30.4%  n=454
        "pins": {"n": 384, "net": 113.83,
                 "dd_net": 48.33, "oos_n": 224, "oos_net": -42.77, "oos_dd_net": 54.63},
    },
    "ext4_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=4.0 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 4.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +384.11R  net +279.16R  dd 35.54R  win 30.4%  n=454
        # all 115 registry books in one pass.
        #   gross +384.11R  net +279.16R  dd 35.54R  win 30.4%  n=454
        # KNOB SATURATION: ext35_utcsat_multi_sw10 differs in config but lands on the same
        # 454 trades / +279.16R / 35.54R drawdown. The differing knob does not bind
        # in this range - saturated, not equivalent. Kept as its own entry so the
        # knob stays visible; do not read the tie as "same book".
        # ext_stop_r 4.0 vs 3.5.
        "pins": {"n": 384, "net": 113.83,
                 "dd_net": 48.33, "oos_n": 224, "oos_net": -42.77, "oos_dd_net": 54.63},
    },

    # --- wage_h / curfew on kings (never tested on king configs) ---
    "wage12_utcsat_multi_sw10": {
        "desc": "utcsat king + wage_h=12 (never tested on king, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_wage_h": 12, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +365.61R  net +273.70R  dd 31.66R  win 31.5%  n=391
        # all 115 registry books in one pass.
        #   gross +365.61R  net +273.70R  dd 31.66R  win 31.5%  n=391
        "pins": {"n": 329, "net": 159.08,
                 "dd_net": 53.19, "oos_n": 202, "oos_net": -15.57, "oos_dd_net": 32.25},
    },
    "wage24_utcsat_multi_sw10": {
        "desc": "utcsat king + wage_h=24 (never tested on king, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_wage_h": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +353.29R  net +273.80R  dd 21.70R  win 33.4%  n=332
        # all 115 registry books in one pass.
        #   gross +353.29R  net +273.80R  dd 21.70R  win 33.4%  n=332
        "pins": {"n": 276, "net": 163.19,
                 "dd_net": 51.87, "oos_n": 175, "oos_net": -24.49, "oos_dd_net": 47.13},
    },
    "wage24_swingpause_sig_sw10": {
        "desc": "best single + wage_h=24 (never tested on best single, current=0)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1,
                    "exp_wage_h": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +284.68R  net +228.40R  dd 20.87R  win 34.2%  n=269
        # all 115 registry books in one pass.
        #   gross +284.68R  net +228.40R  dd 20.87R  win 34.2%  n=269
        "pins": {"n": 219, "net": 224.02, "dd_net": 16.65, "win": 0.324,
                 "oos_n": 136, "oos_net": 26.04, "oos_dd_net": 30.21, "oos_win": 0.265},
    },
    "curfew624_utcsat_multi_sw10": {
        "desc": "utcsat king + skip age 6-24h band (never tested on king, current=0/0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_curfew_a": 6, "exp_curfew_b": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +393.15R  net +304.72R  dd 31.95R  win 32.4%  n=377
        "pins": {"n": 312, "net": 182.26,
                 "dd_net": 59.33, "oos_n": 191, "oos_net": -28.71, "oos_dd_net": 47.81},
    },
    "curfew624_swingpause_sig_sw10": {
        "desc": "best single + skip age 6-24h band (never tested on best single, current=0/0)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1,
                    "exp_curfew_a": 6, "exp_curfew_b": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +259.41R  net +198.91R  dd 23.17R  win 32.7%  n=300
        # all 115 registry books in one pass.
        #   gross +259.41R  net +198.91R  dd 23.17R  win 32.7%  n=300
        "pins": {"n": 256, "net": 181.02, "dd_net": 18.03, "win": 0.301,
                 "oos_n": 153, "oos_net": 30.75, "oos_dd_net": 26.6, "oos_win": 0.268},
    },

    # --- partial_r fine sweep on king multi (current=0, only 7.5 tested on sw20) ---
    "partial1_multi_sw10": {
        "desc": "king multi + partial_r=1.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 1.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +179.60R  net +50.19R  dd 43.84R  win 41.4%  n=553
        # all 115 registry books in one pass.
        #   gross +179.60R  net +50.19R  dd 43.84R  win 41.4%  n=553
        "pins": {"n": 567, "net": 65.91, "dd_net": 42.51,
                 "oos_n": 328, "oos_net": 2.16, "oos_dd_net": 48.9},
    },
    "partial2_multi_sw10": {
        "desc": "king multi + partial_r=2.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 2.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +194.80R  net +72.28R  dd 39.25R  win 37.5%  n=528
        # all 115 registry books in one pass.
        #   gross +194.80R  net +72.28R  dd 39.25R  win 37.5%  n=528
        "pins": {"n": 534, "net": 88.52, "dd_net": 39.56,
                 "oos_n": 307, "oos_net": 11.4, "oos_dd_net": 51.03},
    },
    "partial3_multi_sw10": {
        "desc": "king multi + partial_r=3.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 3.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +212.24R  net +92.55R  dd 39.75R  win 33.5%  n=513
        # all 115 registry books in one pass.
        #   gross +212.24R  net +92.55R  dd 39.75R  win 33.5%  n=513
        "pins": {"n": 518, "net": 109.91, "dd_net": 39.89,
                 "oos_n": 292, "oos_net": 7.5, "oos_dd_net": 52.89},
    },
    "partial4_multi_sw10": {
        "desc": "king multi + partial_r=4.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 4.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +224.78R  net +106.70R  dd 45.39R  win 31.0%  n=506
        # all 115 registry books in one pass.
        #   gross +224.78R  net +106.70R  dd 45.39R  win 31.0%  n=506
        "pins": {"n": 511, "net": 131.6, "dd_net": 41.74,
                 "oos_n": 291, "oos_net": 26.11, "oos_dd_net": 54.43},
    },
    "partial5_multi_sw10": {
        "desc": "king multi + partial_r=5.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 5.0, "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +248.37R  net +131.63R  dd 46.01R  win 30.7%  n=501
        # all 115 registry books in one pass.
        #   gross +248.37R  net +131.63R  dd 46.01R  win 30.7%  n=501
        "pins": {"n": 506, "net": 156.53, "dd_net": 42.36,
                 "oos_n": 290, "oos_net": 37.37, "oos_dd_net": 51.97},
    },
    # === FUNDING RATE FILTER: DEAD (data too sparse, 0 trades filtered) ===
}
