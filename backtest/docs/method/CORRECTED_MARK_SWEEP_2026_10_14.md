# CORRECTED-MARK SWEEP — 2026-10-14

Work done after the volatile-B1 colour fix (`5d6cab2`) landed, i.e. on the
corrected chain: **2840 swings / 7734 marks, fingerprint `83a3af3f6ebf0ffa`**
(IS) and `8981622657925d4d` (OOS).

The premise for the whole sweep: **every threshold and every closed mechanism in
this repo was fitted to marks that were ~3% wrong.** 43 B2s had become FLIPs, 35
FLIPs had become B2s and 51 B1 directions had flipped. So the work is not only
"find new ideas" — it is "re-examine what was decided against a surface that has
since moved".

## Rules, applied to every phase

1. Every knob default-off, with an identity gate before any number is quoted.
2. Tune on **IS only**. OOS stays sealed until the item is decided.
3. Record both eras always, losing included.
4. Win → registry pin + doc. Loss → `closed/CLOSED_DO_NOT_REPEAT.md` with both
   eras and the mechanism. Harness kept either way.
5. Anything causal → every book using it becomes `status: "reference"`.

---

## A1 — baseline frozen

`backtest/tests/exp_baseline_freeze.py`, snapshot
`_baseline_2026_10_14.json`, taken at commit `1bb4be1`.

```
             15m mb50 fingerprint   swings  marks
  IS         83a3af3f6ebf0ffa        2840   7734
  OOS        8981622657925d4d        1571   4344
```

Five fsent books, both eras, recorded in the snapshot. `--compare` re-derives and
diffs; it is D2.

**Note on the fingerprint row format.** It includes the price column:
`time|kind|dir|px|swing`. An earlier fingerprint quoted in this session
(`393577a28ffd3e02`) was computed **without** the price column and is therefore
**not comparable** to `c864262630560f83` or to the values above. Treat that one as
void. The tool now states the format in its own output for exactly this reason.

---

## A2 — colour-rule consistency audit

### A2.1 Is colour routed identically on B1, B2 and FLIP? **YES.**

Four volatile sites, all reading `self.cl > self.op`:

| site | line | routes to |
|---|---|---|
| `watch` (B1) | `firstswing.py:466` | `_lock(...)` |
| confirmed-state volatile | `firstswing.py:524-525` | sustained → B2/FLIP |
| unconfirmed-state volatile | `firstswing.py:577` | `_flip` / `_b2_if_gap_allows` |

The B1 site was the one that was missing and was added on 2026-10-13. All four are
now the same predicate. **No inconsistency found.**

### A2.2 Is the B2 alternation rule still right after B1 locks by colour? **YES.**

`_b2_done_in_dir` and `_last_mark_kind` are untouched by the colour change —
`_lock` still resets `_b2_done_in_dir = False` and sets `_last_mark_kind = "B1"`
whatever direction it locked. The alternation keys off `_last_mark_kind`, not off
the direction, so making the direction colour-derived does not perturb it.
Confirmed empirically: FLIP-FLIP 0, B1/B2 same side 0 violations.

### A2.3 Does any volatile path still reach a bare return with no mark? **NO — but the check was blind.**

This is where the sweep found something, and what it found was **in the audit
tool rather than the engine**.

`exp_swing_invariants.py` reported "20460 suppressed breaks examined, 0
unexplained". That was **half the story**. `_step` is only called when
`self.armed` is True (`firstswing.py:428`), so the harness logged armed bars
only. There is a second population it never saw at all:

```
bars with a break, never armed   : 6154   (volatile 2841)
  ...pre-arm warmup (watch, no pending arm)   : 6040
  ...pending-arm deferral (same-bar arm guard) :  114
  ...unexplained                               :    0
TOTAL break-without-a-mark : 26614  (20460 armed + 6154 never armed)
```

Both un-armed buckets are legitimate and named — the engine had not been armed by
a seal and was not doing anything — but they were outside the check and a reader
had no way to know that. **A harness that passes because it excluded its own
subject is the failure mode this repo already warns about**, and it happened
again, in a harness written specifically to prevent it.

The harness now watches `process_bar` as well, recomputes the break flags at its
entry from the same `e_hi_prev`/`e_lo_prev` the engine uses at
`firstswing.py:374`, and reports the un-armed population as its own buckets. The
headline is now **26614 of 26614 classified, 0 unexplained** — and the number a
reader would have quoted is 77% larger than the one they were given before.

### The one real cost A2 exposed

`defer_same_bar_arm` is True for every swing after the first
(`btc_swing.py`), so each such swing defers its first break to the bar after the
seal. Measured: **579 of 2840 instances (20%) lose exactly one volatile bar** to
this before their first mark. One bar each, median 1, max 1 — bounded, but never
tested as a knob. It is the natural next candidate after B1.

---

*(B1, B2, C1, C2, D1, D2 appended below as they complete.)*
---

## A3 — lookahead gate sweep. TWO FAILURES, both characterised.

**A3.1 `exp_craze_patch_gate.py check` FAILS — the patched engine changed.**

```
baseline sha256 aa189c5fe1acf881a631bbe69af50814558fd2d425890bef9f97fe534105bb18
lines     2359 -> 2710
bytes   125663 -> 148608
n_exp_kwargs 117 -> 126
n_continue    80 -> 82
```

Legitimate engine growth — three of the nine new kwargs are this session's
(`exp_fs_break_confirm`, `exp_fs_confirm_bars`, `exp_fs_trail_trigger`), the rest
are concurrent work. **The gate is doing its job**: every number that harness
produces comes from those bytes, so all of them are now stale.

**Deliberately NOT re-baselined here.** The baseline is a tracked file
(`backtest/tests/_craze_patch_gate.json`) and another process was mid-run against
it; re-writing a gate underneath a live run is exactly the kind of quiet state
change this repo warns about. It needs a deliberate re-approval in its own commit
once the tree is quiet. **Until then, no number from that harness is quotable.**

**A3.2 `exp_origin_lookahead.py` FAILS — six losing books not marked `reference`.**

`decayC_c` −40.97 · `decayC_u` −34.11 · `decayE_c` −1.48 · `gap_campaign3` −40.62 ·
`gap_entry_cap3` −45.48 · `skipwinhalt_multi_sw10` −22.14.

Per the sweep rules, a negative-net book that is not quarantined is hygiene debt:
it can re-enter a shortlist on size alone. Deferred to D1 for the same reason —
`status: "reference"` changes what `shortlisted()` returns, and another process
was running.

Ten further books use quarantined knobs (`exp_require_dir_match`,
`exp_max_swing_age`, `exp_min_swing_ratio`) and are already handled by the
`GRAVEYARD_KNOBS` quarantine in `exp_signal_metrics.py`.

---

## B1 — `b2_gap_bars` sweep. NO WINNER; the pinned value stands.

The never-swept knob. Gap length, not break magnitude — the owner's ruling was
*"even a 0.5 point break is a break"*, which argues about size and never ruled on
length.

**The harness verified itself**: gap=1 reproduces the A1 freeze fingerprint
`83a3af3f6ebf0ffa` exactly, or the run aborts. It did.

The chain moves a lot:

