import sys
sys.path.insert(0, ".")
from src.config import DATA_DIR
import json
fs_file = DATA_DIR / "first_swing_manual.json"
print("Path:", fs_file)
print("Exists:", fs_file.exists())
if fs_file.exists():
    data = json.loads(fs_file.read_text())
    print("Aug 28:", data.get("2026-08-28"))
    print("All days:", list(data.keys())[:10])
else:
    print("Not found. DATA_DIR:", DATA_DIR)
    if DATA_DIR.exists():
        print("Contents:", list(DATA_DIR.iterdir()))
    else:
        print("DATA_DIR not found")
