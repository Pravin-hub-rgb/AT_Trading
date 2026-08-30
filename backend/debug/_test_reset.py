"""Test FsV2Engine.reset()"""
import sys
sys.path.insert(0, ".")

from src.swing_engine import FsV2Engine

eng = FsV2Engine()
eng.reset(100.0, 5, "09:25")

print(f"bars_seen  = {eng.bars_seen}  (expect 1)")
print(f"e_hi       = ({eng.e_hi.px}, {eng.e_hi.idx}, '{eng.e_hi.time}')  (expect 100.0, 5, '09:25')")
print(f"e_lo       = ({eng.e_lo.px}, {eng.e_lo.idx}, '{eng.e_lo.time}')  (expect 100.0, 5, '09:25')")
print(f"declared    = {eng.declared}  (expect False)")
print(f"dir         = {eng.dir}  (expect None)")
print(f"walker type = {type(eng.walker).__name__}  (expect WalkerEngine)")
print("reset() OK")
