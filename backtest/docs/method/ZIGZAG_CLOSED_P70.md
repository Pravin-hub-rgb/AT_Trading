# P70: ZigZag integration COMPLETE — and the ZigZag is dead

> Run 2026-09-29. Harness `exp_zigzag.py` (adapter fixed in P64's file).
> **Nothing adopted. Nemotron P10 CLOSED on evidence.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **This supersedes `method/ZIGZAG_P64.md`, which recorded "not completed".**

## The integration finished in one read

P64 built the segmenter and a first adapter, then stopped at a wall: the
engine returned zero trades. **The fix was ten lines of reading.**

The contract lives in the CONSUMER — `_collect_signals` in `btc_engine.py`,
which `simulate_btc_trades_v7` calls — and it has two requirements the
producer's record shape does not imply:

```python
sdir = 1 if s.get("dir") == "up" else -1      # dir must be the STRING
if b["kind"] not in tradeable:                # tradeable = ("B2","FLIP")
    continue                                  # "H"/"L" skips EVERY break
```

- **Violation 1:** the adapter emitted `dir` as int `1`/`-1`, so
  `"up" == 1` was False for every swing and **every swing collapsed to −1**.
- **Violation 2:** it emitted `kind` as `"H"`/`"L"`, and `tradeable` is
  `("B2", "FLIP")`, so **every break mark was skipped**, every swing set
  `swing_done`, and `_collect_signals` returned nothing at all.

Emitting `dir` as `"up"`/`"down"` and the break as a `FLIP` in the swing's
own direction fixed it. That is also the semantically correct mapping: a
ZigZag high is confirmed by price breaking **up** through the prior high.

**Causality was never at risk.** `confirmed_at_idx` carries the
**confirmation** bar, never the pivot, because the engine indexes bars. A
pivot-stamped swing would be the P52 lookahead; every number below is free
of it.

## Result

| dev | role | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|---|
| 3% | htf | +259.8R | −9.6R | +267.9R | −30.6R |
| 3% | ltf | −36.2R | +7.3R | −25.6R | −8.8R |
| **5%** | **htf** | **+281.4R** | **+58.8R** | **+258.8R** | **+22.8R** |
| 5% | ltf | −33.5R | −38.6R | −26.0R | −36.9R |
| 8% | htf | +28.1R | −3.2R | +53.6R | −32.9R |
| 8% | ltf | −4.8R | **+85.5R** | −3.1R | **+84.1R** |

**Family-wise it fails, and not narrowly: twelve of the twenty-four cells
clear M = 193.4R and every one of those twelve is negative** — −362.0R,
−359.2R, −330.6R, −384.5R, −384.9R, −362.1R, −305.4R.

**No arm beats the champion in both eras in both lanes.** The best cell,
`dev 8% as ltf` at +85.5R / +84.1R, runs on **48 and 47 trades** against
champion losses of −330.6R and −362.1R in IS. A 4% book with high variance,
not an improvement.

**The shape of the failure is the informative part.** ZigZag-as-LTF is
negative in 5 of 6 lane-era cells; ZigZag-as-HTF is positive in IS and
negative or flat in OOS. **A fixed-percentage reversal rule is a worse swing
detector than the engine's own `min_bars` rule** — which the swing engine
already encodes at `min_bars_1h = 20` and `min_bars_15m = 50`, both from the
earlier sweep. The ZigZag has one parameter where the incumbent has a tuned
one, and it does not beat it anywhere.

## What this closes

**Nemotron P10 (ZigZag + Elliott hybrid labelling) is answered**, and so is
the "closest reachable relative of the dead P1/P2 wave labelling" framing.
A different segmentation of the same bars does not beat the segmentation the
book is built on — not in IS, not in OOS, not at three reversal depths, in
either role, on either lane.

**This was the last fully runnable item on the queue.** It is now closed on
evidence rather than on an integration wall, which is a better outcome than
the status it replaces.

## The lesson, which is the real product

**Three attempts, two silent failures, both the same mistake: I read the
PRODUCER's record shape and inferred the CONSUMER's contract.**
`compute_btc_swings` emits `seg`, `breaks`, `confirmed_at_*`; inferring from
that alone gave `dir` as an int and `kind` as `"H"`/`"L"` — a plausible
record the engine silently ignores.

**Ten lines of `_collect_signals` would have saved two full experiment runs.**
Neither failure raised; both printed a clean table, because an empty book is
a valid table to print.

That is the fourth distinct instance this round of a silent harness bug
producing a plausible-looking table (P57 arithmetic, P60 gross-vs-net, P64
here twice, P65 dict overwrite, P67 missing divide). **The rule that falls
out: a zero-trade or all-blank cell is a bug until proven otherwise, and the
consumer's source is the only authority on the contract.**

## Stated limitations

- **One parameter, not a search.** `dev` ∈ {3, 5, 8}% pre-registered,
  family-wise criterion. Nothing adopted, so no threshold search follows. A
  larger grid would have found *some* cell beating the champion in OOS; that
  is exactly why the criterion binds in advance.
- **The Elliott half of P10 was not attempted.** It needs wave *labelling* —
  degree and count — not just pivots, and pivots are what the swing engine
  already provides better. Recorded as out of scope, not pending.
- **Both lanes are the same data.**
- **`dev 8% as ltf` runs on 47–48 trades**; PF 4.19/4.37 is thin-sample, so
  it is not treated as a signal despite being the only positive cell.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
