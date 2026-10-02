"""Run a callable on a thread with a large stack.

Why this exists. `sys.setrecursionlimit(20000)` does NOT buy recursion depth - it
buys a stack overflow. CPython 3.10 recurses on the C stack as well as the Python
stack, so raising the counter past what the thread stack can hold makes the
process die with exception code 0xc00000fd (STACK_OVERFLOW) instead of raising a
catchable RecursionError. Three harnesses were "fixed" that way on 2026-10-01 and
the machine produced seven uncatchable python.exe crashes in ten minutes, each one
looking like a silent hang because no traceback and no stderr reached the log.

The actual fix is a bigger stack, not a bigger counter.

    from _bigstack import run
    fn = run(lambda: build_module())

512 MB is ample for pathlib-level recursion and costs nothing but address space on
a 64-bit process; the thread's stack is reserved lazily, so an idle one is cheap.
"""
import sys
import threading

STACK_BYTES = 512 * 1024 * 1024
RECURSION_LIMIT = 100000


def run(fn, *args, **kwargs):
    """Call fn on a big-stack thread and return its result. Re-raises in the caller."""
    box = {}

    def go():
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(RECURSION_LIMIT)
        try:
            box["value"] = fn(*args, **kwargs)
        except BaseException as e:      # noqa: BLE001 - re-raised below
            box["error"] = e
        finally:
            sys.setrecursionlimit(old)

    try:
        threading.stack_size(STACK_BYTES)
    except (ValueError, RuntimeError):
        pass                            # platform refused the size; limit still helps
    t = threading.Thread(target=go, name="bigstack")
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]
    return box.get("value")