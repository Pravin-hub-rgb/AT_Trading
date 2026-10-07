"""Record which engine a result artifact was measured against, and flag the
ones that were not.

THE PROBLEM. Every committed artifact in backtest/docs and backtest/tests is a
measurement of a specific version of the engine. Nothing in the repo recorded
which version. So when the engine changed - as C17 did - there was no way to
tell, from the artifact alone, whether its numbers were still describing the
engine in the tree. Four artifacts silently had to be re-run, and a fifth
(_halt_sweep) was only caught because someone happened to remember it existed.

THE FIX. A result artifact carries one line naming the engine commit it was
measured against. `verify()` compares that against the engine's current commit
and reports a mismatch. Cheap, no re-runs, and it turns "are these numbers
still true?" from memory into a check.

WHY NOT BACKFILL THE OLD ARTIFACTS. Because the whole value is that the stamp is
trustworthy, and a stamp written today for a number measured three weeks ago
would be a lie with a machine-readable shape. Backfilling is not forbidden -
it is just that a backfilled stamp means "not measured against this engine" and
should be written that way, so `verify` keeps reporting it as stale until it is
re-measured. `stamp_current` will not lie for you: it writes the engine commit
only when the file also records that it was measured now.

USAGE
    python exp_provenance.py verify          # report drift, exit 1 on mismatch
    python exp_provenance.py stamp <file>    # record "measured now"
    python exp_provenance.py show <file>     # print what the file claims

Artifacts carrying no stamp at all are reported as `unrecorded`, which is a
warning rather than a failure. Making them hard failures would mean either
backfilling a lie or re-running every historical artifact, and neither is a
reasonable price for the first version of this. Once new artifacts are stamped
by convention, the unrecorded set only shrinks.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The two files whose contents decide what a backtest number means. C17 changed
# the first of these and every artifact measured before it was describing a
# different engine than the one in the tree.
ENGINE_TRACKED = (
    "backend/src/btc/engines/htf_ltf/unified.py",
)

MD_MARK = "<!-- prov:"
JSON_KEY = "_provenance"

# <!-- prov: engine=abc1234 measured=2026-10-07 harness=exp_foo.py -->
#
# The harness field accepts spaces (a stamp may say "harnesses deleted") and is
# delimited by "-->" rather than by whitespace, so a free-text value cannot stop
# the pattern matching. It was \S+ and a stamp written with a multi-word harness
# was silently unreadable - which reads as "no provenance" and is the one answer
# this file must never give wrongly.
_MD_RE = re.compile(
    r"<!--\s*prov:\s*engine=(?P<engine>[0-9a-f]{7,40})\s+"
    r"measured=(?P<measured>\d{4}-\d{2}-\d{2})"
    r"(?:\s+harness=(?P<harness>[^>]*?))?\s*-->"
)


def engine_commit() -> str:
    """Current short sha of the commit that last touched the engine.

    Falls back to the working-tree marker when git is unavailable, so this never
    invents a plausible-looking sha: an unknown engine must read as unknown.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", *ENGINE_TRACKED],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    sha = out.stdout.strip()
    return sha or "unknown"


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read(path: Path) -> dict | None:
    """The provenance this artifact claims, or None if it claims nothing."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        rec = data.get(JSON_KEY)
        return rec if isinstance(rec, dict) else None
    m = _MD_RE.search(text)
    if not m:
        return None
    out = dict(m.groupdict())
    out["engine"] = out["engine"][:7]
    return out


def stamp_current(path: Path, harness: str | None = None) -> dict:
    """Record that this artifact was measured against the engine as it is now.

    This is the only writer, and it only ever writes the live engine commit.
    There is no flag to stamp an artifact with a different engine, on purpose.
    """
    rec = {"engine": engine_commit()[:7], "measured": today()}
    if harness:
        rec["harness"] = harness
    path = Path(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("%s is not a JSON object; cannot stamp" % path.name)
        data[JSON_KEY] = rec
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return rec

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rec["engine"] = rec["engine"]
    rec["measured"] = rec["measured"]
    mark = MD_MARK + (" engine=%s measured=%s" % (rec["engine"], rec["measured"]))
    if harness:
        mark += " harness=%s" % harness
    mark += " -->"
    # Replace an existing stamp rather than stacking a second one.
    kept = [l for l in lines if not l.strip().startswith(MD_MARK)]
    path.write_text("\n".join([mark] + kept) + "\n", encoding="utf-8")
    return rec


def artifacts() -> list[Path]:
    """Every committed measurement artifact in the repo."""
    out: list[Path] = []
    for base in (ROOT / "backtest" / "docs", ROOT / "backtest" / "tests"):
        if not base.exists():
            continue
        # Every markdown under these trees carries numbers, prose or scratch:
        #   method/*.md      hand-written write-ups
        #   _*.md, _*.json   scratch artifacts a harness writes beside itself
        # The `_`-prefixed markdown family was missing from this inventory, so a
        # stamped file in it was invisible to verify(). A stamp that can never be
        # checked is not a stamp.
        out += list(base.rglob("*.md"))
        out += list(base.rglob("_*.json"))
    return sorted(set(out))


def verify(paths: list[Path] | None = None, quiet: bool = False) -> int:
    """Report artifacts whose engine stamp no longer matches the tree.

    Exit 1 only on a real mismatch. `unrecorded` is printed so the blind spot
    stays visible, but it does not fail the run.
    """
    files = paths if paths is not None else artifacts()
    live = engine_commit()
    stale, unrec, ok = [], [], []
    for p in files:
        rec = read(p)
        if not rec or rec.get("engine") in (None, "", "unknown"):
            unrec.append(p)
        elif str(rec["engine"])[:7] != live[:7]:
            stale.append((p, rec))
        else:
            ok.append((p, rec))

    if not quiet:
        def rel(p: Path) -> str:
            # Files outside the repo (tests, scratch) have no relative path.
            try:
                return str(Path(p).relative_to(ROOT)).replace("\\", "/")
            except ValueError:
                return str(p)
        print("engine under measurement: %s  (%s)" % (live, ENGINE_TRACKED[0]))
        print("=" * 62)
        print("artifacts stamped against this engine : %d" % len(ok))
        print("artifacts with no provenance recorded : %d" % len(unrec))
        print("artifacts measured against OTHER engines: %d" % len(stale))
        if stale:
            print("\nSTALE - measured against a different engine commit:")
            for p, rec in stale:
                print("   %-58s engine=%s measured=%s"
                      % (rel(p), rec.get("engine"), rec.get("measured")))
            print("\n   Re-run their harness, or the numbers in them are describing an")
            print("   engine that is not the one in the tree.")
            print()
            print("   NOTE, and this is a real limitation of this check: a stale stamp")
            print("   means the engine file moved, NOT that the numbers are wrong. Adding a")
            print("   new mode= branch to unified.py shifts the commit every artifact is")
            print("   stamped against while leaving existing books byte-identical. Re-run")
            print("   the cheap ones and compare before assuming damage: if the numbers")
            print("   come back the same, re-stamp them.")
        if unrec and not quiet:
            print("\nunrecorded (warning, not a failure):")
            for p in unrec[:25]:
                print("   %s" % rel(p))
            if len(unrec) > 25:
                print("   ... and %d more" % (len(unrec) - 25))
    return 1 if stale else 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "verify":
        return verify()
    if cmd == "show" and rest:
        rec = read(ROOT / rest[0])
        print(json.dumps(rec, indent=2) if rec else "no provenance recorded")
        return 0
    if cmd == "stamp" and rest:
        harness = None
        if "--harness" in rest:
            harness = rest[rest.index("--harness") + 1]
        print(json.dumps(stamp_current(ROOT / rest[0], harness), indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())