| gap | swings | marks | fingerprint |
|---|---|---|---|
| 0 | 2979 | 8545 | fed09ca4d0ff8c5a |
| **1 (pinned)** | 2840 | 7734 | **83a3af3f6ebf0ffa** |
| 2 | 2762 | 7362 | 16a40e3e76b4d4b7 |
| 3 | 2706 | 7106 | 79290600b1c221c7 |

IS only, by design:

| book | gap=0 | gap=1 | gap=2 | gap=3 |
|---|---|---|---|---|
| `fsent_champ_long` | +500.1 | +561.4 | **+635.7** | +464.8 |
| `fsent_champ_short` | **+781.7** | +667.5 | +601.1 | +520.6 |
| `fsent_champ_long_htf15` | +507.7 | +600.1 | **+636.0** | +557.5 |
| `fsent_champ_long_htffs` | **+970.5** | +906.6 | +846.7 | +764.2 |
| `fsent_champ_long_mcloff` | +516.1 | +605.3 | **+643.0** | +511.5 |
| **TOTAL IS** | +3276.1 | +3340.9 | **+3362.7** | +2818.6 |

**gap=2 leads the total by +21.8R on +3340.9 — +0.65%.** And it wins **only 3 of
5 books**. gap=0 wins the other 2, with two of the largest individual gains in the
table (`short` +114.2, `htffs` +63.9) while losing badly on `long` (−61.3).

A "winner" that depends on which book you ask is not a winner. **OOS was not
opened**, because the sweep rule is that a consistent IS winner earns exactly one
OOS reveal, and this arm is not consistent. The pinned value of 1 stands, and this
is a result rather than a null: the default was right, and now there is a number
saying so instead of an assumption.

**The more interesting secondary finding.** The mark count moves 10% (7734 → 8545
at gap=0) and the books barely move — most are within ±3% of baseline, and the
largest swing in the table is `champ_short` at ±12%. The books are strikingly
insensitive to the size of the B2/FLIP population. Whatever they are trading, it
is close to insensitive to which B2s and FLIPs exist. That is worth knowing before
anyone spends more effort on mark-level rules — and it is the strongest argument
yet for why four consecutive mark-shaping experiments all landed inside noise.

**Harness**: `backtest/experiments/b2_gap_sweep/exp_b2_gap_sweep.py`.

---

## A4 - is the 50-bar gate one knob or two? ANSWERED: one knob, FS only

`minBars` reaches the engine in exactly one place:

    backend/src/firstswing.py:836   def _check_chop
        _inside_window = self.bars_seen < self.min_bars

That is the FS gate. `_b2_if_gap_allows`, `_confirm_direction` and `_flip` never
read `min_bars`, so B2/FLIP are NOT gated by it. And `min_bars_idx` in
btc_swing.py is a DISPLAY marker (the MB50 chart label), not a gate.

So the two 50s share a constant but already do different jobs, exactly as theory
rule 6 states. The concern that they were conflated was wrong. No change needed.

## B2 - re-fit the pinned constants. IS ONLY, OOS NEVER OPENED

All five knobs verified SIM-ONLY (absent from firstswing.py), so the chain is
fixed at 83a3af3f6ebf0ffa for every arm and the A1 identity gate holds throughout.

v1 swept one value across all five books while the baseline let each book sit at
its own pin. That is not a comparison - and it mattered: `fsent_champ_long_mcloff`
has its own max_consecutive_losses = 0, not 3. v1's mcl column is discarded.

v2 sweeps each book independently around its OWN pin, holding the other four.

Per-book verdicts:

| knob | result |
|---|---|
| chop_thresh | INERT in all 5 books |
| atr_high_thresh | flat in all 5 (spread 23-40R, no optimum) |
| sl_buf_atr | 0.005 better by 1-3R in all 5 - noise |
| cooldown_bars | pin 8 CONFIRMED in 4 of 5 (htffs differs by +0.4R) |
| max_consecutive_losses | non-monotonic, 0 best on long/short/htffs |

### Dead knobs - the config lying about the code

Same failure shape as the "extreme pivot" incident: the CONFIG claims something
the CODE does not do.

All five books run `mode="atr_high"`, not `mode="b2_vs_flip_chop"`. In atr_high
mode:

  - `chop_thresh` is NEVER READ. 40 through 74 give identical trades in every
    book. Four of five configs carry a value that does nothing.
  - `ext_stop_r` is live only in a narrow band. 0.0, 3.0 and 5.0 all produce
    IDENTICAL trade sets (n=497); only 1.0 differs (n=368). So the long book's
    pin of 0.0 and everyone else's 3.0 are the same setting.

### The loss-halt costs money

max_consecutive_losses on fsent_champ_long, IS, own pin 3:

    0 -> +605.3R (n=533)      <-- halt disabled
    1 -> +380.6R (n=497)
    2 -> +543.8R
    3 -> +561.4R  <-- the pin
    4 -> +596.3R
    8 -> +602.5R
   12 -> +606.3R

Non-monotonic and strange: halting after ONE loss costs 225R, but not halting at
all is the best result on the book. mcl=3 gives up 44R against mcl=0. The pin is
worse than having no pin. This is IS evidence only and earns at most one OOS
reveal, after the owner rules on it.

### B2 conclusion

No candidate here is worth an OOS reveal on its own. The best single delta is
+45R on a +3340.9R portfolio (+1.4%), and that one is a boundary artifact from a
non-monotonic curve. The real output of B2 is not a better number - it is three
dead knobs and a risk control that hurts.

## BOOK STRUCTURE - the five books are one signal, four slices

exp_book_uniqueness.py hashes each book's closed-trade set at its own pin. No two
share a hash. But the pairwise LIVE-mechanism structure is decisive:

    fsent_champ_long  vs short      differ by exp_fs_entry_side
    fsent_champ_long  vs long_htf15 differ by the swing chain
    fsent_champ_long  vs long_htffs differ by exp_htf_fs_entry
    fsent_champ_long  vs long_mcloff differ by max_consecutive_losses

Every other pair differs by two or more mechanisms. So long is a hub and the
other four are each ONE knob away from it.

Consequence: "+3340.9R across 5 books" is one strategy measured four ways, not
five confirmations. Five positive cells is one positive cell plus four
sensitivity checks. The edge is not thereby fake; the EVIDENCE FOR IT is one
strategy's worth and should not be described as five.

Note the trap this replaces. `fsent_champ_long_mcloff` is NOT a duplicate - at
their own pins the two trade 497 and 533 times and hash differently. Proved
trade-for-trade: long mcl=3 vs mcloff mcl=3 -> both n=497, sha 0ee53f50459e,
identical. So the loss-halt is the only live difference between them. An early
draft of the uniqueness gate called such pairs "duplicates" because realigning
one parameter made hashes match; that is a tautology, since a long book and a
short book differ only in side by definition. The gate now fails ONLY on truly
identical hashes and REPORTS the variant structure instead, because whether a
variant counts as independent confirmation is the owner's call, not a script's.
---

## KNOB LIVENESS GATE (exp_knob_liveness.py) - the claim, as a test not a comment

Owner instruction: annotate, delete nothing, but back the claim with a test because
a comment rots. Four assertions, all PASS:

