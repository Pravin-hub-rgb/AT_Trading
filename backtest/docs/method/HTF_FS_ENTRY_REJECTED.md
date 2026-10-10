> **PARTIALLY SUPERSEDED 2026-10-10 — see `HTF_FS_ENTRY_CORRECTED.md`.**
>
> The REJECTION of `htf_fs=all` still stands, on the negative half-year and the
> drawdown, and both of those reproduce exactly. But one of its three reasons
> does not survive: the period control quoted here — "better in 2 of 6 years",
> "the gain does not survive a half-year fixed effect" — was computed on
> `per_h[c][0]`, the **first trade** of each half-year, while the negative-cell
> check on the line below it correctly used `sum(per_h[c])`. Six single trades
> decided a family-wide rejection. On the half-year net the same arm is better in
> 5 of 6 years with t = +3.42. Reproduced in `exp_period_control_recheck.py`.
>
> Also: the `flip` mode measured here as "IDENTICAL to off" was a no-op **by
> construction** — the table tested `_hfs_on and _hfs == "all"` together, so
> "flip" moved nothing. It is now a real mode and it is the strongest arm in the
> family. Nothing on this page ever measured the selective arm.

# HTF-side FS entry — "window opens on FS"

Date: 2026-10-09. Harness: `exp_htf_fs_entry.py`. Knob: `exp_htf_fs_entry`.

The owner asked for this twice, and the second time asked whether it had been
tested. It had not. It has now.

**Answer: tested, causal, and it makes the books WORSE on the owner's own rule.**
The negative half-year comes back on all three books.

---

## the asymmetry was real

The LTF plane enters at the swing FS print (`exp_fs_entry_side`). The HTF plane
enters on the **break** (`entry_break="flip"/"decisive"/"b2"`). Measured gap:

| | p0 | p25 | p50 | p75 | p100 |
|---|---:|---:|---:|---:|---:|
| window_start − its own direction's FS | 0.0h | 8h | **25h** | 55h | 355h |

**Only 1 window in 528 opens exactly on its FS.** So "we trade on FS" is true on
one plane and false on the other — a real gap, worth measuring.

## the knob

`simulate_btc_trades_v7` already accepts `entry_break="fs_long"/"fs_short"/
"fs_both"` (btc_engine.py:151) — the same machinery the LTF side uses. `exp_htf_fs_entry`
routes the HTF side through it. Default `""` keeps every pinned book byte-identical.

**`flip` mode measured IDENTICAL to `off`** on all three books — because the
shipping books don't read the flip bucket at all. Worth knowing: a knob that does
nothing is a measurement, not a bug.

## results

| book | arm | n | net | dd IS | dd OOS | **neg cells** |
|---|---|---:|---:|---:|---:|---:|
| `champ_long` | off | 839 | +773.0 | 13.4 | 11.9 | 1 |
| `champ_long` | htf_fs=all | 1191 | **+1199.9** | 19.8 | 16.1 | **1** ← still there |
| `htf15` | off | 800 | +822.4 | 17.3 | 16.9 | **0** |
| `htf15` | htf_fs=all | 1161 | **+1222.2** | 29.6 | 16.1 | **1** ← new |
| `sig_multi` | off | 523 | +704.4 | 13.4 | 7.6 | **0** |
| `sig_multi` | htf_fs=all | 686 | **+948.3** | 17.7 | 7.7 | **1** ← new |

**The net jump is enormous and real: +55% on champ_long, +49% on htf15, +35% on
sig_multi.** And every one of them FAILS the owner's rule.

## why it fails — and this is the actual finding

### 1. it re-creates the negative cell it was supposed to fix

`2022-H2` goes **+68.8 → −4.8** on champ_long and `+60.9 → −4.8** on htf15.
Identical value in both books, which is the tell: `2022-H2` is governed by one
specific window behaviour, not by the book.

On `sig_multi` the cell it breaks is `2026-H2`, +70.0 → **−7.0**.

### 2. it is not a better trigger — it is MORE windows

| book | windows used | new | trades/window | net on new windows |
|---|---:|---:|---:|---:|
| `champ_long` | 297 → 206 | 197 | 2.82 → **5.78** | **95%** |
| `htf15` | 284 → 205 | 195 | 2.82 → **5.66** | **93%** |
| `sig_multi` | 260 → 186 | 182 | 2.01 → **3.69** | **101%** |

**95% of the gain sits in windows the book was not trading before.** Trades per
window roughly doubled. This knob did not make the existing windows better — it
brought in 197 new ones.

And the period control says the new ones are not better ones:

- **htf_fs better in 2 of 6 years** (champ_long), **1 of 6** (htf15), **2 of 6** (sig_multi)

By the same test that killed `flip_quality`, **the gain does not survive a
half-year fixed effect.**

### 3. the reason it is "more windows" is a degenerate config

`all` sets flip, decisive and b2 to the **same** `fs_both` entry, collapsing the
three regime buckets into one set. The books then lose the flip/decisive/b2
distinction that `_sw_ts_dir_mag` and the regime gate depend on. **The book that
scores best is the one that stopped distinguishing regimes.**

### 4. drawdown goes the wrong way everywhere

dd IS 13.4 → 19.8, 17.3 → **29.6** (at the 29R budget limit), 13.4 → 17.7.

## causality — clean, so the rejection is on the merits

The worry with an FS-anchored window is that the window would open using a print
the trade had not earned. It does not:

| era | trades | entry before window_start | window_start before its own FS |
|---|---:|---:|---:|
| IS | 770 | **0** | **0** |
| OOS | 421 | **0** | **0** |

`window_start − preceding FS` is **exactly 0.0h at min, p50 and max**. Every
FS-entered window opens precisely at the print. **No lookahead.** The knob is
honest; the book it produces is just not one we want.

## verdict

**Not adopted, and not registered as a candidate.** This is the one arm that
should not be registered, because registering it would imply a measured
candidate worth a forward window, and it fails the owner's primary rule on all
three books.

The knob stays in the engine, default off, because the measurement is the point
and re-deriving it costs an hour.

**What it did settle:** the LTF/HTF asymmetry is real and is not worth closing.
Trading the HTF side on FS buys a 35–55% net jump by doubling the window count,
and pays for it with a fresh negative half-year, 6R of extra drawdown, and a
regime distinction thrown away. On this book's evidence **more windows is not
better windows** — `htf15` and `biasmom05` both fix the negative cell by
*narrowing* what is traded, not by adding to it.