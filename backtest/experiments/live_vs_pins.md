# Live engine vs registry pins

The live engine has 46 parameters. The backtest harness has 151. Nothing
the harness supports is missing from live except the reverse, so a book
using a harness-only knob cannot be reproduced on the live backend at
all.

Six books carry exp_mltf=True in the registry and their branches omit it;
two passed it and crashed. exp_mltf only acts on the loss-window hard
close path, which does not exist in unified.py either, and no book in
the shortlist sets an exp_window_loss_kill_* parameter. So it should be
inert. Measured rather than assumed:

| book | pin n | pin net | live n | live net | reproduces the pin? |
|---|---:|---:|---:|---:|---|
| `fsent_champ_long` | 487 | +459.41 | 487 | +459.41 | yes |
| `fsent_champ_long_htffs` | 751 | +756.98 | 751 | +756.98 | yes |
| `fsent_champ_long_htfesmcl4` | 762 | +771.87 | 762 | +771.87 | yes |
| `fsent_champ_long_mcloff_htf15` | 525 | +538.40 | 525 | +538.40 | yes |
| `fsent_champ_long_htf15_htffs` | 754 | +764.85 | 754 | +764.85 | yes |
| `fsent_champ_long_htf15_tskip6` | 395 | +644.04 | 395 | +644.04 | yes |

**6 of 6 books reproduce their pin on the live engine.**