import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")

inv = json.loads(Path("backtest/tests/_docs_inventory.json").read_text(encoding="utf-8"))
recs = inv["docs"]

# After the restructure the documents live in signal/ method/ closed/, so the
# lookup has to walk the tree rather than assume a flat directory. Match on the
# file name alone, which is what the inventory recorded.
_docs_by_name = {p.name: p for p in Path("backtest/docs").rglob("*.md")}

# Group by the inventory's guess so the reading is organised, but the reading is
# what decides. Print enough of each document to classify it from what it says,
# not from a word count.
want = sys.argv[1] if len(sys.argv) > 1 else "all"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 999

sel = [r for r in recs if want == "all" or r["plane"] == want][:limit]
print("showing %d of %d\n" % (len(sel), len(recs)))
for r in sel:
    t = (_docs_by_name.get(r["file"])
         or (Path("backtest/docs") / r["file"])).read_text(
        encoding="utf-8", errors="replace")
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    head = lines[0][:95] if lines else "(empty)"
    body = " ".join(lines[1:5])[:300].replace("\n", " ")
    print("--- %s   [inv: %s]" % (r["file"], r["plane"]))
    print("    %s" % head)
    if body:
        print("    %s" % body)