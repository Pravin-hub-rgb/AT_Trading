"""Batch-run groups: a name -> list of book keys, for `run_experiment --group`.

Copied verbatim from the one-file registry. A key in a group may be an alias;
run_experiment resolves it.
"""

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
