# FINALISATION CHECKLIST

Everything between "research is closed" and "one book is live". Written
2026-10-16 because the owner asked for a checklist and said he will otherwise
forget. Ordered so that each item unblocks the next.

Legend: **[x]** done · **[~]** in progress · **[ ]** open · **[!]** needs an owner decision

---

## A. Owner decisions — these are yours, nothing else moves until they are made

- [x] **A1. Opposite-direction lock ON for every book.**
      Not for the top two only. The exposure argument is not strategy-specific:
      a long and a short on one symbol nets to roughly zero price exposure while
      paying two lots of fees and holding margin twice.
      *Measured on the corrected engine, 54 books / 108 book-eras: 1.36% of
      35,078 trades refused, net better on 43 book-eras and worse on 30, sum of
      all changes +266.91R, drawdown better on 19 and worse on 6.*

- [ ] **A2. Which book goes forward — 107 or 110?**
      Forward testing decides, not this document. Both are carried until the
      window closes. Minimum 50 trades or six months, whichever is later.

- [!] **A3. The loss cap: on or off?**
      This is a capital decision, not a performance one.
      - **On** (the registered default, `max_consecutive_losses=3`): costs 4–5%
        of trades; worst rolling-50 window goes from −20R to −5.85R.
      - **Off**: only if the capital is deep enough to sit through the drawdown
        without acting on it.
      Note 107 already ships with the cap at 0, so "off" is 107's current
      behaviour and "on" would be the change.

- [ ] **A4. Minimum sample, or stop early?**
      The proposed rule is 50 trades or six months. Confirm, or set another.

---

## B. Blocking — the engine default changed, everything downstream must be re-derived

- [x] **B1. Re-derive all 54 book pins under `exp_no_opposite=1`.**
      Done. The default flip moves every trade list:
      107 goes 535/+539.77 → 525/+538.40, 110 goes 412/+639.84 → 395/+644.04.

- [x] **B2. Re-run the guards.** All three pass:
      - [x] `exp_live_vs_pins.py` — live engine vs registry pins
      - [x] `exp_dropdown_check.py` — dropdown → version allowlist → dispatch
      - [x] `exp_desc_pin_audit.py` — hand-written descriptions vs pins
            (13 stale descriptions corrected on the way through)

- [ ] **B3. Rebuild `_results.json`.**
      Its 26-book metrics were computed under the old default and are now wrong.
      This is the source for the results screen and for the top-five scorecard.

- [ ] **B4. Update the two docs written today.**
      - [ ] `LIVE_CONFIGURATION.md` — the lock is now default ON and reaches
            live for free; the "recommended ON, needs re-measuring" hedge is stale.
      - [ ] `FORWARD_TESTING_CONTRACT.md` — note that the lock is live behaviour
            in both arms of the forward test.

---

## C. Never measured — and it decides whether a backtest R equals a live R

- [ ] **C1. Stop-fill slippage.**
      Backtest fills a stop at the stop price, or at the bar open if the bar
      gapped through. The exchange fills at market. Nothing in this repo has ever
      measured how often a 15m low goes past the stop. Until it does, every
      figure here is a backtest figure and not a live one.
      Cheap to measure and it belongs before money moves.

- [ ] **C2. 1h marks verified against the owner's chart.**
      Still outstanding from the corrected-mark sweep. The window-floor and
      cap-days work assumed these marks are right.

---

## D. Forward testing — the part that must not be burned

- [ ] **D1. Extend the forward downloader.**
      Forward files stop at 2026-10-09. Today is 2026-10-16, so roughly 33 days
      are missing and the six-month clock is already running.

- [ ] **D2. Score, do not tune.**
      If anything in the forward window suggests a change, the window is spent
      and a new one starts. Both candidates stay as-is.

- [ ] **D3. Decide at close** → feed into A2.

---

## E. Live work — ON HOLD by owner instruction, do not start

Parked deliberately. Listed so it is not lost, in the order it must be done.

- [ ] **E1. The fresh engine params module.** The one `2ada7a6` removed on the
      grounds that "the live bot gets a fresh module when an engine is actually
      chosen for it". Choosing the book is what unblocks this.
- [ ] **E2. Six extra engine arguments for 107, seven for 110.** The live call
      forwards only seven knobs today; every registered book also needs
      `pivot_rule`, `exp_persist`, `exp_fs_entry_side`, `max_positions`,
      `exp_partial_r`.
- [ ] **E3. Swing length from the book's `swing` key, not from `SWING`.** Both
      candidates are `htf15` (min_bars 15) and the live bot hardcodes
      `min_bars_1h = 20`. This one is easy to miss and would silently run the
      wrong swing chain — swing length is the most load-bearing constant in the
      family.
- [ ] **E4. `exp_trail_skip_n` in `_trail_sl()` — 110 only.** Zero references in
      the live bot today; it walks every trailing event from the entry and must
      learn to skip the first six.
- [x] **E5. Opposite-direction lock reaches live for free.** Verified: the live
      engine default is now 1 and `live_loop.py` does not pass the knob
      explicitly, so it inherits it with no wiring at all.

---

## F. Deferred — the owner's call, not blocked on anything above

- [ ] **F1. Recovery columns on the results screen.** The fields exist in
      `_results.json` (longest underwater stretch, time-to-recover, fraction of
      time green) and are not displayed. Same for the pin-sum versus all-factor
      selection policy in the exporter.
- [ ] **F2. 30m/1h ladder confirmation for 110's `exp_trail_skip_n`.** The
      timeframe-family grid has never run since 2026-10-10 (the harness was
      dropping every cell), so 110's strongest structural knob is confirmed only
      on 15m/1h.

---

## G. Standing rules for the rest of this work

1. **A2 is not decided by a good number appearing.** If 110's 3-trade forward
   result happens to be positive, that is not evidence. The window closes on
   sample size, not on a favourable reading.
2. **The lock is default ON and is not a variable.** If a future book needs it
   off to reproduce a historical list, set `exp_no_opposite: 0` on that book
   explicitly and say why. Do not flip the engine default back.
3. **Anything measured before 2026-10-08 is stale** — it predates the causal-stop
   fix and the mark corrections.
4. **The 2021–2022 era is spent.** It has been used to filter, so it is not a
   holdout and cannot arbitrate anything.