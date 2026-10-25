# Wait-for-FS gate: /results repin, rule proof, gate ON/OFF sweep, paper restart

## STATUS: DONE (2026-10-22)

Scope was narrowed by the owner to the **36 /results books only** - the set in
`backtest/tests/_results.json`. Everything below is what actually ran.

| check | result |
|---|---|
| `exp_gate_sweep.py` - 36 books, gate ON and OFF, both eras | 846s, 0 errors |
| **the rule**: fall-through entries before the previous swing's FS | **0** across all 36 books, both eras |
| registry pins == sweep `new_pins` | 36/36 exact |
| ungated arm == the committed pre-gate pins | 36/36 exact, so ON-OFF is the gate and nothing else |
| `exp_desc_pin_audit.py` | RESULT: PASS (all six checks) |
| `exp_pinverify.py` (36 books) | 0 mismatches - "every pin re-derived from the engine matches" |
| `test_vendored_parity.py` | VENDORED PARITY OK (520 / +508.37 / 27.23) |
| `exp_live_vs_pins.py` | 6 of 6 MATCH |
| `test_regime_buckets.py` | ALL_REGIME_TESTS_OK |
| `test_experiments_craze.py` | identity gate IDENTICAL=True, suite green (113s) |
| paper book | running on the gated vendored engine, log at `live_stuff/_logs/paper_run5.log` |

**The gate's cost, measured**: book 107 goes 525t/+538.40R -> **520t/+508.37R** in
sample and 295t/+272.92R -> **290t/+220.71R** out of sample. The pre-FS entries
were worth +36.56R IS and +50.19R OOS; the chain that replaced them was worth
~+7.8R / ~+4.5R.

**Does the rule help any book? No.** Four books improve in sample
(`fsent_champ_long_mode_union` +118.04R, `fsent_champ_trailhalf` +6.42R,
`fsent_champ_long_mode_fd` +3.96R, `fsent_champ_long_mode_atr_low` +3.10R) and
**every one of them is worse out of sample**. `fsent_both_trail_half` is
byte-identical ON and OFF - it sets no `exp_fs_entry_side`, so it is the control
that proves the gate is inert outside the fs path. Full tables:
`backtest/experiments/gate_sweep.md`.

**Two conventions fixed along the way** (both pre-existing, both exposed by the gate):
- `exp_pinverify.py` compared the pin's `n` (CLOSED trades, the registry's
  documented lens) against the RAW trade count. They agreed only by accident,
  while every book happened to end its era on a closed trade. The gate moved the
  last trade of ten books onto an open one and the accident stopped holding.
  It now compares closed to closed.
- `test_experiments_craze.py` compared the patched engine against a FROZEN
  archive (`v18_streak_halt`) that no longer ships - `v18` was removed from
  `BTC_VERSIONS`. `run_experiment.py:66-81` had already made the same
  correction and written down why; the craze file never got it.

---

# Original plan (kept for the record)


## 0. Corrections to the previous version of this plan (read first)

Two facts I got wrong last time, both because I counted the family modules instead of the
registry:

- **"207 pinned books" is wrong.** 207 is the number of `"pins": {` blocks *in the six family
  modules*, which includes every retired book. The **live** registry holds **~94 books**
  (248 module entries − 154 retired keys; the exact number is printed by the script in Task 1).
  `exp_repin_all.py` iterates `EXPERIMENTS` **after** the prune, so it already only touches
  live books. No re-run of retired books is needed or possible through the registry.
- **"re-run all 207" is the wrong instruction.** The sweep is the live books with pins. The
  retired ones stay where they are (`registry/retired.py::archived()`), and their pins stay
  as they were — they are not books anymore.

## 1. Where all the books are

