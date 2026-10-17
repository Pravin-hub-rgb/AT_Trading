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
| `fsent_champ_long` | 497 | +466.92 | 497 | +466.92 | yes |
| `fsent_champ_long_htffs` | 753 | +757.99 | 753 | +757.99 | yes |
| `fsent_champ_long_htfesmcl4` | 762 | +770.53 | 762 | +770.53 | yes |
| `fsent_champ_long_mcloff_htf15` | 535 | +539.77 | 535 | +539.77 | yes |
| `fsent_champ_long_htf15_htffs` | 756 | +765.86 | 756 | +765.86 | yes |
| `fsent_champ_long_htf15_tskip6` | 412 | +639.84 | 412 | +639.84 | yes |

**6 of 6 books reproduce their pin on the live engine.**