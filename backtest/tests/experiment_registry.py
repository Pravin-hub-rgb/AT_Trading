"""Experiment Registry — all live experiment configs as data dicts.

No code, just configs. To add a new experiment, add a dict entry below.
Run with: python run_experiment.py <key>

Keys starting with "_" are hidden from --list (internal/reference only).
"""

# ---------------------------------------------------------------------------
# PRODUCTION BASELINE (all experiments inherit from this)
# Source: engine.v18_params + V18_ENGINE
# ---------------------------------------------------------------------------
ENGINE_DEFAULTS = {
    "sl_buf_atr": 0.01,
    "ext_stop_r": 1.5,
    "chop_thresh": 61.8,
    "mode": "b2_vs_flip_chop",
    "cooldown_bars": 10,
    "max_consecutive_losses": 3,
    "atr_low_thresh": 0.35,
    "atr_high_thresh": 0.65,
    "htf_rr": 3.0,
    "window_end": "exit",
}

# BP = BASE with chop_thresh overridden to 58.0 (production tuning)
BP = {**ENGINE_DEFAULTS, "chop_thresh": 58.0}

# ---------------------------------------------------------------------------
# EXPERIMENT REGISTRY
# ---------------------------------------------------------------------------
# Each entry:
#   desc       : human-readable description
#   engine     : "shipped" (unpatched) or "patched" (craze superset)
#   params     : overrides merged onto BASE (or BP if use_bp=True)
#   use_bp     : if True, merge onto BP (chop=58); if False, merge onto ENGINE_DEFAULTS
#   swing      : "sw20" (min_bars_1h) or "sw10" (fast 1h chain)
#   pins       : expected results for validation (optional)
#   htf_rr     : override htf_rr if needed (default 3.0)
# ---------------------------------------------------------------------------

