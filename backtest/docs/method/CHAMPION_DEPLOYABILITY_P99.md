# P99 / P100 - CHAMPION DEPLOYABILITY. The real number.


<!-- C17-NOTICE -->
> **C17 NOTICE (2026-10-07).** The figures in this document were measured before
> the C17 gate fix, which removed a lookahead from the HTF window gate and
> invalidated 214 of 215 registry pins. They are kept as the dated record they
> were, and they are **not** what the engine produces today - do not quote them
> as current. Current numbers: `python exp_pinverify.py` (re-derives every pin),
> `docs/method/C17_WINDOW_END_CAUSALITY.md` (what changed and why),
> `docs/multi/MULTI_RANKINGS.md` and `docs/signal/SIGNAL_RANKINGS.md`
> (regenerated from a post-C17 measurement).
------------------------------------------------------------------------------

Branch: agents/champion-reality-audit
Date: 2026-09-30. Net accounting, both eras, both lanes where run.

## WHAT THIS SETTLES

The champion pin (+325.8R IS / +70.1R OOS) is produced by
`test_experiments_craze.py`, which reads v18_streak_halt.py as TEXT and
patches it with two kwargs the shipped engine has never had:

    exp_mltf     = True     multi-position: allow overlapping entries
    exp_persist  = 7        regime hysteresis: hold old regime 7 flips
    exp_partial_r= 0.0      already OFF, never load-bearing

The shipped engine accepts 16 params. The harness accepts 130.

## STEP 0 - HARD GATE (pass)

exp_champion_true.py reproduced the pin exactly:

    champion_multi_sw10 IS : n=500  net=+325.8R      PIN OK

Without this, nothing below is trustworthy. It passed.

## STEP 1 - ABLATION (3 arms, identical data, identical params)

Only the flags change. exp_ablation.py, results in _ablation.jsonl.

| arm | exp_mltf | exp_persist | IS | OOS | maxconc |
|---|---|---|---|---|---|
| **A** production-as-is | OFF | OFF | 395t **+137.7R** PF 1.86 | 230t **-13.3R** PF 1.10 | 1 |
| **B** persist only | OFF | 7 | 387t +150.4R PF 1.93 | 219t **-1.8R** PF 1.18 | 1 |
| **C** champion control | ON | 7 | 500t **+325.8R** PF 2.38 | 279t **+70.1R** PF 1.59 | 6 IS / 5 OOS |

Arm C reproduces the pin on both eras. The controls are sound.

## STEP 2 - CAN THE SHIPPED ENGINE REPRODUCE ARM A? YES.

exp_shipped_direct.py calls
`src.btc.engines.htf_ltf.v18_streak_halt.simulate_htf_ltf_streak_halt`
DIRECTLY. No harness, no source patching, no `tc.build_module()`.

    SHIPPED ENGINE, champion params, zero harness:
      n=395  net=+137.72R  PF=1.859  maxconc=1

Identical to harness arm A to the cent. So arm A is not a harness
artefact - it is what production code does today, with the three
harness-only kwargs dropped.

## WHAT `busy_until` ACTUALLY IS (my earlier claim was wrong)

I previously reported that a string-compare bug in `busy_until` cost the
champion 58% of its IS R. That conflated two different code paths.

- v18:577 `bar_time` is a DATETIME. v18:743 `busy_until` is a DATE.
  `"2026-09-30 14:00:00" <= "2026-09-30"` is always False. Real bug.
- But test_experiments_craze.py:955 rewrites that line to
  `if (not exp_mltf) and busy_until and ...`. Champion has
  exp_mltf=True, so the guard short-circuits and never runs.
- method/BLEED_AUTOPSY.md:157 already documented multi-position as intended:
  "with exp_mltf concurrent positions, 178 trades read state".

So concurrency is DESIGN. The guard bug is real but lives in a lane the
champion never runs. My "champion books 3-6 deep by accident" was wrong.

The serial book (arm A) is NOT the champion with a bug fixed. It is a
DIFFERENT strategy that happens to be reachable from shipped code.

## THE ANSWER TO "WHAT IS THE REAL NUMBER"

There is no single real number. There are two different books and they
disagree on OOS:

- **Reachable today, no porting:** IS +137.7R, **OOS -13.3R**. Negative.
- **Pinned champion, needs exp_mltf ported:** IS +325.8R, **OOS +70.1R**.

Every single-axis arm is negative OOS. Only the multi-position book is
positive OOS. The features are load-bearing, and they must be ported.

## WHAT exp_persist IS

test_experiments_craze.py:935-941. It is regime hysteresis, not a
position count:

    if use != _rg_s:              # regime flipped
        _rg_c += 1
        if _rg_c >= exp_persist:  # 7 consecutive disagreements
            _rg_s = use; _rg_c = 0 # then switch
    use = _rg_s                   # otherwise keep the OLD regime

Contribution is real but small: +12.7R IS and +11.5R OOS. The bulk of
the champion is exp_mltf.

## STATUS OF EARLIER CLAIMS

- P96 "58% of IS R is unavailable to a bot whose guard works" -
  **RETRACT.** It measured arm A against arm C and called the difference
  a bug cost. It is a strategy difference.
- P97 "the queue is structurally empty" - **still true**, but it was
  never evidence against the champion. Under exp_mltf there is no queue
  by design.
- P94/P98 "396 trades = -156.9R losing sub-book" - the figure is arithmetically
  right, the reading was not. It describes arm C split by a post-outcome
  event, not a defect in the shipped book.

## STILL OPEN

- Multi-position port needs a capital model. Six simultaneous positions
  sized as one position each is a different risk profile from the
  single-position sizing the engine assumes.
- OOS is 12.5 days and 2 trades on the forward lane. Nothing here is a
  ruling on live merit.
- ~~`method/reality of champion.md` flagged three findings in the HTF GATE path
  that nobody has opened yet. That is the next audit, ahead of the port.~~
  **RESOLVED 2026-09-26** (`method/new bugs.md:601` — all three closed and re-verified):
  C14 at `v18_streak_halt.py:269,272`, covered by `test_c14_c15_gates_present`
  which PASSES; C15 at `:539,513`, covered by `test_c15_count_band` which PASSES.
  Independently re-verified inside v19 by
  [`method/HTF_GATE_AUDIT_P101.md`](method/HTF_GATE_AUDIT_P101.md). This line said "nobody has
  opened it yet" five days after it was opened and closed.