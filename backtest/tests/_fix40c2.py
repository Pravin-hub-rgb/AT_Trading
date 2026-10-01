import io

# --- 1) craze comment: replace the two contradictory blocks with one correct one ---
p1 = "backtest/tests/test_experiments_craze.py"
lines = io.open(p1, encoding="utf-8").read().splitlines(True)
start = next(i for i, l in enumerate(lines) if l.startswith("    # 3g) N5/N6 wage gate"))
end = next(i for i, l in enumerate(lines) if l.startswith("    s = s.replace(t6f, t6f +"))
new_block = (
    "    # 3g) N5/N6 wage gate: skip entries inside HTF windows younger than\n"
    "    #     exp_wage_h hours. Age = signal-bar ts - RAW window start ts (the\n"
    "    #     window's flip/b2 1h entry-bar OPEN; no +2700 shift). This is the\n"
    "    #     FINAL convention: validated 4/4 exact vs the user's coarse matrix\n"
    "    #     (265/294/304/307t) and 4/4 vs the user's fine table (196.3/\n"
    "    #     231.1/197.2/179.1). See docs/EXP40C_EXP41_WAGE_EXT.md sections\n"
    "    #     3.1 and 4.3. The deleted Exp40/41 harness's N5 rows (275t/+224.5\n"
    "    #     etc.) used an unrecoverable convention and are non-authoritative;\n"
    "    #     earlier +2700, closed-candle, canonical-parent and leg-anchor\n"
    "    #     variants were all tested and rejected (audit trail: doc sec 4.3).\n"
    "    t6f = '        if not (s + 2700 < bar_ts <= e + 2700): continue\\n'\n"
    "    assert s.count(t6f) == 1, \"window membership\"\n"
)
lines[start:end] = [new_block]
io.open(p1, "w", encoding="utf-8", newline="").write("".join(lines))
print("craze comment fixed")

# --- 2) doc: mojibake cleanup, file-map note, rewrite tail (sections 10-12) ---
p2 = "backtest/docs/EXP40C_EXP41_WAGE_EXT.md"
txt = io.open(p2, encoding="utf-8").read()
for a, b in (("\u00c2\u00a7", "\u00a7"), ("\u00e2\u20ac\u201d", "\u2014"),
             ("\u00e2\u20ac\u201c", "\u2013"), ("\u00e2\u2020\u2019", "\u2192"),
             ("\u00c2", "")):
    txt = txt.replace(a, b)
note = (
    "* `backtest/tests/test_verify_wage.py` - DELETED by the second lane after\n"
    "  producing the section 10 verification numbers (violation of section 12\n"
    "  rule 6). Numbers cross-checked against _exp40c_out.txt Phase C.\n"
)
tl = txt.splitlines(True)
i1 = next(i for i, l in enumerate(tl) if l.startswith("## 1. Engine"))
tl.insert(i1, note)
txt = "".join(tl)
i10 = txt.index("## 10. Independent verification")
txt = (txt[:i10]
       + io.open("backtest/tests/_doc_tail1.md", encoding="utf-8").read()
       + io.open("backtest/tests/_doc_tail2.md", encoding="utf-8").read())
io.open(p2, "w", encoding="utf-8", newline="").write(txt)
print("doc rewritten (mojibake cleaned, tail = new sections 10-12)")
