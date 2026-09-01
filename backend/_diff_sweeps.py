"""Compare pre-fix vs post-fix sweeps + TS/Python port parity."""
import sys

bef = open("../frontend/_sweep_before.txt", encoding="utf-8").read().splitlines()
aft = open("../frontend/_sweep_after.txt", encoding="utf-8").read().splitlines()
py = open("_sweep_py.txt", encoding="utf-8").read().splitlines()

bef_d = {l.split("|")[0]: l for l in bef}
aft_d = {l.split("|")[0]: l for l in aft}
py_d = {l.split("|")[0]: l for l in py}

changed = [d for d in bef_d if bef_d[d] != aft_d.get(d)]
print(f"bef={len(bef)} aft={len(aft)} py={len(py)}")
print(f"changed days: {len(changed)}")
for d in changed:
    b = bef_d[d]
    a = aft_d.get(d, "NO-DECL")
    flag = " <-- no longer declared" if a == "NO-DECL" else ""
    print(f"  {d}: BEFORE {b} | AFTER {a}{flag}")

# parity TS vs PY
ts_only = [d for d in aft_d if aft_d[d] != py_d.get(d)]
py_only = [d for d in py_d if py_d[d] != aft_d.get(d)]
print(f"TS-vs-PY mismatches: {len(ts_only) + len(py_only)}")
for d in sorted(set(ts_only) | set(py_only)):
    print(f"  TS {aft_d.get(d,'-')} | PY {py_d.get(d,'-')}")