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
        "pins": {"n": 357, "net": 174.8, "dd": 23.4},
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
        "pins": {"n": 357, "net": 174.7, "dd": 23.4},
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
        "pins": {"n": 400, "net": 307.8, "dd": 17.1},
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
        "pins": {"n": 362, "net": 243.9, "dd": 23.1},
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

    "utcsat_multi_sw10": {
        "desc": "king + SKIP UTC-SATURDAY only (UTC Sun = +124.2R is KEPT) — NEW KING (+359.0 / DD 14.8)",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                    "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                    "chop_thresh": 58.0, "cooldown_bars": 8,
                    "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                    "exp_partial_r": 0.0, "exp_mltf": True,
                    "exp_persist": 7, "exp_skip_utc_sat": 1, "window_end": "exit"},
        "swing": "sw10",
        "pins": {"n": 454, "net": 359.0, "dd": 14.8},
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
    "cooldown": ["skipwin1_multi_sw10", "skipwin2_multi_sw10", "swingpause_multi_sw10",
                  "skip1pause_multi_sw10", "skipwin1_single_sw10", "swingpause_single_sw10",
                  "skipwinhalt_multi_sw10", "skipwinhalt_single_sw10",
                  "swingpause_cd0_single_sw10", "swingpause_single_sw20"],
    "patterns": ["nowknd_multi_sw10", "nowknd_single_sw10", "nowknd_swingpause_single_sw10",
                  "fliponly_multi_sw10", "fliponly_swingpause_single_sw10",
                  "wage24_multi_sw10", "legskip2_multi_sw10",
                  "utcsat_multi_sw10", "utcsat_swingpause_single_sw10"],
    "best": ["utcsat_multi_sw10", "nowknd_swingpause_single_sw10"],
    "all": None,  # None = run everything except hidden
}
