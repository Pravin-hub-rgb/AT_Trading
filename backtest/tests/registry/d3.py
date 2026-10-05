"""D3 - the loss-autopsy families.

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

BOOKS = {
    # ===== D3 COOLDOWN FAMILY (loss-reactive window skip / swing pause) =====

    "skipwin1_multi_sw10": {
        "desc": "king + skip the next HTF window opened after a loss",
        "status": "reference",   # dead: net -38.54R - not a candidate.
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
        "pins": {"n": 145, "net": -38.54, "dd_net": 52.54,
                 "oos_n": 81, "oos_net": 17.06, "oos_dd_net": 37.41},
    },
    "skipwin2_multi_sw10": {
        "desc": "king + skip the next 2 HTF windows opened after a loss",
        "status": "reference",   # dead: net -65.33R - not a candidate.
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
        "pins": {"n": 101, "net": -65.33, "dd_net": 66.47,
                 "oos_n": 72, "oos_net": 58.90, "oos_dd_net": 14.74},
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
        "pins": {"n": 444, "net": 241.06, "dd_net": 41.60,
                 "oos_n": 249, "oos_net": 76.69, "oos_dd_net": 35.70},
    },
    # REMOVED 2026-10-02: skip1pause_multi_sw10. Verified identical to
    # skipwin1_multi_sw10 on unified.py - same count, same net, same trade list.
    # exp_skipwin=1 already removes the window, so the added exp_swingpause has
    # nothing left to pause.
    "skip1pause_multi_sw10": "skipwin1_multi_sw10",
    "skipwin1_sig_sw10": {
        "desc": "baseline single + skip the next HTF window opened after a loss",
        "status": "reference",   # dead: net -38.88R - not a candidate.
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": None,
    },
    "swingpause_sig_sw10": {
        "desc": "baseline single + pause until a swing FORMED after the loss confirms",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 356, "net": 137.51, "dd_net": 48.4, "win": 0.258,
                 "oos_n": 214, "oos_net": -19.75, "oos_dd_net": 37.03, "oos_win": 0.243},
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
        "pins": {"n": 323, "net": 28.35, "dd_net": 45.34,
                 "oos_n": 198, "oos_net": 73.56, "oos_dd_net": 44.34},
    },
    "skipwinhalt_sig_sw10": {
        "desc": "baseline single + skip the next HTF window after a HALT (3 straight losses)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 276, "net": 37.68, "dd_net": 39.94, "win": 0.246,
                 "oos_n": 159, "oos_net": -7.0, "oos_dd_net": 31.51, "oos_win": 0.226},
    },
    # REMOVED 2026-10-02: swingpause_cd0_single_sw10. exp_swingpause forces
    # cooldown_bars=0 itself, so this entry set cooldown_bars=0 and added the same
    # flag - it was swingpause_single_sw10 under a second name, and both read
    # 451 / +232.45R after the rerun. Kept as a pointer rather than a copy so a
    # script naming it still finds the meaning.
    "swingpause_cd0_single_sw10": "swingpause_sig_sw10",
    "swingpause_sig_sw20": {
        "desc": "baseline single sw20 + swing-pause (fresh structure)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 342, "net": 117.99, "dd_net": 53.69, "win": 0.304,
                 "oos_n": 193, "oos_net": -10.72, "oos_dd_net": 30.27, "oos_win": 0.259},
    },

    # ===== D3 PATTERN FAMILY (from loss autopsy: weekends, entry kinds, window age) =====
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
        "pins": {"n": 403, "net": 301.39, "dd_net": 25.88,
                 "oos_n": 219, "oos_net": 24.76, "oos_dd_net": 29.76},
    },
    "nowknd_sig_sw10": {
        "desc": "baseline single + SKIP WEEKEND entries — isolate weekend effect",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 321, "net": 107.64, "dd_net": 41.49, "win": 0.274,
                 "oos_n": 192, "oos_net": 27.0, "oos_dd_net": 27.33, "oos_win": 0.26},
    },
    "nowknd_swingpause_sig_sw10": {
        "desc": "swingpause single + SKIP WEEKEND — NEW BEST SINGLE (+217.6 / DD 18.2 / 12.0)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 295, "net": 205.2, "dd_net": 27.15, "win": 0.295,
                 "oos_n": 174, "oos_net": 24.61, "oos_dd_net": 23.14, "oos_win": 0.259},
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
        "pins": {"n": 286, "net": 202.45, "dd_net": 35.43,
                 "oos_n": 155, "oos_net": -10.70, "oos_dd_net": 52.55},
    },
    "fliponly_swingpause_sig_sw10": {
        "desc": "swingpause single + FLIP entries only — B2 was 178t for -0.6R",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 237, "net": 140.8, "dd_net": 32.65, "win": 0.253,
                 "oos_n": 146, "oos_net": -34.23, "oos_dd_net": 42.72, "oos_win": 0.171},
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
        "pins": {"n": 364, "net": 240.58, "dd_net": 31.33,
                 "oos_n": 218, "oos_net": 76.29, "oos_dd_net": 34.05},
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
        "pins": {"n": 269, "net": 235.96, "dd_net": 29.15,
                 "oos_n": 162, "oos_net": 15.67, "oos_dd_net": 35.65},
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
        "pins": {"n": 454, "net": 358.92, "dd_net": 21.18,
                 "oos_n": 253, "oos_net": 60.21, "oos_dd_net": 29.38},
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
        "pins": {"n": 453, "net": 279.47, "dd_net": 35.54,
                 "oos_n": 254, "oos_net": 66.90, "oos_dd_net": 24.64},
    },
    "utcsat_swingpause_sig_sw10": {
        "desc": "swingpause single + SKIP UTC-SATURDAY only (UTC Sun = +51.7R is KEPT)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 323, "net": 134.24, "dd_net": 34.88, "win": 0.282,
                 "oos_n": 198, "oos_net": 22.29, "oos_dd_net": 20.67, "oos_win": 0.278},
    },

    # NOTE: utc_sat variants consolidated into the other lane's keys
    # (utcsat_multi_sw10 / utcsat_swingpause_single_sw10) — identical params.
    "utc_wknd_swingpause_sig_sw10": {
        "desc": "swingpause single + skip full UTC weekend (Sat+Sun) — for comparison vs Sat-only",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 285, "net": 139.95, "dd_net": 42.4, "win": 0.291,
                 "oos_n": 172, "oos_net": -26.32, "oos_dd_net": 35.55, "oos_win": 0.221},
    },

    # ===== D3 RISK-WIDTH FAMILY (skip stale/stretched breaks) =====
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
        "pins": {"n": 432, "net": 268.79, "dd_net": 41.70,
                 "oos_n": 257, "oos_net": 85.94, "oos_dd_net": 42.74},
    },
    "chopband_swingpause_sig_sw10": {
        "desc": "swingpause single + skip entries in the 15m-chop transition band [55,61)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 320, "net": 183.75, "dd_net": 38.13, "win": 0.262,
                 "oos_n": 197, "oos_net": -8.15, "oos_dd_net": 40.48, "oos_win": 0.249},
    },
    "atrr_swingpause_sig_sw10": {
        "desc": "swingpause single + skip entries when 15m ATR5/ATR20 > 1.4 (vol blow-off)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 316, "net": 150.79, "dd_net": 38.33, "win": 0.247,
                 "oos_n": 198, "oos_net": -9.41, "oos_dd_net": 29.4, "oos_win": 0.242},
    },
    "chopband_atrr_swingpause_sig_sw10": {
        "desc": "swingpause single + chop15 band AND ATR blow-off skip (combo)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 269, "net": 134.36, "dd_net": 33.04, "win": 0.257,
                 "oos_n": 177, "oos_net": -4.23, "oos_dd_net": 42.84, "oos_win": 0.232},
    },
    "atrr_swingpause_sig_sw20": {
        "desc": "VALIDATION: atrr gate on sw20 chain (cross-chain robustness)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 313, "net": 118.1, "dd_net": 49.66, "win": 0.291,
                 "oos_n": 177, "oos_net": -4.86, "oos_dd_net": 32.29, "oos_win": 0.266},
    },
    "atrr_cd0_swingpause_sig_sw10": {
        "desc": "VALIDATION: atrr gate with cd=0 (pause-only cooldown)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 317, "net": 149.0, "dd_net": 40.11, "win": 0.246,
                 "oos_n": 198, "oos_net": -16.81, "oos_dd_net": 33.91, "oos_win": 0.232},
    },
    "chopband_swingpause_sig_sw20": {
        "desc": "VALIDATION: chopband gate on sw20 chain (cross-chain robustness)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 309, "net": 91.03, "dd_net": 46.41, "win": 0.278,
                 "oos_n": 181, "oos_net": -6.79, "oos_dd_net": 37.34, "oos_win": 0.26},
    },
    "chopband_atrr_swingpause_sig_sw20": {
        "desc": "VALIDATION: chopband + atrr combo on sw20 chain",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 277, "net": 109.26, "dd_net": 42.76, "win": 0.271,
                 "oos_n": 159, "oos_net": -6.8, "oos_dd_net": 43.23, "oos_win": 0.252},
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
        "pins": {"n": 392, "net": 315.45, "dd_net": 36.41,
                 "oos_n": 235, "oos_net": 91.73, "oos_dd_net": 22.94},
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
        "pins": {"n": 311, "net": 295.46, "dd_net": 26.61,
                 "oos_n": 201, "oos_net": 36.07, "oos_dd_net": 31.36},
    },
    "fullstack_swingpause_sig_sw10": {
        "desc": "single full stack: weekend skip + swingpause + chop15 band + ATR blow-off",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 225, "net": 243.8, "dd_net": 23.41, "win": 0.307,
                 "oos_n": 149, "oos_net": 31.24, "oos_dd_net": 31.3, "oos_win": 0.262},
    },
    "fullstack_wage10_cd0_sig_sw10": {
        "desc": "KING SINGLE: fullstack + wage10 + cd=0 — chop15 band + ATR blow-off",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 199, "net": 273.18, "dd_net": 24.29, "win": 0.322,
                 "oos_n": 139, "oos_net": 26.15, "oos_dd_net": 34.97, "oos_win": 0.252},
    },

    # ===== D3 WAGE VALIDATION FAMILY (other bot's sweep finding: wage12 on single +61R) =====
    # ===== D3 WAGE VALIDATION FAMILY (other bot's sweep finding: wage12 on single +61R) =====

    "wage12_swingpause_sig_sw10": {
        "desc": "REPLICATE other bot: nowknd_swingpause single + wage_h=12",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 259, "net": 267.3, "dd_net": 24.41, "win": 0.301,
                 "oos_n": 155, "oos_net": 12.05, "oos_dd_net": 30.81, "oos_win": 0.252},
    },
    "wage8_swingpause_sig_sw10": {
        "desc": "VALIDATION: wage neighborhood 8h",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 265, "net": 250.36, "dd_net": 22.96, "win": 0.294,
                 "oos_n": 161, "oos_net": 30.26, "oos_dd_net": 29.88, "oos_win": 0.267},
    },
    "wage10_swingpause_wskip_sig_sw10": {
        "desc": "KING SINGLE: wage 10h + swing pause + IST weekend skip — cd=0 redundant with swingpause",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 262, "net": 270.8, "dd_net": 22.96, "win": 0.305,
                 "oos_n": 158, "oos_net": 35.63, "oos_dd_net": 25.81, "oos_win": 0.272},
    },
    # === SKIP-FIRST-SWING: DEAD — first swing is where the edge lives (Exp 19 confirmed) ===
    "wage16_swingpause_sig_sw10": {
        "desc": "VALIDATION: wage neighborhood 16h",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 246, "net": 256.74, "dd_net": 24.57, "win": 0.305,
                 "oos_n": 147, "oos_net": 30.97, "oos_dd_net": 26.19, "oos_win": 0.272},
    },
    "wage20_swingpause_sig_sw10": {
        "desc": "VALIDATION: wage neighborhood 20h — declines past the plateau",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 234, "net": 209.51, "dd_net": 22.98, "win": 0.303,
                 "oos_n": 143, "oos_net": 48.54, "oos_dd_net": 23.62, "oos_win": 0.287},
    },
    "wage12_swingpause_sig_nowknd_sw10": {
        "desc": "VALIDATION: wage12 WITHOUT weekend skip (stack interaction) — wage works alone (+60.9R)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 316, "net": 202.92, "dd_net": 42.31, "win": 0.275,
                 "oos_n": 191, "oos_net": -5.93, "oos_dd_net": 40.24, "oos_win": 0.236},
    },
    "wage12_swingpause_sig_sw20": {
        "desc": "VALIDATION: wage12 on sw20 chain — TRANSFERS (+24.5R, -4.9DD)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 303, "net": 148.81, "dd_net": 45.64, "win": 0.307,
                 "oos_n": 172, "oos_net": -5.26, "oos_dd_net": 35.9, "oos_win": 0.25},
    },

    # ===== D3 CAUSAL SL FAMILY (user's fix: running extreme SL) =====
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
        "pins": {"n": 493, "net": 185.08, "dd_net": 47.70,
                 "oos_n": 283, "oos_net": 82.65, "oos_dd_net": 43.92},
    },
    "causalsl_swingpause_sig_sw10": {
        "desc": "swingpause single + causal SL",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 351, "net": 112.04, "dd_net": 52.68, "win": 0.271,
                 "oos_n": 213, "oos_net": -9.56, "oos_dd_net": 26.26, "oos_win": 0.254},
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
        "pins": {"n": 448, "net": 237.43, "dd_net": 36.53,
                 "oos_n": 256, "oos_net": 79.48, "oos_dd_net": 22.60},
    },

    # ===== D3 BIAS MOMENTUM (1h swing magnitude ratio) =====
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
        "pins": {"n": 456, "net": 277.86, "dd_net": 46.63,
                 "oos_n": 261, "oos_net": 87.84, "oos_dd_net": 38.73},
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
        "pins": {"n": 391, "net": 248.81, "dd_net": 38.30,
                 "oos_n": 210, "oos_net": 100.42, "oos_dd_net": 28.22},
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
        "pins": {"n": 420, "net": 298.15, "dd_net": 35.33,
                 "oos_n": 237, "oos_net": 77.76, "oos_dd_net": 24.64},
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
        "pins": {"n": 359, "net": 264.66, "dd_net": 29.71,
                 "oos_n": 192, "oos_net": 91.58, "oos_dd_net": 19.02},
    },
    "bm05_swingpause_sig_sw10": {
        "desc": "swingpause single + bias momentum min 0.5 — FAILS on single (-29.6R)",
        "engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "pins": {"n": 336, "net": 106.52, "dd_net": 46.58, "win": 0.259,
                 "oos_n": 204, "oos_net": -4.73, "oos_dd_net": 34.19, "oos_win": 0.25},
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
        "pins": {"n": 458, "net": 259.80, "dd_net": 51.69,
                 "oos_n": 248, "oos_net": 17.03, "oos_dd_net": 41.93},
    },

    # ===== D3 TRAIL QUALITY (skip far trail levels) =====
    # ===== D3 UNION DUAL-QUALIFICATION (2x2 autopsy: FLIP-only window = fragile cell) =====

    "dualunion_multi": {
        "desc": "union + filters + DUAL-QUALIFIED only (skip FLIP-window-only matches)",
                "status": "reference",   # LOOKAHEAD - end_px. See closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_min_swing_ratio measures abs(seg.end_px - seg.start_px) - the
                                  # swing FINAL leg - to decide whether the trade is big enough. end_px
                                  # is only settled at confirmed_at_idx. Measured: 0 of 137 trades
                                  # (union_multi) and 0 of 90 (dualunion_multi) had a swing settled by
                                  # the entry bar. This is the M2 field that method/FS_TIME_GEOMETRY.md already
                                  # closed as retrospective. Do not ship, do not cite.
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
        "graveyard_knobs": ['exp_min_swing_ratio'],
},
    "union_multi": {
        "desc": "union + filters (no dual gate) — reference for dual comparison",
                "status": "reference",   # LOOKAHEAD - end_px. See closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_min_swing_ratio measures abs(seg.end_px - seg.start_px) - the
                                  # swing FINAL leg - to decide whether the trade is big enough. end_px
                                  # is only settled at confirmed_at_idx. Measured: 0 of 137 trades
                                  # (union_multi) and 0 of 90 (dualunion_multi) had a swing settled by
                                  # the entry bar. This is the M2 field that method/FS_TIME_GEOMETRY.md already
                                  # closed as retrospective. Do not ship, do not cite.
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
        "graveyard_knobs": ['exp_min_swing_ratio'],
},

    # ===== D3 STRUCTURAL ALIGNMENT (dir match + swing age + running magnitude) =====
    # ===== D3 STRUCTURAL ALIGNMENT (dir match + swing age + running magnitude) =====

    "dirmatch_multi_sw10": {
        "desc": "king + REQUIRE forming swing direction match — +479.9R / DD 13.8 / WR 38.6%",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
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
    "age25_multi_sw10": {
        "desc": "king + max swing age 25 bars",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
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
        "graveyard_knobs": ['exp_max_swing_age'],
},
    "age25_dirmatch_multi_sw10": {
        "desc": "king + dir match + age 25 — +386.7R / DD 9.8 / WR 43.8% (BEST quality)",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
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
        "graveyard_knobs": ['exp_require_dir_match', 'exp_max_swing_age'],
},
    "age10_dirmatch_multi_sw10": {
        "desc": "king + dir match + age 10 — +455.5R / DD 6.0 / WR 51.7% (MONSTER, 151t)",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
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
        "graveyard_knobs": ['exp_require_dir_match', 'exp_max_swing_age'],
},

    # ===== D3 CAUSAL SL FAMILY (user's fix: running extreme SL) =====
    # ===== D3 CAUSAL SL FAMILY (user's fix: running extreme SL) =====

    "dirmatch_swingpause_sig_sw10": {
        "desc": "swingpause single + dir match — +288.1R / DD 14.1 / WR 35.5%",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
    "age10_dirmatch_swingpause_sig_sw10": {
        "desc": "swingpause single + dir match + age 10 — 🔥 BEST EVER: +435.7R / DD 5.7 / WR 53.8%",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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
        "graveyard_knobs": ['exp_require_dir_match', 'exp_max_swing_age'],
},
    "dirmatch_sig_sw10": {
        "desc": "baseline single (no swingpause) + dir match — +237.7R / DD 15.7",
                "status": "reference",   # LOOKAHEAD - see closed/CLOSED_DO_NOT_REPEAT.md 2026-10-04
                                  # exp_require_dir_match / exp_max_swing_age read the swing FINAL
                                  # direction, which is only final at confirmed_at_idx - median 8h AFTER
                                  # the entry bar. That label IS the trade outcome, so the filter was
                                  # reading the answer. Path-true (exp_dir_causal=1) numbers are in
                                  # _dir_causal_pins.json. Do not ship, do not cite.
"engine": "patched",
        "params": { "max_positions": 1,"mode": "atr_high", "atr_high_thresh": 0.65,
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

    # ===== SHIPPED BASELINE (identity gate reference) =====
}
