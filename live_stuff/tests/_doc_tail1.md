## 10. Independent verification (2026-09-19, second lane)

An independent verification pass was run by a second lane with its own test
script (`test_verify_wage.py`, since DELETED - see §12 rule 6) importing the
same `build_module()` from `test_experiments_craze.py`. Identity gate passed
(flags-off == shipped, n=351, exact R-list). The script itself is no longer on
disk; every number below was cross-checked against `_exp40c_out.txt` Phase C
and matches to the decimal - which is only possible with the same fine-fill
engine, the same identity-gated base case, and the same wage gate.

### 10.1 ext_stop verification - all 6 cells MATCH (fine NET, funding-inclusive)

| Config | ext | exp40c fine (§5.2) | Independent rerun | Status |
|---|---|---|---|---|
| lb30 w0 | 1.5 | 349t NET +196.3 | 349t NET +196.3 | MATCH |
| lb30 w0 | 2.5 | 377t NET +231.1 | 377t NET +231.1 | MATCH |
| A4 w0 | 1.5 | 359t NET +203.3 | 359t NET +203.3 | MATCH |
| A4 w0 | 2.5 | 390t NET +141.3 | 390t NET +141.3 | MATCH |
| OPT-cd10 w0 | 1.5 | 453t NET +259.4 | 453t NET +259.4 | MATCH |
| OPT-cd10 w0 | 2.5 | 512t NET +291.4 | 512t NET +291.4 | MATCH |

Both sides of every comparison are FINE (1m-fill) numbers - the rerun did use
precise 1m fills and the base case. (A bare-15m rerun cannot reproduce
1m-re-timed counts plus funding-inclusive NET to the decimal.)

### 10.2 Wage gate verification - all 5 cells MATCH (fine vs fine)

Comparison correction: an earlier draft of this table compared COARSE claimed
counts against FINE verified runs and reported "off by 1 trade". That was an
apples-to-oranges label - fine counts differ from coarse counts by design
(1m exit re-timing shifts busy/cooldown chains, §4.1). The correct comparison,
fine claimed vs fine verified:

| Config | exp40c fine (§5.2) | Independent rerun | Status |
|---|---|---|---|
| lb30 w24 ext1.5 | 265t NET +185.0 | 265t NET +185.0 | MATCH |
| lb30 w24 ext2.0 | 293t NET +197.2 | 293t NET +197.2 | MATCH |
| lb30 w24 ext2.5 | 303t NET +179.1 | 303t NET +179.1 | MATCH |
| lb30 w0 ext1.5 | 349t NET +196.3 | 349t NET +196.3 | MATCH |
| lb30 w0 ext2.5 | 377t NET +231.1 | 377t NET +231.1 | MATCH |

The three w24 rows also match the user's own quoted fine table (197.2 / 179.1),
which together with §4.2's coarse matrix makes the external validation
4/4 coarse + 4/4 fine on the final gate.

### 10.3 Deleted-harness N5 rows - non-authoritative (the honest version)

The original Exp40/41 harness was deleted after its run and its exact wage-age
convention is UNRECOVERABLE. Do not guess it and do not describe it - a first
draft here guessed "entry_ts - window_start with no raw-s correction", which is
identical to the current gate's formula and therefore cannot explain a
difference. That guess was wrong and has been removed.

What is known empirically (full audit trail in §4.3):
* 13+ candidate conventions were tested (raw-s, +2700/+3600 shifts,
  closed-candle, canonical flip-first parent, dir-blind, leg anchors, post-hoc
  ledger partitions). NONE reproduces the N5 rows (lb30+w24 275t/+224.5,
  lb14+w24 281t/+201.9, A4+w24 266t/+228.6).
* The current gate reproduces the user's OWN records exactly wherever they
  overlap: coarse matrix 4/4 (§4.2) and fine table 4/4 (§4.3).
* The N5 lb30 delta is large (rebuilt 265t/+185.0 vs claimed 275t/+224.5 =
  -39.5R) while the A4 delta is small (261t/+223.1 vs 266t/+228.6 = -5.5R).
  No tested convention explains the lb30 gap.

Therefore: N5 rows are NON-AUTHORITATIVE - not proven fraudulent, but
unreproducible from any code we can run, and contradicted by the only external
authority available (the user's own numbers). Never cite them as reference
values; the validated rebuild's output is the reference.

**Material consequence (read this):** the N5 message claimed "lb30+w24 =
+224.5, w24 works on all 3 bases (+28.2 on lb30)". Under the validated gate,
lb30-w24-ext1.5 is **+185.0 NET = w24 HURTS by -11.3R on that lane** (base
+196.3). w24 remains positive on A4 (+223.1 vs +203.3) and strongly positive on
OPT-cd10 (+337.7 vs +259.4). The corrected statement is "w24 is
base-dependent", not "w24 works on all bases".

### 10.4 Gate audit - no B3-style inflation

The ext_stop gate evaluates at the signal bar close (pre-fill), using the HTF
window's entry_price and risk - both closed-1h-candle values, knowable at
decision time. No forward-looking data enters the gate. The wage gate uses
`bar_ts - s` where `s` is the window's 1h entry-bar timestamp (closed candle)
- also causal. Both gates are ENTRY-only: they vote dead/alive at the signal
bar; SL/trail/exit logic never changes. No inflation bug found.

