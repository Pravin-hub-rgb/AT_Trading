"""exp_registry_snapshot - the gate for splitting the registry, and the gate
for any later change to it.

WHY THIS EXISTS

experiment_registry.py is 223 books in one file. It is being split into a
package because a file that size cannot be reviewed, and because a family
cannot be moved without reading the other 222 books to find its edges.

A refactor of a registry is not supposed to change a single number, and the
failure mode is not a crash - it is a book that quietly stops being in
EXPERIMENTS, or an alias that stops resolving, or one dict that loses a line
to a bad copy. None of those raise. They show up weeks later as a shortlist
that reorders.

So this snapshots the registry's whole public surface to JSON, and compares two
snapshots field by field. Run it before a refactor and after:

    python exp_registry_snapshot.py write  before.json
    ... make the change ...
    python exp_registry_snapshot.py check before.json

`check` compares every key of EXPERIMENTS deep, plus ALIASES, BP,
ENGINE_DEFAULTS, GROUPS and both thresholds. It does not compare set
membership - a book that is missing entirely is the failure this exists to
catch, and it is reported by name.
"""
import sys, json, argparse, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

PUBLIC = ("EXPERIMENTS", "ALIASES", "BP", "ENGINE_DEFAULTS", "GROUPS",
          "SHORTLIST_IS_MIN", "SHORTLIST_OOS_MIN", "book", "alias_of",
          "shortlisted")

# ---------------------------------------------------------------------------
# The split map: which family each section of the one-file registry belongs to.
# Keys are the LINE NUMBERS of the "# ===== ... =====" section comments. Keys
# that are generic rules (2577 / 2579) sit inside the champions block.
# ---------------------------------------------------------------------------
_FAMILY_BY_SECTION = {
    44: "trail", 1974: "trail", 3817: "trail",
    235: "sweep", 502: "sweep", 578: "sweep", 902: "sweep",
    1227: "signal", 1254: "signal", 1394: "signal", 1493: "signal",
    1546: "signal", 1600: "signal",
    1662: "risk", 2090: "risk", 2691: "risk", 2754: "risk", 3197: "risk",
    4103: "risk", 4129: "risk",
    2791: "d3", 2963: "d3", 3252: "d3", 3494: "d3", 3645: "d3",
    3702: "d3", 3876: "d3", 3925: "d3", 4025: "d3",
    2337: "kingsweep", 2417: "kingsweep", 2452: "kingsweep",
    2478: "kingsweep", 2501: "kingsweep", 4225: "kingsweep",
    2577: "kingsweep", 2579: "kingsweep",
}

_ORDER = ["trail", "sweep", "signal", "risk", "d3", "kingsweep"]

MODULE_NAMES = {
    "trail": "trail.py", "sweep": "sweep.py", "signal": "signal.py",
    "risk": "risk.py", "d3": "d3.py", "kingsweep": "kingsweep.py",
}

TITLES = {
    "trail": "TRAIL - exit-side trail shapes, the trail sweep surface, trail quality.",
    "sweep": "SWEEP - the grid sweeps: final audit, script-grid, knob-gap.",
    "signal": "SIGNAL - one-position books: FS exit, directional entry, serial, the signal book.",
    "risk": "RISK - decay gates, window caps, risk width, entry quality, baselines.",
    "d3": "D3 - the loss-autopsy families.",
    "kingsweep": "KINGSWEEP - the kingsweep, the optimal lanes, and our champions.",
}

MODULE_HEADER = '''"""{title}

Part of the experiment registry split; see exp_registry_snapshot.py for the
check that guarantees this is a pure move. Every entry is a data dict - to add
a book, drop it in this family and it appears in EXPERIMENTS on next import.
"""

'''