| # | assertion | result |
|---|---|---|
| 1 | chop_thresh 40/58/74 identical under mode=atr_high | PASS - all sha a16f6ad995ab, n=466 |
| 2 | ext_stop_r 0.0/3.0/5.0 identical AND 1.0 differs | PASS - 1.0 -> n=348 vs 466 |
| 3 | max_positions ABSENT equivalent to 0 | PASS - sha a16f6ad995ab both |
| 4 | chop_thresh IS LIVE under mode=b2_vs_flip_chop | PASS - 40 -> n=585, 74 -> n=465 |

Assertion 4 is the one that earns the file. "Dead" was only ever true for one mode,
and under production mode `b2_vs_flip_chop` the same key swings the book from 585
trades to 465. A comment saying "chop_thresh is dead" would have been a lie waiting
for a mode flip.

### The keys stay in the registry

  chop_thresh    BP default 58.0 == the books' value, so removal is a no-op TODAY,
                 but live under production mode. Deleting it defers the breakage.
  ext_stop_r     ALL books carry it. BP default is 1.5, INSIDE the live band.
                 Deleting it does not no-op, it switches a trailing stop on.
  max_positions  absent from BP entirely; removal is safe but buys nothing.
  cooldown_bars  books pin 8, BP defaults 10, measured -126.8R. Same trap.

## MCL MATRIX (exp_mcl_matrix.py) - NET, both eras, 4 books x 8 values

The +44R was GROSS. NET of fees/slip/funding it is +37.2R on IS for long: the 36
extra trades at mcl=0 cost 101.2R of trading cost against 94.4R at mcl=3, so ~7R
came straight off the top. Cross-check: mcloff (pin mcl=0) reproduces long@mcl=0 to
the decimal in BOTH eras, which verifies the NET accounting against the registry.

### The finding that decides it: mcl=0 buys profit with pain

    book                    mcl=0 MaxCL   mcl=3 MaxCL    mcl=0 DD   mcl=3 DD
    fsent_champ_long              13          12        17.7       19.6
    fsent_champ_short             12          10        11.8        8.7
    fsent_champ_long_htf15        22          22        22.0       21.1
    fsent_champ_long_htffs        13          12        15.7       12.9

Turning the halt OFF makes the worst losing streak WORSE or equal in all four
books, and the drawdown worse in three of four. A loss-halt exists to shorten the
bad run. At mcl=0 it does not. So the extra NET is being bought with exactly the
two things the owner said matter most.

### And it does not generalise

    book                    dNET IS    dNET OOS      agree?
    fsent_champ_long         +37.20      -2.05      *** SIGN FLIP ***
    fsent_champ_short         -2.49     +46.74      *** SIGN FLIP ***
    fsent_champ_long_htf15   +34.53     +15.36      same sign
    fsent_champ_long_htffs   +52.51     +40.54      same sign

Two of four reverse direction between eras. Short is the clearest: the pin beats
mcl=0 by 2.5R on IS and loses by 46.7R on OOS. Nothing here is a stable win.

### mcl=1 is pathological on every axis

NET collapses and drawdown peaks at mcl=1 in all four books (long 308R / DD 22.3;
short 349R / 14.9; htf15 357R / 23.2; htffs 631R / 20.9). The neighbour of the
optimum being catastrophic is why the whole ladder was plotted instead of a
two-point test.

### Standout book: fsent_champ_long_htffs

Best NET/DD in BOTH eras at its pin - IS 58.9 (+757.99R, DD 12.86, PF 4.04,
MaxCL 12), OOS 29.6 (+313.35R, DD 10.59, PF 3.40, MaxCL 10). It also holds the
lowest losing streak of its own ladder at mcl=3. No other book is as good on both
eras of the risk-adjusted measure.

NOTHING PROMOTED. No champion picked, no book deleted, no config edited. The
registry is exactly as it was before this sweep.
---

## WHAT max_consecutive_losses ACTUALLY DOES (exp_mcl_mechanism.py)

Read in the shipping engine, backend/src/btc/engines/htf_ltf/unified.py:1312 and
the booking block after it:

    entry gate                        booking, once the trade closes
    ---------------                    -----------------------------------
    if halt_skip_next:                 if max_consecutive_losses > 0:
        halt_skip_next=False                if r_multiple <= 0:
        consecutive_losses = 0                  consecutive_losses += 1
        continue    <-- DROP the signal         if >= max_consecutive_losses:
                                              halt_skip_next = True
                                              consecutive_losses = 0  <-- RESET ON FIRE
                                       else:
                                           consecutive_losses = 0

Three properties, each measured:

### 1. It resets when it fires, so it can never end a run

The counter is zeroed the instant the halt fires. A losing run of length L therefore
triggers floor(L/N) halts, not one. It never stops trading; it keeps nibbling one
trade per N losses. There is no recovery condition and no wait for a win.

    book                    n(0)   runs  longest run
    fsent_champ_long         533    108        13
    fsent_champ_short        505     94        12
    fsent_champ_long_htf15   535    109        22
    fsent_champ_long_htffs   802    161        13

### 2. Roughly 40-50% of its skips are shadowed by the cooldown

`continue` drops a SIGNAL, not a trade. If cooldown_bars=8 had already blocked
that signal, the halt removes nothing. Measured on long at mcl=3: 61 firings, only
36 trades actually lost - 41% shadowed.

Direct test, holding everything else fixed:

    book                    lost @cd=8   lost @cd=0
    fsent_champ_long               36           71
    fsent_champ_short              39           77
    fsent_champ_long_htf15         35           77
    fsent_champ_long_htffs         49          118

With the cooldown off the halt is twice as effective. So about half of what mcl
appears to do on these books is really the cooldown, and mcl is shadowed by it.

### 3. THE HALT DELETES WINNERS - in every book

Walk the mcl=0 sequence, apply the engine's own rule, and price what it drops:

    book                  skipped   their NET   their WR%   kept NET
    fsent_champ_long          55       +31.0R      38.2%     +574.4R
    fsent_champ_short         58        +7.0R      20.7%     +663.0R
    fsent_champ_long_htf15    51       +17.1R      37.3%     +624.7R
    fsent_champ_long_htffs    83       +40.4R      28.9%     +928.7R

The trades it throws away are profitable in aggregate in all four books. The
mechanism is not neutral - it is working against the strategy, deleting positive
expectancy trades, and the Net difference it produces is well inside the
era-to-era sign flip already documented.

### What mcl is, stated plainly

It is a THROTTLE, not a streak breaker: "every N consecutive losses, discard one
signal", half-masked by the cooldown, discarding net-positive trades. The name
`max_consecutive_losses` implies a risk control that caps the worst run. It does
not, which is exactly why mcl=0 showed a WORSE MaxConsecL than mcl=3 in all four
books - the halt was never shortening the streak to begin with.

This is the third instance in this sweep of a NAME promising something the CODE
does not do, after `extreme pivot` and the dead `chop_thresh`. Worth treating as
a pattern: the config is the spec, and the spec is frequently wrong.

## IS htffs JUST long WITH MORE TRADES?  NO.

    long  n=497          htffs n=753          overlap 233 of 753 (30.9%)

    bucket                            n      gross R   R/trade
    shared entries                 233       +389.1     1.670
    htffs ONLY (extra entries)     520       +517.5     0.995
    long ONLY (htffs dropped)      264       +172.3     0.653

