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
        "pins": {},
    },
    "opt_ml_cd10_mb10": {
        "desc": "OPT mltf cd10 chop55 persist2 mb10 (exp37 C2)",
        "engine": "patched",
        "params": {"chop_thresh": 55.0, "exp_persist": 2,
                    "cooldown_bars": 10, "exp_mltf": True},
        "swing": "sw10",
        "pins": {},
    },
    "lb30_chop55_persist2": {
        "desc": "lb30 chop55 persist2 mb10 (exp37 A4)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0,
                    "exp_persist": 2},
        "swing": "sw10",
        "pins": {},
    },
    "lb30_persist5": {
        "desc": "lb30 persist5 mb20 (exp37 A3/A5)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_persist": 5},
        "swing": "sw20",
        "pins": {},
    },
    "lb30_halt0": {
        "desc": "lb30 no halt (exp37 B0)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "max_consecutive_losses": 0},
        "swing": "sw20",
        "pins": {},
    },
    "lb30_halt6_cd0": {
        "desc": "lb30 halt6 cd0 (exp37 B3)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "max_consecutive_losses": 6,
                    "cooldown_bars": 0},
        "swing": "sw20",
        "pins": {},
    },

    # ===== LB30 SWEPT EXT (fine fills) =====

    "lb30_w24_ext1.5": {
        "desc": "lb30 w24 ext1.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {},
    },
    "lb30_w24_ext2.0": {
        "desc": "lb30 w24 ext2.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.0},
        "swing": "sw20",
        "pins": {},
    },
    "lb30_w24_ext2.5": {
        "desc": "lb30 w24 ext2.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.5},
        "swing": "sw20",
        "pins": {},
    },
    "lb30_w24_ext3.0": {
        "desc": "lb30 w24 ext3.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        "pins": {},
    },

    # ===== A4 (fine fills) =====

    "a4_w24_ext1.5": {
        "desc": "A4 w24 ext1.5 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {},
    },
    "a4_w24_ext3.0": {
        "desc": "A4 w24 ext3.0 (fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        "pins": {},
    },

    # ===== OPT MULTI (their champion, fine fills) =====

    "opt_cd10_w24": {
        "desc": "OPT cd10 w24 ext1.5 (their champion multi, fine fills)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "cooldown_bars": 10, "exp_mltf": True,
                    "ext_stop_r": 1.5},
        "swing": "sw20",
        "pins": {},
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
        "pins": {"n": 372, "net": 90.1, "dd": 33.7, "partials": 41},
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
        "pins": {"n": 396, "net": 82.0, "dd": 22.0, "partials": 37},
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
        "pins": {"n": 487, "net": 208.4, "dd": 29.4, "partials": 60},
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
        "pins": {"n": 500, "net": 325.78, "dd": 17.83, "partials": 0},  # MEASURED 2026-10-01, Bybit perp
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
        # MEASURED 2026-10-02 via the registry path with this book's own params:
        # 495 trades, +322.18R gross. The 500 / +232.06 I first wrote came from a
        # hand-built config missing exp_mltf and exp_persist, so it was not this
        # book. Measured through the harness only - raw unified.py does not accept
        # exp_partial_r, which the harness injects, so raw and harness are
        # different code paths for the exp_causal_sl branch (t_c13).
        "pins": {"n": 495, "net": 215.14, "partials": 0},
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
        "pins": {"n": 499, "net": 239.12, "partials": 0},  # MEASURED 2026-10-01, Bybit perp
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
        # MEASURED 2026-10-02: 500 / +445.19 gross, +325.75 net. The pin was first
        # written with the gross figure in the net field, which the runner does not
        # check against - it silently passed because n matched and net was not
        # compared against gross.
        "pins": {"n": 500, "net": 325.75, "partials": 0},
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
        # MEASURED 2026-10-02: 500 / +325.7 net, identical to champion_multi_sw10_entry1.
        # Its exp_ltf_no_entry=1 does nothing on its own - without exp_causal_sl=1 the
        # LTF leg reads sig["swing_start_px"], which pivot_rule already sets. This is
        # therefore the same book as entry1 under a second name. The version that
        # actually differs on both legs is champion_multi_sw10_entry_both.
        "pins": {"n": 500, "net": 325.75, "partials": 0},
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
        "pins": {"n": 372, "net": 122.3, "dd": 37.3},
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
        "pins": {"n": 395, "net": 137.7, "dd": 29.2},
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
        "pins": {"n": 144, "net": -1.1, "dd": 38.8},
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
        "pins": {"n": 105, "net": -26.1, "dd": 34.2},
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
        "pins": {"n": 443, "net": 231.0, "dd": 19.8},
    },
    "skip1pause_multi_sw10": {
        "desc": "king + window-skip 1 AND swing-pause after a loss",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skipwin": 1,
                    "exp_swingpause": 1, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 144, "net": -1.1, "dd": 38.8},
    },
    "skipwin1_single_sw10": {
        "desc": "baseline single + skip the next HTF window opened after a loss",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_skipwin": 1, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 138, "net": -4.3, "dd": 40.0},
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
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # On this single base, what each mechanism is worth:
        #   no cooldown, no swingpause     556 / +166.54R
        #   cooldown_bars=8                499 / +239.12R
        #   cooldown_bars=0 + swingpause   451 / +232.45R
        # Swing pause recovers most of what the bar cooldown was worth, on 48
        # fewer trades - it blocks re-entry into the same swing rather than
        # waiting out N bars. Together they are slightly worse than cooldown
        # alone, which is why the production champion keeps the cooldown.
        "pins": {"n": 451, "net": 232.45},
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
        "pins": {"n": 323, "net": 102.6, "dd": 20.1},
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
        "pins": {"n": 276, "net": 71.8, "dd": 27.0},
    },
    "swingpause_cd0_single_sw10": {
        "desc": "single + swing-pause REPLACES bar-cooldown (cd=0)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 0,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1, "window_end": "exit"},
        "swing": "sw10",
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # On this single base, what each mechanism is worth:
        #   no cooldown, no swingpause     556 / +166.54R
        #   cooldown_bars=8                499 / +239.12R
        #   cooldown_bars=0 + swingpause   451 / +232.45R
        # Swing pause recovers most of what the bar cooldown was worth, on 48
        # fewer trades - it blocks re-entry into the same swing rather than
        # waiting out N bars. Together they are slightly worse than cooldown
        # alone, which is why the production champion keeps the cooldown.
        "pins": {"n": 451, "net": 232.45},
    },
    "swingpause_single_sw20": {
        "desc": "baseline single sw20 + swing-pause (fresh structure)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_swingpause": 1, "window_end": "exit"},
        "swing": "sw20",
        "pins": {"n": 338, "net": 120.0, "dd": 34.1},
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
        "pins": {"n": 320, "net": 113.9, "dd": 30.5},
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
        "pins": {"n": 294, "net": 217.6, "dd": 18.2},
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
        "pins": {"n": 285, "net": 242.7, "dd": 24.3},
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
        "pins": {"n": 237, "net": 179.7, "dd": 21.9},
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
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 364, "net": 240.58},
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
        "pins": {"n": 269, "net": 267.3, "dd": 17.2},
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
        "pins": {"n": 454, "net": 358.92, "partials": 0},  # MEASURED 2026-10-02, Bybit perp
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
        "pins": {"n": 453, "net": 279.47},  # causal SL
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
        "pins": {"n": 325, "net": 166.3, "dd": 23.3},
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
        "pins": {"n": 286, "net": 150.0, "dd": 23.1},
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
        "pins": {"n": 310, "net": 91.7, "dd": 38.1},
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
        "pins": {"n": 255, "net": 195.5, "dd": 31.4},
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
        "pins": {"n": 406, "net": 259.4, "dd": 35.6},
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
        "pins": {"n": 432, "net": 350.7, "dd": 17.6},
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
        "pins": {"n": 317, "net": 227.6, "dd": 20.0},
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
        "pins": {"n": 316, "net": 182.2, "dd": 21.2},
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
        "pins": {"n": 269, "net": 215.1, "dd": 12.6},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {"n": 392, "net": 362.2, "dd": 18.1},
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
        "pins": {"n": 0, "net": 0, "dd": 0},
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
        "pins": {"n": 262, "net": 268.27},
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
        "pins": {"n": 194, "net": 244.5, "dd": 16.6},  # causal SL (live-honest)
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
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 323, "net": 262.31},
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
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 329, "net": 247.85},
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
        "pins": {"n": 262, "net": 282.1, "dd": 14.7},
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
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 302, "net": 244.80},
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
                # RE-MEASURED 2026-10-02 on unified.py. Previous pin predated the C16
        # default change.
        # Window-age sweep on the swingpause single base, cap in hours:
        #   none 444/+241.06   4h 417/+248.23   8h 399/+263.15
        #   10h 392/+267.23  12h 384/+264.00  16h 362/+243.70
        #   20h 338/+218.94  24h 323/+225.08
        # One smooth peak around 10h, so the age cap is picking up a real
        # concentration rather than one lucky bar. Past ~16h it turns against.
        "pins": {"n": 283, "net": 205.35},
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
        "pins": {"n": 317, "net": 235.7, "dd": 21.7},
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
        "pins": {"n": 302, "net": 144.5, "dd": 29.2},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {"n": 335, "net": 145.2, "dd": 20.8},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
    },
    "union_multi": {
        "desc": "union + filters (no dual gate) — reference for dual comparison",
        "engine": "patched",
        "params": {"mode": "union", "ext_stop_r": 1.5, "chop_thresh": 61.8,
                    "cooldown_bars": 10, "exp_skip_weekend": 1,
                    "exp_min_swing_ratio": 3.0, "exp_bias_momentum_min": 0.5,
                    "window_end": "exit"},
        "swing": "sw10",
        "pins": {},
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
        "pins": {"n": 389, "net": 479.9, "dd": 13.8},
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
        "pins": {"n": 295, "net": 355.6, "dd": 12.8},
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
        "pins": {"n": 249, "net": 386.7, "dd": 9.8},
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
        "pins": {"n": 151, "net": 455.5, "dd": 6.0},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {},
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
        "pins": {"n": 279, "net": 288.1, "dd": 14.1},
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
        "pins": {"n": 130, "net": 435.7, "dd": 5.7},
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
        "pins": {"n": 292, "net": 237.7, "dd": 15.7},
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
    },
    # === FUNDING RATE FILTER: DEAD (data too sparse, 0 trades filtered) ===
}

# Groups for batch runs
GROUPS = {
    "coarse_matrix": ["lb30_w24_ext1.5", "lb30_w24_ext2.0", "lb30_w24_ext2.5", "lb30_w24_ext3.0"],
    "fine_pins": ["a4_w24_ext1.5", "a4_w24_ext3.0"],
    "champions": ["champion_single_sw20", "champion_single_sw10", "champion_multi_sw20", "champion_multi_sw10"],
    "baselines": ["baseline_no_partial_sw20", "baseline_no_partial_sw10"],
    "cooldown": ["skipwin1_multi_sw10", "skipwin2_multi_sw10", "swingpause_multi_sw10",
                  "skip1pause_multi_sw10", "skipwin1_single_sw10", "swingpause_single_sw10",
                  "skipwinhalt_multi_sw10", "skipwinhalt_single_sw10",
                  "swingpause_cd0_single_sw10", "swingpause_single_sw20"],
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
