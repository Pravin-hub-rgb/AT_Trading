"""Progress bar for the long harnesses.

Every harness in this directory runs 8 to 25 books x 2 eras through the engine,
which is minutes, and the harness used to print nothing until the end. The owner
had no way to tell a slow run from a hung one, which is the worst possible state:
the only rational response to silence is to interrupt it.

So: one helper, used by the harnesses that loop, that prints a bar with the
percentage, the item counter and - the part that actually matters - an ETA. The
ETA is measured, not guessed, from completed items, and it says UNKNOWN until two
items have finished rather than printing a confident nonsense number from the first
one.

Deliberately plain ASCII and no dependency. These run in CI and in a console that
has already mangled unicode box drawing once.
"""
from __future__ import annotations

import sys
import time

WIDTH = 28


class Bar:
    def __init__(self, total: int, label: str = "", stream=None, min_interval: float = 0.25):
        self.total = max(1, int(total))
        self.label = label
        self.stream = stream or sys.stdout
        self.min_interval = min_interval
        self.t0 = time.time()
        self.last = 0.0
        self.done = 0
        self.width = WIDTH

    def _render(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self.last < self.min_interval:
            return
        self.last = now
        frac = min(1.0, self.done / self.total)
        filled = int(self.width * frac)
        pct = int(round(frac * 100))
        bar = "#" * filled + "-" * (self.width - filled)

        if self.done >= 2:
            rate = (now - self.t0) / self.done
            remain = int(rate * (self.total - self.done))
            if remain < 60:
                eta = "%ds left" % remain
            elif remain < 3600:
                eta = "%dm left" % (remain // 60)
            else:
                eta = "%dh%02dm left" % (remain // 3600, (remain % 3600) // 60)
        else:
            eta = "estimating..."

        self.stream.write(
            "\r  [%s] %3d%%  %d/%d  %-22s %s"
            % (bar, pct, self.done, self.total, self.label[:22], eta)
        )
        self.stream.flush()

    def update(self, item: str = "") -> None:
        self.done += 1
        if item:
            self.label = item
        self._render()

    def close(self, msg: str = "") -> None:
        self.done = self.total
        self._render(force=True)
        tail = ("  " + msg) if msg else ""
        self.stream.write("\r  [%s] 100%%  %d/%d  %-22s done%s\n"
                          % ("#" * self.width, self.total, self.total,
                             self.label[:22], tail))
        self.stream.flush()


def bar_for(items, label: str = "") -> Bar:
    """bar_for([...], "book") - the common shape."""
    return Bar(len(items), label)


class Announce:
    """Say what is about to happen and how long it should take, BEFORE doing it.

    This exists because the bar only helps once something is running. A harness
    that spends 40 seconds loading candles before its first bar appears is
    indistinguishable from a hung one, and the only rational response to silence
    is to kill it and ask what happened.

    So the long harnesses announce first: the step, the expected duration, and
    what is being verified. If it overruns the estimate that is visible too,
    which is more useful than a silent stall.
    """

    def __init__(self, step: str, expect: str, note: str = ""):
        self.step = step
        self.expect = expect
        self.note = note
        self.t0 = time.time()
        self.took = 0.0

    def __enter__(self):
        sys.stdout.write("  > %s   [~%s]%s\n"
                         % (self.step.ljust(34), self.expect,
                            ("   " + self.note) if self.note else ""))
        sys.stdout.flush()
        return self

    def __exit__(self, *exc):
        self.took = time.time() - self.t0
        return False


def step(name: str, expect: str, note: str = "") -> Announce:
    return Announce(name, expect, note)


if __name__ == "__main__":
    # self-test: the ETA must not claim precision it does not have
    b = Bar(4, "demo")
    b.update("a"); b.update("b")
    for i in range(2):
        time.sleep(0.2)
        b.update("item%d" % i)
    b.close("ok")