| what | where | count |
|---|---|---|
| book definitions | `backtest/tests/registry/{trail,sweep,signal,risk,d3,kingsweep}.py` | 248 entries |
| retired keys (dropped from `EXPERIMENTS` at `registry/__init__.py:41-52`) | `backtest/tests/registry/retired.py` | 154 (85 on 2026-10-08 + 69 re-retired 2026-10-14) |
| **live books** | `experiment_registry.EXPERIMENTS` after the prune | **~94** |
| live books with pins (what the sweep measures) | `pins` is a dict with `n` | printed by Task 1 |
| the 36 `/results` books | the live `fsent*` books with pins — selected by `exp_results_export.py:148-178` | 36 |
| books the gate can touch | `params.exp_fs_entry_side` set | **38** (36 pinned + 2 graveyard `fsent_dirmatch_long/short`, `pins: None`) |
| books the gate can NOT touch | everything else — they run the "decisive" path, which already had the C13a pre-FS filter since 2026-09-11 | ~169 pinned |
| retired books, still runnable | `registry/retired.py::archived()` → `backtest/tests/_archive_list.{md,json}` (last dump 2026-10-08, **stale** — the 69 re-retired are not in it) | 154 |

Module entry counts: trail 14, sweep 53, signal 43, risk 40, d3 56, kingsweep 42.

**The registry is a package** (`backtest/tests/registry/`), merged by
`registry/__init__.py`: `trail, sweep, signal, risk, d3, kingsweep`, then the retired keys are
deleted, then `ALIASES` is derived. `exp_apply_repin.py` resolves shadowed duplicate
definitions by comparing against the merged dict, so a book defined in two modules is rewritten
once.

## 2. The rule, and exactly where it was violated

**The rule:** no entry may be taken before the **previous** swing has printed its FS.

Three entry paths exist:

| path | when | pre-FS safe? |
|---|---|---|
| **FS side** of a directional book (`exp_fs_entry_side`) | at the swing's **own** FS print | **yes, by construction** — you are right, this is safe and stays safe |
| **fall-through side** of a directional book | at the first B2/FLIP/DECISIVE mark | **this was the hole** |
| non-fs books ("decisive") | at the first B2/FLIP mark | already gated since 2026-09-11 (C13a) |

**The code hole:** `backend/src/btc/btc_engine.py`, `_collect_signals`, the `if not _use_fs:`
block. Commit `539935c` (2026-10-04, "DIRECTIONAL FS ENTRY") added `entry_break="fs_long" /
"fs_short"` whose fall-through sub-loop re-implemented first-B2/FLIP collection with **no
pre-FS check**, no origin-stop guard, and an early return past the normal loop's C13a filter.
From that date, every fall-through entry was taken on an **undeclared** swing. The normal
loop's C13a filter (`:442-448`) was bypassed entirely for those books.

**The reach, precisely:** the gate's fall-through branch is only reachable from the **LTF
leg** of a book with `exp_fs_entry_side` set:
- `exp_fs_entry_side="long"` → the **short** side enters on breaks → gated (this is why
  "shorts have traded undeclared swings since Oct 4").
- `exp_fs_entry_side="short"` → the **long** side enters on breaks → gated.
- The HTF leg can only be handed `"fs_both"` (`unified.py:780-782`), and `"fs_both"` makes
  `_use_fs` true for every swing → **no fall-through** → the HTF leg is not reachable by the
  gate. It does not need to be.

**The limit of the rule, stated so nobody re-reads it as a bug:** a fall-through entry still
happens on a swing that has **not printed its own FS**. That is not a violation of the rule
and it is not causally avoidable — the swing's extreme is not final until its FS prints, and
that FS is *after* the entry bar (established 2026-10-03, `bf942bf`/`8c1c1bc`). "Wait for the
previous swing's FS" is the maximum causally satisfiable form of the rule.

**Trade-level violations:** for book 107 alone the pre-gate run had **51 IS** and **48 OOS**
pre-FS entries. Across the 38 fs-entry books the count is not yet measured — Task 1 produces
the per-book violation list.

## 3. What the gate cost on book 107 (measured)

