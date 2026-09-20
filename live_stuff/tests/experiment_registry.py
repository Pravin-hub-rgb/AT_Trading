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
#   fine       : use 1m fine fills for exit precision
#   pins       : expected results for validation (optional)
#   htf_rr     : override htf_rr if needed (default 3.0)
# ---------------------------------------------------------------------------

EXPERIMENTS = {

    # ===== COARSE MATRIX (no fine fills, gross R) =====

    "lb30_w24_ext1.5": {
        "desc": "lb30 w24 ext1.5 (coarse gross)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 265, "gross": 231.6},
    },
    "lb30_w24_ext2.0": {
        "desc": "lb30 w24 ext2.0 (coarse gross)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.0},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 294, "gross": 248.2},
    },
    "lb30_w24_ext2.5": {
        "desc": "lb30 w24 ext2.5 (coarse gross)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 2.5},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 304, "gross": 231.7},
    },
    "lb30_w24_ext3.0": {
        "desc": "lb30 w24 ext3.0 (coarse gross)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 307, "gross": 222.4},
    },

    # ===== A4 FINE PINS =====

    "a4_w24_ext1.5": {
        "desc": "A4 w24 ext1.5 (coarse, on sw20)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 1.5},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 250, "gross": 207.1},
    },
    "a4_w24_ext3.0": {
        "desc": "A4 w24 ext3.0 (coarse, on sw20)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "ext_stop_r": 3.0},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 285, "gross": 218.8},
    },

    # ===== OPT MULTI (their champion) =====

    "opt_cd10_w24": {
        "desc": "OPT cd10 w24 ext1.5 (their champion multi, coarse)",
        "engine": "patched",
        "params": {"exp31_lb": 30, "chop_thresh": 55.0, "exp_persist": 2,
                    "exp_wage_h": 24, "cooldown_bars": 10, "exp_mltf": True,
                    "ext_stop_r": 1.5},
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 300, "gross": 216.5},
    },

    # ===== OUR CHAMPIONS (partial exits) =====

    "champion_single_sw20": {
        "desc": "Champion single sw20 (raw NET king, +261.5)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "window_end": "exit"},
        "swing": "sw20",
        "fine": True,
        "pins": {"n": 371, "net": 261.5, "dd": 29.3, "partials": 42},
    },
    "champion_single_sw10": {
        "desc": "Champion single sw10 (best NET/DD ratio, +238.4)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "window_end": "exit"},
        "swing": "sw10",
        "fine": True,
        "pins": {"n": 395, "net": 238.4, "dd": 16.0, "partials": 38},
    },
    "champion_multi_sw20": {
        "desc": "Champion multi sw20 (+465.1)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw20",
        "fine": True,
        "pins": {"n": 487, "net": 465.1, "dd": 21.9, "partials": 62},
    },
    "champion_multi_sw10": {
        "desc": "Champion multi sw10 — NEW OVERALL KING (+472.9)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 7.5, "exp_mltf": True,
                    "exp_persist": 7, "window_end": "exit"},
        "swing": "sw10",
        "fine": True,
        "pins": {"n": 501, "net": 472.9, "dd": 14.5, "partials": 60},
    },

    # ===== BASELINES (no partial, for delta measurement) =====

    "baseline_no_partial_sw20": {
        "desc": "Champion config without partial exits sw20 (baseline, +148.2)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "window_end": "exit"},
        "swing": "sw20",
        "fine": True,
        "pins": {"n": 371, "net": 148.2, "dd": 37.3},
    },
    "baseline_no_partial_sw10": {
        "desc": "Champion config without partial exits sw10 (baseline, +163.6)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "window_end": "exit"},
        "swing": "sw10",
        "fine": True,
        "pins": {"n": 394, "net": 163.6, "dd": 29.2},
    },

    # ===== SHIPPED BASELINE (identity gate reference) =====

    "_shipped_sw20": {
        "desc": "Shipped engine, all flags off, sw20 (identity reference)",
        "engine": "shipped",
        "params": {},
        "use_bp": True,
        "swing": "sw20",
        "fine": False,
        "pins": {"n": 351, "gross": 225.3},
    },
    "_shipped_sw15": {
        "desc": "Shipped engine, all flags off, sw15 (craze identity)",
        "engine": "shipped",
        "params": {},
        "use_bp": True,
        "swing": "sw15",
        "fine": False,
        "pins": {"n": 340, "gross": 225.3},
    },
}

# Groups for batch runs
GROUPS = {
    "coarse_matrix": ["lb30_w24_ext1.5", "lb30_w24_ext2.0", "lb30_w24_ext2.5", "lb30_w24_ext3.0"],
    "fine_pins": ["a4_w24_ext1.5", "a4_w24_ext3.0"],
    "champions": ["champion_single_sw20", "champion_single_sw10", "champion_multi_sw20", "champion_multi_sw10"],
    "baselines": ["baseline_no_partial_sw20", "baseline_no_partial_sw10"],
    "all": None,  # None = run everything except hidden
}
