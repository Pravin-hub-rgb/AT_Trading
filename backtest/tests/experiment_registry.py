"""Experiment Registry — the public surface, now a re-export.

The 223 books used to live in this one file. They are split across six family
modules under `registry/` (trail, sweep, signal, risk, d3, kingsweep) plus
base/groups/helpers, and merged by `registry/__init__.py`. See
`pipeline/signal/EXPERIMENTS.md` for where each family went and
`exp_registry_snapshot.py` for the check that guarantees the move changed no
book.

This module stays because seven harnesses import from it, and because renaming
the import path across all of them in the same commit would bury the data move
under an unreviewable diff. It is now ~40 lines.

Public surface, unchanged:
    EXPERIMENTS, ALIASES, BP, ENGINE_DEFAULTS, GROUPS,
    SHORTLIST_IS_MIN, SHORTLIST_OOS_MIN, book(), alias_of(), shortlisted()

`book(key)` returns the resolved config for a key, following aliases.
`shortlisted(key)` is a size filter, not a verdict — see closed/CLOSED_DO_NOT_REPEAT.md
for why the reference books clear it and are still not candidates.

To add an experiment, add a dict entry to the right family module.
Run with: python run_experiment.py <key>
"""
import sys as _sys
import os as _os

# Make the sibling `registry` package importable no matter how this module was
# reached (harnesses add backtest/tests to sys.path, or import it by path).
_pkg_parent = _os.path.dirname(_os.path.abspath(__file__))
if _pkg_parent not in _sys.path:
    _sys.path.insert(0, _pkg_parent)

import registry as _registry
from registry import (EXPERIMENTS, ALIASES, BP, ENGINE_DEFAULTS, GROUPS,
                      SHORTLIST_IS_MIN, SHORTLIST_OOS_MIN, book, alias_of,
                      shortlisted)

__all__ = ["EXPERIMENTS", "ALIASES", "BP", "ENGINE_DEFAULTS", "GROUPS",
           "SHORTLIST_IS_MIN", "SHORTLIST_OOS_MIN", "book", "alias_of",
           "shortlisted"]
