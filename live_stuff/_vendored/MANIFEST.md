# Vendored engine files

These files are copied from the research/backend tree so `live_stuff` deploys
as a sealed folder. The only edits are import-path rewrites (`src.btc...` ->
relative vendored imports). Behaviour is unchanged; parity was verified against
the book-107 pins on 2026-10-19.

| file | source | bytes | sha256 |
|---|---|---:|---|
| `unified.py` | `backend/src/btc/engines/htf_ltf/unified.py` | 104,368 | `79c8e5db88afe252a814abfff3830d0ebefdced22130096eb85339657271eaf8` |
| `btc_engine.py` | `backend/src/btc/btc_engine.py` | 46,553 | `60e9adb23c24fda49a51d53f44c50578c3134323871c7cc0531fd0a48c7dd091` |
| `v7_timecap.py` | `backend/src/btc/engines/v7_timecap.py` | 11,893 | `978ab6443e6af551b90e39dd78d43330bd36d01ddaf26fce5c98fbe2c72fd3a2` |
| `firstswing.py` | `backend/src/firstswing.py` | 69,990 | `d7d475f8c926ba2fa628031d2c82ac889be1ae40fb7007bd0363e874201b10f3` |
| `walker.py` | `backend/src/walker.py` | 20,262 | `8bd435b4587975110bd9ecb2334609ad3c1c46e39c795f9cb8f352688c76562e` |
| `persistent_swing.py` | `backend/src/live/persistent_swing.py` | 10,674 | `51a6a2d20deedeac28bbab4726ffc88dd513c793f0c8de3b8621bce7b6dbb4b7` |
| `mark.py` | `backtest/engine/mark.py` | 2,471 | `f5d9fef800d5eae84523bbcc2c8ab1457ed17493bff0804d9e546625420e4fa8` |

## Parity check (IS, book 107)

- Vendored `unified` + `fine_ltf=data["fine"]`: **525 trades / +538.40R / DD 28.38** (exact pin match).
- Live basis (`fine_ltf=[]`): **526 trades / +537.13R / DD 29.65** (+1 trade, -1.27R, +1.27R DD).
- Coarse basis is accepted: live never needs 1m data.

Do not edit these files in place. Re-vendor from the sources above and re-run
the parity check if the engine changes.
