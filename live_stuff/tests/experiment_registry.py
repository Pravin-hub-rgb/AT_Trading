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
        "desc": "Champion multi sw10 WITHOUT partials — ACTUAL KING (+325.8, trail-fix)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 500, "net": 325.8, "dd": 17.8, "partials": 0},
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

    # ===== SHIPPED BASELINE (identity gate reference) =====
    # D3 anchor audit (2026-09-20): the old "_shipped_sw20" pin {n:351, gross:225.3}
    # was an IMPOSSIBLE hybrid — n came from the fine+chop58 run (gross there is
    # +238.0), gross came from the coarse+chop61.8 run (n there is 340).
    # Split into two exact reference rows, one per basis. See docs/ANCHOR_BASIS_AUDIT.md.

    "_shipped_coarse_618": {
        "desc": "Shipped engine, flags off, sw20, COARSE 15m fills + chop 61.8 (identity-gate basis)",
        "engine": "shipped",
        "params": {},
        "use_bp": False,
        "swing": "sw20",
        "basis": "coarse",
        "pins": {"n": 340, "gross": 225.3},
    },
    "_shipped_fine_58": {
        "desc": "Shipped engine, flags off, sw20, FINE 1m fills + chop 58 (production basis)",
        "engine": "shipped",
        "params": {},
        "use_bp": True,
        "swing": "sw20",
        "basis": "fine",
        "pins": {"n": 351, "gross": 238.0},
    },
    # NOTE: no separate "sw15" row — run_one fixes the LTF chain at sw15 (mb50)
    # and cfg["swing"] selects only the HTF window chain, so a sw15 row is not
    # expressible and _shipped_coarse_618 IS the craze identity twin (verified:
    # 340t / +225.3R, IDENTICAL to test_experiments_craze.main() gate output).
}

# Groups for batch runs
GROUPS = {
    "coarse_matrix": ["lb30_w24_ext1.5", "lb30_w24_ext2.0", "lb30_w24_ext2.5", "lb30_w24_ext3.0"],
    "fine_pins": ["a4_w24_ext1.5", "a4_w24_ext3.0"],
    "champions": ["champion_single_sw20", "champion_single_sw10", "champion_multi_sw20", "champion_multi_sw10"],
    "baselines": ["baseline_no_partial_sw20", "baseline_no_partial_sw10"],
    "all": None,  # None = run everything except hidden
}
