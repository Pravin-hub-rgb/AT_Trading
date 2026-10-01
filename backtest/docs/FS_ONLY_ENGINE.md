# FS-ONLY ENGINE — built and run. The premise was wrong; the book is real but small.

Date: 2026-09-28. Harness: `exp_fs_only_engine.py` → `_fs_only.json`
Controls exact in all four cells (500t +325.8R / 454t +358.9R /
279t +70.2R / 253t +60.2R, all net). 57.2s.

## The premise, and why it was wrong

`FS_ENTRY.md` said, and the handover repeated:

> "2900 swings exist in IS and 1634 in OOS, all with an FS — so a *true*
> FS-only engine could in principle take swings that never produced a
> B2/flip entry… **That is not simulated here.**"

**2,900 swings confirmed exactly.** But the run found **zero** swings
without a B2/FLIP mark — every swing carries one. So the 2,586 figure is
not a population of unpriced *swings*; it is a population of unpriced
*trades*. The 314 in `FS_ENTRY.md` is the count that survived the window
gate, the chop/regime gate, the direction match, cooldown and `busy_until`
— not the count of swings that had a tradeable mark.

So the "10× bigger book" was an arithmetic artefact of reading a post-filter
trade count as a pre-filter swing count. **The FS-only book is not bigger.
It is smaller** — 263 trades IS, 108 OOS.

## Result

| SL mode | r | IS | OOS (utcsat) |
|---|---|---|---|
| `fs_pivot` | 2.0 | 2t −2.0R | 4t −4.0R |
| `fs_pivot` | 3.0 | 2t −2.0R | 4t −4.0R |
| **`seg_start`** | **2.0** | **263t +31.7R, trim +0.079, exB5 +21.7** | 108t +1.3R, **trim −0.037** |
| `seg_start` | 3.0 | 179t +18.3R, trim +0.014 | 58t +3.3R, trim −0.012 |

Two clean findings, both useful:

**1. `fs_pivot` is not a usable stop.** It yields 2–4 trades. The FS
pivot is the swing's own end extreme, so by the time the FS fires, price is
already at that level and the stop sits inside the entry. The geometry
rejects almost everything. `seg_start` (the swing's origin — the shipped SL
convention) is the only usable variant.

**2. `seg_start r=2.0` is the strongest FS result ever recorded, and it
still fails the same-sign bar.** IS trimmed mean **+0.079** with
**ex-best-5 +21.7** — a genuinely positive, tail-robust IS result on 263
trades. OOS: 108t +1.3R, trimmed mean **−0.037**, ex-best-5 −8.7.

That is an era flip on the best arm. Per the repo's standing rule (same
sign in both eras or it is closed), **FS-only is CLOSED**.

It is worth recording *how* close it was, because this is the only positive
trimmed-mean 15m result in the whole session: +0.079 IS is not noise, and
if a future agent finds an OOS-consistent variant of "enter at FS with a
swing-origin stop and 2R", that is where to start. Do not re-run these four
cells expecting a different answer.

## Verdict

- **FS-only closed.** 0/4 cells pass both eras.
- **The last open book in the repo is now tested.** Combined with the 1m
  closure, the research programme has no untested book left on the
  single-instrument BTC book. Remaining open items are engineering
  (`v18_streak_halt` live size state) or cross-instrument.
- Three bugs of mine were caught by running rather than reading: `set` vs
  `dict` on the date store, `fs_at_time` being **two different formats**
  (full datetime at `btc_swing.py:88`, bare `HH:MM` at `:108` — matching
  only full datetimes gave zero signals), and the `bool(s["breaks"])`
  population test described above.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
