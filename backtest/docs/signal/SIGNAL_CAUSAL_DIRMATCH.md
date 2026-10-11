# SIGNAL PLANE — causal direction match

Generated from `backtest/tests/_signal_causal_dirmatch.json` by
`backtest/tests/_gen_causal_doc.py`, computed by
`backtest/tests/exp_signal_causal_dirmatch.py`.

## The question

`exp_require_dir_match=1` takes a 15m signal only if the 15m swing
containing it points the same way. Read raw, that swing's direction is
only final at `confirmed_at_idx` — a median of 8 hours **after** the
entry — and it is the trade's own outcome. That is the look-ahead
already caught and quarantined.

`exp_dir_causal=1` is the one line that makes it legal: ignore any swing
not yet confirmed at the entry bar.

Everything here ran **with** the guard. The quarantined numbers were not
rerun and must not be quoted.

This is the first time the causal filter has been measured on a
`max_positions == 1` book. Previously it was only ever run on multi books,
so the signal-plane answer did not exist.

## The test

Every clean signal book, run twice: once as-is, once with
`exp_require_dir_match=1, exp_dir_causal=1`. A filter that merely removes
trades leaves R per trade flat; one that finds something raises it. Both
are reported, and "no" is a permitted answer.

| | books tested |
|---|---:|
| in both eras | 44 |

## In-sample — by change in R per trade

`base` is the book as pinned. `causal` adds the legal direction-match.
Positive `dR/t` means the filter made each surviving trade better.

