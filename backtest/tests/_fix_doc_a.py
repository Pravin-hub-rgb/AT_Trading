import io
p = "backtest/docs/method/EXP40C_EXP41_WAGE_EXT.md"
L = io.open(p, encoding="utf-8").read().splitlines(True)
i0 = next(i for i, l in enumerate(L) if l.startswith("## A."))
i1 = next(i for i, l in enumerate(L) if l.startswith("## 1."))
new = """## A. File map — every file, what it is, status

Scope: this experiment line (exp40c / exp41 / exp42) plus everything they
import or produce. Deletion policy (§12 rule 6): **nothing in this list gets
deleted** — harnesses stay runnable, outputs stay on disk. The only file ever
deleted in this line is `test_verify_wage.py` (deleted by the second
verification lane, documented in the table).

| File | What it is | Status |
|---|---|---|
| `backtest/tests/exp40c_wage_gate.py` | **Exp40c harness** — identity gate + Phase A matrix validation + Phase B coarse 18-cell matrix + Phase C fine 18-cell matrix. Writes `_exp40c_results.json`. Exports `BP` / `fund` / `run_coarse`, reused by exp41 and exp42. | ✅ RUNNABLE — keep |
| `backtest/tests/exp41_wf_leaders.py` | **Exp41 harness** — Phase 1: missing OPT-cd10 × ext2.0 cells; Phase 2: segmented walk-forward (6 segs, fixed configs) on 8 leader configs. Writes `_exp41_results.json`. Imports `BP/fund/run_coarse` from exp40c. | ✅ RUNNABLE — keep |
| `backtest/tests/exp42_wage_sweep.py` | **Exp42 harness** — wage-threshold sweep {0,12,18,24,36,48} × {lb30, A4, OPT-cd10, lb14} at ext1.5 + lb14 re-check + segmented WF on the same sweep ledgers. Gates: identity + user coarse matrix + 6 fine pins to exp40c Phase C; aborts on any mismatch. Writes `_exp42_results.json`. | ✅ RUNNABLE — keep |
| `backtest/tests/test_experiments_craze.py` | The **craze module** — builds an instrumented copy of the shipped engine via `build_module()` and patches in experiment knobs (`exp31_lb`, `exp_persist`, `exp_mltf`, `exp_wage_h`, …). The **wage gate lives here** (§3.1 for the exact patch code). | ✅ patched, identity-gated — keep |
| `backtest/tests/exp40b_ext25_a4_opt.py` | **STALE legacy runner** — its `main()` predates the current `build_module()` signature (crashes on `build_module(split_mb=True)`; pre-existing, never touched). Superseded by exp40c. Do not run its `main()`. | ⚠️ stale — keep for record only |
| `backtest/tests/_tmp_open.py` | Legacy ad-hoc probe (uses the original `test_experiments.py`, no wage/ext knobs). Predates exp40c. | record only — keep |
| `backtest/tests/_fix40c2.py` | One-shot patch script: fixed the contradictory wage-gate comment in the craze module, cleaned doc encoding, installed doc §10–§12. | patch audit trail — keep |
| `backtest/tests/_fix42.py` | One-shot patch script: repaired exp42's scrambled insert seam (reordered lines). | patch audit trail — keep |
| `backtest/tests/_doc_tail1.md`, `_doc_tail2.md` | Source text of doc §10–§12, applied by `_fix40c2.py`. | keep |
| `backtest/tests/_exp40c_results.json` | Full exp40c matrix, machine-readable (coarse + fine, 18 cells each). | output |
| `backtest/tests/_exp40c_out.txt` / `_exp40c_err.txt` | exp40c console log / stderr (err empty on final run). | output |
| `backtest/tests/_exp41_results.json` | Full exp41 output (cells + WF), machine-readable. | output |
| `backtest/tests/_exp41_out.txt` / `_exp41_err.txt` | exp41 console log / stderr (err empty on final run). | output |
| `backtest/tests/_exp42_results.json` | Full exp42 output (sweep + WF), machine-readable. | output |
| `backtest/tests/_exp42_out.txt` / `_exp42_err.txt` | exp42 console log / stderr (err empty). | output |
| `backtest/tests/_exp40b_out.txt`, `_exp40b_err.txt`, `_exp40b_results.json` | Stale exp40b legacy outputs (from before the current gate). | record only |
| `backtest/tests/test_verify_wage.py` | Second verification lane's script that produced §10's numbers — **DELETED by that lane** after running (violation of §12 rule 6). Its numbers were cross-checked against `_exp40c_out.txt` Phase C and match to the decimal. Do not delete replacements. | ❌ deleted by second lane — documented |
| `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` | The shipped engine all rows share. **Never modified.** | production |
| `backtest/tests/test_experiments.py` | Original shipped `simulate_v18_experiments` (used by legacy probes like `_tmp_open.py`). Not used by 40c/41/42 (they use the craze module). | untouched |

**Lineage note:** the ORIGINAL deleted Exp40/41 harness (whose gate code was
unrecoverable) is what exp40c rebuilt and validated — its replacement is the
asserted craze patch, which is *stricter* (identity gate + external matrix
check + fine pins). Nothing else in this line has ever been deleted.

"""
L[i0:i1] = [new]
io.open(p, "w", encoding="utf-8", newline="").write("".join(L))
print("file map rewritten: %d lines total" % len(L))