| | IS | OOS |
|---|---|---|
| pre-gate (registry pins, net lens) | 525t / +538.40R / DD 28.38 | 295t / +272.92R / DD 11.05 |
| post-gate | **520t / +508.37R / DD 27.23** | **290t / +220.71R / DD 9.61** |
| coarse-basis A/B (`Temp\opencode\repin_ab_gate.log`) | 526 / +537.13 → 522 / +508.33 | 295 / +273.52 → 291 / +227.83 |

The dropped pre-FS entries were worth **+36.56R IS / +50.19R OOS** as a group; the chain
shift brought in 47 IS / 44 OOS new trades worth only ~+7.8R / ~+4.5R. Net cost:
**-28.8R IS, -45.7R OOS** (coarse) / **-30.03R IS, -52.21R OOS** (fine).

Blast radius over the 36 repinned books (registry diff): 35 moved, `fsent_both_trail_half`
unchanged (238 / +35.73 — it has no `exp_fs_entry_side`, so it is the control). Worst:
`fsent_champ_short_session` 501 / +582.58 → 423 / +313.00 (**-269.58R**), `fsent_sig_multi`
-238.55R, `fsent_champ_short` -95.70R, `fsent_sig_full` -78.41R. **OOS is hurt more than IS
on most books** (e.g. `fsent_champ_long_mode_atr_low` OOS 187.96 → 94.46). That is the
honest headline of this change.

## 4. The one sweep that answers all four questions

**New script `backtest/experiments/exp_gate_sweep.py`.** It reuses the existing, proven lens
(`exp_repin_all.py::_era_stats`, `_dd`, `run_experiment.net_r`, `get_swings`, `get_data`,
`build_family_module`) so the numbers are produced by exactly the code path that produced the
current pins — do **not** re-implement the lens.

For every **live** book with pins, in both eras:

1. **gate ON** → the stats that become the new pins. Emit them in the exact 13-field
   `new_pins` shape `exp_apply_repin.py` and `exp_fix_descs.py` already read
   (`n, net, dd_net, wr_net, gross_win, oos_n, oos_net, oos_dd_net, oos_wr_net,
   oos_gross_win, n_all, net_all, dd_net_all`).
2. **violation check (ON)** → for every trade, assert
   `trade["entry_idx"] >= swings[trade["swing_no"] - 1]["confirmed_at_idx"]`,
   where `swings` is the LTF chain `get_swings(data, "sw15")` (the same chain the trades
   index into; `entry_idx` and `confirmed_at_idx` are both indices into the 15m `c15` rows).
   **Violations must be 0.** This is the proof the user asked for — measured, not argued.
   Skip a trade whose swing has no predecessor (first swing of the chain).
   Also record the margin distribution in bars: how many entries land on the exact prev-FS
   bar vs later. That is the price of the patience, in bars.
3. **gate OFF** → same stats, plus the list of trades that violate the rule. Run this only
   for the books with `exp_fs_entry_side` (the gate cannot exist on the others).
   Implementation: monkeypatch, do not touch the shipping path —
   ```python
   import src.btc.btc_engine as be
   _orig = be._collect_signals
   def _off(*a, **kw):
       kw["filter_pre_fs"] = False
       return _orig(*a, **kw)
   be._collect_signals = _off
   ```
   This works because `unified.py:746` imports `_collect_signals` **inside the function**, so
   the patched attribute is picked up at call time. The HTF leg is unaffected either way
   (it only ever gets `"fs_both"`, which has no fall-through).
4. **spot-check that the gate is inert elsewhere**: for 3 books with no
   `exp_fs_entry_side`, assert the ON and OFF trade lists are byte-identical.

Outputs:

