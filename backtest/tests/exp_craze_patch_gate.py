"""exp_craze_patch_gate - prove a refactor of the patch walk changed nothing.

WHY A GATE, AND NOT JUST "THE TESTS PASS"

test_experiments_craze.py::_build_module is one function of about 1450 lines
containing 58 sequential `s = s.replace(anchor, replacement)` calls. Splitting
it into named functions is a pure refactor by intent, and intent is not
evidence. The failure mode is silent in a specific way: a patch that stops
applying leaves the engine valid and merely missing a knob, so every harness
that uses that knob either produces a different number or raises a TypeError
much later, in a file that has nothing to do with the patch.

It can also pass every existing check. exp_fastcheck runs the PATCHED engine,
so a missing patch makes the patched engine agree with itself and every pin
still verifies. exp_port_differential compares patched against shipped, and a
knob removed from the patch entirely makes the shipped engine the only one
with it, which is a difference the differential would flag - but only for the
nine knobs it happens to cover, not for the other forty-nine.

So the gate is the only real answer: capture the exact text the patch walk
produces, do the refactor, capture it again, and require byte equality. There
is no tolerance and no normalisation. Either the 2300-odd lines of patched
engine are identical or the refactor is wrong.

    cd backtest/tests
    python exp_craze_patch_gate.py write    # before a refactor
    ... refactor ...
    python exp_craze_patch_gate.py check    # after; exit 1 on any difference

Writes the SHA256 of the patched source plus the line count and the param
count, so a difference says which of the three moved rather than just "changed".
"""
import sys, json, hashlib, argparse, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

STATE = ROOT / "backtest" / "tests" / "_craze_patch_gate.json"


def patched_source():
    """The exact source text build_module() would hand to importlib.

    Captured by intercepting _load_module rather than by re-running the patch
    walk: build_module() runs the walk on a big-stack thread and returns the
    callable, and the text it built is what actually got exec'd. Intercepting
    means we hash the real artifact, not a reconstruction of it.
    """
    import test_experiments_craze as C
    captured = {}
    original = C._load_module

    def spy(text, name):
        captured["text"] = text
        # Still import it: a patch that produces unparseable source must fail
        # here, not silently pass the hash comparison.
        return original(text, name)

    C._load_module = spy
    try:
        C.build_module()
    finally:
        C._load_module = original
    if "text" not in captured:
        raise SystemExit("could not intercept the patched source")
    return captured["text"]


def fingerprint():
    text = patched_source()
    b = text.encode("utf-8")
    return {
        "sha256": hashlib.sha256(b).hexdigest(),
        "bytes": len(b),
        "lines": text.count("\n"),
        # A cheap second opinion: if the hash differs but these match, the
        # change was whitespace. If either differs, real code moved.
        "n_exp_kwargs": text.count("    exp_") + text.count("    b3_"),
        "n_continue": text.count("            continue\n")
                      + text.count("                continue\n"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["write", "check", "show"])
    a = ap.parse_args(argv)

    print("building the patched engine and fingerprinting it...", flush=True)
    fp = fingerprint()
    print("  sha256  %s" % fp["sha256"])
    print("  %d bytes, %d lines, %d exp_* kwargs, %d continue statements"
          % (fp["bytes"], fp["lines"], fp["n_exp_kwargs"], fp["n_continue"]))

    if a.mode == "show":
        return 0

    if a.mode == "write":
        STATE.write_text(json.dumps(fp, indent=1), encoding="utf-8")
        print("\nwrote %s" % STATE.name)
        return 0

    # check
    if not STATE.exists():
        print("\nno baseline at %s - run `write` before the refactor" % STATE.name)
        return 2
    old = json.loads(STATE.read_text(encoding="utf-8"))
    print("\nbaseline sha256 %s" % old["sha256"])
    if fp["sha256"] == old["sha256"]:
        print("RESULT: PASS - the patched engine is byte-identical.")
        print("        The refactor moved no code.")
        return 0
    print("RESULT: FAIL - the patched engine changed.")
    for k in ("lines", "bytes", "n_exp_kwargs", "n_continue"):
        if fp.get(k) != old.get(k):
            print("        %-14s %s -> %s" % (k, old.get(k), fp.get(k)))
    print("        The diff is the whole story: every number this harness")
    print("        produces comes from these bytes.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())