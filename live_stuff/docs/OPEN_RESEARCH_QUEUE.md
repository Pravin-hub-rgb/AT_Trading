# OPEN RESEARCH QUEUE — every suggestion from the second-researcher round,
# in the order received. No priority. Worked one at a time.

Date: 2026-09-28. Source: `other bots proposal.md` (four sets: Nemotron 3,
Big Pickle, Link3.0, Mimo-V2). ~30 proposals were returned; they are
deduplicated below.

**Status key:** `[x]` done this session · `[~]` partially done · `[ ]` open

---

## DONE THIS SESSION

- `[x]` **P1/P2 wave labelling (Elliott)** — closed. The swing chain is
  sequential with a mean 10.3-bar gap, so no nested wave pair exists. One
  candidate in 2,900 swings. `P1P2_WAVE.md`
- `[x]` **Retracement depth at entry** (the P1/P2 quantity relocated to
  where it exists) — closed on two grounds: the harness omitted the HTF
  window gate so it did not reproduce the champion's book (1,285 vs 500
  trades), and the depth distribution is saturated at its floor (p10 =
  0.998) so the ladder has no gradient. `RETRACE_DEPTH.md`
- `[x]` **FS-only book with swing-trail exits** — closed. The "2,586
  never-priced swings" premise is false: all 2,900 carry a B2/FLIP.
  `FS_ONLY_ENGINE.md`
- `[x]` **Kelly sizing** — computed, and the interesting output is that
  the naive binary form is wrong for a heavy-tailed book and the
  long-run-corrected form is small (0.2-0.3% of bankroll per trade).
  `KELLY_CONTINUOUS.md`

## STRUCTURALLY EXCLUDED — do not attempt

- `[x]` **Order-book / microstructure** — `data/flow/bookDepth/` exists
  (3,617 files, never read) but starts 2023-01, so it has no 2021-22
  coverage and can never satisfy the two-era bar. Not weak: excluded.
  Same for `funding/`, `metrics/`, `premium1h/`.
- `[x]` **Scheduled events** — already closed path-true with ±1-day
  placebos (`SCHEDULED_EVENTS_AUTOPSY.md`). Confirmed, not re-proposed.
- `[x]` **30m / 2h timeframes** — already closed (`exp_tf_family.py`;
  30m costs 84R IS / 55R OOS).
- `[x]` **B1 entry** — closed (`B1_ENTRY.md`, WR 27.8% → 17.2%).
- `[x]` **4h HTF confirmation** — already closed.

## OPEN — engineering-blocked

- `[ ]` **Position resize instead of close** — the engine has no size
  channel (`v18_streak_halt.py` has zero hits for equity/size/notional),
  and `exp_max_concurrent` was already swept (cap=5 free-to-better).
  Blocked on the size channel existing first.
- `[ ]` **Correlation-aware portfolio weighting** — blocked on data: the
  current alt sweep is Binance fapi, not Bybit perp. The `inv_corr` scheme
  also degenerated to 100% LINK and its number must not be used.
  `PORTFOLIO_KILL_WEIGHT.md`

## OPEN — the real queue

- `[ ]` **Multi-swing 1h bias confirmation (2-of-3)** *(Nemotron)* —
  intervenes on the *bias timeline*, which no closed row has touched.
  Genuinely untested. **This is where to go next.**
- `[ ]` **1h swing geometry gate at bias-window open** *(Nemotron)* —
  magnitude / duration / confirmation source, all known at the swing's
  confirmation instant. Overlaps the graveyard's "range width" row, so it
  must be pre-registered as distinct or it is a re-run.
- `[ ]` **Alt breadth as a BTC HTF feature** *(Nemotron P6)* — alt index
  state gating BTC bias. Flagged as risky by the proposer; the
  cross-sectional-rotation closure creates real tension.
- `[ ]` **One family-wise pass on `data/forward/bybit/`** *(Mimo-V2)* —
  adjudicate all unadopted survivors in a single pre-registered pass
  rather than spending the slice one candidate at a time. ~464 trades, so
  it can rule on things and confirm none.
- `[ ]` **Bybit perp alt data** — the transfer census (7/13 passing, 5/6
  kills-clean) is on Binance fapi and therefore does not answer a Bybit
  question. Fetching Bybit alts is the precondition for the whole
  multi-instrument thread.
- `[ ]` **ZigZag re-count over `normal_highs`/`normal_lows`** — the raw
  pivot pools already exist in `firstswing.py`; a different segmentation
  of the same bars, which is the closest reachable relative of the dead
  P1/P2 wave labelling.

## Notes recorded from the round

- My briefing was **three-quarters wrong** on "untouched" seeds, and two
  of its errors had reached `HANDOVER_SESSION.md`:
  `chop_thresh=58.0` is **inert** under `mode="atr_high"`, and
  `sw10`/`sw20` are built from the **1h** stream, not 15m. Both verified
  in code. `SECOND_RESEARCHER_REVIEW.md`
- The method failure across the session was checking **shape** and
  assuming **meaning**. `probe_structure.py` now runs first.
  `PROCESS_FIX_PROBES.md`
