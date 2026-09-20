import io
p = "live_stuff/tests/exp42_wage_sweep.py"
L = io.open(p, encoding="utf-8").read().splitlines(True)
# current layout: 1-64 part1+main start (ends 'print("PHASE 1...")'),
# 65-92 phase2+main end, 93 blank, 94-106 phase1 loop body (correct indent,
# wrong place), 107 blank, 108-116 duplicated constants -> discard.
assert L[91].startswith("if __name__"), L[91]
assert L[93].startswith(" for tag"), L[93]
assert L[105].startswith(" print(flush=True)"), L[105]
new = L[:64] + L[93:106] + L[64:92]
io.open(p, "w", encoding="utf-8", newline="").write("".join(new))
print("exp42 reordered: %d lines" % len(new))
