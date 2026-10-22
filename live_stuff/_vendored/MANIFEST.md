# Vendored engine files

These files are copied from the research/backend tree so `live_stuff` deploys
as a sealed folder. The only edits are import-path rewrites (`src.btc...` ->
relative vendored imports). Behaviour is unchanged; parity was verified against
the book-107 pins on 2026-10-22.

| file | source | bytes | sha256 |
|---|---|---:|---|
| `unified.py` | `backend/src/btc/engines/htf_ltf/unified.py` | 104,484 | `dce0d00c02305b8a8510ffb1a269c3e93331087afcd92341373dc30a62e2b662` |
| `btc_engine.py` | `backend/src/btc/btc_engine.py` | 47,307 | `cffbdf3537d7b3c8ef3a5fc6e656f81c86de9db41f758e609159fc8bc844b0df` |
| `v7_timecap.py` | `backend/src/btc/engines/v7_timecap.py` | 11,893 | `978ab6443e6af551b90e39dd78d43330bd36d01ddaf26fce5c98fbe2c72fd3a2` |
| `firstswing.py` | `backend/src/firstswing.py` | 69,990 | `d7d475f8c926ba2fa628031d2c82ac889be1ae40fb7007bd0363e874201b10f3` |
| `walker.py` | `backend/src/walker.py` | 20,262 | `8bd435b4587975110bd9ecb2334609ad3c1c46e39c795f9cb8f352688c76562e` |
| `persistent_swing.py` | `backend/src/live/persistent_swing.py` | 10,674 | `51a6a2d20deedeac28bbab4726ffc88dd513c793f0c8de3b8621bce7b6dbb4b7` |
| `mark.py` | `backtest/engine/mark.py` | 2,471 | `f5d9fef800d5eae84523bbcc2c8ab1457ed17493bff0804d9e546625420e4fa8` |

`btc_engine.py` is byte-identical to its source (it has no `src.btc` imports to
rewrite), so its vendored hash equals the research one.

## Parity check (IS, book 107)

- Vendored `unified` + `fine_ltf=data["fine"]`: **520 trades / +508.37R / DD 27.23** (exact pin match).
- Live basis (`fine_ltf=[]`): **522 trades / +508.33R / DD 28.50** (+2 trades, -0.04R, +1.27R DD).
- Coarse basis is accepted: live never needs 1m data.

2026-10-21 re-vendor: unified gains an additive result key
`htf_trades_decisive` (the ATR-routed decisive-sim windows needed by the
live tracker; live was keying flip/b2 buckets only while book 107's regime
selects decisive/flip). Trade computation untouched — the day's rerun of
the pin harness reproduced both pins exactly (IS 526/+537.13R PIN OK,
OOS 295/+273.52R PIN OK).

2026-10-22 re-vendor: `btc_engine.py` gains the **wait-for-FS gate** — an
entry on a mark may only be taken once the previous swing has printed its FS.
The gate lives in the `fs_` branch's fall-through sub-loop, so it changes the
short side of book 107 and nothing else. Book 107 moves from 525t / +538.40R to
**520t / +508.37R** in sample (-30.03R) and from 295t / +272.92R to **290t /
+220.71R** out of sample (-52.21R): the pre-FS entries it removes were worth
+36.56R in sample and +50.19R out of sample, and the chain that replaced them
was worth less than what it removed. The live-basis row above is the same
engine run coarse, which is what the deployed book actually trades on.

Do not edit these files in place. Re-vendor from the sources above and re-run
the parity check if the engine changes.
