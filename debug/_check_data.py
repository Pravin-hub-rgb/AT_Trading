import sys
sys.path.insert(0, "backend")
from src.config import DATA_DIR, ROOT_DIR, BACKEND_DIR
print("DATA_DIR:", DATA_DIR)
print("ROOT_DIR:", ROOT_DIR)
print("BACKEND_DIR:", BACKEND_DIR)
import os
print("DATA_DIR exists:", os.path.exists(DATA_DIR))
data_file = DATA_DIR / "nifty_5min.csv"
print("5min data file:", data_file)
print("File exists:", os.path.exists(data_file))
if os.path.exists(data_file):
    print("File mtime:", os.path.getmtime(data_file))
    print("File size:", os.path.getsize(data_file))
