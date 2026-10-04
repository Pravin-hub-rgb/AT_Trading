# THE EXPERIMENT PIPELINE

How to add a knob, run an experiment, record the result, and know whether the
result is allowed to exist. Read [`../ONBOARDING.md`](../ONBOARDING.md) first.

**No numbers appear in this folder.** A number here is wrong the moment the
engine changes. Measured results live in `experiment_registry.py` and are read
out by `REGISTRY_BOARD.md`.

---

## 1. Before you write anything

**Read `CLOSED_DO_NOT_REPEAT.md`.** It is not a list of failures, it is a list of
*mechanisms* that failed, with the reason. Three families shipped large numbers
that were reading the future; if your idea is close to any of them, the reason it
failed usually applies to yours too.

**Name the family** from [`FAMILIES.md`](FAMILIES.md). If the family is already
represented in the book you are extending, you are probably adding a fit.

**State the causal story.** For any knob that reads a swing: which field, and
when does that field settle. If the answer is "at the entry bar, from the swing
that contains the entry", you have written lookahead — that is exactly what
`exp_require_dir_match` did.

## 2. Adding a knob

Default-off. Always.

**In the engine** — `backend/src/btc/engines/htf_ltf/unified.py`, in the
signature with a comment saying what it reads and when:

```python
exp_my_thing=0.0,   # what it does. reads seg.end_px, settled at confirmed_at_idx
```

**As a harness patch** — only if the engine cannot express it as a keyword.
`backtest/tests/test_experiments_craze.py` patches the *shipped source text* with
an asserted anchor, so the patch fails loudly if the engine moves instead of
silently doing nothing.

Two rules that were both learned the hard way:

- **Do not shadow a name that already exists in an enclosing scope.** `import
  bisect as _b` inside one function and a bare `bisect` elsewhere bit this
  during the directional-FS work.
- **If the harness asserts an anchor, the anchor is a real dependency.** Update
  it in the same commit as the engine change, or the harness stops patching and
  every result becomes a lie.

## 3. Running

```bash
cd backtest/tests

python run_experiment.py <book>          # one book, both eras
python exp_fastcheck.py <book> [<book>] # re-derive pins from the engine, both eras
python exp_fastcheck.py                 # top 12 shortlisted, both eras
python exp_pinverify.py                 # every pinned book - slow, authoritative
python exp_origin_lookahead.py          # the standing hygiene gates
```

Write the experiment as a script that prints a table and writes a JSON next to
it. Put it in `backtest/experiments/` with a `_results.json` beside it.

## 4. The three checks before a number is allowed out

**a. Identity.** With your knob at its default, the patched engine must
reproduce the shipped book exactly. `exp_origin_lookahead.py` and the identity
gate in the craze harness both do this. A knob that moves a book at its default
is not default-off.

**b. Both eras.** In sample and out of sample, from the engine. One era is not a
result.

**c. Causality.** Say which field is read and when it settles. If the answer is
"the swing's final label", it is read from the future at the entry bar and the
whole family is closed — see `CLOSED_DO_NOT_REPEAT.md`.

## 5. Recording the result

**If it wins:** add a book to `experiment_registry.py` with
`exp_fs_entry_side`-style `params`, an exact `pins` block, and a doc under
`backtest/docs/` carrying the table. Then re-derive it:

```bash
python exp_fastcheck.py <new_book>
```

`exp_fastcheck.py` prints how many books it did *not* check, on purpose. Its pass
is about the books it names and nothing else.

**If it loses:** one paragraph in `CLOSED_DO_NOT_REPEAT.md` with the numbers, both
eras, and the mechanism. Do not delete the harness — the next person will want
to know it was tried. `exp_prefix_audit.py` is in that file as an example of a
harness that is kept precisely because it does not work: it missed a leak that
was already proven, and that is worth knowing.

**If the knob is lookahead:** mark every book that uses it `status: "reference"`
with a comment naming the field and the measurement. `shortlisted()` excludes
reference books, so a contaminated number cannot re-enter on size alone.

## 6. Layout

```
backtest/experiments/<name>/
    exp_<name>.py        the harness
    <name>_results.json  what it printed
backtest/docs/pipeline/  this folder - how, never what
backtest/docs/           per-family write-ups, results included
backtest/tests/          the registry, the runner, the verifiers
```

## 7. Things that will waste your time if nobody told you

- **A post-hoc re-score of closed trades is not a measurement.** If the rule
  changes which trades exist, re-scoring measures the old book. This produced a
  phantom +349.90R that was +174.58R in the engine.
- **A generic audit tool can be confidently wrong.** `exp_prefix_audit.py`
  cleared a book that was proven contaminated. Read the knob's actual selector.
- **Overlaying across books does not prove a book.** `fsent_dirmatch_*` looked
  strong as an overlay and was contaminated at the base.
- **Do not quote a number from a doc.** The engine has moved; most prose numbers
  in this repo predate the causal stop fix. Run it.