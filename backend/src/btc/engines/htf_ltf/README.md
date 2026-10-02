# One engine. One file.

`unified.py` is the only engine. Nothing else in `engines/htf_ltf/` is a
second implementation.

**Every new experiment is a registry entry with `params`, not a new engine
file.** The Retro / Causal / ENTRY-1 books are `pivot_rule` values on one
engine, not three files:

| book | pivot_rule | n | gross |
|---|---|---|---|
| CHAMPION CAUSAL | `leg` | 499 | +355.72R |
| CHAMPION ENTRY-1 | `leg_no_entry` | 500 | +445.19R |
| (research baseline) | `origin` | 500 | +445.22R |

Everything else in this directory is either a shim that forwards to
`unified.py`, or a historical baseline that predates the unification and is no
longer reachable from the route. None of it may be edited to change strategy
behaviour; a change belongs in `unified.py` and in the book's `params`.

This is not a style preference. Three real divergences this session came from
the same cause — a feature existing in two places, or a flag that one copy
honoured and another ignored:

- `exp_persist` injected into the harness while already native in the engine,
  producing two hysteresis blocks and a book that was neither configuration.
- The identity gate importing `v18_streak_halt` while the harness patched
  `unified.py`, so it diffed two different books and reported DIVERGED forever.
- `max_positions` and `exp_persist` hardcoded in `v19_champion.py` while the
  route passed neither, so repointing the import silently changed a pinned book
  from 500 trades to 503.

One file means a bug is fixed once and cannot survive in a second copy.

`backtest/checks/exp_single_engine.py` enforces this. It fails if a file
appears here that is not on the allowlist, and it fails if the registry names
an engine other than `unified`.