| book | base n | base net | base R/t | base wr% | causal n | causal net | causal R/t | causal wr% | dN | dNet | **dR/t** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `chopband_atrr_swingpause_sig_sw10` | 269 | +134.4 | +0.499 | 22.7% | 136 | +119.8 | +0.881 | 25.0% | -133 | -14.6 | **+0.381** |
| `nowknd_sig_sw10` | 321 | +107.6 | +0.335 | 25.5% | 176 | +115.3 | +0.655 | 27.8% | -145 | +7.7 | **+0.320** |
| `chopband_atrr_swingpause_sig_sw20` | 277 | +109.3 | +0.394 | 24.5% | 133 | +93.7 | +0.705 | 30.8% | -144 | -15.6 | **+0.310** |
| `fullstack_wage10_cd0_sig_sw10` | 199 | +273.2 | +1.373 | 29.1% | 87 | +143.8 | +1.653 | 31.0% | -112 | -129.4 | **+0.280** |
| `fsswing_sig_sw10` | 404 | +31.2 | +0.077 | 24.3% | 220 | +71.2 | +0.324 | 27.3% | -184 | +40.0 | **+0.246** |
| `curfew624_swingpause_sig_sw10` | 250 | +176.6 | +0.706 | 28.4% | 142 | +134.7 | +0.949 | 29.6% | -108 | -41.9 | **+0.242** |
| `b2doji_swingpause_sig_sw10` | 335 | +119.5 | +0.357 | 23.0% | 195 | +111.3 | +0.571 | 26.7% | -140 | -8.2 | **+0.214** |
| `chopband_swingpause_sig_sw20` | 309 | +91.0 | +0.295 | 25.6% | 171 | +82.8 | +0.484 | 30.4% | -138 | -8.2 | **+0.189** |
| `atrr_swingpause_sig_sw20` | 313 | +118.1 | +0.377 | 26.5% | 171 | +96.7 | +0.566 | 29.8% | -142 | -21.4 | **+0.189** |
| `champion_sig_sw10` | 396 | +37.8 | +0.096 | 24.0% | 214 | +60.1 | +0.281 | 25.7% | -182 | +22.3 | **+0.185** |
| `wage20_swingpause_sig_sw10` | 234 | +209.5 | +0.895 | 28.6% | 126 | +136.0 | +1.079 | 31.0% | -108 | -73.5 | **+0.184** |
| `rmax15_swingpause_sig_sw10` | 310 | +126.6 | +0.408 | 21.6% | 169 | +98.8 | +0.585 | 23.1% | -141 | -27.8 | **+0.176** |
| `utc_wknd_swingpause_sig_sw10` | 285 | +139.9 | +0.491 | 26.3% | 169 | +112.5 | +0.666 | 27.8% | -116 | -27.4 | **+0.175** |
| `wage24_swingpause_sig_sw10` | 220 | +225.2 | +1.024 | 30.9% | 120 | +142.6 | +1.188 | 31.7% | -100 | -82.6 | **+0.164** |
| `age50_swingpause_sig_sw10` | 350 | +133.2 | +0.381 | 22.0% | 204 | +110.5 | +0.542 | 24.5% | -146 | -22.7 | **+0.161** |
| `bm05_swingpause_sig_sw10` | 336 | +106.5 | +0.317 | 22.9% | 202 | +94.0 | +0.465 | 24.3% | -134 | -12.5 | **+0.148** |
| `utcsat_swingpause_sig_sw10` | 323 | +134.2 | +0.416 | 25.1% | 192 | +107.8 | +0.562 | 26.0% | -131 | -26.4 | **+0.146** |
| `rmax10_swingpause_sig_sw10` | 255 | +184.4 | +0.723 | 20.0% | 126 | +108.9 | +0.864 | 21.4% | -129 | -75.5 | **+0.141** |
| `atrr_cd0_swingpause_sig_sw10` | 317 | +149.0 | +0.470 | 22.1% | 168 | +101.4 | +0.604 | 23.2% | -149 | -47.6 | **+0.134** |
| `fsswing_sig_sw20` | 384 | +98.4 | +0.256 | 27.3% | 208 | +80.1 | +0.385 | 33.2% | -176 | -18.3 | **+0.129** |
| `atrr_swingpause_sig_sw10` | 316 | +150.8 | +0.477 | 22.2% | 168 | +101.4 | +0.604 | 23.2% | -148 | -49.4 | **+0.126** |
| `champion_sig_sw20` | 377 | +89.3 | +0.237 | 27.1% | 202 | +72.4 | +0.358 | 32.2% | -175 | -16.9 | **+0.121** |
| `fsent_sig_full` | 234 | +291.0 | +1.244 | 41.0% | 188 | +254.0 | +1.351 | 42.0% | -46 | -37.0 | **+0.107** |
| `causalsl_swingpause_sig_sw10` | 351 | +112.0 | +0.319 | 24.2% | 215 | +89.5 | +0.416 | 23.3% | -136 | -22.5 | **+0.097** |
| `swingpause_sig_sw20` | 342 | +118.0 | +0.345 | 28.4% | 202 | +89.2 | +0.442 | 31.7% | -140 | -28.8 | **+0.097** |
| `fsent_sig_sw20_short` | 343 | +146.9 | +0.428 | 34.1% | 270 | +140.9 | +0.522 | 33.0% | -73 | -6.0 | **+0.093** |
| `fsent_sig_sw20_short_wr` | 343 | +146.9 | +0.428 | 34.1% | 270 | +140.9 | +0.522 | 33.0% | -73 | -6.0 | **+0.093** |
| `wage12_swingpause_sig_sw20` | 303 | +148.8 | +0.491 | 28.7% | 165 | +96.2 | +0.583 | 34.5% | -138 | -52.6 | **+0.092** |
| `fullstack_swingpause_sig_sw10` | 225 | +243.8 | +1.084 | 28.0% | 111 | +128.6 | +1.159 | 26.1% | -114 | -115.2 | **+0.075** |
| `swingpause_sig_sw10` | 356 | +137.5 | +0.386 | 22.8% | 213 | +97.8 | +0.459 | 24.4% | -143 | -39.7 | **+0.073** |
| `fliponly_swingpause_sig_sw10` | 237 | +140.8 | +0.594 | 23.2% | 164 | +105.9 | +0.646 | 23.2% | -73 | -34.9 | **+0.051** |
| `fsent_sig_fs_mom` | 235 | +262.3 | +1.116 | 38.7% | 190 | +219.5 | +1.155 | 37.9% | -45 | -42.8 | **+0.039** |
| `fsent_sig_wk_pause_short` | 302 | +206.9 | +0.685 | 35.8% | 242 | +171.2 | +0.708 | 35.1% | -60 | -35.7 | **+0.022** |
| `fsent_sig_sw10_short` | 369 | +174.1 | +0.472 | 32.2% | 296 | +140.8 | +0.476 | 31.4% | -73 | -33.3 | **+0.004** |
| `wage12_swingpause_sig_nowknd_sw10` | 316 | +202.9 | +0.642 | 25.3% | 174 | +112.1 | +0.644 | 27.0% | -142 | -90.8 | **+0.002** |
| `chopband_swingpause_sig_sw10` | 320 | +183.7 | +0.574 | 23.1% | 186 | +105.1 | +0.565 | 24.7% | -134 | -78.6 | **-0.009** |
| `nowknd_swingpause_sig_sw10` | 295 | +205.2 | +0.696 | 27.5% | 173 | +113.7 | +0.657 | 26.6% | -122 | -91.5 | **-0.038** |
| `wage8_swingpause_sig_sw10` | 265 | +250.4 | +0.945 | 27.5% | 148 | +132.9 | +0.898 | 31.1% | -117 | -117.5 | **-0.046** |
| `wage12_swingpause_sig_sw10` | 259 | +267.3 | +1.032 | 28.6% | 142 | +139.1 | +0.980 | 31.7% | -117 | -128.2 | **-0.052** |
| `wage10_swingpause_wskip_sig_sw10` | 262 | +270.8 | +1.034 | 28.6% | 145 | +140.4 | +0.968 | 32.4% | -117 | -130.4 | **-0.065** |
| `wage16_swingpause_sig_sw10` | 246 | +256.7 | +1.044 | 28.9% | 135 | +131.7 | +0.976 | 30.4% | -111 | -125.0 | **-0.068** |
| `skipwinhalt_sig_sw10` | 276 | +37.7 | +0.137 | 22.8% | 179 | +1.3 | +0.007 | 25.1% | -97 | -36.4 | **-0.129** |
| `fsent_sig_sw10_long` | 355 | +116.4 | +0.328 | 32.7% | 289 | +50.3 | +0.174 | 28.0% | -66 | -66.1 | **-0.154** |
| `skipwin1_sig_sw10` | 139 | -41.7 | -0.300 | 17.3% | 115 | -60.8 | -0.529 | 16.5% | -24 | -19.1 | **-0.229** |

