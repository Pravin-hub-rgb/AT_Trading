"""Write the measured numbers into the registry pins.

WHAT THIS DOES
--------------
Reads the measurements already collected in _rerun_state.json and rewrites the
`pins` dict of every affected book inside backtest/tests/registry/*.py.

exp_repin_stale.py can emit a patch but deliberately never edits the registry -
it prints lines to paste by hand. That is the right default for a tool nobody has
looked at yet, and the wrong answer once the owner has said the numbers are real
and the pins have to move. So this applies them.

HOW THE EDIT IS MADE SAFE
-------------------------
Not by string substitution. Each registry file is parsed with ast, every book's
`pins` value node is located with its exact line/col span, and only that span is
replaced. Keys, params, desc, status and every comment in the file survive
byte-for-byte, because nothing outside the pins span is ever touched.

If a book has no pins, or the old pin is None, it is left alone - there is nothing
to update. Field shape is preserved through exp_repin_stale.new_pin(), which only
rewrites keys the old pin already carried, so a book that never recorded `win` does
not suddenly grow one, and OOS fields keep their oos_ prefix.

The registry is tracked in git, so `git diff` is the revert.
"""
import ast
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

import exp_repin_stale as repin
from experiment_registry import EXPERIMENTS

REG_DIR = HERE / "registry"
STATE = HERE / "_rerun_state.json"
CARD = HERE / "_rerun_applied.json"
IS_FIELDS = ("n", "net", "dd_net", "win")
OOS_FIELDS = ("oos_n", "oos_net", "oos_dd_net", "oos_win")
OOS_SRC = {"oos_n": "n", "oos_net": "net", "oos_dd_net": "dd_net", "oos_win": "win"}


def fmt(key, v):
    if v is None:
        return "None"
    if isinstance(v, float):
        # win / oos_win are fractions carried to three decimals across the whole
        # registry (0.102 .. 0.447). Two decimals turns 0.423 into 0.42, which
        # silently loses the field's precision and makes the round-trip fail.
        p = 3 if key in ("win", "oos_win") else 2
        s = ("%.*f" % (p, v)).rstrip("0").rstrip(".")
        return s if s else "0"
    return repr(v)


def render(pin, multiline):
    """Match the file's own style: one line when it fits, wrapped otherwise."""
    items = ['"%s": %s' % (k, fmt(k, pin[k])) for k in IS_FIELDS if k in pin]
    items += ['"%s": %s' % (k, fmt(k, pin[k])) for k in OOS_FIELDS if k in pin]
    one = "{" + ", ".join(items) + "}"
    if not multiline or len(one) <= 88:
        return one
    head = items[:2]
    tail = items[2:]
    out = "{" + head[0] + ", " + head[1] + ",\n                 "
    out += ", ".join(tail) + "}"
    return out


def collect_spans():
    """book key -> (file, start_offset, end_offset, old_pin_dict, was_multiline)"""
    spans = {}
    for f in sorted(REG_DIR.glob("*.py")):
        if f.name in ("__init__.py", "base.py", "helpers.py", "retired.py",
                      "groups.py", "trail.py"):
            # trail.py DOES hold books; re-add below
            if f.name != "trail.py":
                continue
        src = f.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            raise SystemExit("%s does not parse: %s" % (f.name, e))
        lines = src.splitlines(keepends=True)
        offs = [0]
        for ln in lines:
            offs.append(offs[-1] + len(ln))
        books = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    getattr(t, "id", None) == "BOOKS" for t in node.targets):
                books = node.value
        if books is None:
            continue
        for k, v in zip(books.keys, books.values):
            if not isinstance(k, ast.Constant) or not isinstance(v, ast.Dict):
                continue
            for pk, pv in zip(v.keys, v.values):
                if getattr(pk, "value", None) != "pins":
                    continue
                if not (isinstance(pv, ast.Dict) and pv.keys):
                    continue
                key = k.value
                spans[key] = (f, offs[pv.lineno - 1] + pv.col_offset,
                              offs[pv.end_lineno - 1] + pv.end_col_offset,
                              ast.literal_eval(pv),
                              "\n" in src[offs[pv.lineno - 1] + pv.col_offset:
                                          offs[pv.end_lineno - 1] + pv.end_col_offset])
    return spans


def main():
    st = json.loads(STATE.read_text(encoding="utf-8"))
    spans = collect_spans()

    plan = {}
    for k, v in st.items():
        if not v.get("done"):
            continue
        e = v["eras"]
        if e.get("is", {}).get("error") or e.get("oos", {}).get("error"):
            print("  SKIP (error) %s" % k)
            continue
        old = spans.get(k, (None,))[3]
        if not old:
            continue
        new = repin.new_pin(old, e["is"], e["oos"])
        if new == old:
            continue
        plan[k] = (old, new)

    by_file = {}
    for k, (old, new) in plan.items():
        by_file.setdefault(spans[k][0], []).append(k)

    print("=" * 74)
    print("RE-PIN  %d books across %d registry file(s)" % (len(plan), len(by_file)))
    print("=" * 74)
    total_fields = 0
    applied = {}
    for f, keys in sorted(by_file.items()):
        src = f.read_text(encoding="utf-8")
        edits = []
        for k in keys:
            _f, s, e, old, ml = spans[k]
            new = plan[k][1]
            edits.append((s, e, render(new, ml)))
            applied[k] = {"file": f.name, "old": old, "new": new}
        edits.sort(reverse=True)
        for s, e, txt in edits:
            src = src[:s] + txt + src[e:]
        f.write_text(src, encoding="utf-8")
        nf = sum(len([x for x in plan[k][1]]) for k in keys)
        total_fields += nf
        print("  %-18s %3d books" % (f.name, len(keys)))

    print("\n  %d books, %d pin fields rewritten" % (len(plan), total_fields))

    # verify by re-reading the registry from disk
    for m in list(sys.modules):
        if m.startswith("experiment_registry") or m.startswith("registry"):
            del sys.modules[m]
    import importlib
    fresh = importlib.import_module("experiment_registry").EXPERIMENTS
    bad = []
    for k, rec in applied.items():
        got = (fresh.get(k) or {}).get("pins")
        want = rec["new"]
        if got != want:
            bad.append((k, want, got))
    print("  verification: %d/%d books read back exactly as written"
          % (len(applied) - len(bad), len(applied)))
    if bad:
        print("  MISMATCHES:")
        for k, want, got in bad[:10]:
            print("    %-36s want %s" % (k, want))
            print("    %-36s got  %s" % ("", got))
        return 1

    CARD.write_text(json.dumps(applied, indent=1, sort_keys=True), encoding="utf-8")
    print("  card -> %s" % CARD.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
