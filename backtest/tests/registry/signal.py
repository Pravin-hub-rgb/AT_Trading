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
        "pins": {"n": 507, "net": 298.0, "dd_net": 40.91,
                 "oos_n": 295, "oos_net": 68.92, "oos_dd_net": 48.72},
    },
    # ===== DIRECTIONAL FS ENTRY (engine knob exp_fs_entry_side) =====
    # ===== DIRECTIONAL FS ENTRY (engine knob exp_fs_entry_side) =====
    # Measured 2026-10-04 by exp_fs_directional_leg.py on CAUSAL leg-family
    # books, both eras. Only the ENTRY TRIGGER changes on one side; the other
    # side, the LTF cascade and every risk knob are untouched. Do not confuse
    # with the closed FS-EXIT work in closed/CLOSED_DO_NOT_REPEAT.md: same FS print,
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
          "pins": {"n": 528, "net": 533.37, "dd_net": 13.42,
                   "oos_n": 311, "oos_net": 239.59, "oos_dd_net": 11.88},
      },

    # SINGLE-VARIANT ABLATION of fsent_champ_long: the 3-loss streak halt off.
    # The point of registering it rather than folding it into the base is
    # attribution.
    #
    # chop_thresh stays at 58.0 even though it is dead code here - mode="atr_high"
    # never reads it - so that this entry differs from its base by exactly one
    # BEHAVIOURAL knob and the delta is traceable to the halt alone.
    #
    # ext_stop_r is set to 0.0 explicitly rather than dropped, for two reasons.
    # It is provably inert since C17: 3.0 and 0.0 produce byte-identical trade
    # lists AND an identical equity curve, both eras (exp_equity_lens.py Q1), so
    # this change is not what makes the book differ. And omitting the key would
    # NOT mean "off" - BP carries ext_stop_r=1.5, and 1.5 is a live filter that
    # blocks 122 IS / 86 OOS signals. Write 0.0, never nothing.
    "fsent_champ_long_nohalt": {
          "desc": "fsent_champ_long with max_consecutive_losses=0 (the 3-loss streak halt removed) and ext_stop_r=0.0 (provably inert since C17, written explicitly because omitting the key would inherit BP's 1.5). Every behavioural knob identical to the base.",
          "engine": "patched",
          "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 0, "ext_stop_r": 0.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long"},
          "swing": "sw10",
          "pins": {"n": 575, "net": 566.6, "dd_net": 15.1,
                   "oos_n": 337, "oos_net": 270.9, "oos_dd_net": 14.2},
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
          "pins": {"n": 533, "net": 600.6, "dd_net": 17.6,
                   "oos_n": 312, "oos_net": 239.53, "oos_dd_net": 23.87},
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
          "pins": {"n": 525, "net": 465.0, "dd_net": 20.66,
                   "oos_n": 310, "oos_net": 238.76, "oos_dd_net": 11.88},
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
          "pins": {"n": 531, "net": 596.71, "dd_net": 17.6,
                    "oos_n": 311, "oos_net": 229.65, "oos_dd_net": 24.63},
      },
    "fsent_champ_trailhalf": {
        "desc": "CANDIDATE: fsent_champ_long + exp_trail_half=1. Multi check on 2026-10-06: OOS +287.0 / avgR 1.032 / PF 3.00 / DD 16.5 vs base +245.0 / 0.793 / 2.76 / 11.9. Lifts total and per-trade, at DD cost. NOT adopted - needs exp_port_differential parity + cohort autopsy first.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg",
                       "exp_fs_entry_side": "long",
                       "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 496, "net": 536.19, "dd_net": 31.68,
                 "oos_n": 282, "oos_net": 282.08, "oos_dd_net": 16.45},
    },
    "fsent_utcsat_trailhalf": {
        "desc": "CANDIDATE: fsent_utcsat_long + exp_trail_half=1. Repeats the fsent_champ_trailhalf lift (OOS +286.4 / avgR 1.034 / PF 3.00 / DD 16.5 vs base +244.2 / 0.793 / 2.75 / 11.9). NOT adopted.",
        "engine": "patched",
        "params": {"mode": "atr_high", "atr_high_thresh": 0.65,
                       "atr_low_thresh": 0.35, "sl_buf_atr": 0.01,
                       "chop_thresh": 58.0, "cooldown_bars": 8,
                       "max_consecutive_losses": 3, "ext_stop_r": 3.0,
                       "exp_partial_r": 0.0, "exp_mltf": True,
                       "exp_persist": 7, "window_end": "exit",
                       "pivot_rule": "leg_no_entry",
                       "exp_fs_entry_side": "long",
                       "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 497, "net": 534.46, "dd_net": 31.29,
                 "oos_n": 281, "oos_net": 281.49, "oos_dd_net": 16.45},
    },

    "fsent_dirmatch_long": {
          "desc": "dirmatch multi + LONGS enter at swing FS",
                  "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
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
                  "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
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
          "pins": {"n": 374, "net": 175.41, "dd_net": 16.620,
                   "oos_n": 239, "oos_net": 103.31, "oos_dd_net": 11.820},
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
          "pins": {"n": 353, "net": 121.23, "dd_net": 21.07,
                   "oos_n": 232, "oos_net": 74.15, "oos_dd_net": 13.33},
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
          "pins": {"n": 343, "net": 146.2, "dd_net": 30.8,
                   "oos_n": 203, "oos_net": 97.0, "oos_dd_net": 8.9},
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
          "pins": {"n": 343, "net": 146.2, "dd_net": 30.8, "win": 0.362,
                 "oos_n": 203, "oos_net": 97.0, "oos_dd_net": 8.9, "oos_win": 0.325},
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
          # Measured from the engine, both eras, by exp_pinrefresh.py.
          #
          # The pin this replaces read IS 285 / +208.16 and was WRONG - but the
          # params were not. That number is step 2 of _signal_combo.json, a
          # TWO-knob ladder: exp_fs_entry_side=short + exp_bias_momentum_min=0.8.
          # This book carries FOUR knobs - those two plus exp_swingpause=1 and
          # exp_skip_weekend=1, which that ladder never added. So the number
          # belonged to a different configuration and was copied here by
          # mistake. It is left in this comment rather than deleted, so that if
          # anyone finds +208.16 quoted as this book, this is where it came from
          # and why it is wrong.
          #
          # Which way the error ran is worth recording: the real book is BETTER
          # in sample (+262.29 against +208.16) and the OOS was never recorded
          # at all, so nothing downstream was harmed by believing the smaller
          # number. That is luck, not a property of the process - the identical
          # mistake in the other direction would have shipped an inflated book.
          "pins": {"n": 235, "net": 268.37, "dd_net": 8.96, "win": 0.426,
                   "oos_n": 153, "oos_net": 166.8, "oos_dd_net": 9.14,
                   "oos_win": 0.425},
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
          "pins": {"n": 234, "net": 295.83, "dd_net": 10.78, "win": 0.44,
                   "oos_n": 152, "oos_net": 194.44, "oos_dd_net": 6.96, "oos_win": 0.477},
      },
    # ===== FS TWEAKS — registered as candidate books, measured 2026-10-06 =====
    # Same stack as fsent_sig_full (and its both-side mirror), one lever added
    # each time. Measured by _sig_fs_tweaks.py / _sig_fs_mirror.py, same
    # closed-trades basis as the pins. NOT adopted: the decay/trail-half cells
    # lift OOS R/trd and PF on ~half the trades, at the cost of total OOS net.
    # Family-level shape repeats on fsent_sig_fs_mom and fsent_sig_wk_pause_short.
    "fsent_sig_trail_delay1": {
        "desc": "fsent_sig_full + exp_trail_half=1 and exp_trail_delay_r=1.0. The one trail cell that lifts OOS R/trd (+1.46), by gating the ratchet and cutting n.",
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
                   "window_end": "exit",
                   "exp_trail_half": 1,
                   "exp_trail_delay_r": 1.0},
        "swing": "sw10",
        "pins": {"n": 199, "net": 418.51, "dd_net": 13.34, "win": 0.382,
                 "oos_n": 123, "oos_net": 182.01, "oos_dd_net": 7.54, "oos_win": 0.426},
    },
    "fsent_sig_decay_crossed": {
        "desc": "fsent_sig_full + P36 decay gate, mode 'crossed', thr 0.75, legs 4. Halves the book; OOS R/trd +1.91, PF 4.60, DD ~base — filter shape, half the trades.",
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
                   "window_end": "exit",
                   "exp_decay_mode": 4,
                   "exp_decay_thr": 0.75,
                   "exp_decay_legs": 4},
        "swing": "sw10",
        "pins": {"n": 104, "net": 195.59, "dd_net": 8.64, "win": 0.481,
                 "oos_n": 67, "oos_net": 130.28, "oos_dd_net": 7.39, "oos_win": 0.507},
    },
    "fsent_sig_half_crossed": {
        "desc": "fsent_sig_full + trail_half + decay_crossed. The sharpest shape: OOS avgR +2.27, PF 4.85, on n=62. NOT adopted — smallest sample of the three, OOS total well below base.",
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
                   "window_end": "exit",
                   "exp_trail_half": 1,
                   "exp_decay_mode": 4,
                   "exp_decay_thr": 0.75,
                   "exp_decay_legs": 4},
        "swing": "sw10",
        "pins": {"n": 97, "net": 340.9, "dd_net": 8.46, "win": 0.423,
                 "oos_n": 63, "oos_net": 142.09, "oos_dd_net": 7.26, "oos_win": 0.435},
    },
    "fsent_both_trail_half": {
        "desc": "fsent_sig_full stack with exp_fs_entry_side='both' + exp_trail_half. Best measured both-side tweak here, but OOS +96.9 on n=141 — the lane stays far below the short-only book. Keep as the ceiling on 'both'.",
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
                   "exp_fs_entry_side": "both",
                   "exp_bias_momentum_min": 0.8,
                   "exp_partial_r": 0.0,
                   "exp_trail_skip_n": 2,
                   "exp_fs_small_swing": 6.0,
                   "exp_skip_weekend": 1,
                   "window_end": "exit",
                   "exp_trail_half": 1},
        "swing": "sw10",
        "pins": {"n": 253, "net": 77.69, "dd_net": 31.43, "win": 0.296,
                 "oos_n": 142, "oos_net": 96.91, "oos_dd_net": 14.81, "oos_win": 0.34},
    },
    # ===== THE SIGNAL BOOK =====
    # ===== THE SIGNAL BOOK =====
    # One position at a time. weekend + swingpause + shorts entering at the swing
    # FS print. Both filters are period-level/structural, which is what survived
    # validation in signal/ANCHOR_BASIS_AUDIT.md; the per-trade indicators (chop15 band,
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
          "pins": {"n": 306, "net": 203.26, "dd_net": 10.6,
                   "oos_n": 180, "oos_net": 129.95, "oos_dd_net": 10.53},
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
          "pins": {"n": 510, "net": 322.18, "dd_net": 41.77,
                   "oos_n": 290, "oos_net": 82.61, "oos_dd_net": 54.27},
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
          "pins": {"n": 404, "net": 42.54, "dd_net": 45.11, "win": 0.272,
                 "oos_n": 245, "oos_net": 11.21, "oos_dd_net": 34.62, "oos_win": 0.265},
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
          "pins": {"n": 382, "net": 99.19, "dd_net": 50.05, "win": 0.296,
                 "oos_n": 218, "oos_net": 0.42, "oos_dd_net": 35.97, "oos_win": 0.266},
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
        "pins": {"n": 516, "net": 310.62, "dd_net": 46.66,
                 "oos_n": 302, "oos_net": 75.7, "oos_dd_net": 45.81},
    },
    # ===== P36 DECAY GATE (engine knob, measured 2026-10-02 IS+OOS) =====
}