EXPERIMENTS = {

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
        "pins": {"n": 510, "net": 215.50, "dd": 60.37},
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
        "pins": {"n": 446, "net": 198.09, "dd": 44.56},
    },
    "lb30_chop55_persist2": {
        "desc": "lb30 chop55 persist2 mb10 (exp37 A4)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0,
                    "exp_persist": 2},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +356.19R  net +247.51R  dd 46.17R  win 30.3%  n=429
        # all 115 registry books in one pass.
        #   gross +356.19R  net +247.51R  dd 46.17R  win 30.3%  n=429
        "pins": {"n": 429, "net": 247.51, "dd": 46.17},
    },
    "lb30_persist5": {
        "desc": "lb30 persist5 mb20 (exp37 A3/A5)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_persist": 5},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +368.99R  net +267.30R  dd 49.18R  win 32.4%  n=410
        # all 115 registry books in one pass.
        #   gross +368.99R  net +267.30R  dd 49.18R  win 32.4%  n=410
        "pins": {"n": 410, "net": 267.30, "dd": 49.18},
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
        "pins": {"n": 484, "net": 276.86, "dd": 60.28},
    },
    "lb30_halt6_cd0": {
        "desc": "lb30 halt6 cd0 (exp37 B3)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "max_consecutive_losses": 6,
                    "cooldown_bars": 0},
        "swing": "sw20",
        "pins": {"n": 538, "net": 140.96, "dd": 84.06},
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +276.39R  net +140.96R  dd 84.06R  win 28.4%  n=538
        # all 115 registry books in one pass.
        #   gross +276.39R  net +140.96R  dd 84.06R  win 28.4%  n=538
    },

    # ===== LB30 SWEPT EXT (fine fills) =====

    "lb30_w24_ext1.5": {
        "desc": "lb30 w24 ext1.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {"n": 337, "net": 336.67, "dd": 35.92},
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +425.66R  net +336.67R  dd 35.92R  win 36.8%  n=337
        # all 115 registry books in one pass.
        #   gross +425.66R  net +336.67R  dd 35.92R  win 36.8%  n=337
    },
    "lb30_w24_ext2.0": {
        "desc": "lb30 w24 ext2.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.0},
        "swing": "sw20",
        "pins": {"n": 380, "net": 344.61, "dd": 36.58},
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +441.61R  net +344.61R  dd 36.58R  win 35.8%  n=380
        # all 115 registry books in one pass.
        #   gross +441.61R  net +344.61R  dd 36.58R  win 35.8%  n=380
    },
    "lb30_w24_ext2.5": {
        "desc": "lb30 w24 ext2.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.5},
        "swing": "sw20",
        "pins": {"n": 405, "net": 315.08, "dd": 42.82},
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +419.56R  net +315.08R  dd 42.82R  win 35.3%  n=405
        # all 115 registry books in one pass.
        #   gross +419.56R  net +315.08R  dd 42.82R  win 35.3%  n=405
    },
    "lb30_w24_ext3.0": {
        "desc": "lb30 w24 ext3.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        "pins": {"n": 415, "net": 314.51, "dd": 42.27},
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +420.18R  net +314.51R  dd 42.27R  win 35.4%  n=415
        # all 115 registry books in one pass.
        #   gross +420.18R  net +314.51R  dd 42.27R  win 35.4%  n=415
    },

    # ===== A4 (fine fills) =====

    "a4_w24_ext1.5": {
        "desc": "A4 w24 ext1.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {"n": 300, "net": 144.13, "dd": 47.02},
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +224.59R  net +144.13R  dd 47.02R  win 31.7%  n=300
        # all 115 registry books in one pass.
        #   gross +224.59R  net +144.13R  dd 47.02R  win 31.7%  n=300
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
        "pins": {"n": 368, "net": 133.69, "dd": 48.14},
    },

    # ===== OPT MULTI (their champion, fine fills) =====

    "opt_cd10_w24": {
        "desc": "OPT cd10 w24 ext1.5 (their champion multi, fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "cooldown_bars": 10, "exp_mltf": True,
                    "ext_stop_r": 1.5},
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

        "pins": {"n": 300, "net": 144.13, "dd": 47.02},
    },

    # ===== OUR CHAMPIONS (partial exits) =====

    "champion_single_sw20": {
        "desc": "Champion single sw20 (partial exit, +90.1 post trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 496, "net": 196.28, "dd": 58.21},
    },
    "champion_single_sw10": {
        "desc": "Champion single sw10 (partial exit, +82.0 post trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 503, "net": 170.91, "dd": 50.48},
    },
    "champion_multi_sw20": {
        "desc": "Champion multi sw20 (partial exit, +208.4 post trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw20",
        # pin was n=487 net=208.4; now n=493 net=213.33 (win rate 31.8%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=493 net=213.33. Full sweep incl. gross/dd/win-rate:
        #   gross +329.42R  net +213.33R  dd 50.64R  win 31.8%  n=493
        "pins": {"n": 493, "net": 213.33, "dd": 50.64},
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
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "origin"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=500 net=325.78. Full sweep incl. gross/dd/win-rate:
        #   gross +445.22R  net +325.78R  dd 27.72R  win 30.0%  n=500
        # pin was n=500 net=325.78; now n=500 net=325.78 (win rate 30.0%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 500, "net": 325.78, "dd": 27.72},
    },
    # =========================================================================
    # THE CHAMPION BOOKS - one engine (unified.py), three stop-placement rules.
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
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
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
        "pins": {"n": 495, "net": 215.09, "dd": 34.72},
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
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
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
        "pins": {"n": 499, "net": 239.12, "dd": 46.85},
        "oos": {"n": 280, "net": 72.8},  # MEASURED. NOT the origin book's 279 / +70.15.
    },

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
        "pins": {"n": 500, "net": 325.75, "dd": 27.72},
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

        "pins": {"n": 500, "net": 325.75, "dd": 27.72},
    },

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
        "pins": {"n": 496, "net": 232.38, "dd": 61.58},
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
        "pins": {"n": 502, "net": 238.45, "dd": 53.86},
    },

    # ===== D3 COOLDOWN FAMILY (loss-reactive window skip / swing pause) =====

    "skipwin1_multi_sw10": {
        "desc": "king + skip the next HTF window opened after a loss",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skipwin": 1, "window_end": "exit"},
        "swing": "sw10",
        # the rerun makes that much starker: skipping the next window after a loss
        # turns a roughly break-even idea into a reliably negative one.
        # It also makes exp_mltf inert - see the note on skip1pause below.
        # all 115 registry books in one pass.
        # Was n=145 net=-38.54. Full sweep incl. gross/dd/win-rate:
        #   gross -5.52R  net -38.54R  dd 52.54R  win 19.3%  n=145
        "pins": {"n": 145, "net": -38.54, "dd": 52.54},
    },
    "skipwin2_multi_sw10": {
        "desc": "king + skip the next 2 HTF windows opened after a loss",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skipwin": 2, "window_end": "exit"},
        "swing": "sw10",
        # the rerun makes that much starker: skipping the next window after a loss
        # turns a roughly break-even idea into a reliably negative one.
        # It also makes exp_mltf inert - see the note on skip1pause below.
        # all 115 registry books in one pass.
        # Was n=101 net=-65.33. Full sweep incl. gross/dd/win-rate:
        #   gross -43.46R  net -65.33R  dd 66.47R  win 13.9%  n=101
        "pins": {"n": 101, "net": -65.33, "dd": 66.47},
    },
    "swingpause_multi_sw10": {
        "desc": "king + pause until a swing FORMED after the loss confirms (fresh structure)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_swingpause": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=444 net=241.06. Full sweep incl. gross/dd/win-rate:
        #   gross +346.75R  net +241.06R  dd 41.60R  win 28.8%  n=444
        # all 115 registry books in one pass.
        #   gross +346.75R  net +241.06R  dd 41.60R  win 28.8%  n=444
        # single and multi of this book produce the same trade count, the same net,
        # and the same trade-list hash. The multi leg is only meaningful where
        # cooldown_bars is kept alongside the pause, as this entry does.
        "pins": {"n": 444, "net": 241.06, "dd": 41.60},
    },
    # REMOVED 2026-10-02: skip1pause_multi_sw10. Verified identical to
    # skipwin1_multi_sw10 on unified.py - same count, same net, same trade list.
    # exp_skipwin=1 already removes the window, so the added exp_swingpause has
    # nothing left to pause.
    "skip1pause_multi_sw10": "skipwin1_multi_sw10",
    "skipwin1_single_sw10": {
        "desc": "baseline single + skip the next HTF window opened after a loss",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_skipwin": 1, "window_end": "exit"},
        "swing": "sw10",
        # the rerun makes that much starker: skipping the next window after a loss
        # turns a roughly break-even idea into a reliably negative one.
        # It also makes exp_mltf inert - see the note on skip1pause below.
        # all 115 registry books in one pass.
        # Was n=148 net=-38.88. Full sweep incl. gross/dd/win-rate:
        #   gross -7.13R  net -38.88R  dd 53.91R  win 20.3%  n=148
        "pins": {"n": 148, "net": -38.88, "dd": 53.91},
    },
    "swingpause_single_sw10": {
        "desc": "baseline single + pause until a swing FORMED after the loss confirms",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=451 net=232.45. Full sweep incl. gross/dd/win-rate:
        #   gross +347.86R  net +242.55R  dd 48.67R  win 29.7%  n=451
        # all 115 registry books in one pass.
        #   gross +347.86R  net +242.55R  dd 48.67R  win 29.7%  n=451
        # default change.
        # On this single base, what each mechanism is worth:
        #   no cooldown, no swingpause     556 / +166.54R
        #   cooldown_bars=8                499 / +239.12R
        #   cooldown_bars=0 + swingpause   451 / +232.45R
        # Swing pause recovers most of what the bar cooldown was worth, on 48
        # fewer trades - it blocks re-entry into the same swing rather than
        # waiting out N bars. Together they are slightly worse than cooldown
        # alone, which is why the production champion keeps the cooldown.
        "pins": {"n": 451, "net": 242.55, "dd": 48.67},
    },
    "skipwinhalt_multi_sw10": {
        "desc": "king + skip the next HTF window after a HALT (3 straight losses)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skipwin_halt": 1, "window_end": "exit"},
        "swing": "sw10",
        # without it this family runs at -38R, with it +28R - but it does not come
        # close to plain bar cooldown (+239R). Skip-window is not a cooldown
        # substitute; the halt is what stops the bleeding, not the skip.
        # all 115 registry books in one pass.
        # Was n=323 net=28.35. Full sweep incl. gross/dd/win-rate:
        #   gross +100.84R  net +28.35R  dd 45.34R  win 26.9%  n=323
        "pins": {"n": 323, "net": 28.35, "dd": 45.34},
    },
    "skipwinhalt_single_sw10": {
        "desc": "baseline single + skip the next HTF window after a HALT (3 straight losses)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_skipwin_halt": 1, "window_end": "exit"},
        "swing": "sw10",
        # without it this family runs at -38R, with it +28R - but it does not come
        # close to plain bar cooldown (+239R). Skip-window is not a cooldown
        # substitute; the halt is what stops the bleeding, not the skip.
        # all 115 registry books in one pass.
        # Was n=328 net=29.64. Full sweep incl. gross/dd/win-rate:
        #   gross +102.02R  net +29.64R  dd 60.09R  win 27.4%  n=328
        "pins": {"n": 328, "net": 29.64, "dd": 60.09},
    },
    # REMOVED 2026-10-02: swingpause_cd0_single_sw10. exp_swingpause forces
    # cooldown_bars=0 itself, so this entry set cooldown_bars=0 and added the same
    # flag - it was swingpause_single_sw10 under a second name, and both read
    # 451 / +232.45R after the rerun. Kept as a pointer rather than a copy so a
    # script naming it still finds the meaning.
    "swingpause_cd0_single_sw10": "swingpause_single_sw10",
    "swingpause_single_sw20": {
        "desc": "baseline single sw20 + swing-pause (fresh structure)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1, "window_end": "exit"},
        "swing": "sw20",
        # the sw10 book despite the similar name and count - different swing
        # structure (1316 swings vs 1601), different trade-list hash, 57R lower.
        # Note this entry sets cooldown_bars=8 AND exp_swingpause=1 together,
        # which is the only book that keeps both.
        # all 115 registry books in one pass.
        # Was n=444 net=154.08. Full sweep incl. gross/dd/win-rate:
        #   gross +258.19R  net +154.08R  dd 57.93R  win 30.9%  n=444
        "pins": {"n": 444, "net": 154.08, "dd": 57.93},
    },

    # ===== D3 PATTERN FAMILY (from loss autopsy: weekends, entry kinds, window age) =====

    "nowknd_multi_sw10": {
        "desc": "king + SKIP WEEKEND entries (Sat/Sun) — autopsy: 110t for -1.9R",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_weekend": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +389.89R  net +301.39R  dd 25.88R  win 31.8%  n=403
        # all 115 registry books in one pass.
        #   gross +389.89R  net +301.39R  dd 25.88R  win 31.8%  n=403
        "pins": {"n": 403, "net": 301.39, "dd": 25.88},
        # MEASURED 2026-10-02 on unified.py. The previous pin was 400 / +307.8;
        # it reproduced under no stop rule and predated the C16 default change.`n        #`n        # One knob over the causal champion, widened from Saturday to the whole`n        # weekend. Measured on the same base:`n        #   no calendar filter     499 trades  +239.12`n        #   skip Saturday only      453         +279.47`n        #   skip Sat+Sun            403         +301.39`n        #   skip Sunday only        438         +173.10`n        #`n        # Saturday is where the edge is: skipping it is worth +40R, skipping`n        # Sunday instead loses 66R. So the weekend filter works, but almost all`n        # of it is the Saturday half - Sunday is a profitable day.`n        "pins": {"n": 403, "net": 301.39},
    },
    "nowknd_single_sw10": {
        "desc": "baseline single + SKIP WEEKEND entries — isolate weekend effect",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_skip_weekend": 1, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=320 net=113.9; now n=401 net=278.06 (win rate 31.9%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=401 net=278.06. Full sweep incl. gross/dd/win-rate:
        #   gross +364.66R  net +278.06R  dd 32.28R  win 31.9%  n=401
        "pins": {"n": 401, "net": 278.06, "dd": 32.28},
    },
    "nowknd_swingpause_single_sw10": {
        "desc": "swingpause single + SKIP WEEKEND — NEW BEST SINGLE (+217.6 / DD 18.2 / 12.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=294 net=217.6; now n=365 net=228.26 (win rate 31.2%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=365 net=228.26. Full sweep incl. gross/dd/win-rate:
        #   gross +308.44R  net +228.26R  dd 30.31R  win 31.2%  n=365
        "pins": {"n": 365, "net": 228.26, "dd": 30.31},
    },
    "fliponly_multi_sw10": {
        "desc": "king + FLIP entries only (B2 was +82.4 on multi — test cut)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_kinds": "FLIP", "window_end": "exit"},
        "swing": "sw10",
        # pin was n=285 net=242.7; now n=286 net=202.45 (win rate 26.2%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=286 net=202.45. Full sweep incl. gross/dd/win-rate:
        #   gross +281.28R  net +202.45R  dd 35.43R  win 26.2%  n=286
        "pins": {"n": 286, "net": 202.45, "dd": 35.43},
    },
    "fliponly_swingpause_single_sw10": {
        "desc": "swingpause single + FLIP entries only — B2 was 178t for -0.6R",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_kinds": "FLIP", "window_end": "exit"},
        "swing": "sw10",
        # pin was n=237 net=179.7; now n=268 net=211.34 (win rate 28.0%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=268 net=211.34. Full sweep incl. gross/dd/win-rate:
        #   gross +282.78R  net +211.34R  dd 29.50R  win 28.0%  n=268
        "pins": {"n": 268, "net": 211.34, "dd": 29.50},
    },
    "wage24_multi_sw10": {
        "desc": "king + only enter HTF windows older than 24h (mature bias)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_wage_h": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=364 net=240.58. Full sweep incl. gross/dd/win-rate:
        #   gross +326.35R  net +240.58R  dd 31.33R  win 32.4%  n=364
        # all 115 registry books in one pass.
        #   gross +326.35R  net +240.58R  dd 31.33R  win 32.4%  n=364
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 364, "net": 240.58, "dd": 31.33},
    },
    "legskip2_multi_sw10": {
        "desc": "king + skip entry if HTF leg already progressed 2R (tighter ext)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_legskip_r": 2.0, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=269 net=267.3; now n=269 net=235.96 (win rate 31.6%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=269 net=235.96. Full sweep incl. gross/dd/win-rate:
        #   gross +301.69R  net +235.96R  dd 29.15R  win 31.6%  n=269
        "pins": {"n": 269, "net": 235.96, "dd": 29.15},
    },

    # ENTRY-1 + UTC-Saturday. Both filters are settled at the entry bar:
    # leg_no_entry reads candles[start..break-1], exp_skip_utc_sat is a
    # calendar test. Neither can see the future.
    #
    # Measured 2026-10-02 on unified.py:
    #   leg_no_entry, no Saturday filter     500 trades  +325.75 net
    #   leg_no_entry + skip UTC Saturday      454 trades  +358.92 net
    #
    # Note where that lands. +358.92 is within 0.03R of the origin book with
    # the same filter (454 / +358.95). That is not a coincidence and not a bug:
    # ENTRY-1 and origin read the same extreme for all but a handful of stops,
    # so they produce the same book. What separates this from the champion is
    # the stop rule, and it is the settled one - see the rule at
    # btc_engine.py and exp_origin_lookahead.py.
    "utcsat_entry_minus_1": {
        "desc": "ENTRY-1 stop + SKIP UTC-SATURDAY - both settled at the entry bar",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit",
                    "pivot_rule": "leg_no_entry",
                    "exp_skip_utc_sat": 1},
        "swing": "sw10",
        # pin was n=454 net=358.92; now n=454 net=358.92 (win rate 30.8%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=454 net=358.92. Full sweep incl. gross/dd/win-rate:
        #   gross +466.44R  net +358.92R  dd 21.18R  win 30.8%  n=454
        "pins": {"n": 454, "net": 358.92, "dd": 21.18},
    },

    "utcsat_multi_sw10": {
        "desc": "king multi + SKIP UTC-SATURDAY — causal SL (live-honest)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=453 net=279.47. Full sweep incl. gross/dd/win-rate:
        #   gross +384.34R  net +279.47R  dd 35.54R  win 30.5%  n=453
        # all 115 registry books in one pass.
        #   gross +384.34R  net +279.47R  dd 35.54R  win 30.5%  n=453
        # MEASURED 2026-10-02 on unified.py, re-run. The previous pin was 449 /
        # +295.7 and reproduced under no stop rule: origin 454/+358.95, leg
        # 453/+279.47, leg_no_entry 454/+358.92. It predated the C16 default
        # change and belonged to no current configuration.
        #
        # One knob over the causal champion: skip UTC Saturdays. 499 -> 453
        # trades, +239.12 -> +279.47 net. 57 of the 86 removed entries fell on
        # a Saturday and were carrying -16.80R gross. The other 29, and the 40
        # that appear, are the cooldown and streak-halt chain moving - removing
        # trades re-opens entries that the skip had closed off.
        "pins": {"n": 453, "net": 279.47, "dd": 35.54},
    },
    "utcsat_swingpause_single_sw10": {
        "desc": "swingpause single + SKIP UTC-SATURDAY only (UTC Sun = +51.7R is KEPT)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=325 net=166.3; now n=406 net=245.70 (win rate 29.6%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=406 net=245.7. Full sweep incl. gross/dd/win-rate:
        #   gross +340.27R  net +245.70R  dd 36.47R  win 29.6%  n=406
        "pins": {"n": 406, "net": 245.70, "dd": 36.47},
    },

    # NOTE: utc_sat variants consolidated into the other lane's keys
    # (utcsat_multi_sw10 / utcsat_swingpause_single_sw10) — identical params.
    "utc_wknd_swingpause_single_sw10": {
        "desc": "swingpause single + skip full UTC weekend (Sat+Sun) — for comparison vs Sat-only",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_utc_sat": 1, "exp_skip_utc_sun": 1,
                    "window_end": "exit"},
        "swing": "sw10",
        # pin was n=286 net=150.0; now n=350 net=121.03 (win rate 29.1%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=350 net=121.03. Full sweep incl. gross/dd/win-rate:
        #   gross +196.56R  net +121.03R  dd 40.49R  win 29.1%  n=350
        "pins": {"n": 350, "net": 121.03, "dd": 40.49},
    },

    # ===== D3 RISK-WIDTH FAMILY (skip stale/stretched breaks) =====

    "rmax15_swingpause_single_sw10": {
        "desc": "swingpause single + skip entries with stop width over 1.5% of price — DEAD (cascade)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 376, "net": 187.78, "dd": 57.54},
    },
    "rmax10_swingpause_single_sw10": {
        "desc": "swingpause single + skip entries with stop width over 1.0% of price — DEAD",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 294, "net": 228.59, "dd": 47.91},
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
        "pins": {"n": 407, "net": 255.56, "dd": 50.19},
    },

    # ===== D3 LTF REGIME FAMILY (chop15 transition band + ATR blow-off) =====

    "chopband_multi_sw10": {
        "desc": "king + skip entries in the 15m-chop transition band [55,61)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_chop15_lo": 55.0,
                    "exp_chop15_hi": 61.0, "window_end": "exit"},
        "swing": "sw10",
        # the filter still admits the same trades - only what they are worth moved.
        # all 115 registry books in one pass.
        # Was n=432 net=268.79. Full sweep incl. gross/dd/win-rate:
        #   gross +365.58R  net +268.79R  dd 41.70R  win 30.3%  n=432
        "pins": {"n": 432, "net": 268.79, "dd": 41.70},
    },
    "chopband_swingpause_single_sw10": {
        "desc": "swingpause single + skip entries in the 15m-chop transition band [55,61)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=395 net=241.65. Full sweep incl. gross/dd/win-rate:
        #   gross +332.04R  net +241.65R  dd 38.57R  win 30.6%  n=395
        # all 115 registry books in one pass.
        #   gross +332.04R  net +241.65R  dd 38.57R  win 30.6%  n=395
        # value: the same band over the swingpause base books 78 more trades than
        # its pin claimed, so this pin described a materially different book.
        # dd not re-measured.
        "pins": {"n": 395, "net": 241.65, "dd": 38.57},
    },
    "atrr_swingpause_single_sw10": {
        "desc": "swingpause single + skip entries when 15m ATR5/ATR20 > 1.4 (vol blow-off)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=316 net=182.2; now n=381 net=241.57 (win rate 28.1%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=381 net=241.57. Full sweep incl. gross/dd/win-rate:
        #   gross +337.85R  net +241.57R  dd 46.77R  win 28.1%  n=381
        "pins": {"n": 381, "net": 241.57, "dd": 46.77},
    },
    "chopband_atrr_swingpause_single_sw10": {
        "desc": "swingpause single + chop15 band AND ATR blow-off skip (combo)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=321 net=264.45. Full sweep incl. gross/dd/win-rate:
        #   gross +344.36R  net +264.45R  dd 35.77R  win 29.0%  n=321
        # all 115 registry books in one pass.
        #   gross +344.36R  net +264.45R  dd 35.77R  win 29.0%  n=321
        # value: the same band over the swingpause base books 78 more trades than
        # its pin claimed, so this pin described a materially different book.
        # dd not re-measured.
        "pins": {"n": 321, "net": 264.45, "dd": 35.77},
    },
    "atrr_swingpause_single_sw20": {
        "desc": "VALIDATION: atrr gate on sw20 chain (cross-chain robustness)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +266.27R  net +171.57R  dd 50.43R  win 30.8%  n=390
        # all 115 registry books in one pass.
        #   gross +266.27R  net +171.57R  dd 50.43R  win 30.8%  n=390
        "pins": {"n": 390, "net": 171.57, "dd": 50.43},
    },
    "atrr_cd0_swingpause_single_sw10": {
        "desc": "VALIDATION: atrr gate with cd=0 (pause-only cooldown)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +337.57R  net +240.56R  dd 47.35R  win 28.3%  n=385
        # all 115 registry books in one pass.
        #   gross +337.57R  net +240.56R  dd 47.35R  win 28.3%  n=385
        "pins": {"n": 385, "net": 240.56, "dd": 47.35},
    },
    "chopband_swingpause_single_sw20": {
        "desc": "VALIDATION: chopband gate on sw20 chain (cross-chain robustness)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "window_end": "exit"},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +237.43R  net +146.42R  dd 51.76R  win 31.2%  n=388
        # all 115 registry books in one pass.
        #   gross +237.43R  net +146.42R  dd 51.76R  win 31.2%  n=388
        "pins": {"n": 388, "net": 146.42, "dd": 51.76},
    },
    "chopband_atrr_swingpause_single_sw20": {
        "desc": "VALIDATION: chopband + atrr combo on sw20 chain",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +256.38R  net +175.90R  dd 44.83R  win 30.4%  n=329
        # all 115 registry books in one pass.
        #   gross +256.38R  net +175.90R  dd 44.83R  win 30.4%  n=329
        "pins": {"n": 329, "net": 175.90, "dd": 44.83},
    },
    "utcsat_chopband_multi_sw10": {
        "desc": "utcsat king + chop15 band skip — stack test",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "window_end": "exit"},
        "swing": "sw10",
        # the filter still admits the same trades - only what they are worth moved.
        # all 115 registry books in one pass.
        # Was n=392 net=315.45. Full sweep incl. gross/dd/win-rate:
        #   gross +407.37R  net +315.45R  dd 36.41R  win 31.6%  n=392
        "pins": {"n": 392, "net": 315.45, "dd": 36.41},
    },
    "fullstack_atrr_utcsat_multi_sw10": {
        "desc": "EXP: utcsat multi + chop15 band + ATR ratio blow-off",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_chop15_lo": 55.0, "exp_chop15_hi": 61.0,
                    "exp_atr_ratio_max": 1.4, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=311 net=295.46. Full sweep incl. gross/dd/win-rate:
        #   gross +373.24R  net +295.46R  dd 26.61R  win 29.9%  n=311
        # pin was n=0 net=0; now n=311 net=295.46 (win rate 29.9%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 311, "net": 295.46, "dd": 26.61},
    },
    "fullstack_swingpause_single_sw10": {
        "desc": "single full stack: weekend skip + swingpause + chop15 band + ATR blow-off",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_chop15_lo": 55.0,
                    "exp_chop15_hi": 61.0, "exp_atr_ratio_max": 1.4,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=262 net=268.27. Full sweep incl. gross/dd/win-rate:
        #   gross +327.89R  net +268.27R  dd 24.22R  win 32.4%  n=262
        # MEASURED 2026-10-02 on unified.py, single position (no exp_mltf).
        # Previous pin 225 / +282.9 predated the C16 default change.
        #
        # Decomposition on the same single base (502 trades / +238.45R with no
        # filters), each knob alone:
        #   weekend only      401  +278.06R   <- carries the most
        #   chopband only     438  +271.88R
        #   swingpause only   451  +242.55R
        #   atr_ratio only    416  +241.94R   <- nearly free, cuts 86 trades for +3.5R
        #   all four together 262  +268.27R   <- LESS than weekend alone
        #
        # The stack does not compound. Weekend alone is +278.1R and the full
        # stack is +268.3R, so three of the four filters are costing more than
        # they add once weekend is in. That is the finding: this book was named
        # for being the best and it is not - it is the champion base plus a
        # weekend filter with three filters stacked on top that dilute it.
        "pins": {"n": 262, "net": 268.27, "dd": 24.22},
    },
    "fullstack_wage10_cd0_single_sw10": {
        "desc": "KING SINGLE: fullstack + wage10 + cd=0 — chop15 band + ATR blow-off",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 10,
                    "exp_chop15_lo": 55.0,
                    "exp_chop15_hi": 61.0, "exp_atr_ratio_max": 1.4,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=234 net=316.64. Full sweep incl. gross/dd/win-rate:
        #   gross +372.69R  net +316.64R  dd 23.96R  win 34.6%  n=234
        # pin was n=194 net=244.5; now n=234 net=316.64 (win rate 34.6%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        "pins": {"n": 234, "net": 316.64, "dd": 23.96},
    },

    # ===== D3 WAGE VALIDATION FAMILY (other bot's sweep finding: wage12 on single +61R) =====

    "wage12_swingpause_single_sw10": {
        "desc": "REPLICATE other bot: nowknd_swingpause single + wage_h=12",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 12, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=323 net=262.31. Full sweep incl. gross/dd/win-rate:
        #   gross +334.38R  net +262.31R  dd 27.48R  win 31.9%  n=323
        # all 115 registry books in one pass.
        #   gross +334.38R  net +262.31R  dd 27.48R  win 31.9%  n=323
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 323, "net": 262.31, "dd": 27.48},
    },
    "wage8_swingpause_single_sw10": {
        "desc": "VALIDATION: wage neighborhood 8h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 8, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=329 net=247.85. Full sweep incl. gross/dd/win-rate:
        #   gross +322.49R  net +247.85R  dd 29.39R  win 31.6%  n=329
        # all 115 registry books in one pass.
        #   gross +322.49R  net +247.85R  dd 29.39R  win 31.6%  n=329
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 329, "net": 247.85, "dd": 29.39},
    },
    "wage10_swingpause_wskip_single_sw10": {
        "desc": "KING SINGLE: wage 10h + swing pause + IST weekend skip — cd=0 redundant with swingpause",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 10, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=262 net=282.1; now n=330 net=308.65 (win rate 32.4%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=330 net=308.65. Full sweep incl. gross/dd/win-rate:
        #   gross +385.19R  net +308.65R  dd 26.27R  win 32.4%  n=330
        "pins": {"n": 330, "net": 308.65, "dd": 26.27},
    },
    # === SKIP-FIRST-SWING: DEAD — first swing is where the edge lives (Exp 19 confirmed) ===
    "wage16_swingpause_single_sw10": {
        "desc": "VALIDATION: wage neighborhood 16h",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 16, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=302 net=244.8. Full sweep incl. gross/dd/win-rate:
        #   gross +311.83R  net +244.80R  dd 28.04R  win 31.5%  n=302
        # all 115 registry books in one pass.
        #   gross +311.83R  net +244.80R  dd 28.04R  win 31.5%  n=302
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 302, "net": 244.80, "dd": 28.04},
    },
    "wage20_swingpause_single_sw10": {
        "desc": "VALIDATION: wage neighborhood 20h — declines past the plateau",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_skip_weekend": 1, "exp_wage_h": 20, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=283 net=205.35. Full sweep incl. gross/dd/win-rate:
        #   gross +266.66R  net +205.35R  dd 26.45R  win 31.4%  n=283
        # all 115 registry books in one pass.
        #   gross +266.66R  net +205.35R  dd 26.45R  win 31.4%  n=283
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 283, "net": 205.35, "dd": 26.45},
    },
    "wage12_swingpause_single_nowknd_sw10": {
        "desc": "VALIDATION: wage12 WITHOUT weekend skip (stack interaction) — wage works alone (+60.9R)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_wage_h": 12, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=317 net=235.7; now n=392 net=196.94 (win rate 30.1%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=392 net=196.94. Full sweep incl. gross/dd/win-rate:
        #   gross +287.92R  net +196.94R  dd 41.23R  win 30.1%  n=392
        "pins": {"n": 392, "net": 196.94, "dd": 41.23},
    },
    "wage12_swingpause_single_sw20": {
        "desc": "VALIDATION: wage12 on sw20 chain — TRANSFERS (+24.5R, -4.9DD)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_wage_h": 12, "window_end": "exit"},
        "swing": "sw20",
        # pin was n=302 net=144.5; now n=394 net=153.32 (win rate 32.2%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=394 net=153.32. Full sweep incl. gross/dd/win-rate:
        #   gross +245.75R  net +153.32R  dd 43.96R  win 32.2%  n=394
        "pins": {"n": 394, "net": 153.32, "dd": 43.96},
    },

    # ===== D3 CAUSAL SL FAMILY (user's fix: running extreme SL) =====

    "causalsl_multi_sw10": {
        "desc": "king + causal SL (running extreme, not retroactive pivot)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_causal_sl": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +290.91R  net +185.08R  dd 47.70R  win 29.0%  n=493
        # all 115 registry books in one pass.
        #   gross +290.91R  net +185.08R  dd 47.70R  win 29.0%  n=493
        "pins": {"n": 493, "net": 185.08, "dd": 47.70},
    },
    "causalsl_swingpause_single_sw10": {
        "desc": "swingpause single + causal SL",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_causal_sl": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +294.31R  net +195.67R  dd 45.42R  win 29.6%  n=446
        # all 115 registry books in one pass.
        #   gross +294.31R  net +195.67R  dd 45.42R  win 29.6%  n=446
        "pins": {"n": 446, "net": 195.67, "dd": 45.42},
    },
    "causalsl_utcsat_multi_sw10": {
        "desc": "utcsat king + causal SL",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_causal_sl": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +328.97R  net +237.43R  dd 36.53R  win 30.6%  n=448
        # all 115 registry books in one pass.
        #   gross +328.97R  net +237.43R  dd 36.53R  win 30.6%  n=448
        "pins": {"n": 448, "net": 237.43, "dd": 36.53},
    },

    # ===== D3 BIAS MOMENTUM (1h swing magnitude ratio) =====

    "bm05_multi_sw10": {
        "desc": "king + bias momentum min 0.5 (skip fading-bias windows)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_bias_momentum_min": 0.5,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +385.93R  net +277.86R  dd 46.63R  win 30.5%  n=456
        # all 115 registry books in one pass.
        #   gross +385.93R  net +277.86R  dd 46.63R  win 30.5%  n=456
        "pins": {"n": 456, "net": 277.86, "dd": 46.63},
    },
    "bm08_multi_sw10": {
        "desc": "king + bias momentum min 0.8 (stricter)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_bias_momentum_min": 0.8,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +342.15R  net +248.81R  dd 38.30R  win 31.5%  n=391
        # all 115 registry books in one pass.
        #   gross +342.15R  net +248.81R  dd 38.30R  win 31.5%  n=391
        "pins": {"n": 391, "net": 248.81, "dd": 38.30},
    },
    "bm05_utcsat_multi_sw10": {
        "desc": "utcsat king + bias momentum min 0.5",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_bias_momentum_min": 0.5, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +396.58R  net +298.15R  dd 35.33R  win 31.0%  n=420
        # all 115 registry books in one pass.
        #   gross +396.58R  net +298.15R  dd 35.33R  win 31.0%  n=420
        "pins": {"n": 420, "net": 298.15, "dd": 35.33},
    },
    "bm08_utcsat_multi_sw10": {
        "desc": "utcsat king + bias momentum min 0.8",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_bias_momentum_min": 0.8, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +349.60R  net +264.66R  dd 29.71R  win 32.6%  n=359
        # all 115 registry books in one pass.
        #   gross +349.60R  net +264.66R  dd 29.71R  win 32.6%  n=359
        "pins": {"n": 359, "net": 264.66, "dd": 29.71},
    },
    "bm05_swingpause_single_sw10": {
        "desc": "swingpause single + bias momentum min 0.5 — FAILS on single (-29.6R)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_bias_momentum_min": 0.5, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=335 net=145.2; now n=425 net=243.81 (win rate 30.1%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=425 net=243.81. Full sweep incl. gross/dd/win-rate:
        #   gross +342.60R  net +243.81R  dd 49.00R  win 30.1%  n=425
        "pins": {"n": 425, "net": 243.81, "dd": 49.00},
    },
    "bm05_multi_sw20": {
        "desc": "VALIDATION: bm05 on sw20 chain (cross-chain transfer)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_bias_momentum_min": 0.5,
                    "window_end": "exit"},
        "swing": "sw20",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +370.20R  net +259.80R  dd 51.69R  win 31.9%  n=458
        # all 115 registry books in one pass.
        #   gross +370.20R  net +259.80R  dd 51.69R  win 31.9%  n=458
        "pins": {"n": 458, "net": 259.80, "dd": 51.69},
    },

    # ===== D3 TRAIL QUALITY (skip far trail levels) =====

    "trail10_swingpause_single": {
        "desc": "swingpause single + skip trail levels > 1.0% from entry",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 328, "net": -311.27, "dd": 313.38},
    },
    "trail06_swingpause_single": {
        "desc": "swingpause single + skip trail levels > 0.6% from entry",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 233, "net": -276.56, "dd": 276.56},
    },
    "trail10_multi": {
        "desc": "king + skip trail levels > 1.0% from entry",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_trail_max_dist": 1.0,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross -151.55R  net -247.51R  dd 248.22R  win 17.8%  n=246
        # all 115 registry books in one pass.
        #   gross -151.55R  net -247.51R  dd 248.22R  win 17.8%  n=246
        "pins": {"n": 246, "net": -247.51, "dd": 248.22},
    },

    # ===== D3 UNION DUAL-QUALIFICATION (2x2 autopsy: FLIP-only window = fragile cell) =====

    "dualunion_multi": {
        "desc": "union + filters + DUAL-QUALIFIED only (skip FLIP-window-only matches)",
        "engine": "patched",
        "params": {"mode": "union", "ext_stop_r": 1.5, "chop_thresh": 61.8,
                    "cooldown_bars": 10, "exp_skip_weekend": 1,
                    "exp_min_swing_ratio": 3.0, "exp_bias_momentum_min": 0.5,
                    "exp_union_dual_only": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +228.26R  net +201.70R  dd 9.04R  win 48.9%  n=90
        # all 115 registry books in one pass.
        #   gross +228.26R  net +201.70R  dd 9.04R  win 48.9%  n=90
        "pins": {"n": 90, "net": 201.70, "dd": 9.04},
    },
    "union_multi": {
        "desc": "union + filters (no dual gate) — reference for dual comparison",
        "engine": "patched",
        "params": {"mode": "union", "ext_stop_r": 1.5, "chop_thresh": 61.8,
                    "cooldown_bars": 10, "exp_skip_weekend": 1,
                    "exp_min_swing_ratio": 3.0, "exp_bias_momentum_min": 0.5,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +288.15R  net +245.39R  dd 16.45R  win 44.5%  n=137
        # all 115 registry books in one pass.
        #   gross +288.15R  net +245.39R  dd 16.45R  win 44.5%  n=137
        "pins": {"n": 137, "net": 245.39, "dd": 16.45},
    },

    # ===== D3 STRUCTURAL ALIGNMENT (dir match + swing age + running magnitude) =====

    "dirmatch_multi_sw10": {
        "desc": "king + REQUIRE forming swing direction match — +479.9R / DD 13.8 / WR 38.6%",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_require_dir_match": 1,
                    "window_end": "exit"},
        "swing": "sw10",
        # one; the net moved because the stop rule changed underneath it.
        # all 115 registry books in one pass.
        # Was n=389 net=444.21. Full sweep incl. gross/dd/win-rate:
        #   gross +533.97R  net +444.21R  dd 24.01R  win 38.8%  n=389
        "pins": {"n": 389, "net": 444.21, "dd": 24.01},
    },
    "age25_multi_sw10": {
        "desc": "king + max swing age 25 bars",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_max_swing_age": 25,
                    "window_end": "exit"},
        "swing": "sw10",
        # pin was n=295 net=355.6; now n=293 net=319.22 (win rate 37.2%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=293 net=319.22. Full sweep incl. gross/dd/win-rate:
        #   gross +392.64R  net +319.22R  dd 25.86R  win 37.2%  n=293
        "pins": {"n": 293, "net": 319.22, "dd": 25.86},
    },
    "age25_dirmatch_multi_sw10": {
        "desc": "king + dir match + age 25 — +386.7R / DD 9.8 / WR 43.8% (BEST quality)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_require_dir_match": 1,
                    "exp_max_swing_age": 25, "window_end": "exit"},
        "swing": "sw10",
        # one; the net moved because the stop rule changed underneath it.
        # all 115 registry books in one pass.
        # Was n=248 net=357.01. Full sweep incl. gross/dd/win-rate:
        #   gross +416.47R  net +357.01R  dd 21.47R  win 43.5%  n=248
        "pins": {"n": 248, "net": 357.01, "dd": 21.47},
    },
    "age10_dirmatch_multi_sw10": {
        "desc": "king + dir match + age 10 — +455.5R / DD 6.0 / WR 51.7% (MONSTER, 151t)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_require_dir_match": 1,
                    "exp_max_swing_age": 10, "window_end": "exit"},
        "swing": "sw10",
        # one; the net moved because the stop rule changed underneath it.
        # all 115 registry books in one pass.
        # Was n=150 net=417.68. Full sweep incl. gross/dd/win-rate:
        #   gross +462.24R  net +417.68R  dd 13.45R  win 51.3%  n=150
        "pins": {"n": 150, "net": 417.68, "dd": 13.45},
    },

    # ===== D3 CAUSAL SL FAMILY (user's fix: running extreme SL) =====

    "causalsl_multi_sw10": {
        "desc": "king + causal SL (running extreme, not retroactive pivot)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_causal_sl": 1, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 493, "net": 185.08, "dd": 47.70},
    },
    "causalsl_swingpause_single_sw10": {
        "desc": "swingpause single + causal SL",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_causal_sl": 1, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 446, "net": 195.67, "dd": 45.42},
    },
    "causalsl_utcsat_multi_sw10": {
        "desc": "utcsat king + causal SL",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_causal_sl": 1, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 448, "net": 237.43, "dd": 36.53},
    },

    # ===== D3 ALIGNMENT ON SINGLES =====

    "dirmatch_swingpause_single_sw10": {
        "desc": "swingpause single + dir match — +288.1R / DD 14.1 / WR 35.5%",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_require_dir_match": 1, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=279 net=288.1; now n=362 net=273.84 (win rate 37.6%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=362 net=273.84. Full sweep incl. gross/dd/win-rate:
        #   gross +352.26R  net +273.84R  dd 30.04R  win 37.6%  n=362
        "pins": {"n": 362, "net": 273.84, "dd": 30.04},
    },
    "age10_dirmatch_swingpause_single_sw10": {
        "desc": "swingpause single + dir match + age 10 — 🔥 BEST EVER: +435.7R / DD 5.7 / WR 53.8%",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1,
                    "exp_require_dir_match": 1,
                    "exp_max_swing_age": 10, "window_end": "exit"},
        "swing": "sw10",
        # pin was n=130 net=435.7; now n=149 net=414.08 (win rate 53.7%).
        # dd not re-measured - _net_stats no longer exposes a drawdown field.
        # all 115 registry books in one pass.
        # Was n=149 net=414.08. Full sweep incl. gross/dd/win-rate:
        #   gross +457.69R  net +414.08R  dd 12.90R  win 53.7%  n=149
        "pins": {"n": 149, "net": 414.08, "dd": 12.90},
    },
    "dirmatch_single_sw10": {
        "desc": "baseline single (no swingpause) + dir match — +237.7R / DD 15.7",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_require_dir_match": 1,
                    "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=392 net=442.72. Full sweep incl. gross/dd/win-rate:
        #   gross +532.64R  net +442.72R  dd 31.02R  win 39.5%  n=392
        # all 115 registry books in one pass.
        #   gross +532.64R  net +442.72R  dd 31.02R  win 39.5%  n=392
        # default change.
        # exp_require_dir_match: take the 15m signal only when it agrees with the
        # HTF swing direction. On the single base this book now books 100 MORE
        # trades than its pin said (292 -> 392) and nearly doubles its net, so the
        # old pin was describing a materially different book.
        "pins": {"n": 392, "net": 442.72, "dd": 31.02},
    },

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
    # History: docs/ANCHOR_BASIS_AUDIT.md records why the single original pin
    # {351, +225.3R} was split into two - n came from the fine+chop58 run while
    # gross came from the coarse+chop61.8 run. exp_crosslane.py still listed both
    # rows as reference lanes and was updated alongside this removal.

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
        "pins": {"n": 422, "net": 295.70, "dd": 36.16},
    },
    "b2doji_swingpause_single_sw10": {
        "desc": "king single + skip B2 entries with doji candle (body/range < 0.3)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 414, "net": 188.71, "dd": 46.29},
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
        "pins": {"n": 434, "net": 261.40, "dd": 37.95},
    },
    "age50_swingpause_single_sw10": {
        "desc": "king single + skip entries on swings older than 50 bars",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 429, "net": 137.14, "dd": 48.05},
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
        "pins": {"n": 407, "net": 265.38, "dd": 36.00},
    },

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
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 3, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +344.06R  net +229.45R  dd 53.26R  win 29.1%  n=495
        # all 115 registry books in one pass.
        #   gross +344.06R  net +229.45R  dd 53.26R  win 29.1%  n=495
        "pins": {"n": 495, "net": 229.45, "dd": 53.26},
    },
    "persist4_multi_sw10": {
        "desc": "king multi + persist=4 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 4, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +347.93R  net +231.70R  dd 46.85R  win 29.5%  n=501
        # all 115 registry books in one pass.
        #   gross +347.93R  net +231.70R  dd 46.85R  win 29.5%  n=501
        "pins": {"n": 501, "net": 231.70, "dd": 46.85},
    },
    "persist5_multi_sw10": {
        "desc": "king multi + persist=5 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 5, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +354.53R  net +239.00R  dd 46.85R  win 29.5%  n=498
        # all 115 registry books in one pass.
        #   gross +354.53R  net +239.00R  dd 46.85R  win 29.5%  n=498
        "pins": {"n": 498, "net": 239.00, "dd": 46.85},
    },
    "persist6_multi_sw10": {
        "desc": "king multi + persist=6 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 6, "window_end": "exit"},
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

        "pins": {"n": 499, "net": 239.12, "dd": 46.85},
    },
    "persist8_multi_sw10": {
        "desc": "king multi + persist=8 (fine sweep, current=7)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 8, "window_end": "exit"},
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

        "pins": {"n": 499, "net": 239.12, "dd": 46.85},
    },

    # --- htf_rr re-sweep on king multi (current=3.0, swept pre-fix only) ---
    "htfrr2_multi_sw10": {
        "desc": "king multi + htf_rr=2.0 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 2.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +397.50R  net +292.86R  dd 35.68R  win 29.6%  n=423
        # all 115 registry books in one pass.
        #   gross +397.50R  net +292.86R  dd 35.68R  win 29.6%  n=423
        "pins": {"n": 423, "net": 292.86, "dd": 35.68},
    },
    "htfrr25_multi_sw10": {
        "desc": "king multi + htf_rr=2.5 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 2.5,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +324.69R  net +221.11R  dd 34.27R  win 27.9%  n=419
        # all 115 registry books in one pass.
        #   gross +324.69R  net +221.11R  dd 34.27R  win 27.9%  n=419
        "pins": {"n": 419, "net": 221.11, "dd": 34.27},
    },
    "htfrr35_multi_sw10": {
        "desc": "king multi + htf_rr=3.5 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 3.5,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +303.14R  net +202.29R  dd 41.04R  win 28.1%  n=406
        # all 115 registry books in one pass.
        #   gross +303.14R  net +202.29R  dd 41.04R  win 28.1%  n=406
        "pins": {"n": 406, "net": 202.29, "dd": 41.04},
    },
    "htfrr4_multi_sw10": {
        "desc": "king multi + htf_rr=4.0 (re-sweep post-fix, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "htf_rr": 4.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +321.93R  net +222.36R  dd 38.81R  win 29.2%  n=397
        # all 115 registry books in one pass.
        #   gross +321.93R  net +222.36R  dd 38.81R  win 29.2%  n=397
        "pins": {"n": 397, "net": 222.36, "dd": 38.81},
    },

    # --- ext_stop_r sweep on utcsat king (current=3.0, never swept on king) ---
    "ext2_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=2.0 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 2.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +402.41R  net +301.86R  dd 41.77R  win 32.6%  n=417
        # all 115 registry books in one pass.
        #   gross +402.41R  net +301.86R  dd 41.77R  win 32.6%  n=417
        "pins": {"n": 417, "net": 301.86, "dd": 41.77},
    },
    "ext25_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=2.5 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 2.5,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +385.83R  net +281.30R  dd 36.18R  win 30.8%  n=442
        # all 115 registry books in one pass.
        #   gross +385.83R  net +281.30R  dd 36.18R  win 30.8%  n=442
        "pins": {"n": 442, "net": 281.30, "dd": 36.18},
    },
    "ext35_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=3.5 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.5,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +384.11R  net +279.16R  dd 35.54R  win 30.4%  n=454
        # all 115 registry books in one pass.
        #   gross +384.11R  net +279.16R  dd 35.54R  win 30.4%  n=454
        "pins": {"n": 454, "net": 279.16, "dd": 35.54},
    },
    "ext4_utcsat_multi_sw10": {
        "desc": "utcsat king + ext_stop_r=4.0 (sweep on king, current=3.0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 4.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
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

        "pins": {"n": 454, "net": 279.16, "dd": 35.54},
    },

    # --- wage_h / curfew on kings (never tested on king configs) ---
    "wage12_utcsat_multi_sw10": {
        "desc": "utcsat king + wage_h=12 (never tested on king, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_wage_h": 12, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +365.61R  net +273.70R  dd 31.66R  win 31.5%  n=391
        # all 115 registry books in one pass.
        #   gross +365.61R  net +273.70R  dd 31.66R  win 31.5%  n=391
        "pins": {"n": 391, "net": 273.70, "dd": 31.66},
    },
    "wage24_utcsat_multi_sw10": {
        "desc": "utcsat king + wage_h=24 (never tested on king, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_wage_h": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +353.29R  net +273.80R  dd 21.70R  win 33.4%  n=332
        # all 115 registry books in one pass.
        #   gross +353.29R  net +273.80R  dd 21.70R  win 33.4%  n=332
        "pins": {"n": 332, "net": 273.80, "dd": 21.70},
    },
    "wage24_swingpause_single_sw10": {
        "desc": "best single + wage_h=24 (never tested on best single, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 269, "net": 228.40, "dd": 20.87},
    },
    "curfew624_utcsat_multi_sw10": {
        "desc": "utcsat king + skip age 6-24h band (never tested on king, current=0/0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1,
                    "exp_curfew_a": 6, "exp_curfew_b": 24, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +393.15R  net +304.72R  dd 31.95R  win 32.4%  n=377
        "pins": {"n": 377, "net": 304.72, "dd": 31.95},
    },
    "curfew624_swingpause_single_sw10": {
        "desc": "best single + skip age 6-24h band (never tested on best single, current=0/0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 300, "net": 198.91, "dd": 23.17},
    },

    # --- partial_r fine sweep on king multi (current=0, only 7.5 tested on sw20) ---
    "partial1_multi_sw10": {
        "desc": "king multi + partial_r=1.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 1.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +179.60R  net +50.19R  dd 43.84R  win 41.4%  n=553
        # all 115 registry books in one pass.
        #   gross +179.60R  net +50.19R  dd 43.84R  win 41.4%  n=553
        "pins": {"n": 553, "net": 50.19, "dd": 43.84},
    },
    "partial2_multi_sw10": {
        "desc": "king multi + partial_r=2.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 2.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +194.80R  net +72.28R  dd 39.25R  win 37.5%  n=528
        # all 115 registry books in one pass.
        #   gross +194.80R  net +72.28R  dd 39.25R  win 37.5%  n=528
        "pins": {"n": 528, "net": 72.28, "dd": 39.25},
    },
    "partial3_multi_sw10": {
        "desc": "king multi + partial_r=3.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 3.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +212.24R  net +92.55R  dd 39.75R  win 33.5%  n=513
        # all 115 registry books in one pass.
        #   gross +212.24R  net +92.55R  dd 39.75R  win 33.5%  n=513
        "pins": {"n": 513, "net": 92.55, "dd": 39.75},
    },
    "partial4_multi_sw10": {
        "desc": "king multi + partial_r=4.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 4.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +224.78R  net +106.70R  dd 45.39R  win 31.0%  n=506
        # all 115 registry books in one pass.
        #   gross +224.78R  net +106.70R  dd 45.39R  win 31.0%  n=506
        "pins": {"n": 506, "net": 106.70, "dd": 45.39},
    },
    "partial5_multi_sw10": {
        "desc": "king multi + partial_r=5.0 (fine sweep, current=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 5.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        # all 115 registry books in one pass.
        # Was n=None net=None. Full sweep incl. gross/dd/win-rate:
        #   gross +248.37R  net +131.63R  dd 46.01R  win 30.7%  n=501
        # all 115 registry books in one pass.
        #   gross +248.37R  net +131.63R  dd 46.01R  win 30.7%  n=501
        "pins": {"n": 501, "net": 131.63, "dd": 46.01},
    },
    # === FUNDING RATE FILTER: DEAD (data too sparse, 0 trades filtered) ===
}


