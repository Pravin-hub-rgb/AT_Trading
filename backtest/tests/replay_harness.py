"""Path shim. The real module lives in backtest/sweeps/.

Sixty-four harnesses in this directory do `from replay_harness import ...` without
putting backtest/sweeps on sys.path. They only worked if something else had
imported it first, so they broke or did not break depending on what ran before them
in the same process.

Load the real file by path. Do NOT do this:

    del sys.modules[__name__]
    import replay_harness          # <-- re-imports THIS file, forever

That version was here first and it was wrong. backtest/tests sits at the front of
sys.path in most harnesses, so `import replay_harness` finds this shim again,
which deletes itself and imports again, until the stack ran out. It was masked by
a sys.setrecursionlimit(20000) elsewhere in the tree, which turned the RecursionError
into a stack overflow - process killed, exception code 0xc00000fd, no traceback.
The cause was this loop, not a deep walk anywhere.
"""
import importlib.util
import sys
from pathlib import Path

_REAL = Path(__file__).resolve().parents[1] / "sweeps" / "replay_harness.py"
_spec = importlib.util.spec_from_file_location(__name__, _REAL)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[__name__] = _mod          # bind the name to the real module...
_spec.loader.exec_module(_mod)        # ...then execute it