| file | content |
|---|---|
| `backtest/experiments/repin_all.json` | `{"measured": {...}, "new_pins": {...}}` — the same file the existing writer/desc-fixer read. The pre-gate one is first moved to `repin_all_pregate_20261019.json` as the diff baseline. |
| `backtest/experiments/gate_sweep.json` | per book: ON stats, OFF stats, delta, violation counts + the violating trades (book, era, entry_ts, entry_idx, swing_no, prev swing confirmed_at, side, r_multiple) |
| `backtest/experiments/gate_sweep.md` | three tables: **(a) the book inventory** — every live book: name, family module + line, pinned?, fs-entry?, pre-gate pins, post-gate pins, delta; **(b) the gate ON/OFF table** — which books the gate **helps** and which it **hurts**; **(c) the violation table** — per book, how many pre-FS entries the gate removed, and what they were worth |

Resumability: write after every book (same pattern as `exp_repin_all.py`). **Delete
`repin_all.json` before starting** — its resume path is broken (it loads the whole old file
as `done`, so `name in done` is never true and the file re-nests itself one level deeper per
run; the committed file already carries three nested `new_pins` keys).

### The four questions this answers

| question | answer source |
|---|---|
| "find all the books, where are they" | table (a) of `gate_sweep.md` |
| "which books get better with the no-pre-FS rule" | table (b) — gate ON vs OFF, both eras |
| "where does it violate this rule" | table (c) + the per-trade violation list, with the gate OFF |
| "are we sure nothing enters before the previous swing's FS" | the ON-run violation count (**must be 0** for every book) |

## 5. Ordered tasks

> Shell note: this session's permission rules block `python` and `git stash`. The sweep must
> run in a shell where `python` is allowed. `git stash push/pop` is also blocked — do not
> attempt the stash-based bisect.

### Task 1 — the sweep (background, long-running)

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\experiments
Move-Item repin_all.json repin_all_pregate_20261019.json   # MUST
python -u exp_gate_sweep.py
```

Print at the start: live book count, live books with pins, fs-entry count. **Report those
numbers to the user** — they answer "90+" with the exact figure.

### Task 2 — read the report, then write the pins

Read `gate_sweep.md` tables (a) and (b) and report:
- the inventory (which books moved, which did not, and why),
- **the books the gate helps** — if any book improves in both eras, that is a candidate to
  raise, because book 107 got worse and the rule may not be a universal win.

Then, only if the moved set is exactly the 38 fs-entry books (36 pinned + the 2 with no pins),
write the pins:

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\experiments
python exp_apply_repin.py            # DRY RUN: read the sample block it prints
python exp_apply_repin.py --apply
```

- It handles all six modules, resolves shadowed duplicates against the merged registry, and
  preserves existing `pins_legacy` blocks (it will not mint a second one).
- **Gate the write on the report**: if any book outside the fs-entry set moved, stop and
  diagnose — that would mean the gate leaked into the "decisive" path.
- After `--apply`, read the registry back and assert every written book's pins equal
  `repin_all.json["new_pins"][book]` exactly.
- Note: `signal.py` already carries the 36 gate pins from the previous session;
  `exp_apply_repin.py` rewrites them in its own canonical formatting. That is expected.

### Task 3 — refresh the prose measured claims

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\experiments
# 1. edit ANCHOR (exp_fix_descs.py:33)
#      OLD: "as of 2026-10-15 (exp_repin_all.py, net lens)"
#      NEW: "as of 2026-10-22 (exp_repin_all.py, net lens, wait-for-FS gate)"
# 2. add a step that REPLACES the old anchor with the new one before the
#    "add anchor if missing" step, or descs end up carrying two anchors.
python exp_fix_descs.py            # DRY RUN
python exp_fix_descs.py --apply
python exp_desc_pin_audit.py        # MUST print RESULT: PASS
```

`exp_desc_pin_audit.py` check E is the machine check that every
`IS/OOS <n>t / <±>R [/ DD <x>R]` claim in a desc matches that book's pins. Comparative prose
(parent deltas, permutation p-values, significance) is **not** re-derived — those are
analysis decisions, and the new anchor is what tells the reader the numbers moved.

### Task 4 — verification chain (all must pass)

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\tests
python exp_pinverify.py                     # every live pinned book reproduces (TOL 0.5)
python exp_results_export.py                # regenerates backtest/tests/_results.json  <-- REQUIRED
python C:\Users\Pravin\AppData\Local\Temp\opencode\test_vendored_parity.py   # 520 / +508.37 / 27.23
python C:\Users\Pravin\AppData\Local\Temp\opencode\test_regime_buckets.py    # ALL_REGIME_TESTS_OK
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\experiments
python exp_live_vs_pins.py                  # 6 of 6 books reproduce on the LIVE engine
```