## Out-of-sample — by change in R per trade

`base` is the book as pinned. `causal` adds the legal direction-match.
Positive `dR/t` means the filter made each surviving trade better.

| book | base n | base net | base R/t | base wr% | causal n | causal net | causal R/t | causal wr% | dN | dNet | **dR/t** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `rmax10_swingpause_sig_sw10` | 88 | -32.6 | -0.370 | 10.2% | 47 | -3.1 | -0.067 | 14.9% | -41 | +29.5 | **+0.304** |
| `rmax15_swingpause_sig_sw10` | 154 | -54.2 | -0.352 | 12.3% | 87 | -20.4 | -0.235 | 14.9% | -67 | +33.8 | **+0.118** |
| `age50_swingpause_sig_sw10` | 211 | -23.9 | -0.113 | 23.2% | 131 | -3.5 | -0.027 | 25.2% | -80 | +20.4 | **+0.087** |
| `champion_sig_sw10` | 231 | -16.3 | -0.071 | 23.4% | 139 | +0.5 | +0.003 | 24.5% | -92 | +16.8 | **+0.074** |
| `swingpause_sig_sw10` | 214 | -19.7 | -0.092 | 23.8% | 134 | -3.1 | -0.023 | 25.4% | -80 | +16.6 | **+0.069** |
| `bm05_swingpause_sig_sw10` | 204 | -4.7 | -0.023 | 24.5% | 125 | +4.5 | +0.036 | 26.4% | -79 | +9.2 | **+0.059** |
| `fsswing_sig_sw10` | 237 | +12.6 | +0.053 | 26.2% | 140 | +13.5 | +0.096 | 26.4% | -97 | +0.9 | **+0.043** |
| `chopband_atrr_swingpause_sig_sw10` | 177 | -4.2 | -0.024 | 23.2% | 100 | +0.4 | +0.004 | 27.0% | -77 | +4.6 | **+0.028** |
| `causalsl_swingpause_sig_sw10` | 213 | -9.6 | -0.045 | 24.4% | 134 | -5.1 | -0.038 | 24.6% | -79 | +4.5 | **+0.007** |
| `fsent_sig_sw10_long` | 229 | +81.5 | +0.356 | 30.1% | 189 | +67.5 | +0.357 | 30.7% | -40 | -14.0 | **+0.001** |
| `wage12_swingpause_sig_nowknd_sw10` | 191 | -5.9 | -0.031 | 23.0% | 108 | -3.7 | -0.034 | 25.0% | -83 | +2.2 | **-0.003** |
| `wage12_swingpause_sig_sw10` | 155 | +12.0 | +0.078 | 24.5% | 86 | +6.2 | +0.073 | 29.1% | -69 | -5.8 | **-0.005** |
| `fsent_sig_sw10_short` | 239 | +100.9 | +0.422 | 31.0% | 184 | +76.2 | +0.414 | 32.6% | -55 | -24.7 | **-0.009** |
| `atrr_cd0_swingpause_sig_sw10` | 198 | -16.8 | -0.085 | 22.7% | 111 | -10.7 | -0.096 | 25.2% | -87 | +6.1 | **-0.011** |
| `skipwin1_sig_sw10` | 82 | -24.0 | -0.293 | 15.9% | 66 | -20.2 | -0.306 | 18.2% | -16 | +3.8 | **-0.013** |
| `atrr_swingpause_sig_sw10` | 198 | -9.4 | -0.048 | 23.7% | 110 | -10.9 | -0.099 | 24.5% | -88 | -1.5 | **-0.052** |
| `fullstack_wage10_cd0_sig_sw10` | 139 | +26.1 | +0.188 | 24.5% | 67 | +8.7 | +0.130 | 28.4% | -72 | -17.4 | **-0.059** |
| `fsent_sig_wk_pause_short` | 179 | +128.8 | +0.719 | 35.2% | 140 | +92.4 | +0.660 | 37.1% | -39 | -36.4 | **-0.059** |
| `chopband_swingpause_sig_sw10` | 197 | -8.1 | -0.041 | 24.4% | 126 | -14.2 | -0.112 | 24.6% | -71 | -6.1 | **-0.071** |
| `fliponly_swingpause_sig_sw10` | 146 | -34.2 | -0.234 | 17.1% | 104 | -33.4 | -0.321 | 19.2% | -42 | +0.8 | **-0.086** |
| `b2doji_swingpause_sig_sw10` | 207 | -12.7 | -0.061 | 22.7% | 130 | -21.2 | -0.163 | 23.1% | -77 | -8.5 | **-0.101** |
| `nowknd_swingpause_sig_sw10` | 174 | +24.6 | +0.141 | 25.3% | 109 | +3.3 | +0.031 | 28.4% | -65 | -21.3 | **-0.111** |
| `champion_sig_sw20` | 208 | -13.0 | -0.063 | 25.0% | 127 | -23.3 | -0.184 | 22.0% | -81 | -10.3 | **-0.121** |
| `fsswing_sig_sw20` | 211 | +0.2 | +0.001 | 26.5% | 127 | -15.2 | -0.120 | 22.0% | -84 | -15.4 | **-0.121** |
| `skipwinhalt_sig_sw10` | 159 | -7.0 | -0.044 | 22.6% | 117 | -19.4 | -0.166 | 22.2% | -42 | -12.4 | **-0.122** |
| `wage8_swingpause_sig_sw10` | 161 | +30.3 | +0.188 | 26.1% | 95 | +5.9 | +0.062 | 29.5% | -66 | -24.4 | **-0.126** |
| `fsent_sig_sw20_short` | 203 | +95.0 | +0.468 | 31.5% | 155 | +51.9 | +0.335 | 32.9% | -48 | -43.1 | **-0.133** |
| `fsent_sig_sw20_short_wr` | 203 | +95.0 | +0.468 | 31.5% | 155 | +51.9 | +0.335 | 32.9% | -48 | -43.1 | **-0.133** |
| `wage10_swingpause_wskip_sig_sw10` | 158 | +35.6 | +0.226 | 26.6% | 89 | +6.5 | +0.073 | 29.2% | -69 | -29.1 | **-0.153** |
| `wage16_swingpause_sig_sw10` | 147 | +31.0 | +0.211 | 26.5% | 85 | +4.1 | +0.049 | 28.2% | -62 | -26.9 | **-0.162** |
| `utc_wknd_swingpause_sig_sw10` | 172 | -26.3 | -0.153 | 21.5% | 102 | -32.1 | -0.315 | 23.5% | -70 | -5.8 | **-0.162** |
| `swingpause_sig_sw20` | 193 | -10.7 | -0.056 | 24.4% | 127 | -29.3 | -0.231 | 22.0% | -66 | -18.6 | **-0.175** |
| `fsent_sig_fs_mom` | 152 | +165.6 | +1.090 | 40.1% | 120 | +109.7 | +0.914 | 40.0% | -32 | -55.9 | **-0.175** |
| `wage12_swingpause_sig_sw20` | 172 | -5.3 | -0.031 | 25.0% | 93 | -20.0 | -0.215 | 21.5% | -79 | -14.7 | **-0.184** |
| `utcsat_swingpause_sig_sw10` | 198 | +22.3 | +0.113 | 27.3% | 123 | -10.5 | -0.086 | 26.8% | -75 | -32.8 | **-0.198** |
| `fullstack_swingpause_sig_sw10` | 149 | +31.2 | +0.210 | 25.5% | 83 | +0.8 | +0.010 | 26.5% | -66 | -30.4 | **-0.200** |
| `atrr_swingpause_sig_sw20` | 177 | -4.9 | -0.028 | 25.4% | 101 | -24.3 | -0.241 | 23.8% | -76 | -19.4 | **-0.213** |
| `chopband_atrr_swingpause_sig_sw20` | 159 | -6.8 | -0.043 | 24.5% | 90 | -23.3 | -0.259 | 23.3% | -69 | -16.5 | **-0.216** |
| `wage24_swingpause_sig_sw10` | 136 | +26.0 | +0.192 | 25.7% | 77 | -2.2 | -0.029 | 26.0% | -59 | -28.2 | **-0.220** |
| `fsent_sig_full` | 153 | +190.5 | +1.245 | 45.1% | 116 | +118.4 | +1.020 | 44.8% | -37 | -72.1 | **-0.224** |
| `nowknd_sig_sw10` | 192 | +27.0 | +0.141 | 25.5% | 114 | -11.3 | -0.099 | 25.4% | -78 | -38.3 | **-0.240** |
| `wage20_swingpause_sig_sw10` | 143 | +48.5 | +0.340 | 28.0% | 80 | +6.7 | +0.083 | 28.8% | -63 | -41.8 | **-0.256** |
| `curfew624_swingpause_sig_sw10` | 149 | +30.3 | +0.203 | 26.2% | 86 | -7.0 | -0.081 | 24.4% | -63 | -37.3 | **-0.284** |
| `chopband_swingpause_sig_sw20` | 181 | -6.8 | -0.037 | 24.9% | 114 | -44.1 | -0.387 | 19.3% | -67 | -37.3 | **-0.349** |