def _split_sections(lines):
    """Slice the EXPERIMENTS body into per-family line lists, byte-exact."""
    body_start = next(i for i, l in enumerate(lines) if l.startswith("EXPERIMENTS = {"))
    close = next(i for i in range(body_start + 1, len(lines))
                 if lines[i].rstrip() == "}")
    starts = sorted(_FAMILY_BY_SECTION)
    buckets = {fam: [] for fam in _ORDER}
    # Anything between the dict open and the first header (the schema comment)
    # rides with the first section so no book loses its own comment block.
    buckets[_FAMILY_BY_SECTION[starts[0]]].extend(lines[body_start + 1:starts[0] - 1])
    for idx, start in enumerate(starts):
        # Slice up to (NOT including) the next header's line. For the LAST
        # section stop before the original closing "}" (index close) so every
        # family slice is brace-free and each BOOKS gets exactly one "}" from
        # the writer below. Slicing to close+1 instead puts a second brace in
        # the last family and it fails with "unmatched '}'".
        end = starts[idx + 1] if idx + 1 < len(starts) else close
        buckets[_FAMILY_BY_SECTION[start]].extend(lines[start - 1:end])
    return buckets

def write_modules():
    src = (ROOT / "backtest/tests/experiment_registry.py").read_text(encoding="utf-8")
    buckets = _split_sections(src.splitlines())
    pkg = ROOT / "backtest/tests/registry"
    pkg.mkdir(exist_ok=True)
    for fam in _ORDER:
        body = "\n".join(buckets[fam]).rstrip() + "\n"
        # Each family's slice holds its section comments and book dicts but NOT
        # the final "}" that closed the original EXPERIMENTS (that brace belongs
        # to the last section only). Close it per-family so each BOOKS is valid.
        text = MODULE_HEADER.format(title=TITLES[fam]) + "BOOKS = {\n" + body.rstrip("\n") + "\n}\n"
        (pkg / MODULE_NAMES[fam]).write_text(text, encoding="utf-8")
        print("registry/%s: %d lines" % (MODULE_NAMES[fam], text.count("\n")))
    _write_helpers(pkg)
    _write_base(pkg)
    _write_groups(pkg, src)
    return pkg

HELPERS = '''"""Alias resolution and the shortlist rule over the merged registry.

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
'''

BASE = '''"""The base every book inherits from, and the source of BP.

Split out from the single-file registry. ENGINE_DEFAULTS is the engine's own
behaviour, not filters - see pipeline/BASELINE.md, which is why a book
overriding all ten is a different book rather than a filtered baseline.
"""

ENGINE_DEFAULTS = {
    "sl_buf_atr": 0.01,
    "ext_stop_r": 1.5,
    "chop_thresh": 61.8,
    "mode": "b2_vs_flip_chop",
    "cooldown_bars": 10,
    "max_consecutive_losses": 3,
    "atr_low_thresh": 0.35,
    "atr_high_thresh": 0.65,
    "htf_rr": 3.0,
    "window_end": "exit",
}

# BP = BASE with chop_thresh overridden to 58.0 (production tuning)
BP = {**ENGINE_DEFAULTS, "chop_thresh": 58.0}
'''

def _write_helpers(pkg):
    (pkg / "helpers.py").write_text(HELPERS, encoding="utf-8")
    print("registry/helpers.py")

def _write_base(pkg):
    (pkg / "base.py").write_text(BASE, encoding="utf-8")
    print("registry/base.py")

def _write_groups(pkg, src):
    """GROUPS is copied verbatim - it is a name -> [book keys] map, and
    rewriting it by hand risks dropping a key. A book here may be an alias."""
    lines = src.splitlines()
    gi = next(i for i, l in enumerate(lines) if l.startswith("GROUPS = {"))
    gj = next(i for i in range(gi + 1, len(lines)) if lines[i].rstrip() == "}")
    block = "\n".join(lines[gi:gj + 1])
    text = ('"""Batch-run groups: a name -> list of book keys, for `run_experiment '
            '--group`.\n\nCopied verbatim from the one-file registry. A key in a '
            'group may be an alias;\nrun_experiment resolves it.\n"""\n\n'
            + block + "\n")
    (pkg / "groups.py").write_text(text, encoding="utf-8")
    print("registry/groups.py")


