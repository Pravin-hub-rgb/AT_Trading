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
| `fsent_champ_long` | 481 | +434.88 | 481 | +434.88 | yes |
| `fsent_champ_long_htffs` | 721 | +729.32 | 721 | +729.32 | yes |
| `fsent_champ_long_htfesmcl4` | 736 | +762.50 | 736 | +762.50 | yes |
| `fsent_champ_long_mcloff_htf15` | 520 | +508.37 | 520 | +508.37 | yes |
| `fsent_champ_long_htf15_htffs` | 716 | +725.98 | 716 | +725.98 | yes |
| `fsent_champ_long_htf15_tskip6` | 390 | +621.74 | 390 | +621.74 | yes |

**6 of 6 books reproduce their pin on the live engine.**