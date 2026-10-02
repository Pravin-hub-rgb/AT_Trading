"""Compatibility shim - the implementation moved, this name must not.

v18_streak_halt.py and v19_champion.py were archived under _archive/ once
unified.py was verified byte-identical to both on all three pivot rules. But
roughly a hundred scripts across backtest/, backend/debug/ and backend/tests/
import these module paths by name, and their numbers are cited in docs. Moving
the files broke all of them.

So the implementation stays in _archive/ and this file re-exports it. Import
paths keep working; production still runs unified.py alone.
"""
import sys as _sys
from src.btc.engines.htf_ltf._archive import _v18_real as _impl

# Re-export every public and private name, which is what `import *` plus the
# explicit list was doing badly. Module-level attributes only.
for _k in dir(_impl):
    if not _k.startswith("__"):
        globals()[_k] = getattr(_impl, _k)

# Callers that did `import module as m` then `m.simulate_...` need this too.
_sys.modules[__name__ + "._impl"] = _impl