- `exp_results_export.py` is **not optional**: `/results` is served from the committed
  artifact `backtest/tests/_results.json` (via `backend/src/btc/btc_results_routes.py` →
  `frontend/src/components/ResultsPanel.tsx`). It was never regenerated after the previous
  session's repin — the page would show pre-gate charts against new pins. This is a known gap.
- `exp_live_vs_pins.py` is the dot-to-dot parity check (live engine vs registry pin for the
  six multi books). It must still say 6 of 6.

### Task 5 — the craze harness (one line, precedent already in the repo)

`backtest/tests/test_experiments_craze.py` fails its own anchor (311t/+99.7R vs the
340/225.3 it asserts). It is **pre-existing and provably unrelated to the gate**:

- Its "shipped" baseline is `src.btc.engines.htf_ltf.v18_streak_halt` — a **frozen archive**
  (`_archive/_v18_real.py`). `v18` was removed from `BTC_VERSIONS` (`btc_routes.py:111`), so
  that engine does not ship and is not dispatchable.
- It calls `_collect_signals(swings_ltf, "decisive", ...)` — the "decisive" path, never the
  `fs_` branch. The gate cannot reach it, on either side of the comparison.
- Measured: `craze_gate2.log` and `craze_nogate2.log` both report shipped = 311t / +99.7R
  while the patched build reports 369t / +207.55R. The divergence is live engine vs dead
  archive.
- **The repo already fixed this once, elsewhere**: `run_experiment.py:66-81` documents that
  the identity gate "used to import v18_streak_halt here, which made the gate diff two
  different books… It reported DIVERGED no matter what" and now does
  `import src.btc.engines.htf_ltf.unified as shipped_mod`. The craze file was never given the
  same fix.

**Fix**: change the craze file's `shipped_mod` import to `src.btc.engines.htf_ltf.unified`
(same one-line change `run_experiment.py` already made), re-anchor the assert to the measured
value, and fix the module docstring (it still says it loads `v18_streak_halt.py`; it has
loaded `unified.py` since `00191fd`).

- If the identity gate then passes → the suite is green and meaningful.
- If it still fails → the patch set is genuinely non-inert (the 2026-10-09 "OOS gap" from
  commit `00191fd`, whose own message says *"This is NOT DONE"*). Then **do not weaken the
  gate**: record it as a pre-existing research-harness defect, keep the anchor honest, let
  the suite fail loudly, and do not let it block the gate. The gate change does not depend
  on it.

### Task 6 — live-side refresh

1. `live_stuff/_vendored/MANIFEST.md` — the vendored `btc_engine.py` **hash changed** (the
   gate) and the parity numbers are stale. Recompute both hashes and update the parity table
   from the Task 1 payload (do not retype numbers). The `unified.py` row stays as the
   2026-10-21 re-vendor recorded it, unless Task 4's live-vs-pins run says otherwise.
