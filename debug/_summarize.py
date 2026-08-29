"""Summarize final results across all test days."""
import json

days = ["2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28"]
lines = []
lines.append(f"{'Day':<12} {'Status':<7} {'TS':<40} {'PY':<40}")
lines.append("-" * 100)
all_match = True
for day in days:
    try:
        with open(f"debug/_ts_{day}.json") as f: ts = json.load(f)
        with open(f"debug/_py_{day}.json") as f: py = json.load(f)
    except FileNotFoundError:
        lines.append(f"{day:<12} MISSING")
        all_match = False
        continue
    ts_f = ts["final"]
    py_f = py["final"]
    match = "MATCH" if ts_f == py_f else "DIFF"
    if ts_f != py_f:
        all_match = False
    ts_str = f"{ts_f['dir']}@{ts_f['startIdx']}-{ts_f['endIdx']}({ts_f['confirmSource']})"
    py_str = f"{py_f['dir']}@{py_f['startIdx']}-{py_f['endIdx']}({py_f['confirmSource']})"
    lines.append(f"{day:<12} {match:<7} {ts_str:<40} {py_str:<40}")

lines.append("-" * 100)
lines.append("ALL MATCH!" if all_match else "SOME DIFFS!")
with open("debug/_summary.txt", "w") as f:
    f.write("\n".join(lines))
print("\n".join(lines))