## What it does across the plane

| | count |
|---|---:|
| R/trade up in **both** eras | 9 |
| R/trade down in **both** eras | 8 |
| eras disagree on the sign | 27 |
| books tested | 44 |

A book counts as improved only if the sign holds in both eras. The ones
where it does not are the ones that would have looked good on whichever
era was checked first.

Improved in both eras:

- `rmax10_swingpause_sig_sw10` — IS +0.141, OOS +0.304 R/t
- `chopband_atrr_swingpause_sig_sw10` — IS +0.381, OOS +0.028 R/t
- `rmax15_swingpause_sig_sw10` — IS +0.176, OOS +0.118 R/t
- `fsswing_sig_sw10` — IS +0.246, OOS +0.043 R/t
- `champion_sig_sw10` — IS +0.185, OOS +0.074 R/t
- `age50_swingpause_sig_sw10` — IS +0.161, OOS +0.087 R/t
- `bm05_swingpause_sig_sw10` — IS +0.148, OOS +0.059 R/t
- `swingpause_sig_sw10` — IS +0.073, OOS +0.069 R/t
- `causalsl_swingpause_sig_sw10` — IS +0.097, OOS +0.007 R/t

Worse in both eras:

- `skipwinhalt_sig_sw10` — IS -0.129, OOS -0.122 R/t
- `skipwin1_sig_sw10` — IS -0.229, OOS -0.013 R/t
- `wage16_swingpause_sig_sw10` — IS -0.068, OOS -0.162 R/t
- `wage10_swingpause_wskip_sig_sw10` — IS -0.065, OOS -0.153 R/t
- `wage8_swingpause_sig_sw10` — IS -0.046, OOS -0.126 R/t
- `nowknd_swingpause_sig_sw10` — IS -0.038, OOS -0.111 R/t
- `chopband_swingpause_sig_sw10` — IS -0.009, OOS -0.071 R/t
- `wage12_swingpause_sig_sw10` — IS -0.052, OOS -0.005 R/t