htffs is not a volume clone. It adds 520 entries long never takes at ~1.0 R/trade
AND drops 264 of long's entries - the weak ones, at 0.65 R/trade. Both operations
add value independently. Per-trade economics:

    long   +561.4 / 497 = 1.13 R/trade
    htffs  +906.6 / 753 = 1.20 R/trade

So htffs has BOTH better per-trade economics and 1.52x the volume, which is why
its NET/DD is far ahead in both eras. The volume is real but it is not the reason
htffs wins - the quality per trade is higher too.

The legitimate concern that remains is concentration, not fake edge: 753 IS trades
means 158.6R of trading cost against long's 94.4R. That is already subtracted in
every NET figure above.
---

## ARE cooldown_bars AND max_consecutive_losses REDUNDANT? (exp_cd_mcl_redundancy.py)

First, a correction to my own last message. I called the halt "broken" and "working
against the strategy." The owner is right that it is working as designed: lose
three in a row, skip the NEXT trade, take the one after. That is exactly what the
code does and exactly what was intended. The measurements stand; my verdict on
them did not.

The useful question is not whether the halt is sound in the abstract but whether
it earns its place GIVEN cooldown is already on. Both gates block entries after a
loss - one on a TIME window, one on a COUNT.

### The cooldown is the real gate, by a wide margin

cd=8 vs cd=0, holding mcl=3, NET, IS:

    book                    cd=0      cd=8       dNET      dNET%     DD 0     DD 8    DD%
    fsent_champ_long      +325.04   +466.92    +141.88      +44%   40.23    19.57    -51%
    fsent_champ_short     +408.19   +569.33    +161.14      +39%   18.49     8.65    -53%
    fsent_champ_long_htf15 +378.36  +505.24    +126.88      +34%   38.07    21.05    -45%
    fsent_champ_long_htffs +542.28   +757.99    +215.71      +40%   40.36    12.86    -68%

Cooldown alone is worth +34% to +44% of net and cuts drawdown by 45-68%. That is
the largest single-gate effect measured anywhere in this sweep.

### The cd=8 pin is confirmed, at both mcl levels

    book                    best cd @mcl=0    best cd @mcl=3
    fsent_champ_long              8                8
    fsent_champ_short             4                8
    fsent_champ_long_htf15       12                8
    fsent_champ_long_htffs        4                8

cd=8 is the argmax in all four books at the shipped mcl=3. At mcl=0 the curve is
flat from 4 to 12 on short/htf15/htffs, so those are ties rather than a better
value. The pin is right and is not sensitive to the mcl setting.

### MCL on its own does nothing

cd=0, so nothing else is blocking entries:

    book                    neither    halt alone     dNET    dNET OOS
    fsent_champ_long       +326.24      +325.04      -1.20      +8.76
    fsent_champ_short      +416.60      +408.19      -8.41      +7.04
    fsent_champ_long_htf15 +360.03      +378.36     +18.33     +21.68
    fsent_champ_long_htffs +533.38      +542.28      +8.90      -4.59

Every effect is inside +-5% of a 325-542R book, and IS and OOS disagree in sign
for three of four. Alone it is indistinguishable from noise. That is the direct
answer to "is mcl a viable gate by itself" - no.

### On top of cooldown it is redundant, but not harmless

cd=8 fixed, mcl 0 -> 3, IS:

    book                  dNET      dDD    dMaxCL
    fsent_champ_long     -37.20    +1.90       -1
    fsent_champ_short     +2.49    -3.15       -2
    fsent_champ_long_htf15 -34.53   -0.94        0
    fsent_champ_long_htffs -52.51   -2.84       -1

It costs net in three of four. It buys a small reduction in DD and losing streak
in three of four - and on long it buys a 1-trade streak reduction while making DD
WORSE. So the owner's read is correct: if cooldown is on, the second gate is
largely redundant. It is not free, but it is also not the catastrophe the gross
numbers implied.

### Per-book, because the answer is not uniform

    book                  keep mcl=3?   why
    fsent_champ_short        YES        MaxCL 12->10 and DD 11.80->8.65, best risk
                                        profile of any cell, for +2.49R
    fsent_champ_long_htffs   YES        MaxCL 13->12 and DD 15.70->12.86, costs
                                        52.51R which the best NET/DD absorbs
    fsent_champ_long_htf15   MARGINAL    DD 21.99->21.05, MaxCL unchanged, -34.53R
    fsent_champ_long         NO         DD gets WORSE 17.67->19.57 for -37.20R;
                                        only MaxCL improves, by one trade

On the owner's own priority - drawdown and losing streak first - mcl=3 earns its
place on short and htffs, is a coin-flip on htf15, and does not earn it on long.
That is a per-book decision, not a global one, and it is the one place in this
sweep where the halt is measurably doing the job its name implies.

## THE FIVE BOOKS ARE ONE FAMILY

fsent_champ_long, short, long_htf15, long_htffs, long_mcloff are separate books
and all five stay in the registry and stay runnable. Nothing is retired. They are
one family: every other book is exactly one mechanism from long - entry side,
swing chain, HTF flip entry, loss-halt off. Recorded here so nobody later reads
five green cells as five independent confirmations. It is one signal measured
four ways.
---

## D2 - IDENTITY GATE AND FULL RE-VERIFY

    exp_baseline_freeze.py --compare
      IDENTICAL - chain fingerprints and all 10 book/era cells match the freeze

    exp_theory_wording_gate.py    pass
    exp_knob_liveness.py          pass - all 4 claims hold
    exp_book_uniqueness.py        pass - no duplicates, 4 variants reported
    exp_inverse_fs.py             chain == A1 freeze

Every number in this sweep was produced against chain 83a3af3f6ebf0ffa. Nothing
in the engine, the registry or the pins was changed at any point.

The wording gate needed a real fix rather than an exemption. It failed on two
correct lines in this log that merely NAMED the incident in quotes and backticks.
The filename allowlist was the wrong instrument because it cannot tell a citation
from a claim on any given line. It now strips quoted, backticked and fenced spans
and flags only BARE PROSE - stricter in the place that matters, not looser.

## C1 - THE INVERSE CONDITION: swings whose extreme is never broken

Census on the corrected chain, 2840 swings:

    both (B2 + FLIP)  1348   47.5%
    b2_only           1028   36.2%
    flip_only          464   16.3%   <- the C1 population
    fs_only              0    0.0%
    none                 0    0.0%

A first attempt classified every swing into "both" because B1 is present on nearly
all of them; the classifier now keys on B2/FLIP presence only.

Forward move in the LEG direction, mean / median dollars:

    bucket        n      +8 bars          +24 bars         +48 bars
    both       1348    +15.3 /  -3.1     +3.9 /  -3.6    +18.2 /  -7.8
    b2_only    1028     +0.8 /  +0.4    +41.5 / +21.7    +10.5 /  -1.0
    flip_only   464    +31.6 /  +5.9    +51.4 /  +7.6    +57.4 /  +3.7

CLOSED NEGATIVE. The means look alarming - +57.4 at +48 bars for the never-broken
group versus +14.9 for the rest - and mean and median are printed together
precisely so that reads correctly. Every % that went the leg's way is ~50%. The
means are a fat tail, not a signal: the MEDIAN forward move for the never-broken
population is +3.7 dollars on a 60k instrument. There is no missed opportunity
here, and the 464 FLIP-only swings are correctly classified.