2. `live_stuff/book.py` header carries the pre-gate pins ("IS 525t/+538.40R, OOS
   295t/+272.92R") → update from the new pins.
3. `live_stuff/docs/working theory of 107.md` — append the wait-for-FS verdict: the rule, the
   scope (LTF fall-through side only; the FS side is safe by construction; the HTF leg is
   unreachable), the cost (§3 numbers), the OOS-costs-more-than-IS finding, and the explicit
   statement that a fall-through entry is on a swing that has not printed its own FS — by
   design, not by bug.

### Task 7 — restart the paper book (currently DOWN)

`live_stuff/_logs/paper_run3.log` and `.err` are **0 bytes** (created 13:24, never written) —
the previous `cmd /c "… start /b python -u main.py …"` launch produced no output, so the
restart never happened. `paper_run2.log` stops at 13:21 (the kill). No paper process runs.

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\live_stuff
Get-Process python -ErrorAction SilentlyContinue     # confirm nothing is running; kill if so
Start-Process python -ArgumentList '-u','main.py','2026-09-21 00:00:00','2026-10-01 00:00:00','--exchange','bybit' `
  -RedirectStandardOutput '_logs\paper_run4.log' -RedirectStandardError '_logs\paper_run4.err' -WindowStyle Hidden
```

`main.py` prints its banner before any network call, so **an empty log after 30s means the
process never started** — check that first, not the db. Confirm it runs the **gated vendored**
engine (`live_stuff/_vendored/btc_engine.py` carries the gate; the copy is byte-identical to
`backend/src/btc/btc_engine.py`).

### Task 8 — commits (three, in this order)

- **A** — `backend/src/btc/btc_engine.py`, `live_stuff/_vendored/btc_engine.py`,
  `backtest/tests/registry/*.py` (pins), `backtest/tests/_results.json`,
  `backtest/experiments/repin_all.{json,md}`, `gate_sweep.{json,md}`,
  `backtest/tests/_gate_invariant.json`, `live_stuff/_vendored/MANIFEST.md`,
  `live_stuff/book.py`, `live_stuff/docs/working theory of 107.md`
  → *"wait for the previous swing's FS before any fs-branch entry; re-derive every live
  registry pin and the /results artifact under the gate"*
- **B** — `backend/src/btc/engines/htf_ltf/unified.py` (+vendored), `live_stuff/live/*`,
  `live_stuff/live/persistence/trade_store.py` → *"decisive-window regime tracker"*
- **C** — `backtest/tests/test_experiments_craze.py` → *"point the craze identity gate at the
  shipping engine"*

Commit only when the user says so. `git stash@{0..2}` are the previous session's orphans —
**do not drop them without explicit consent**.

## 6. Risks

| risk | detection | response |
|---|---|---|
| gate leaks into the "decisive" path | any non-fs book that moved in `gate_sweep.md` | **stop**; diagnose before writing pins |
| the other ~169 live books have stale pins for a non-gate reason | `exp_pinverify.py` all-OK | report as `other-drift`, re-derive, do not hide it inside the gate commit |
| descs end up with two chain anchors | `exp_desc_pin_audit.py` check F + the diff | the Task 3 anchor-replacement step prevents it |
| the sweep's "OFF" arm is not a faithful pre-gate engine | the OFF trade list must reproduce the **pre-gate** pins for the 36 books | that is the cross-check: OFF stats for book 107 must be 525 / +538.40 IS and 295 / +272.92 OOS |
| paper book starts on the wrong engine or not at all | empty `paper_run4.log` | the banner prints before any I/O; empty = not started |
| the craze fix exposes the 00191fd gap | identity gate still DIVERGED | park it loudly; do not weaken the gate; it does not block the gate change |

## 7. Out of scope

- Re-deriving comparative claims in the descs (parent deltas, permutation p-values) — analysis
  decisions, not derivations.
- The two graveyard fs-entry books (`fsent_dirmatch_long` / `fsent_dirmatch_short`,
  `pins: None`) — nothing to update.
- Retired books — not re-run, not re-pinned. `registry/retired.py::archived()` still exposes
  them; `backtest/tests/_archive_list.md` is stale (2026-10-08, before the 69 re-retirements)
  and can be refreshed with `exp_archive_list.py` if the user wants.
- `backtest/docs/_patched_engine.py` — a stale historical reference copy, imported by nothing.
- The old stashes (`stash@{0..2}`) — user consent required.
