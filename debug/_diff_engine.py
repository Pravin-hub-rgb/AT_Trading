"""Compare TS vs Python FsV2Engine outputs bar-by-bar."""
import json
import math

TS = "debug/_ts_2026-08-28.json"
PY = "debug/_py_2026-08-28.json"

with open(TS) as f:
    ts_data = json.load(f)
with open(PY) as f:
    py_data = json.load(f)

print("=" * 60)
print(f"FRONTEND (TS): {ts_data['day']} | {ts_data['totalBars']} bars")
print(f"  declared: {ts_data['final']['declared']}")
print(f"  dir:      {ts_data['final']['dir']}")
print(f"  tier:     {ts_data['final']['tier']}")
print(f"  start:    idx={ts_data['final']['startIdx']} px={ts_data['final']['startPx']}")
print(f"  end:      idx={ts_data['final']['endIdx']} px={ts_data['final']['endPx']}")
print(f"  confirmedAtIdx:  {ts_data['final']['confirmedAtIdx']}")
print(f"  confirmSource:   {ts_data['final']['confirmSource']}")
print(f"  lastConfirmHit:  {ts_data['final']['lastConfirmHit']}")
print()
print(f"BACKEND (PY): {py_data['day']} | {py_data['totalBars']} bars")
print(f"  declared: {py_data['final']['declared']}")
print(f"  dir:      {py_data['final']['dir']}")
print(f"  tier:     {py_data['final']['tier']}")
print(f"  start:    idx={py_data['final']['startIdx']} px={py_data['final']['startPx']}")
print(f"  end:      idx={py_data['final']['endIdx']} px={py_data['final']['endPx']}")
print(f"  confirmedAtIdx:  {py_data['final']['confirmedAtIdx']}")
print(f"  confirmSource:   {py_data['final']['confirmSource']}")
print(f"  lastConfirmHit:  {py_data['final']['lastConfirmHit']}")
print()
print("=" * 60)

def fmt_px(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return round(v, 2)

def deep_compare(ts_bar, py_bar, bar_idx):
    diffs = []

    def compare_val(key, tv, pv):
        if key == "eHi":
            if fmt_px(tv["px"]) != fmt_px(pv["px"]):
                diffs.append(f"  eHi.px: TS={fmt_px(tv['px'])} PY={fmt_px(pv['px'])}")
            if tv["idx"] != pv["idx"]:
                diffs.append(f"  eHi.idx: TS={tv['idx']} PY={pv['idx']}")
        elif key == "eLo":
            if fmt_px(tv["px"]) != fmt_px(pv["px"]):
                diffs.append(f"  eLo.px: TS={fmt_px(tv['px'])} PY={fmt_px(pv['px'])}")
            if tv["idx"] != pv["idx"]:
                diffs.append(f"  eLo.idx: TS={tv['idx']} PY={pv['idx']}")
        elif key in ("eHiPivot", "eLoPivot"):
            if tv is None and pv is None:
                return
            if fmt_px(tv["px"] if tv else None) != fmt_px(pv["px"] if pv else None):
                diffs.append(f"  {key}.px: TS={fmt_px(tv['px'] if tv else None)} PY={fmt_px(pv['px'] if pv else None)}")
        elif key in ("normalHighs", "normalLows", "microHighs", "microLows"):
            ts_l = [(l["px"], l["idx"], l["t"]) for l in tv] if tv else []
            py_l = [(l["px"], l["idx"], l["t"]) for l in pv] if pv else []
            if len(ts_l) != len(py_l):
                diffs.append(f"  {key} len: TS={len(ts_l)} PY={len(py_l)}")
            else:
                for j in range(len(ts_l)):
                    if ts_l[j] != py_l[j]:
                        diffs.append(f"  {key}[{j}]: TS={ts_l[j]} PY={py_l[j]}")
        elif key == "lockedLevelPx":
            tv_fmt = fmt_px(tv) if tv is not None else None
            pv_fmt = fmt_px(pv) if pv is not None else None
            if tv_fmt != pv_fmt:
                diffs.append(f"  lockedLevelPx: TS={tv_fmt} PY={pv_fmt}")
        elif key in ("startPx", "candPx"):
            if fmt_px(tv) != fmt_px(pv):
                diffs.append(f"  {key}: TS={fmt_px(tv)} PY={fmt_px(pv)}")
        elif tv != pv:
            diffs.append(f"  {key}: TS={tv} PY={pv}")

    for key in [
        "barsSeen", "eHi", "eLo", "eHiPivot", "eLoPivot",
        "dir", "baseDir", "sameSideBreaks", "oppositeSideBreaks",
        "dirConfirmed", "dirConfirmedIdx",
        "locked", "lockedLevelPx",
        "startIdx", "startPx", "candIdx", "candPx",
        "sustainStreak", "declared",
        "normalHighs", "normalLows", "microHighs", "microLows",
    ]:
        compare_val(key, ts_bar.get(key), py_bar.get(key))

    return diffs

n = min(len(ts_data["states"]), len(py_data["states"]))
total_diffs = 0
print(f"Comparing {n} bars...")
print()
for i in range(n):
    ts_bar = ts_data["states"][i]
    py_bar = py_data["states"][i]
    diffs = deep_compare(ts_bar, py_bar, i)
    if diffs:
        t = ts_bar["t"]
        total_diffs += len(diffs)
        print(f"BAR {i:3d} ({t}) DIFFS:")
        for d in diffs:
            print(d)

print()
print("=" * 60)
if total_diffs == 0:
    print("PERFECT MATCH -- zero diffs across all bars!")
else:
    print(f"{total_diffs} total diffs found")
