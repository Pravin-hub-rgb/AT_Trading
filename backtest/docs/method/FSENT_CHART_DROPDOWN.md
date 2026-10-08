# the fsent pair, exposed on the chart — and a knob the API cannot accept

Date: 2026-10-08. Adds two dropdown entries to `/btc`, both at the top:
`fsent_champ_long` and `fsent_champ_long_atr_low`.

## what was added

| layer | file | change |
|---|---|---|
| version list | `backend/src/btc/btc_routes.py` | both keys added to `BTC_VERSIONS` |
| standalone set | same | both added to `STANDALONE_HTF_LTF_VERSIONS` so the chart gets `htf_windows` |
| labels | same | `VERSION_LABELS` entries quoting the pins |
| dispatch | same | one branch handling both, keyed on `version` |
| TS type | `frontend/src/lib/btcApi.ts` | `BtcVersion` union extended |
| dropdown | `frontend/src/lib/books.ts` | two `BookOption`s **prepended** |

`prepended` is what puts them at the top: `btc/page.tsx:983` renders
`BOOK_OPTIONS.map(...)` in array order, so index 0 is the first option.

Two entries, one knob apart:

| book | mode | IS | OOS |
|---|---|---|---|
| `fsent_champ_long` | `atr_high` | 528t / +533.37R / dd 13.42 | 311t / +239.59R / dd 11.88 |
| `fsent_champ_long_atr_low` | `atr_low` | 641t / +721.30R / dd 28.90 | 315t / +280.70R / dd 14.60 |

Every other value comes from the shared `V19` block, so the two are comparable on
one chart: same risk model, same costs, same swing definition, opposite sign on the
regime selector.

## neither of these is the old "unified" entry

`unified` is `champion_multi_sw10_leg` — 499t / +239.12R — and it has **no
directional FS entry at all**. It trades the FS print on neither side. The new pair
sets `exp_fs_entry_side="long"`: longs enter at the swing FS print, shorts still
enter at the break. That one change is why the count moves 499 → 528.

## the knob the API cannot accept

The registry records `exp_mltf=True` on both books. **`exp_mltf` is not a parameter
of the real engine.** Measured, not assumed:

```
simulate_htf_ltf_streak_halt: 38 named params, **kwargs = False
'exp_mltf' in real signature: False
```

There is no `**kwargs`, so a route branch that passed `exp_mltf=True` would raise
`TypeError` on the user's request. The harness gets away with it because
`test_experiments_craze.build_module()` **patches the engine source text** before
importing it — `exp_tf_family.build_family_module` injects `htf_bar_secs` /
`ltf_bar_secs` the same way. The API calls the engine unpatched.

What `exp_mltf=True` actually does is allow overlapping positions — it disarms the
`busy_until` slot gate. The real engine expresses the same thing as
`max_positions=0`, documented in `unified.py` as "0 = unlimited (v19 behaviour),
the gate never fires". So the route passes `max_positions=0` and omits `exp_mltf`,
which is also why the pre-existing `unified` branch does the same.

**That equivalence is now proven, not assumed.** `exp_route_parity.py` runs both
books through the exact route parameter set with no `exp_mltf` and requires the
registry pins to reproduce, then cross-checks the real unpatched engine against the
patched harness:

```
fsent_champ_long              IS   got  528t / +533.37R / dd 13.42R   want 528t / +533.37R / dd 13.42R   OK
fsent_champ_long_mode_atr_low IS   got  641t / +721.34R / dd 28.88R   want 641t / +721.30R / dd 28.90R   OK
fsent_champ_long              OOS  got  311t / +239.59R / dd 11.88R   want 311t / +239.59R / dd 11.88R   OK
fsent_champ_long_mode_atr_low OOS  got  315t / +280.72R / dd 14.56R   want 315t / +280.70R / dd 14.60R   OK
real unpatched engine, all four cells: OK
RESULT: PASS
```

It also asserts up front that every param the route passes is a real engine
parameter — the check that would have caught the `TypeError` before a request hit
it. And it prints a warning if `exp_mltf` ever appears in the real signature, so
the choice here gets revisited rather than silently rotting.

The harness and the API now agree because they run the same engine with the same
arguments. Before this, the chart could have shown a book that did not match the
number in its own label.

## a behaviour change worth naming

`getBook()` in `books.ts` falls back to `BOOK_OPTIONS[0]`. Prepending the pair
makes that `fsent_champ_long` instead of `champion_causal`, so an id that no
longer resolves now lands on the fsent base. `DEFAULT_BOOK` is deliberately
unchanged at `champion_causal` — the point of the change is that the pair is
available and first, not that everyone's landing book moves. The fallback shift is
stated in the file.

## verification

- `npx tsc --noEmit` — clean, no output.
- `npm run lint` — 206 problems (172 errors, 34 warnings), **identical before and
  after** these changes, confirmed by stashing. `books.ts` and `btcApi.ts` produce
  no findings at all.
- `exp_route_parity.py` — PASS, four pin cells plus four real-engine cells.
- backend imports clean; both keys present in `BTC_VERSIONS`,
  `STANDALONE_HTF_LTF_VERSIONS` and `VERSION_LABELS`.

## still not promoted

Adding a book to the dropdown is visibility, not adoption. The owner's drawdown
budget is **29R**, confirmed 2026-10-08, and both fit:

- `fsent_champ_long` — 13.42R IS, 11.88R OOS
- `fsent_champ_long_atr_low` — 28.90R IS, 14.60R OOS

The recommendation on the evidence is unchanged (`OWNER_SCORECARD_MODES.md`,
`MODE_DURATION_CALENDAR.md`): keep `fsent_champ_long` as the base, because
`atr_low`'s extra return retains only 21.9% out of sample (+187.9R in sample,
+41.1R out of it). Its in-sample drawdown of 28.90R also takes 5.7 months to form,
the slowest descent of the five books measured. Both are now one dropdown click
away for inspection, which is what the chart is for.