TWO CAVEATS STATED, NOT BURIED

  1. The comparison is CONFOUNDED. The two groups end differently - a B2 swing
     ends on a break of its extreme, a FLIP-only swing ends on a reversal.
     Measuring forward from two structurally different endpoints compares the
     endpoints, not the populations.
  2. A true missed-B2 counterfactual needs an ENTRY RULE for swings that never
     broke their extreme - where would it have entered? That is a strategy design
     decision, not a measurement. Until the owner picks that rule the number
     cannot be read as recoverable value.

The robust statistic resolves it either way: +3.7 median is noise.

The 464 are evenly spread - 15.5-17.1% by year, 15.0% down legs vs 17.6% up, all
source=chop. No regime or directional concentration to exploit.

## C2 - GRAVEYARD AUDIT: chop x ATR routing, re-tested on the corrected chain

One graveyard entry was closed on the PRE-CORRECTION chain (2026-10-07, IS
528 / +533.37 - old marks) and closed for a reason that could be chain-dependent:
an ERA SPLIT. But the observation UNDERNEATH it did not era-split. The entry
records the joint cell chop-HIGH + ATR-LOW as the book's best region in both eras
and surviving outlier removal. So the question is whether the CELL survives
correction - not whether to retry the routing, which stays closed.

Two bugs in the first attempt, both mine and both worth recording:

  - CHOP_HI=55 and ATR_LO=0.55 were HARD-CODED and both sat outside the data. 1h
    CHOP p90 is 25.7; 15m ATR% p90 is 0.57. The "high chop" cells were therefore
    EMPTY and the test was vacuous. A gate whose test cell cannot occur looks
    exactly like a gate whose test cell found nothing.
  - Buckets were SORTED by value before computing drawdown and losing streak. Both
    are path dependent, so sorting produced maxDD=182 and streak=254 - nonsense.
    Order is now preserved.

Thresholds derived from this book's own 497 trades (chop p50 = 10.39,
ATR p50 = 0.285):

    bucket                  n    mean    median     maxDD   maxStreak
    chop HI / atr LO      106   +1.190   -0.158      5.67         7
    chop HI / atr HI      143   +0.923   -0.100      5.08         5
    chop LO / atr LO      142   +1.524   -0.300     14.43        17
    chop LO / atr HI      106   +0.818   -0.177      9.62         8

THE RECORDED JOINT CELL DOES NOT REPRODUCE. chop-LO/atr-LO has the HIGHEST mean
(+1.524 against +1.190), so "high chop + low ATR is the best region" is not what
the corrected chain shows.

But a cleaner pattern did appear, and it is about risk rather than return:
HIGH CHOP roughly HALVES drawdown (5.1-5.7 against 9.6-14.4) and shortens the
worst losing streak two to threefold (5-7 against 8-17). ATR contributes nothing
on either axis.

NOT PROPOSED, AND OOS NOT OPENED. This is a characterisation of IS, not a filter.
The original died by era-split, so the only honest next step is a decision by the
owner on whether a chop filter is worth one OOS reveal - and if it is, exactly
one, after the fact. Nothing in unified.py changed and no mode branch was added.

## HOUSEKEEPING - LEFT AS FOUND, ON PURPOSE

Two known-dirty items are documented rather than fixed, because the owner asked
that the books be left alone and both fixes would require either editing the
registry or re-approving a shared baseline mid-run:

  - `exp_craze_patch_gate.py check` fails against a stale tracked baseline
    (aa189c5..., 125663 bytes / 2359 lines) while the engine is legitimately
    148608 bytes / 2710 lines. Re-baselining is an approval, not a fix.
  - `exp_origin_lookahead.py` flags six negative books that are not marked
    status="reference": decayC_c -40.97, decayC_u -34.11, decayE_c -1.48,
    gap_campaign3 -40.62, gap_entry_cap3 -45.48, skipwinhalt_multi_sw10 -22.14.
    Those are registry edits and were left alone deliberately.

Both are recorded here so they read as known state rather than as new failures.
---

## DECAY CENSUS - the gate that had never been switched on. 120 cells, 0 wins.

exp_decay_mode / exp_decay_thr / exp_decay_legs - the P36 decay gate at
unified.py:820. Four files in the repo NAME it. None of them sets a value.
exp_decay_mode defaults to 0 and mode 0 returns False on the first line, so this
gate has been dead code in every number this repo has ever produced.

Causality checked before use, per pipeline 4c. _decay_legs stamps each leg with
confirmed_at_time, _decay_frac filters `L[0] <= t` at the entry bar and reads
candles only to `bisect(candle_ts_ltf, t) - 1`. Nothing after the entry bar is
read. Legal rule, unlike the M2 / end_px / prevpos families.

4 modes x 3 thresholds x 2 leg-windows x 5 books = 120 cells, both eras.
Identity gate first: exp_decay_mode=0 reproduced every pinned book to the
decimal.

    cells tested .................. 120
    cells that BLOCK anything ..... 120
    cells that IMPROVE net ........ 0

Every single setting lost. And the loss is monotone in how much it removes -
on fsent_champ_long:

    mode1 thr=0.75 legs=4   n 497->378  (-119 trades)  dNET  -105.36
    mode1 thr=0.50 legs=4   n 497->237  (-260 trades)  dNET  -245.76
    mode1 thr=0.25 legs=4   n 497->114  (-383 trades)  dNET  -421.71

Worst cell overall is htffs mode4 thr=0.25 legs=4 at **-776.15R**.

### WHY THIS IS A NULL AND NOT A FLIP

The obvious suspicion is that the gate is simply inverted - the other bot's
`session`/`session_flip` pair is exactly that shape, and an inverted filter loses
while its twin wins. Two checks say no.

1. thr=1.01 blocks NOTHING on any of the four modes (n=497, identical to base).
   So the threshold is a plain monotone "block more as it falls", and the top of
   its range is a true no-op. There is no complementary mode on the other side
   of 1.0 waiting to collect what this one rejects.
2. Modes 1/5, 2/6, 3/7 and 4/8 are the natural inverse pairs. **Every mode 5-8
   cell was identical to its partner** - the inverse modes did not even appear as
   separate cells, because at thr<1 the `>=` and `<` tests partition identically
   across this data. There is no twin to run.

So this is not a gate with the sign flipped. It is a gate that identifies a
condition these books' good trades are already IN, and removing them removes the
book. 120 of 120.

### What it means

The decay signal is not a filter, it is a description of when this strategy is
already committed. Every one of the 120 cells is a way of asking "what if we
stopped trading the parts that already look weak" and the answer each time is
"less". That is worth knowing and it is the same shape as the mcl finding: a
mechanism that sounds protective, whose job the book is already doing.

Recorded rather than deleted, per pipeline section 5. Nothing promoted, no knob
added, no book or pin touched. Own directory, no overlap with the concurrent
mode-census work.
---

## MARK CONTINUATION - the one hypothesis that was not a knob fit. Result: NO.

exp_edge_decay found the signal is not decaying but ACCRUING at roughly +0.04
reward/ATR per bar for ~24 bars after a mark, with the FS entry landing near
+16 bars worth of it. That produced one testable claim:

    a mark followed by ~16 bars of continuation should be a DIFFERENT trade from
    a mark followed by immediate failure.

