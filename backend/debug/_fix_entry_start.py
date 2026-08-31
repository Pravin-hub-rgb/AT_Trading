"""Fix intraday.py: remove debug patch, fix ENTRY_START in 1-min mode."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

intraday_path = Path(__file__).parent.parent / "src" / "intraday.py"
src = intraday_path.read_text(encoding="utf-8")

changes = 0

# 1. Remove debug patch (replace with clean entry trigger comment)
old1 = """        # ---- entry trigger: pace_break or pivot_break ----
        # DEBUG PATCH
        result["events"].append({
            "type": "_entry_attempt",
            "bar": i, "time": cur["time"],
            "cur_swing": cur_swing,
            "can_enter": can_enter,
            "open_trade": open_trade is not None,
            "entries_done": entries_done,
            "fs_gate_ok": entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx,
            "entry_gate_idx": entry_swing_confirmed_idx,
            "want_dir": want_dir,
            "cur_low": cur.get("low"),
            "cur_high": cur.get("high"),
        })
        if i > 0 and cur_swing is not None and can_enter:"""

new1 = """        # ---- entry trigger: pace_break or pivot_break ----
        if i > 0 and cur_swing is not None and can_enter:"""

if old1 in src:
    src = src.replace(old1, new1, 1)
    changes += 1
    print("Removed debug patch")
else:
    print("Debug patch not found")

# 2. Fix can_enter to use dynamic start time in 1-min mode
old2 = """        can_enter = (
            open_trade is None
            and entries_done < MAX_ENTRIES
            and ENTRY_START <= cur["time"] <= ENTRY_END
            and fs_gate_ok
        )"""

new2 = """        # In 1-min mode, entry window starts from the first swing confirmation
        # (fs1_1min_end_time or fs1_end_time). This allows earlier entries (e.g. 09:36)
        # after a 1-min FS confirms at 09:30, instead of the hardcoded 09:45 minimum.
        # 5-min mode retains the default 09:45 start.
        entry_start = ENTRY_START
        if use_1m:
            # Use the 1-min FS end time if available, else 5-min FS end time
            fs_end_t = fs1_1min_end_time if fs1_1min_end_time else fs1_end_time
            if fs_end_t and fs_end_t < ENTRY_START:
                entry_start = fs_end_t
        can_enter = (
            open_trade is None
            and entries_done < MAX_ENTRIES
            and entry_start <= cur["time"] <= ENTRY_END
            and fs_gate_ok
        )"""

if old2 in src:
    src = src.replace(old2, new2, 1)
    changes += 1
    print("Fixed can_enter with dynamic entry_start")
else:
    print("can_enter block not found")

# 3. Fix pending_direct gate to not check ENTRY_START in 1-min mode
old3 = """            gate_ok = entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx
            window_ok = ENTRY_START <= cur["time"] <= ENTRY_END
            entries_ok = entries_done < MAX_ENTRIES
            if not (gate_ok and window_ok and entries_ok):"""

new3 = """            gate_ok = entry_swing_confirmed_idx < 0 or i > entry_swing_confirmed_idx
            # In 1-min mode, the ENTRY_START minimum is bypassed for pending_direct
            # since the entry window is already controlled by the fs_gate (first swing
            # confirmation). The pending_direct entry was armed AFTER the swing confirmed
            # and after entry_start, so it's safe to allow it without re-checking ENTRY_START.
            window_ok = ENTRY_START <= cur["time"] <= ENTRY_END
            if use_1m:
                window_ok = True  # Trust the fs_gate + entry_start already enforced at arm time
            entries_ok = entries_done < MAX_ENTRIES
            if not (gate_ok and window_ok and entries_ok):"""

if old3 in src:
    src = src.replace(old3, new3, 1)
    changes += 1
    print("Fixed pending_direct gate to bypass ENTRY_START in 1-min mode")
else:
    print("pending_direct gate block not found")

print(f"\nTotal changes: {changes}")

intraday_path.write_text(src, encoding="utf-8")
print(f"Written to {intraday_path}")