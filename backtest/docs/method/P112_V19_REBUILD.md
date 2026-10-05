# P112 — v19 rebuilt clean, and the pin is proven by a real import

**Date:** 2026-09-30 · **Commit:** `7077046` · **Branch:** `agents/champion-reality-audit`

This answers the four objections raised in *method/reality of champion followup.md* (L209–L214).
All four were correct at the time they were written. All four are now closed.

---

## 1. The proof harnesses could not be re-run — CLOSED

Followup L209 was right: `exp_v19_proof.py` and `exp_v19_oos.py` both read
`backtest/tests/_v19_src.py`, which does not exist and never was committed.

Both now read the committed engine:

    backend/src/btc/engines/htf_ltf/v19_champion.py

Anyone can now re-run them and get the same numbers.

## 2. The docstring is corrupted — CLOSED

Followup L212 was right: line 17 contained six consecutive quote characters,
`""""""v11_conditional_htf...`. The v19 header docstring had been prepended
without closing.

Worth recording *how* this was fixed, because the obvious fix is wrong.
Closing the header on its own line makes the file compile, but it turns v18's
docstring into a bare string statement, and `from __future__ import annotations`
then stops being the first statement:

    SyntaxError: from __future__ imports must occur at the beginning of the file

The header is therefore an ASCII comment block, not a docstring. v18's docstring
stays the module docstring and the future import stays first.

## 3. Encoding damage — CLOSED (partly)

Followup L213 was right that the file showed mojibake. The root cause was
worse than "written by a mangling tool": **v18 already contained mojibake**, and
my copy step read v18 as utf-8 and wrote it back, re-encoding those bytes a
second time. v18 shows the damage once, my copy showed it twice over.

v19 is now built from v18 as latin-1 and written with `newline=""`. Every byte
maps to one codepoint and back. Verified by byte comparison: the first byte
that differs between v18 and v19 is the first of our four edits.

Residual, stated plainly: **the inherited mojibake is still there.** It is a
property of v18, not of v19. Cleaning it is a separate change and was not made
here, because touching those bytes would change v18's own content.

## 4. "The pin is currently unproven" — CLOSED

Not asserted. Re-derived by importing the committed file from disk:

    py_compile              COMPILE OK
    IS   n=500  net=+325.78R  PF 2.384
    OOS  n=279  net=+70.15R   PF 1.591

---

## Audit of the 500 trades

`backtest/tests/exp_v19_audit.py` — checks the engine, not the summary.

| Check | Result |
|---|---|
| `exit_idx` after `entry_idx`, all trades | PASS |
| no NaN, no exit past the final candle | PASS |
| `entry_price == close` of the signal bar | PASS, 0 exceptions |
| `close[i] == open[i+1]` at every entry | PASS, 0 exceptions |
| R recomputed from entry/SL/exit | PASS, max drift 0.00175 |
| all 187 SL exits exactly `-1.0R` | PASS |
| no duplicate trades | PASS, 0 |
| max concurrent positions | 6 |

**No defect found in v19's trade construction.**

The 0.00175 R drift is display rounding, not a modelling error: `r_multiple` is
stored to 1–3 decimals, and zero trades drift beyond the 0.005 a 2-decimal
rounding would allow.

Two things worth recording because they look alarming and are not:

- **163 of 313 trail exits (52.1%) closed negative.** That is expected. The
  trail follows price back toward entry, so a stopped-out winner can close
  below zero. None is worse than `-1R`, which is the real invariant.
- **Entry price is not `c15[entry_idx]["open"]`.** It is the close of that bar,
  which equals the open of the next. This is the causal rule already proven in
  P109, not a fill bug.

## Is v19 just v18 with a new name?

No. Same parameters, only the code differs:

| Engine | n | net | PF | max concurrent |
|---|---|---|---|---|
| v18 original | 395 | +137.72R | 1.859 | 1 |
| v19 champion | 500 | +325.78R | 2.384 | 6 |

The difference is the removed one-position gate, `busy_until` never being
armed, and `PERSIST=7` regime hysteresis.

Note the caution this earns: the harness still hard-codes `exp_mltf` and
`exp_persist` and still carries roughly a hundred other research flags. v19 is
the champion **with the harness in it**. Freezing production parameters from it
is still open work, and is deliberately not started.

---

## Still open

- Forward evidence remains thin: 2 trades over 12.5 days.
- `method/THE_CHAMPION_HANDOFF.md` predates P102 and P106–P109 and is stale.
- The `mojibake` inherited from v18 is cosmetic and untouched.

## Reproduce

    python -m py_compile backend/src/btc/engines/htf_ltf/v19_champion.py
    cd backtest/tests
    python exp_v19_import.py     # IS 500 / +325.78R
    python exp_v19_oos.py        # OOS 279 / +70.15R
    python exp_v19_audit.py      # 12 structural checks
    python exp_v18v19.py         # v18 vs v19, same params