This mattered because it is the first condition in this whole sweep on the one
thing the FS gate throws away. Every other hypothesis conditioned on something the
engine already filters on. This one conditions on whether the swing trended or
failed - and because we enter 37 bars after the mark on median, that is PAST
information visible at the entry bar.

Causality: score = (close[i0+16] - close[i0]) / ATR(i0+16), signed by leg
direction, where i0 is the last mark before FS. The window closes strictly before
the entry bar; 532 IS swings and 294 OOS swings were skipped precisely because
their window would close at or after entry.

The score separates PERFECTLY on the raw distribution. That is the trap:

    IS    above median  n=1153  mean RA +2.422   >0 in 100.0% of swings
          below median  n=1155  mean RA -0.746   >0 in  32.3%
    OOS  above median  n= 638  mean RA +2.497   >0 in 100.0%
          below median  n= 639  mean RA -0.824   >0 in  29.4%

"100.0% of high-continuation swings moved the right way" is not a trading edge.
It is the definition of the score - it IS the forward move. The distribution test
was circular and should not have been run as a check.

The book test is the real one, and it splits by era:

    book                IS HIGH/LOW     OOS HIGH/LOW
    long            +310/+130  strong   +103/+112   FLAT
    short           +440/+136  strong   +142/ +74   holds
    long_htf15      +311/+165  strong   +112/+138   REVERSES
    long_htffs      +435/+333  strong   +155/+187   REVERSES

IS is emphatic and consistent: HIGH continuation trades better in all four books,
by a wide margin. OOS keeps it in ONE of four. Same shape as the shape result and
the volatile result - a large IS effect that does not survive.

### THE CONFOUND, checked because the numbers looked too good

If high-continuation trades simply carry a tighter stop, their R-multiple is
inflated by arithmetic and none of the IS margin is signal. On fsent_champ_long:

    bucket    median r_multiple    median risk $
    HIGH             +0.036            810.9
    LOW              -0.405            748.7

The stop geometry is NOT the explanation - HIGH trades have a slightly LARGER
risk in dollars, which makes their better R more impressive, not less. So the IS
result is not a stop-size artefact. It is real on IS and it still dies on OOS.

CLOSED NEGATIVE. Three for three now: swing shape, volatile candles, and mark
continuation all produced large consistent IS effects that reverse or vanish on
OOS. That consistency is itself the finding, and it is worth stating plainly:

    THE EDGE IN THIS BOOK FAMILY IS AN ERA EFFECT.

Every hypothesis tested against this data finds large IS gains, because IS is
where the family was fitted. The moment a hypothesis is checked on OOS, two or
three out of four cells reverse. The book's OOS numbers stay strongly positive
(the A1 freeze has all five books positive in both eras), so the family is not
fake - but its IS margin is not evidence of anything portable, and no further
IS-only hypothesis in this direction is worth running.

THAT IS THE STOPPING RULE, AND IT IS THE USEFUL OUTPUT

Phase 3 of the plan was "hypotheses only after the inventory". The inventory is
done and the hypothesis phase produced three negatives with the same signature.
The remaining untested knobs (window_floor, cap_days, trail_half) should be run
as a census with the inverse test, NOT as hypothesis sources - the same treatment
the decay gate got. That is the only version of "look for new edge" that this
data supports.

Nothing promoted, no knob added, no book or pin touched. Own directory.
---

## UNTOUCHED-KNOB CENSUS - all 7 fire. One has a mechanism, and it is not the
## one the net first suggests.

Last untouched input space. Read from the signature, every one of these was named
in the engine and swept by nothing:

    exp_window_floor_s     only ever 2_700    exp_cap_days     only ever 16
    exp_window_floor_mode  only ever "fixed"  exp_min_sl_pct   only ever 0
    exp_no_opposite        only ever 0        exp_trail_half   only 0 or 1
    exp_trail_skip_n       0..3, never swept

Firing check first, the lesson of the decay gate. **All 7 fire.** Not one is a
NULL. So this space is genuinely live, unlike the decay gate.

## exp_trail_skip_n - the first candidate that survives OOS. Mechanism found.

The knob drops the first N trailing-stop events outright
(`_trail_skip_rem -= 1; _tr_ok = False` at unified.py:1493). Naive reading of
the net: "skip 5 trail events and htffs nearly doubles".

    book              IS skip_n=5    IS pin    OOS skip_n=5   OOS pin   agrees
    long               +520.72      +466.92      +269.79      +215.32    BOTH
    short              +484.64      +569.33      +174.98      +195.01    neither
    long_htf15         +623.25      +505.24      +300.29      +254.81    BOTH
    long_htffs        +1354.16      +757.99      +337.41      +313.35    BOTH

Three of four, both eras. That is the shape that shape / volatile / continuation
all failed to produce.

### BUT THE MECHANISM IS NOT "BETTER EXITS"

Exit-reason census on htffs, which is the big winner:

    skip_n     n   trail exit   SL exit   win%   median R
        0    753          749        4    42.6%      -0.20
        2    716          425      291    45.8%      -0.23
        3    665          351      314    43.8%      -0.40
        5    617          288      329    42.5%      -1.00
        8    523          233      290    41.9%      -1.00

At skip_n=0, 749 of 753 trades exit on the TRAIL and only 4 hit the stop. At
skip_n=5 it has INVERTED: 288 trail, 329 SL. The knob is not improving exits. It
is **turning trailing stops off for the first N moves, so positions that would
have been closed early at a small profit instead ride until the stop**.

The median R tells the truth: -0.20 at the pin, -1.00 from skip_n=4 onward. Every
extra "win" bought this way costs more when it fails. Net rises because the
average winner grows, not because the median trade improves. That is a
right-tail bet, and it is the same fat-tail structure that killed the
volatile-early result earlier in this sweep.

### Why it is still interesting, and why nothing is promoted

  - short LOST at skip_n=5 (-84.69R on IS). A knob that pays on three books and
    costs on the fourth is not a family-level rule.
  - DD RISES with it on both winners: htffs 12.86 -> 26.45, htf15 21.05 -> 19.29
    is better but htffs doubles. MaxConsecL on htffs goes 12 -> 26.
  - The owner has said drawdown and losing streak matter most. This knob trades
    both away to buy net.

So: STRONG on era agreement, but it fails the owner's own stated risk priority and
is non-uniform across books. Registered as evidence, NOT promoted. The next step
if the owner wants it is a per-book value chosen on the risk constraint, not the
net argmax.

## The other six

  exp_cap_days=32   the only big loser: dIS +125.51/+121.81/+111.84 across three
                    books, dOOS -22.91/+15.74/-28.26. OOS agrees on ONE of three.
                    Textbook IS-only. The same "hold longer pays" illusion.
  exp_trail_half=1  +603.43 on htffs IS, -33.91 OOS. One book, one era. WEAK.
  exp_min_sl_pct    0.001/0.002 wins on 3 books, OOS agrees on all 3, but the
                    size is +5.96/+3.39/+2.87R. Noise-level. NOT WORTH IT.
  exp_no_opposite   nothing beats the pin anywhere. A real gate, no gain.
  exp_window_floor  16 IS candidates, OOS agrees on 11, but the deltas are
    _s / _mode    +3 to +13R. Also noise-level. Note 0 (enter immediately) gives
                    MORE trades and slightly more net than the 2_700 floor - the
                    entry-latency floor is roughly neutral, which is worth knowing
                    given exp_edge_decay measured a 37-bar median latency.