class _AliasRegistry(dict):
    """dict of book configs, where a string value means "same book as that key".

    Two registry books turned out to be the same experiment under two names once
    rerun on unified.py (see the notes on swingpause_cd0_single_sw10 and
    skip1pause_multi_sw10). Rather than copy the config - which is how the
    duplication went unnoticed in the first place, because the copies drifted -
    the alias points at the surviving entry. Readers can keep doing
    EXPERIMENTS[key]["params"] and get the real config.
    """

    def __getitem__(self, key):
        val = super().__getitem__(key)
        return self._deref(key, val)

    def get(self, key, default=None):
        if key not in self:
            return default
        return self[key]

    def _deref(self, key, val, _seen=None):
        if not isinstance(val, str):
            return val
        _seen = _seen or set()
        if key in _seen:
            raise KeyError("alias loop at %r" % key)
        _seen.add(key)
        if val not in self:
            raise KeyError("%r aliases %r, which is not a book" % (key, val))
        return self._deref(val, super().__getitem__(val), _seen)


EXPERIMENTS = _AliasRegistry(EXPERIMENTS)


def book(key):
    """Resolved config for a book key, following aliases."""
    return EXPERIMENTS[key]


def alias_of(key):
    """The surviving key if `key` is an alias, else None."""
    val = dict.__getitem__(EXPERIMENTS, key)
    return val if isinstance(val, str) else None