def snapshot(reg):
    """Everything a caller can import. Books are stored raw, not summarised -
    a count would hide a changed param, which is the thing worth catching."""
    return {
        "EXPERIMENTS": {k: v for k, v in reg.EXPERIMENTS.items()},
        "ALIASES": dict(reg.ALIASES),
        "BP": dict(reg.BP),
        "ENGINE_DEFAULTS": dict(reg.ENGINE_DEFAULTS),
        "GROUPS": {k: v for k, v in reg.GROUPS.items()},
        "SHORTLIST_IS_MIN": reg.SHORTLIST_IS_MIN,
        "SHORTLIST_OOS_MIN": reg.SHORTLIST_OOS_MIN,
    }


def _diff(what, a, b, out):
    if isinstance(a, dict) and isinstance(b, dict):
        only_a = sorted(set(a) - set(b))
        only_b = sorted(set(b) - set(a))
        for k in only_a[:20]:
            out.append("%s: only in BEFORE: %s" % (what, k))
        for k in only_b[:20]:
            out.append("%s: only in AFTER:  %s" % (what, k))
        if len(only_a) > 20:
            out.append("%s: ...and %d more only in BEFORE" % (what, len(only_a) - 20))
        if len(only_b) > 20:
            out.append("%s: ...and %d more only in AFTER" % (what, len(only_b) - 20))
        for k in sorted(set(a) & set(b)):
            if a[k] != b[k]:
                out.append("%s[%s]: differs" % (what, k))
        return
    if a != b:
        out.append("%s: %r -> %r" % (what, a, b))


def compare(old, new):
    out = []
    for key in ("EXPERIMENTS", "ALIASES", "BP", "ENGINE_DEFAULTS", "GROUPS"):
        _diff(key, old.get(key), new.get(key), out)
    for key in ("SHORTLIST_IS_MIN", "SHORTLIST_OOS_MIN"):
        if old.get(key) != new.get(key):
            out.append("%s: %r -> %r" % (key, old.get(key), new.get(key)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["write", "check", "show", "split"])
    ap.add_argument("path", nargs="?", help="snapshot file")
    ap.add_argument("--module", default="experiment_registry",
                    help="module to snapshot (default experiment_registry)")
    a = ap.parse_args(argv)

    if a.mode == "split":
        pkg = write_modules()
        print("\nmodules written to %s" % pkg)
        print("Next: build registry/__init__.py, replace experiment_registry.py")
        print("with the re-export, then `check` against your before snapshot.")
        return 0

    reg = importlib.import_module(a.module)
    missing = [n for n in PUBLIC if not hasattr(reg, n)]
    if missing:
        print("FAIL: %s does not export %s" % (a.module, ", ".join(missing)))
        return 2
    snap = snapshot(reg)

    if a.mode == "show":
        e = snap["EXPERIMENTS"]
        books = [k for k, v in e.items() if isinstance(v, dict)]
        print("EXPERIMENTS rows : %d (%d books, %d aliases)"
              % (len(e), len(books), len(e) - len(books)))
        print("ALIASES         : %d" % len(snap["ALIASES"]))
        print("GROUPS          : %d" % len(snap["GROUPS"]))
        print("pinned books    : %d" % sum(1 for k in books if (e[k].get("pins") or {}).get("n")))
        return 0

    if a.mode == "write":
        if not a.path:
            print("write needs a path")
            return 2
        pathlib.Path(a.path).write_text(json.dumps(snap, indent=1, sort_keys=True,
                                                  default=str), encoding="utf-8")
        print("wrote %s (%d rows)" % (a.path, len(snap["EXPERIMENTS"])))
        return 0

    # check
    if not a.path:
        print("check needs a path")
        return 2
    old = json.loads(pathlib.Path(a.path).read_text(encoding="utf-8"))
    # the before-file was written with default=str, so tuples came back as
    # lists. That is fine for comparison as long as both sides are normalised.
    bad = compare(old, json.loads(json.dumps(snap, default=str)))
    if bad:
        print("FAIL: %d difference(s) against %s" % (len(bad), a.path))
        for b in bad[:60]:
            print("    - %s" % b)
        if len(bad) > 60:
            print("    ...and %d more" % (len(bad) - 60))
        return 1
    print("PASS: %s matches %s exactly." % (a.module, a.path))
    print("      %d EXPERIMENTS rows, %d ALIASES, %d GROUPS."
          % (len(snap["EXPERIMENTS"]), len(snap["ALIASES"]), len(snap["GROUPS"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())