## The pattern across all four negative-plus-one cycles

shape, volatile, continuation all produced IS gains that died on OOS. skip_n
survives OOS on three books. The difference is not statistical luck - it is that
skip_n has a MECHANISM verified by an independent measurement (the exit-reason
census), while the others had only a number. That is the first evidence in this
repo that the inverse-mechanism test is the thing that separates real from
illusory, and it took four attempts to find one candidate worth the name.

Nothing promoted, no registry entry, no pin touched. Own directory.
## exp_trail_skip_n VERIFIED - 2 of 3 promote, htffs does not

Owner excluded short from the scope, then asked for a full verification before
anything is adopted. Five checks, each added because something went wrong earlier.

1. IDENTITY clean - skip_n=0 reproduces all three pins to the decimal.

2. THE CENSUS LADDER WAS A BOUNDARY ARTIFACT. The census topped out at skip_n=5
   and 5 was the best value on all three books. Extended to 32, the IS argmax is
   32 on ALL THREE, and htf15 LOSES on OOS at exactly that value. Picking on IS
   net alone would have promoted it and been wrong.

3. PICKED ON RISK, NOT NET. Highest IS net among values whose IS DD is not worse
   than the pin's:

     long    DD-safe at 3,4,5,6 -> 4   IS +530.42  OOS +260.53 HOLDS
     htf15   DD-safe at 2..6    -> 6   IS +639.84  OOS +328.54 HOLDS
     htffs   DD-safe at 2 ONLY  -> 2   IS +799.52  OOS +281.75 LOSES

   htffs has NO promotable value. Its only DD-safe setting loses on OOS, and its
   DD-safe window is one rung against long's four and htf15's five. The +2570R at
   skip_n=32 costs DD 12.86 -> 30.05 and MaxCL 12 -> 23.

5. THE PURGE TEST SETTLES SELECTOR vs RIGHT TAIL. At the pin almost everything
   exits on the trail, so purging SL trades proves nothing there. Above skip_n=4
   the SL population is large and every one exits at exactly -1.000 (median and
   p10 identical). Purging them RAISES the net on all three books
   (long +616 -> +860, htf15 +724 -> +959, htffs +1505 -> +1834). A right-tail
   bet loses exactly that way. These trades convert weak early trail exits into
   ordinary -1.000 losses while survivors go from -0.20 to +2.31 median.

   That is why two of three hold on OOS where swing shape, volatile candles and
   mark continuation all died.

RECOMMENDATION: long=4, htf15=6, htffs=none. Both winners improve IS drawdown
19.57 -> 17.99 and 21.05 -> 18.09 and cut htf15's worst streak 22 -> 13.

CAVEAT THAT TRAVELS WITH IT: OOS drawdown RISES for both (+2.2 and +3.0). The IS
drawdown gain does not carry; what carries is the losing streak and the net. If
OOS drawdown matters equally for the owner, only long at skip_n=3 is free on both
(+230.92 OOS vs +269.79 at 5).

Nothing promoted, no registry entry, no pin touched.
---

## SERIAL LADDER - the whole experiment on max_positions=1. One winner, and it
## is the knob the engine doc says IS the entire multi edge.

Owner: "we only are working on max position = unlimited .. we didn't test any
these so max position = 1 'sig' book. So if we pick a base where there are very
less filter and wanna test some hypothesis there ... because you have been working
on multi only."

Correct, and it was the most load-bearing correction in this sweep. Checking the
registry: EVERY exp_trail_skip_n result in this repo is a multi book.
fsent_sig_full and fsent_sig_trail_delay1 are serial but carry skip_n=2 and were
never swept. So the finding registered earlier today had never once been tested
where only one position can be open.

BASE - fsent_sig_sw10_short, max_positions=1, exp_fs_entry_side=short

    ON (11)  mode atr_high, atr_high_thresh 0.65, atr_low_thresh 0.35,
             chop_thresh 58.0, cooldown_bars 8, exp_partial_r 7.5, ext_stop_r 3.0,
             max_consecutive_losses 3, max_positions 1, sl_buf_atr 0.01
    OFF      exp_bias_momentum_min, exp_fs_small_swing, exp_skip_weekend,
             exp_trail_skip_n, exp_trail_half, exp_trail_delay_r, exp_mltf,
             exp_persist, exp_decay_*, exp_causal_sl, exp_ltf_no_entry,
             exp_no_opposite, exp_min_sl_pct

    pins  IS 334t / +167.14R / dd_net 17.58   OOS 208t / +118.71R / dd_net 14.39

Identity note: this lens measures n=333 against a declared 334 with net and
dd_net exact to the decimal. That one-trade gap is the same gross-versus-net lens
difference the registration gate hit on the two skip_n books, so identity passes on
the equity path and the count is not treated as a broken base.

## PHASE 1 - THE TRANSFER TEST. IT DOES NOT TRANSFER.

exp_trail_skip_n on the serial path, full ladder, both eras:

    skip_n      IS net      IS dd_net    OOS net     OOS dd_net
        0     +167.14        17.58      +118.71       14.39
        1     +166.75        17.62      +118.45       14.45
        2     +165.56        15.72      +125.64       11.75
        3     +130.99        13.88       +81.23       12.32
        4     +144.45        15.83       +99.87       15.67
        5     +136.08        18.62       +84.60       13.77
        6     +145.78        19.01       +86.80       16.59
        8      +98.15        16.31       +68.55       21.22
       12      +81.08        17.58       +77.59       13.82
       16      +94.67        20.47      +102.54       12.28
       24     +127.86        15.78       +59.67       11.01

**Every single value loses IS except the pin itself.** The DD-safe values on IS are
0, 2, 3, 4, 8, 12, 24 and the best of them IS the PIN, skip_n=0. On OOS only
skip_n=2 beats the base (+125.64 against +118.71) and that is +6.93R on a book
doing +118.71R - noise, and it sits on the one rung where 2 trades are dropped.

So the honest conclusion, and it corrects the entry I wrote into the registry two
hours ago: **the skip_n finding is a property of the MULTI book, not of the
trailing stop.** It does not generalise to the serial path. The two registered
books are correct as registered - they ARE multi books - but the finding must not
be described as a trailing-stop property. The registry descs already scope them
to their parents; this is the cross-book caveat they should carry.

## PHASE 2 - TEN KNOBS CENSUSED, EIGHT FIRE, ONE WINS

    knob                     verdict on the serial base
    exp_no_opposite          NULL - dead, changes no trade
    exp_trail_half           fires, best net = the PIN (0). Nothing.
    exp_trail_skip_n         fires, best net = the PIN (0). Nothing.
    exp_min_sl_pct           fires, best net = the PIN (0.0). Nothing.
    exp_cap_days             fires, best net = the PIN (16). Nothing.
    exp_window_floor_s       fires. +0/+900 beat the pin. SMALL.
    exp_trail_delay_r        fires, all values lose
    exp_decay_mode           fires, all values lose
    exp_persist              fires, all values lose
    exp_mltf                 fires and IS THE ONLY BIG WINNER.

