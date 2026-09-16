p = 'live_stuff/tests/test_entry_verify.py'
lines = open(p).readlines()

# Test 1: add qty assertion after line 147 (assert r1["status"]...)
# Find it and insert after
for i in range(len(lines)):
    if 'assert r1["status"] == "open"' in lines[i] and i < 160:
        lines.insert(i + 1, '    assert r1["qty"] == 0.001, f"C8: adopted qty must be recorded: {r1[\'qty\']}"\n')
        break

# Test 4: add qty assertion after row(db4, tid4)["status"] == "open"
for i in range(len(lines)):
    if 'assert row(db4, tid4)["status"] == "open"' in lines[i]:
        lines.insert(i + 1, '    assert row(db4, tid4)["qty"] == 0.001, "C8: normal fill qty must be recorded"\n')
        break

# Test 5: add qty assertion after row(db5, tid5)["status"] == "open"
for i in range(len(lines)):
    if 'assert row(db5, tid5)["status"] == "open"' in lines[i]:
        lines.insert(i + 1, '    assert row(db5, tid5)["qty"] == 0.001, "C8: slow fill qty must be recorded"\n')
        break

with open(p, 'w') as f:
    f.writelines(lines)
print('Test assertions added')