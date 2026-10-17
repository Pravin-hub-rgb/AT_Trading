# Does removing exp_mltf move any number?

exp_mltf is a harness-only parameter - unified.py does not accept it and
only does anything on the loss-window hard close path, which unified.py
does not have either. Seventy-five books carry it in the registry, and
the live engine has been silently ignoring it on all of them.

Removing it means re-deriving seventy-five pins, so this measures rather
than assumes: every book is run twice, with the key and without it, and
the resulting TRADE LISTS are compared entry by entry. Identical lists
mean identical numbers by construction.

| book | trades with | trades without | net with | trade lists |
|---|---:|---:|---:|---|
| `fsent_champ_long` | 497 | 497 | +466.92 | identical |
| `fsent_champ_long_htffs` | 753 | 753 | +757.99 | identical |
| `fsent_champ_long_htfesmcl4` | 762 | 762 | +770.53 | identical |
| `fsent_champ_long_htf15_htffs` | 756 | 756 | +765.86 | identical |
| `fsent_champ_long_htf15_tskip6` | 412 | 412 | +639.84 | identical |
| `fsent_champ_long_mcloff_htf15` | 535 | 535 | +539.77 | identical |
| `fsent_champ_short` | 466 | 466 | +569.33 | identical |

**7 books identical, 0 differ.**

The knob did nothing on any book tested. Removing it cannot move a
pin, because the trade lists are byte-identical without it.