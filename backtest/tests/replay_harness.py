"""Path shim. The real module lives in backtest/sweeps/.

Sixty-four harnesses in this directory do `from replay_harness import ...` without
putting backtest/sweeps on sys.path. They only ever worked if something else had
already imported it first, so they broke or did not break depending on what ran
before them in the same process. Put backtest/sweeps at the front of the path,
drop this shim from sys.modules, and re-import so the real module takes the name.
"""
import sys as _sys
from pathlib import Path as _Path

_SWEEPS = str(_Path(__file__).resolve().parents[1] / "sweeps")
if _SWEEPS not in _sys.path:
    _sys.path.insert(0, _SWEEPS)

# Free this name so the import below resolves to backtest/sweeps/replay_harness.py
# instead of looping back onto the shim.
del _sys.modules[__name__]

import replay_harness as _real  # noqa: E402

_sys.modules[__name__] = _real