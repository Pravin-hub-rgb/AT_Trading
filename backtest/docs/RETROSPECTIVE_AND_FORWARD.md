# THE RETROSPECTIVE PROBLEM — and the forward data that answers it

Date: 2026-09-28. This is a method note, not a result. It is the most
important thing in today's session.

## The user's point, and why it is correct

> "retrospect aur forward looking nahi hona chahiye okay yeh dekhna jarroori"

Both failure modes are live in this repo, and they are different problems
that get confused:

- **FORWARD-LOOKING (leakage)** — using information that did not exist at
  the decision instant. This repo has a documented instance: `sM2` read
  `seg.end_px` at B2/flip entry, a price that is not known until the swing
  *ends*, and it shipped a false 4/4 before being retracted. Also
  `AGENT_COORDINATION.md` line 155: folding final R in entry order leaked
  because positions overlap under `exp_mltf`.

- **RETROSPECTIVE (fitting the past)** — not a bug, a method failure. Even
  with perfect causality, if you look at IS+OOS enough times you will find
  something that looks good on both and is noise. The repo's own words:
  **"the champion IS/OOS slices are the most inspected data in this repo.
  Candidates here have looked excellent in IS and died on OOS or
  cross-venue repeatedly."** (HANDOVER section 8)

## What is contaminated, honestly

| today's finding | risk | why |
|---|---|---|
| 1m family closed (0/196) | **low** | a negative; you cannot overfit to "nothing works" |
| net-cost arithmetic (0.79R/trade) | **none** | it is arithmetic, not a fitted parameter |
| FS-only `seg_start r=2.0` | low-mid | one config, same-sign required, and it FAILED the sign test |
| `max_consecutive_losses=3` peak | **mid** | swept on both eras, but 3 was already shipped so "confirmation" is partly retrospective |
| entry-time `swing_no` AUC 0.83/0.92 | **high** | found by scanning many features on both eras; correctly rejected as calendar time, but the SEARCH ITSELF was retrospective |
| **alt sweep 7/13 pass** | **high** | 13 assets screened on the same data that then reported the winners |
| **portfolio 5/6 kills-clean** | **highest** | 13 → 7 → 6. Two rounds of selection, all on data that did the selecting. The equal-weight sleeve and the 1.25–1.79× diversification are *descriptive of a survivorship-selected set* |
| OOS ACF +0.498 | mid | descriptive, not a rule, but discovered by looking |
| Kelly f* | mid | two eras disagree 6×, already flagged |

**The portfolio numbers are the weakest thing produced today, and the
reason is exactly the one the user raised.** I reported "5/6 kills-clean"
as a finding, but those five were chosen by looking. The honest statement
is: *of the assets that passed a screen I ran on the same data, five also
passed a second screen — which is close to what selection alone predicts.*

## THE ANSWER ALREADY EXISTS IN THE REPO AND HAS NEVER BEEN USED

`data/forward/bybit/` — 1,203 x 15m bars, 301 x 1h, 18,049 x 1m, from
**2026-09-13 10:03 IST**. `FORWARD_TEST_PLAN.md` says of it:

> "Isolated post-2026-09-13 slice. **Never merged into data/bybit/.**
>  Used only by exp_forward_eval.py."
> "Does the edge survive on data that was **never used to choose anything**?"
> "OOS 2021-2022 (reused many times, **not a holdout**)"

Today is 2026-09-28. **That slice has been accruing untouched for ~15 days
and no run in this session touched it** — every experiment today ran on
IS 2023-2026 or OOS 2021-2022, both of which are mined.

This is the one asset in the repo that is not retrospective-contaminated,
and it is currently unused.

## THE RULE, stated so it can be enforced

1. **One look.** A candidate gets ONE run on `data/forward`. If it is
   selected from, tuned on, or filtered using that slice, the slice is
   burned — it is no longer forward data and a new boundary must be
   stamped.
2. **Selection must happen strictly upstream.** The 13→7→6 funnel I ran
   today is fine for exploration and worthless as evidence. Any candidate
   that came out of it needs a fresh, untouched window to be believed.
3. **The boundary is written BEFORE the data arrives.** That is what
   `_forward_manifest.json` is for: it stamps the instant and the row
   counts, so the claim "this was not used" is checkable rather than
   remembered.
4. **A retrospective pass is still worth doing** — it just cannot be
   reported as validation. Today's negative results (1m, FS-only) are safe
   precisely because they are negatives; today's positive results
   (portfolio, Kelly) are not, and should be labelled exploratory until a
   forward run exists.

## What I would do with it, if the user wants

- The portfolio sleeve is the thing MOST worth a forward run and the thing
  least entitled to claim validity today. It needs Bybit perp data anyway
  (the current sweep is Binance fapi), so the first step is fetching a
  Bybit alt slice, not reusing `data/forward` for BTC.
- For BTC itself, `data/forward` is ~15 days ≈ 60-70 trades on the
  champion lane. That is a real but small sample: it can **kill** a
  candidate confidently and cannot **confirm** one. Worth knowing which
  direction a gate is aimed in.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
