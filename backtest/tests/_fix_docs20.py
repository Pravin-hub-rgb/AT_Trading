import io
p = "backtest/docs/EXP40C_EXP41_WAGE_EXT.md"
L = io.open(p, encoding="utf-8").read().splitlines(True)
# title: append / 49
ti = next(i for i, l in enumerate(L) if l.startswith("# EXP 40c"))
if "/ 49 " not in L[ti]:
    L[ti] = L[ti].replace("47 / 48 \u2014", "47 / 48 / 49 \u2014")
# file map: insert exp49 row after the exp47 row
fi = next(i for i, l in enumerate(L) if "exp47_yearly_stats.py" in l)
row = "| `backtest/tests/exp49_partial_champion.py`, `_exp49_out.txt`, `_exp49_results.json` | **Exp49 harness** - partial exits (exp_partial_r) + champion reproduction (sw10/sw20) + seg6 WF. Gates: identity + matrix + 4 fine pins + canaries. Section 20. | OK RUNNABLE - keep |\n"
L.insert(fi + 1, row)
io.open(p, "w", encoding="utf-8", newline="").write("".join(L))
print("title + file map updated")
