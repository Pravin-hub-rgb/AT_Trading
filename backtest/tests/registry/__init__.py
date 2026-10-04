"""The experiment registry, as a package.

The books are split across six family modules and merged here. Importing this
package gives the same public surface the old single-file
experiment_registry.py did:

    EXPERIMENTS, ALIASES, BP, ENGINE_DEFAULTS, GROUPS,
    SHORTLIST_IS_MIN, SHORTLIST_OOS_MIN, book(), alias_of(), shortlisted()

Merge order is fixed and matters only for duplicate keys: trail, sweep, signal,
risk, d3, kingsweep. If two families ever define the same book key the later
one wins silently, so the split map in exp_registry_snapshot.py is the place
that has to stay correct - there is no runtime guard here because a book that
is defined twice is a data bug, not a code bug, and it should fail the
snapshot comparison rather than be papered over.

ALIASES is derived from EXPERIMENTS *after* the merge, because it is a
comprehension over the str-valued rows: {k: v for k, v in EXPERIMENTS.items()
if isinstance(v, str)}. Deriving it before the merge - or from a per-family
dict - yields an empty or partial ALIASES, which is the one thing in this
refactor that could have passed a naive smoke test and still been wrong.
"""
from .base import ENGINE_DEFAULTS, BP
from .groups import GROUPS
from . import trail, sweep, signal, risk, d3, kingsweep
from .helpers import (_AliasRegistry, SHORTLIST_IS_MIN, SHORTLIST_OOS_MIN,
                      book as _book, shortlisted as _shortlisted,
                      alias_of as _alias_of)

# The book data, merged. Each family module exposes BOOKS.
EXPERIMENTS = {}
for _mod in (trail, sweep, signal, risk, d3, kingsweep):
    EXPERIMENTS.update(_mod.BOOKS)

# Aliases are the str-valued rows. Derived last, from the merged dict.
ALIASES = {k: v for k, v in EXPERIMENTS.items() if isinstance(v, str)}

# Wrap so EXPERIMENTS[key] resolves an alias to the real config.
EXPERIMENTS = _AliasRegistry(EXPERIMENTS)


def book(key):
    """Resolved config for a book key, following aliases."""
    return _book(EXPERIMENTS, key)


def shortlisted(key):
    """True when the book clears both size thresholds AND is still a candidate."""
    return _shortlisted(EXPERIMENTS, key)


def alias_of(key):
    """The surviving key if `key` is an alias, else None."""
    return _alias_of(EXPERIMENTS, key)


__all__ = ["EXPERIMENTS", "ALIASES", "BP", "ENGINE_DEFAULTS", "GROUPS",
           "SHORTLIST_IS_MIN", "SHORTLIST_OOS_MIN", "book", "alias_of",
           "shortlisted"]
