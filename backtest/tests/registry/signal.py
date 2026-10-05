"""SIGNAL - one-position books: FS exit, directional entry, serial, the signal book.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {
    # ===== FS-EXIT (engine knob, measured 2026-10-03 IS+OOS) =====
    # Enter exactly as the book does, then close the position when its own
    # swing confirms - but only when that confirmation lands within a few
    # hours of the entry. Causal: fs_at_idx >= seg.end_idx and the book enters
    # at a B2/flip break which sits before that, so the exit only ever reads
    # a confirmation that already happened.
    #
    # The band is a plateau at 2-6h, not a knife edge - every arm in it beats
    # the control on BOTH eras. Exiting on ANY FS is far worse than doing
    # nothing (+133.26 IS / +57.90 OOS vs +239.12 / +72.79), because the
    # long-gap swings are where the runners live.
    "fsexit4_c": {
        "desc": "champion leg + exit at own-swing FS when it lands within 4h",
        "engine": "patched",
"params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                     "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                     "chop_thresh": 58.0, "cooldown_bars": 8,
                     "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                     "exp_partial_r": 0.0, "exp_mltf": True,
                     "exp_persist": 7, "window_end": "exit",
                     "pivot_rule": "leg",
                     "exit_fs_max_gap_h": 4.0},
        "swing": "sw10",
        # See the FS_EXIT ladder in exp_fs_exit.py.
        "pins": {"n": 502, "net": 289.98, "dd_net": 42.34,
                 "oos_n": 287, "oos_net": 79.42, "oos_dd_net": 43.91},
    },
    # ===== DIRECTIONAL FS ENTRY (engine knob exp_fs_entry_side) =====
    # ===== DIRECTIONAL FS ENTRY (engine knob exp_fs_entry_side) =====
    # Measured 2026-10-04 by exp_fs_directional_leg.py on CAUSAL leg-family
    # books, both eras. Only the ENTRY TRIGGER changes on one side; the other
    # side, the LTF cascade and every risk knob are untouched. Do not confuse
    # with the closed FS-EXIT work in CLOSED_DO_NOT_REPEAT.md: same FS print,
    # but used to DELAY an entry instead of to close a position.
    "fsent_champ_long": {
          "desc": "champion leg + LONGS enter at swing FS (shorts unchanged)",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # Directional FS entry: ONE side enters at the swing FS print, the
          # other side unchanged. exp_fs_directional_leg.py, both eras.
          "pins": {"n": 525, "net": 528.87, "dd_net": 14.19,
                   "oos_n": 310, "oos_net": 243.92, "oos_dd_net": 11.88},
      },

    "fsent_champ_short": {
          "desc": "champion leg + SHORTS enter at swing FS (longs unchanged)",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # Directional FS entry: ONE side enters at the swing FS print, the
          # other side unchanged. exp_fs_directional_leg.py, both eras.
          "pins": {"n": 532, "net": 571.44, "dd_net": 25.85,
                   "oos_n": 309, "oos_net": 239.32, "oos_dd_net": 23.87},
      },
    # Directional FS entry, continued: a second shipping-family book and the
    # highest-OOS book in the registry. Same knob, different base book.

    "fsent_utcsat_long": {
          "desc": "utcsat entry-1 (leg_no_entry) + LONGS enter at swing FS",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # exp_fs_directional_leg.py, both eras. dd_net pending measure.
          "pins": {"n": 522, "net": 510.54, "dd_net": 22.47,
                   "oos_n": 309, "oos_net": 243.09, "oos_dd_net": 11.88},
      },

    "fsent_utcsat_short": {
          "desc": "utcsat entry-1 (leg_no_entry) + SHORTS enter at swing FS",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # exp_fs_directional_leg.py, both eras. dd_net pending measure.
          "pins": {"n": 530, "net": 562.98, "dd_net": 25.92,
                   "oos_n": 308, "oos_net": 229.44, "oos_dd_net": 24.76},
      },

    "fsent_dirmatch_long": {
          "desc": "dirmatch multi + LONGS enter at swing FS",
                  "status": "reference",   # LOOKAHEAD - see CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "exp_require_dir_match": 1,
                       "window_end": "exit",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          # Directional FS entry on the registry highest-OOS book.
          # exp_fs_directional_leg.py, both eras.
          "pins": None,

        # GRAVEYARD - proved look-ahead. Not a candidate, never a base.
        # Measured by exp_dirmatch_causality.py, not asserted.
        # LOOK-AHEAD, measured not asserted: exp_require_dir_match and its
        # companions read a swing field that is not settled at the entry bar.
        # exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which
        # adds the one missing check (has this swing confirmed by the entry bar)
        # and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to
        # +70.79; on fsent_dirmatch_short, the largest number in this repo, IS
        # +658.65 to +368.54. The edge was the unconfirmed label. Do not quote
        # these numbers and do not copy a base from them. The causal replacements
        # already exist as fsent_champ_long / fsent_champ_short.
        "status": "reference",
        "graveyard": "LOOK-AHEAD, measured not asserted: exp_require_dir_match and its companions read a swing field that is not settled at the entry bar. exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which adds the one missing check (has this swing confirmed by the entry bar) and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to +70.79; on fsent_dirmatch_short, the largest number in this repo, IS +658.65 to +368.54. The edge was the unconfirmed label. Do not quote these numbers and do not copy a base from them. The causal replacements already exist as fsent_champ_long / fsent_champ_short.",
        "graveyard_knobs": ['exp_require_dir_match'],
},

    "fsent_dirmatch_short": {
          "desc": "dirmatch multi + SHORTS enter at swing FS",
                  "status": "reference",   # LOOKAHEAD - see CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "exp_require_dir_match": 1,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short"},
          "swing": "sw10",
          # Directional FS entry on the registry highest-OOS book.
          # exp_fs_directional_leg.py, both eras.
          "pins": None,

        # GRAVEYARD - proved look-ahead. Not a candidate, never a base.
        # Measured by exp_dirmatch_causality.py, not asserted.
        # LOOK-AHEAD, measured not asserted: exp_require_dir_match and its
        # companions read a swing field that is not settled at the entry bar.
        # exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which
        # adds the one missing check (has this swing confirmed by the entry bar)
        # and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to
        # +70.79; on fsent_dirmatch_short, the largest number in this repo, IS
        # +658.65 to +368.54. The edge was the unconfirmed label. Do not quote
        # these numbers and do not copy a base from them. The causal replacements
        # already exist as fsent_champ_long / fsent_champ_short.
        "status": "reference",
        "graveyard": "LOOK-AHEAD, measured not asserted: exp_require_dir_match and its companions read a swing field that is not settled at the entry bar. exp_dirmatch_causality.py reruns the book with exp_dir_causal=1, which adds the one missing check (has this swing confirmed by the entry bar) and changes the result. On dirmatch_multi_sw10 that is IS +444.21 to +70.79; on fsent_dirmatch_short, the largest number in this repo, IS +658.65 to +368.54. The edge was the unconfirmed label. Do not quote these numbers and do not copy a base from them. The causal replacements already exist as fsent_champ_long / fsent_champ_short.",
        "graveyard_knobs": ['exp_require_dir_match'],
},

    # ===== SERIAL SIGNAL BOOKS (max_positions=1) + the 40% win-rate arm =====
    # ===== SERIAL SIGNAL BOOKS (max_positions=1) + the 40% win-rate arm =====
    # The bare serial single book is LOSING out of sample: -16.3R OOS on
    # champion_single_sw10. One position at a time is the deployment shape here
    # because capital does not allow concurrent losers. Directional FS entry
    # turns that book positive in both eras. exp_fs_single.py, both eras.

    "fsent_sig_sw10_short": {
          "desc": "SERIAL signal book: one position at a time, SHORTS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short",
                       "max_positions": 1},
          "swing": "sw10",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 369, "net": 174.30, "dd_net": 16.620,
                   "oos_n": 239, "oos_net": 100.94, "oos_dd_net": 11.820},
      },

    "fsent_sig_sw10_long": {
          "desc": "SERIAL signal book: one position at a time, LONGS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "long",
                       "max_positions": 1},
          "swing": "sw10",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 355, "net": 116.40, "dd_net": 21.10,
                   "oos_n": 230, "oos_net": 80.50, "oos_dd_net": 13.50},
      },

    "fsent_sig_sw20_short": {
          "desc": "SERIAL signal book on the sw20 chain, SHORTS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short",
                       "max_positions": 1},
          "swing": "sw20",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 343, "net": 146.90, "dd_net": 32.50,
                   "oos_n": 203, "oos_net": 95.00, "oos_dd_net": 10.20},
      },

    "fsent_sig_sw20_short_wr": {
          "desc": "sw20 + SHORTS enter at swing FS - only >=40% win rate on the board",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_entry_side": "short"},
          "swing": "sw20",
          # Base params copied from champion_single_sw10/sw20 verbatim.
          # NOTE: the single books carry neither exp_mltf nor exp_persist.
          # exp_fs_single.py, both eras.
          "pins": {"n": 343, "net": 146.94, "dd_net": 32.46, "win": 0.362,
                 "oos_n": 203, "oos_net": 95.0, "oos_dd_net": 10.23, "oos_win": 0.325},
      },
    # ===== SWING-SIZE EXIT AT FS (the owner proposal) =====
    # ===== SWING-SIZE EXIT AT FS (the owner proposal) =====
    # Enter at B2/flip as the book does; when the swing CONFIRMS, measure that
    # swing own leg |end_px - start_px| over ATR(20) and exit if it is small.
    # Both fields are settled at or before confirmed_at_idx and the FS bar has
    # closed, so this is knowable - unlike the same quantity read at the entry
    # bar, which is M2 and is closed as retrospective. exp_fs_small_swing.py.
    "fsent_sig_fs_mom": {
          "desc": "THE SIGNAL BOOK. One position at a time. Weekend + swingpause + shorts entering at the swing FS print + a momentum floor on the bias.",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_fs_entry_side": "short",
                       "exp_swingpause": 1,
                       "exp_skip_weekend": 1,
                       "exp_bias_momentum_min": 0.8,
                       "window_end": "exit"},
          "swing": "sw10",
          # UNPINNED: this book's knobs were written from prose, not from the
          # sweep artifact, and the fastcheck does NOT reproduce the recorded
          # 285/+208.16. Do not cite it until the params are re-derived from
          # _signal_filter_sweep.json / _signal_combo.json and it re-pins.
          "pins": None,
      },
    "fsent_sig_full": {
          "desc": "Best exhaustive candidate on the one-position signal ladder: FS-short + momentum + no partial + trail skip + small-swing exit at FS + weekend skip.",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_fs_entry_side": "short",
                       "exp_bias_momentum_min": 0.8,
                       "exp_partial_r": 0.0,
                       "exp_trail_skip_n": 2,
                       "exp_fs_small_swing": 6.0,
                       "exp_skip_weekend": 1,
                       "window_end": "exit"},
          "swing": "sw10",
          "pins": {"n": 234, "net": 291.02, "dd_net": 10.78, "win": 0.56,
                   "oos_n": 153, "oos_net": 190.93, "oos_dd_net": 6.96, "oos_win": 0.56},
      },
    # ===== THE SIGNAL BOOK =====
    # ===== THE SIGNAL BOOK =====
    # One position at a time. weekend + swingpause + shorts entering at the swing
    # FS print. Both filters are period-level/structural, which is what survived
    # validation in ANCHOR_BASIS_AUDIT.md; the per-trade indicators (chop15 band,
    # atr-ratio) were rejected there and are deliberately absent here.
    # Measured against the PURE BASELINE (same base knobs, zero filters), which
    # is OOS +41.1R - this book is what makes a one-position book viable.
    "fsent_sig_wk_pause_short": {
          "desc": "SIGNAL book: one position, weekend+pause, SHORTS enter at swing FS",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_skip_weekend": 1,
                       "exp_swingpause": 1,
                       "exp_fs_entry_side": "short",
                       "max_positions": 1},
          "swing": "sw10",
          # exp_fs_single.py / exp_fs_untested.py arm set, both eras.
          # peak concurrent positions verified = 1.
          "pins": {"n": 302, "net": 206.87, "dd_net": 10.6,
                   "oos_n": 179, "oos_net": 128.77, "oos_dd_net": 10.5},
      },
    "fsswing6_c": {
          "desc": "champion leg + exit at own-swing FS when its leg is under 6x ATR",
          "engine": "patched",
          "params": {
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0,
                       "exp_mltf": True,
                       "exp_persist": 7,
                       "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw10",
          # exp_fs_small_swing.py, both eras. Monotonic 3->6 ATR.
          "pins": {"n": 502, "net": 283.09, "dd_net": 43.39,
                   "oos_n": 282, "oos_net": 94.16, "oos_dd_net": 44.17},
      },
    # ===== SWING-SIZE EXIT AT FS, single plane =====
    # ===== SWING-SIZE EXIT AT FS, single plane =====
    # Enter at B2/flip as the book does; when the swing CONFIRMS, measure that
    # swing own leg |end_px - start_px| over ATR(20) and exit if it is small. Both
    # fields settle at or before confirmed_at_idx, so this is knowable at the FS
    # bar - unlike the same quantity read at the ENTRY bar, which is M2 and is
    # closed as retrospective. exp_fs_small_swing.py.
    "fsswing_sig_sw10": {
          "desc": "champion single sw10 + exit at FS when its swing leg is under 6x ATR",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw10",
          # Base params copied from the named single book verbatim.
          # exp_fs_small_swing.py, both eras.
          "pins": {"n": 404, "net": 31.25, "dd_net": 51.42, "win": 0.272,
                 "oos_n": 237, "oos_net": 12.59, "oos_dd_net": 29.43, "oos_win": 0.266},
      },
    "fsswing_sig_sw20": {
          "desc": "champion single sw20 + exit at FS when its swing leg is under 6x ATR",
          "engine": "patched",
          "params": { "max_positions": 1,
                       "mode": "atr_high",
                       "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35,
                       "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0,
                       "cooldown_bars": 8,
                       "max_consecutive_losses": 3,
                       "ext_stop_r": 3.0,
                       "exp_partial_r": 7.5,
                       "window_end": "exit",
                       "exp_fs_small_swing": 6.0},
          "swing": "sw20",
          # Base params copied from the named single book verbatim.
          # exp_fs_small_swing.py, both eras.
          "pins": {"n": 384, "net": 98.39, "dd_net": 53.93, "win": 0.292,
                 "oos_n": 211, "oos_net": 0.21, "oos_dd_net": 30.52, "oos_win": 0.275},
      },
    "fsexit6_c": {
        "desc": "champion leg + exit at own-swing FS when it lands within 6h",
        "engine": "patched",
"params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                     "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                     "chop_thresh": 58.0, "cooldown_bars": 8,
                     "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                     "exp_partial_r": 0.0, "exp_mltf": True,
                     "exp_persist": 7, "window_end": "exit",
                     "pivot_rule": "leg",
                     "exit_fs_max_gap_h": 6.0},
        "swing": "sw10",
        # See the FS_EXIT ladder in exp_fs_exit.py.
        "pins": {"n": 508, "net": 303.36, "dd_net": 45.74,
                 "oos_n": 297, "oos_net": 80.30, "oos_dd_net": 45.00},
    },
    # ===== P36 DECAY GATE (engine knob, measured 2026-10-02 IS+OOS) =====
}