ALIASES = {k: v for k, v in dict.items(EXPERIMENTS) if isinstance(v, str)}

# Groups for batch runs
GROUPS = {
    "coarse_matrix": ["lb30_w24_ext1.5", "lb30_w24_ext2.0", "lb30_w24_ext2.5", "lb30_w24_ext3.0"],
    "fine_pins": ["a4_w24_ext1.5", "a4_w24_ext3.0"],
    "champions": ["champion_single_sw20", "champion_single_sw10", "champion_multi_sw20", "champion_multi_sw10"],
    "baselines": ["baseline_no_partial_sw20", "baseline_no_partial_sw10"],
    "cooldown": ["skipwin1_multi_sw10", "skipwin2_multi_sw10", "swingpause_multi_sw10",
                  "skip1pause_multi_sw10", "skipwin1_single_sw10", "swingpause_single_sw10",
                  "skipwinhalt_multi_sw10", "skipwinhalt_single_sw10",
                  "swingpause_single_sw20"],
    "patterns": ["nowknd_multi_sw10", "nowknd_single_sw10", "nowknd_swingpause_single_sw10",
                  "fliponly_multi_sw10", "fliponly_swingpause_single_sw10",
                  "wage24_multi_sw10", "legskip2_multi_sw10",
                  "utcsat_multi_sw10", "utcsat_swingpause_single_sw10"],
    "riskgates": ["rmax15_swingpause_single_sw10", "rmax10_swingpause_single_sw10",
                   "rmax15_multi_sw10"],
    "wageval": ["wage12_swingpause_single_sw10", "wage8_swingpause_single_sw10",
                 "wage10_swingpause_wskip_single_sw10", "wage16_swingpause_single_sw10",
                 "wage20_swingpause_single_sw10", "wage12_swingpause_single_nowknd_sw10",
                 "wage12_swingpause_single_sw20"],
    "ltfregime": ["chopband_multi_sw10", "chopband_swingpause_single_sw10",
                   "atrr_swingpause_single_sw10", "chopband_atrr_swingpause_single_sw10",
                   "utcsat_chopband_multi_sw10", "fullstack_swingpause_single_sw10",
                   "atrr_swingpause_single_sw20", "atrr_cd0_swingpause_single_sw10",
                   "chopband_swingpause_single_sw20", "chopband_atrr_swingpause_single_sw20"],
    "best": ["utcsat_multi_sw10", "fullstack_wage10_cd0_single_sw10"],
    "entryquality": ["b2doji_utcsat_multi_sw10", "b2doji_swingpause_single_sw10",
                      "age50_utcsat_multi_sw10", "age50_swingpause_single_sw10",
                      "combined_b2age_utcsat_multi_sw10"],
    "kingsweep": [
        # persist fine sweep
        "persist3_multi_sw10", "persist4_multi_sw10", "persist5_multi_sw10",
        "persist6_multi_sw10", "persist8_multi_sw10",
        # htf_rr re-sweep (FIXED: htf_rr now in cfg["params"])
        "htfrr2_multi_sw10", "htfrr25_multi_sw10", "htfrr35_multi_sw10", "htfrr4_multi_sw10",
        # ext_stop_r on king
        "ext2_utcsat_multi_sw10", "ext25_utcsat_multi_sw10",
        "ext35_utcsat_multi_sw10", "ext4_utcsat_multi_sw10",
        # wage_h / curfew on kings
        "wage12_utcsat_multi_sw10", "wage24_utcsat_multi_sw10",
        "wage10_swingpause_wskip_single_sw10", "wage24_swingpause_single_sw10",
        "curfew624_utcsat_multi_sw10", "curfew624_swingpause_single_sw10",
        # partial_r fine sweep
        "partial1_multi_sw10", "partial2_multi_sw10", "partial3_multi_sw10",
        "partial4_multi_sw10", "partial5_multi_sw10",
    ],
    "biasmomentum": ["bm05_multi_sw10", "bm08_multi_sw10",
                      "bm05_utcsat_multi_sw10", "bm08_utcsat_multi_sw10",
                      "bm05_swingpause_single_sw10", "bm05_multi_sw20"],
    "dualunion": ["union_multi", "dualunion_multi"],
    "alignment": ["dirmatch_multi_sw10", "age25_multi_sw10",
                   "age25_dirmatch_multi_sw10", "age10_dirmatch_multi_sw10"],
    # "skipfirst": DEAD
    # "funding": DEAD (data too sparse, 0 trades filtered)
    "all": None,  # None = run everything except hidden
}
