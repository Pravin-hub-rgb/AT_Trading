"""Alias resolution and the shortlist rule over the merged registry.

Split out from the single-file registry. This holds no book data - the books
live in the family modules and are merged by registry/__init__.py. The helpers
take EXPERIMENTS as an argument rather than importing it, so this module has no
import-order dependency on the package that owns the data.
"""

SHORTLIST_IS_MIN = 130.0
SHORTLIST_OOS_MIN = 50.0


class _AliasRegistry(dict):
    """dict of book configs, where a string value means "same book as that key".

    Two registry books turned out to be the same experiment under two names once
    rerun on unified.py (swingpause_cd0_single_sw10, skip1pause_multi_sw10).
    Rather than copy the config - which is how the duplication went unnoticed in
    the first place, because the copies drifted - the alias points at the
    surviving entry. Readers keep doing EXPERIMENTS[key]["params"] and get the
    real config.
    """

    def __getitem__(self, key):
        return self._deref(key, super().__getitem__(key))

    def get(self, key, default=None):
        if key not in self:
            return default
        return self[key]

    def _deref(self, key, val, _seen=None):
        if not isinstance(val, str):
            return val
        _seen = _seen or set()
        if key in _seen:
            raise KeyError("alias loop at %r" % key)
        _seen.add(key)
        if val not in self:
            raise KeyError("%r aliases %r, which is not a book" % (key, val))
        return self._deref(val, super().__getitem__(val), _seen)


def book(EXPERIMENTS, key):
    """Resolved config for a book key, following aliases."""
    return EXPERIMENTS[key]


def shortlisted(EXPERIMENTS, key):
    """True when the book clears both size thresholds AND is still a candidate.

    A book marked "reference" is excluded regardless of its size: some of the
    loudest numbers in this registry are artifacts, not edges - the dirmatch/age
    family reads a swing direction that is only final ~8h after the entry bar
    (CLOSED_DO_NOT_REPEAT.md). Size is not admissibility; reference books are
    kept for the record and are never shipping candidates however large.
    """
    cfg = EXPERIMENTS[key]
    if not isinstance(cfg, dict):
        return False
    if cfg.get("status") == "reference":
        return False
    p = cfg.get("pins") or {}
    if not p.get("n"):
        return False
    return p["net"] >= SHORTLIST_IS_MIN and p["oos_net"] >= SHORTLIST_OOS_MIN


def alias_of(EXPERIMENTS, key):
    """The surviving key if `key` is an alias, else None."""
    val = dict.__getitem__(EXPERIMENTS, key)
    return val if isinstance(val, str) else None
