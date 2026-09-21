# EXP 43 — loss autopsy, runner preservation, parent-window diagnostics

**Date:** 2026-09-20. Branch: `experiments/v19-plus`.
**Harness:** `live_stuff/tests/exp43_loss_autopsy.py` → `_exp43_out.txt` / `_exp43_results.json`.
**Run:** `python live_stuff/tests/exp43_loss_autopsy.py 1> live_stuff/tests/_exp43_out.txt 2> live_stuff/tests/_exp43_err.txt` (≈54s).
**Gates (all passed):** identity (flags-off == shipped, n=351) + user lb30-w24 coarse matrix 4/4 + **8/8 fine pins** to exp40c/exp42 Phase C.

---

## 1. Theory — why this experiment exists

This strategy's edge is **tail-dependent**: many small losses (−1R each) are
paid for by rare big runners (≥4R). Before inventing more filters, measure
the structure. Five research questions, from the research-methods review:

* **RQ1 (bug canary):** recompute every w24-ledger trade's window age with the
  same join the gate uses — all must be ≥24h. Any miss = convention drift.
* **RQ2 (decomposition):** what exactly does w24 remove per lane — n, gross,
  NET, WR, median, tails, R by year? Systematic removal or one lucky cluster?
* **RQ3 (runner amputation):** how many ≥3R/≥4R/≥5R/≥10R runners sit in the
  removed young bucket? (the "did we cut off the tail that pays" check)
* **RQ4 (mechanism split):** the pre-fill wage gate does two things at once —
  (a) removes young-window trades, (b) SHIFTS every subsequent entry (busy/
  cooldown chains re-time). How much of each lane's w24 delta is (a) vs (b)?
  `d_removal = −net(removed bucket)`; `chain_shift = d_actual − d_removal`.
* **RQ5 (HTF side):** do LTF trades inherit the parent window's fate? LTF avgR
  by parent-HTF outcome and by window-age bucket. Is there causal HTF-side
  structure left AFTER wage+ext?

Configs: {lb30, A4, lb14, OPT-cd10} × {w0, w24}, all ext1.5, fine fills.

---

## 2. Results

### 2.1 RQ1 — no bugs
Every w24-ledger trade recomputes age ≥24h on all 4 lanes (**0 violations**);
trades carry the regime tag (264–265/265 aged; 1/lane has no dir-matched
covering window — boundary case, not a bug). The rebuilt gate's convention is
internally consistent.

### 2.2 RQ2+RQ3+RQ4 — the decomposition (the big finding)

| lane | w0 NET | w24 NET | d_actual | removed <24h (n / net / WR) | d_removal | **chain-shift** |
|---|---|---|---|---|---|---|
| lb30 | +196.3 | +185.0 | **−11.3** | 99t / −35.7 / 23.2% | +35.7 | **−47.0** |
| A4 | +203.3 | +223.1 | +19.8 | 109t / −15.4 / 23.9% | +15.4 | +4.4 |
| lb14 | +148.0 | +193.7 | +45.7 | 97t / **−56.2** / **15.5%** | +56.2 | −10.5 |
| OPT-cd10 | +259.4 | **+337.7** | **+78.3** | 135t / −25.6 / 18.5% | +25.6 | **+52.7** |

**The w24 gate is NOT primarily a trade-quality filter — it is a timing
intervention.** On the champion, +52.7 of the +78.3 comes from chain
re-timing (subsequent entries land in different spots), only +25.6 from
removing young trash. On lb30 the SAME removal logic is genuinely good
(+35.7, systematic: −5.3/−9.4/−4.0/+3.2 across 2023–26) but the chain-shift
**destroys −47.0** — that is the entire lb30 mystery solved: w24 fails there
not because young windows are fine, but because the re-timed downstream
entries cost more than the trash removal gains.

**Runner amputation is real:** the removed young buckets contain
lb30 5×≥4R (+31.2), A4 5×≥4R + one ≥10R (+53.1 + 27.0), lb14 3×≥4R (+20.9),
OPT-cd10 6×≥4R + one ≥10R (+85.5 + 50.9). The champion amputates 136R of
runners from its ledger — and still nets +78, because the delayed entries
recapture runners elsewhere. lb14 amputates the least and is the only lane
where removal is negative in ALL FOUR years (−16.3/−14.4/−5.2/−0.9) — the
cleanest, most systematic case, matching its DD-king status. A4's benefit is
the least clean (+20.7 of its removal in 2023 alone — partial cluster risk).

### 2.3 RQ5 — parent-window inheritance + age profile

Parent HTF outcome strongly predicts the LTF trade (diagnostic, non-causal —
parent's final R is only known at window close):
lb30: parent-won windows → LTF avgR **+3.09**; parent-lost → **−0.60**.
OPT-cd10: +3.12 vs −0.68.

Age profile of LTF avgR (causal — this is what a gate can actually use):

| age bucket | lb30 | OPT-cd10 |
|---|---|---|
| 0–6h | +0.10 | −0.44 |
| 6–12h | **−0.61** | −0.45 |
| 12–24h | −0.11 | +0.56 |
| 24–48h | +1.16 | +0.22 |
| ≥48h | +1.23 | **+1.45** |

**The age–R shape is U-curved on lb30** (0–6h fine, 6–24h bad, 24h+ good) and
monotonic-ish on OPT-cd10 (bad 0–12h, then rising). So "HTF proves itself" is
real but lane-shaped: w24 is a blunt tool that also cuts lb30's good 0–6h
pocket (+3.1R/31t). The inheritance result says HTF quality matters — but the
only causal handles are age (wage) and extension (ext), both already gated;
a parent-in-profit filter would be lookahead (parent R is known only at
window close).

---

## 3. Verdicts

1. **No bugs.** RQ1 canary clean; gates all pass.
2. **Mechanism corrected:** w24 ≈ ⅓ removal + ⅔ chain re-timing on the
   champion; on lb30 the chain term is −47 and flips the sign. Any future
   entry-gate experiment must report BOTH terms (this is now §12-adjacent
   practice: `d_removal` vs `chain_shift`).
3. **Runner amputation is priced in:** champion removes 136R of ≥4R runners
   and still wins; lb14 removes the fewest and is the most systematic.
4. **A4+w24 caveat:** its removal gain concentrates in 2023 (+20.7 of −15.4);
   treat A4's w24 edge as slightly cluster-flavored.
5. **HTF-side:** strong inheritance exists but is non-causal; causal handles
   (age, ext) are already exploited. The one untested causal idea from the
   age profile: a **curfew gate** (skip only the 6–24h band, keep 0–6h) —
   next-experiment candidate, must be tested pre-fill (post-hoc partitions
   are invalid for chain reasons, §4.3 of the wage doc).

## 4. How to run

```powershell
python live_stuff/tests/exp43_loss_autopsy.py 1> live_stuff/tests/_exp43_out.txt 2> live_stuff/tests/_exp43_err.txt
```

Aborts on any gate mismatch. Nothing is deleted; harness + outputs stay on disk.
