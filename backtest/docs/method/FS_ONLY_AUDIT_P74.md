# P74 — AUDIT OF P73. Wrong label, not a novel experiment, and the
# "+150 trades for +70R" reading is unsupported.

> Run 2026-09-29. Audit of `method/FS_ONLY_P73.md` / `exp_fs_only.py`.
> **P73's "strongest live candidate" claim is WITHDRAWN pending this audit.**
> Nothing adopted. Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

The owner's instruction was to deep-audit P73 before celebrating it,
because FS had already been tested and had not worked. **That instinct was
correct on every count, and the audit found three problems — one serious.**

## Problem 1 — it is not an FS-only engine. I mislabelled it.

P73's title, docstring and queue entry all say "FS-only". **It is not.**

v18 builds its HTF windows from **three** v7 calls — `flip`, `decisive` and
`b2` — and calls v7 again for the LTF layer. P73 routed exactly one:

```python
def routed(swings, eb, **kw):
    return patched(swings, "fs_only" if eb == "decisive" else eb, **kw)
```

**The `flip` and `b2` paths were untouched, and every LTF call that went
through `decisive` also became FS.** The arm is roughly one third
FS-triggered and two thirds break-triggered, interleaved through the same
window, cooldown and `busy_until` machinery.

**Nothing about that is cheating — it is a real configuration — but calling
it "FS-only" is a false description, and it misled every reader including the
queue entry.**

## Problem 2 — it is not novel. It was run one day earlier.

`method/FS_ONLY_ENGINE.md`, dated **2026-09-28**, is the same question answered:

> *"**2,900 swings confirmed exactly.** But the run found **zero** swings
> without a B2/FLIP mark — every swing carries one… **The FS-only book is not
> bigger. It is smaller** — 263 trades IS, 108 OOS."*
>
> | SL mode | r | IS | OOS (utcsat) |
> |---|---|---|---|
> | `seg_start` | 2.0 | 263t **+31.7R**, trim +0.079 | 108t **+1.3R**, trim **−0.037** |

**Their result: 263t +31.7R IS, 108t +1.3R OOS. Mine: 646t +405.2R IS,
364t +233.6R OOS.** Same name, 2.5× the trades, 13× the OOS R.

**The gap is explained and it is not a contradiction.** Their harness is a
**standalone** construction:

- `fs_signals()` builds the FS list directly from the swing chain,
  explicitly *"deliberately NOT `_collect_signals`"*, filtered to swings
  whose marks contain **no** tradeable kind — the never-priced population.
- `simulate_fs_book()` is a **separate mini-simulator**, not the champion
  engine. So FS entries there never pass the champion's window gate, regime
  gate, direction match, cooldown or `busy_until`.

**My arm runs FS entries through the champion's entire pipeline**, and also
captures swings that *did* break. That is why 646 trades instead of 263.
**Different question, different answer — but the two were never
distinguished, and P73 failed to read an existing result first.**

## Problem 3 — `method/FS_ENTRY.md` is a direct warning and P73 did not address it

> *"| **FS entry** | **M2's sign inverts 4/4 — the look-ahead was the whole edge** |"*
>
> *"When you actually buy a swing **after it has been confirmed big**, it is
> the worst thing you can buy — because the move that made it big has already
> happened."*
>
> *"**~36–37% of the book disappears** if we wait for FS. What remains is
> smaller but not obviously worse per trade."*


## On "+150 trades for +70R"

That reading — the owner's, and mine by implication — assumes the FS arm
**adds** to the champion's book. **Nothing in P73 establishes that, and I
never measured it.**

646 − 500 = **146** more trades and +79.4R. If they were *pure additions*
they would be worth +0.54R each, which would be remarkable. **They are
almost certainly not pure additions**: the champion's 500 entries fire on
break marks, and the routed `decisive` path no longer produces break entries
at all, so the two books share trades only where the untouched `flip`/`b2`
paths happened to coincide.

**The missing measurement is a trade-level decomposition:**

- how many of the champion's 500 survive into the FS arm
- how many FS-arm trades are new
- the net R of survivors vs newcomers

**Without it, "+146 trades for +79.4R" is not a claim, it is an arithmetic
coincidence, and P73 was written in a way that invited exactly that reading.**

## What P73 actually established

Stripped of the mislabelling:

> **Routing one of three entry sources in the champion engine from
> `decisive` to FS-first-seal produces a book of 646 trades in IS and 364 in
> OOS — larger, with a better profit factor and a lower drawdown in both
> champion-lane cells, and 3 of 4 cells positive. One cell (utcsat IS) is
> −78.2R. No cell clears M.**

That is a real and interesting observation about a **hybrid** configuration.
**It is not evidence that the book has an edge at first-seal, because that
was never isolated.**

## What has to happen before this is believed

1. **Rename it.** It is a hybrid; every doc, queue entry and index row should
   say so. The "FS-only" framing propagates a false claim.
2. **Run the trade-level decomposition.** Survivors vs newcomers, net R of
   each. Cheap, and it is the number the owner's question is really asking.
3. **Run the P61 period partition.** Still not run, and now more important,
   because the 4-cell result is doing all the persuasive work.
4. **Reconcile with `method/FS_ONLY_ENGINE.md`.** Its 263t/+31.7R is the pure FS
   answer; the two should be cited together, or the difference explained, in
   whichever document survives.
5. **Check the `method/FS_ENTRY.md` inversion.** Does the champion's own signal
   population change the way that document says it must when FS-time buckets
   become entry-eligible?

## Status

**P73's candidate registration is withdrawn.** Not because the numbers are
wrong — they reproduce from the stated patch — but because they were
attributed to a mechanism they do not isolate, and they were presented
without reading two documents that answered the question first.

**The champion is unchanged and nothing is adopted. The honest position is
that a promising hybrid configuration was found and misfiled, and the
decomposition that would justify or kill it has not been run.**

**Why this is not historical colour:**

1. **The 36–37% figure is measured at the same FS trigger P73 uses**, and
   P73 neither reproduces nor explains it. That P73 cannot is explicable —
   P73 leaves two of three paths alone — but a *reason* is not a *check*.
2. **P73's largest cell is +163.4R of OOS profit obtained by making FS-time
   information entry-eligible.** That is exactly the shape `FS_ENTRY` says
   inverts when it becomes legal. **This is not evidence P73 has a
   lookahead** — `fs_at_idx` is causal — but it is a reason to distrust the
   magnitude until the causal chain is checked end to end rather than argued.