exp_persist is worth naming because the engine's own header says it is
"INHERITED, NOT EARNED" - bit-identical on IS alone, -2.40R on OOS. On this
serial base it loses at every value including its own pin of 0. Confirmed dead on
the path it was inherited into.

## THE WINNER - exp_mltf=1 - and it is not a new idea, it is the engine doc

unified.py:41 states the position gate is the entire multi edge: "With the gate on,
the same config is +137.72R IS but -13.26R OOS over 230 trades. Turning it off
gives +325.78R IS / +70.15R OOS." This test reproduces that on a DIFFERENT and
much leaner base, and it is the only knob in the census that improves both eras:

                        IS net     IS dd_net   IS MaxCL   OOS net    OOS dd_net
    base (mltf=0)     +167.14       17.58        9       +118.71       14.39
    mltf=1            +448.37       12.67       10       +220.91       12.18

    +281.23R IS and +102.20R OOS, with drawdown IMPROVING in both eras
    (17.58 -> 12.67 and 14.39 -> 12.18).

Mechanism confirmed by the only measurement that can separate selection from
noise on this family - position overlap:

    IS    base  n=333  trail=333 sl=0  overlap  0%  median R -0.42
          mltf1 n=477  trail=476 sl=1  overlap 36%  median R -0.19
    OOS   base  n=208  trail=208 sl=0  overlap  0%  median R -0.36
          mltf1 n=305  trail=305 sl=0  overlap 38%  median R -0.19

36-38% of holding time now has more than one position open, which is exactly what
the knob does - and the median trade IMPROVES (-0.42 -> -0.19), so unlike
skip_n this is not a right-tail bet. It takes more trades and each is better.
Drawdown falls while volume rises 43%, which is the opposite of every other
candidate in this sweep.

This is NOT a discovery. It is the shipped engine's documented behaviour,
discovered here on the lean base the owner asked for, and it lands on the one book
that had it switched OFF. The obvious follow-up is to check how many registered
books are serial with mltf off, since this repo appears to have that combination
under-explored - but that is the owner's call, not this commit's.

Nothing promoted. No registry entry, no pin changed, no book edited.
---

## exp_mltf ON THE LEAN SERIAL BASE - full metrics, and yes it clears every bar

Owner: "exp_mtlf kaa poora mujhe metrics do win rate etc etc? and if this good for
making a book?"

    fsent_sig_sw10_short, max_positions=1, exp_mltf 0 -> 1

    metric                     IS base   IS mltf     OOS base  OOS mltf
    trades                        333       477           208       305
    trades/yr                   90.7     129.9         104.5     153.2
    GROSS R                    229.67    546.86        145.98    258.03
    cost (fee+slip+fund)       62.53     98.49         27.27     37.12
    NET R                      167.14    448.37        118.71    220.91
    NET per trade               0.502     0.940         0.571     0.724
    WIN RATE %                  34.8      41.3          36.1      40.7
    AvgWin R                     3.39      3.76          3.29      3.08
    AvgLoss R                   -0.75     -0.69         -0.76     -0.69
    Payoff                       4.51      5.43          4.35      4.50
    PROFIT FACTOR                2.41      3.82          2.45      3.08
    maxDD (net)                 17.58     12.67         14.39     12.18
    DD duration (trades)          38        18            47        24
    underwater %                86.8      78.2          83.7      78.0
    Sortino                    209.10    618.89        156.25    320.78
    Calmar                       2.59      9.64          4.12      9.07
    max losing streak               9        12            11        11
    avg hold (h)                 37.8      41.1          35.0      37.5
    trail exits                  333       476           208       305
    stop exits                     0         1             0         0

EVERY RISK AXIS IMPROVES EXCEPT ONE. Win rate +6.5 and +4.6 points, profit factor
2.41 -> 3.82 and 2.45 -> 3.08, drawdown DOWN in both eras, drawdown duration
halved in both (38 -> 18 trades, 47 -> 24), underwater time down 8.6 and 5.6
points, Sortino and Calmar roughly tripled. Net per trade rises 0.502 -> 0.940 on
IS, which is why 43% more volume does not dilute anything.

THE ONE AXIS THAT WORSENS: the IS losing streak goes 9 -> 12. OOS holds at 11.
Given the owner ranks losing streak first, this is the honest caveat and it is the
single thing standing between this and a clean sheet.

### THE OWNER'S OWN BAR - "kabhi negative nahi hona chahiye"

    half-year     base     mltf=1        |  half-year     base     mltf=1
    2023-H1     +10.40    +55.44        |  2021-H1      +23.22    +37.59
    2023-H2      +1.08    +50.82        |  2021-H2      +66.24    +82.61
    2024-H1     +53.26    +85.78        |  2022-H1      +32.19    +83.77
    2024-H2     +31.97    +61.18        |  2022-H2      -2.94    +16.94
    2025-H1      +2.71    +26.04        |
    2025-H2     +17.90    +88.92        |  negative: base 1 of 4
    2026-H1     +43.66    +71.23        |          mltf=1 0 of 4
    2026-H2      +6.16     +8.96        |
    negative: base 0 of 8 |  mltf=1 0 of 8 |

mltf=1 is the ONLY arm in the entire census that FIXES a negative half-year rather
than adding one: 2022-H2 goes -2.94 -> +16.94 on OOS. Every other knob either
left the negative in place or created new ones.

### TAIL DEPENDENCE - and this is the strongest result in the file

Removing the largest winners one at a time, as a percentage of the base:

    drop top N     OOS base    OOS mltf     kept
    top 0          118.71      220.91      186%
    top 1           91.29      193.49      212%
    top 3           65.77      167.97      255%
    top 5           46.34      147.87      319%
    top 10           9.39      104.22     1109%

The base collapses to 8% of itself when its top 10 trades are removed. mltf=1 keeps
47% of the ratio and 104.22R absolute. **Its edge is LESS dependent on the right
tail than the base's, not more.** That is the exact opposite of every candidate in
this sweep - skip_n, cap_days, trail_half all bought net from a fat tail. This one
buys it from breadth.

### VERDICT: yes, it is a book

    [PASS] positive in both eras
    [PASS] improves OOS net            +102.20
    [PASS] improves IS net             +281.23
    [PASS] no worse OOS drawdown       14.39 -> 12.18
    [PASS] no worse OOS losing streak  11 -> 11
    [PASS] ZERO negative half-years, both eras
    [PASS] clears SHORTLIST_IS_MIN 130 and SHORTLIST_OOS_MIN 50 in both eras

WITH TWO THINGS THE OWNER MUST WEIGH FIRST

1. IT IS NOT A NEW MECHANISM. unified.py:41 already documents exp_mltf as the
   entire multi edge - "With the gate on, the same config is +137.72R IS but
   -13.26R OOS over 230 trades. Turning it off gives +325.78R IS / +70.15R OOS."
   This file CONFIRMS that on a lean serial base. A book built on it repackages
   documented shipping behaviour rather than discovering anything, and naming it a
   champion would overstate what was learned.

2. THE IS LOSING STREAK WORSENS 9 -> 12. Everything else in the risk set improves.
   If the streak matters as much as the drawdown, that one cell is the argument
   against, and it should be looked at trade by trade before adoption rather than
   averaged away by a Calmar of 9.64.

Nothing promoted. No registry entry, no pin changed.