"""Show all manual FS data to see if user has set custom FS for 28 Aug."""
import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import json
fs_file = DATA_DIR / "first_swing_manual.json"
data = json.loads(fs_file.read_text())
for d in sorted(data.keys())[-15:]:
    print(f"  {d}: {data[d]}")
