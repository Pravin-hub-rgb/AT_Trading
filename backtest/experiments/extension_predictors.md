# Does anything predict whether a 3R-reacher extends?

## The bar this had to clear

One external reviewer asked whether a mechanism exists. I tested exactly one
candidate state variable, got a null, and reported it as though the
hypothesis had been tested. That was premature. This tests eight at once, on
the one population that matters, and requires agreement across BOTH eras:

> A candidate counts only if it separates extenders from non-extenders in
> the **same direction in both eras**.

One era agreeing is 110's skip_n=16. Two eras disagreeing is the ATR
bucketing. Both are noise wearing a mechanism's clothes.

`ranksep` is the fraction of extender/non-extender pairs where the extender
scores higher. **0.5 is no signal at all.**

### `slope_norm`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `path_eff`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `pullback`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `bars_to_3R`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `leg_ratio`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `decay_frac`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `swing_run`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

### `vol_expand`

| book | era | n ext | mean extender | mean non-extender | ranksep |
|---|---|---:|---:|---:|---:|

---

## Verdict

**Nothing cleared the bar.**

No candidate separated extenders from non-extenders in the same
direction across both eras on every book. The null is now a real null:
it is eight mechanisms tested, not one.

## What this means for the decision

- **Nothing here is adopted.** Even a candidate that cleared the bar would
  be a new rule fitted on the same data that produced the original 3.0.
  The external review's objection applies unchanged.
- **If nothing cleared the bar, the correct action is to stop looking.**
  `htf_rr` stays at 3.0, the question closes, and the remaining effort goes
  to the forward window and the live work — which are the parts that
  actually decide something.
- **The honest summary for the owner:** the mechanism for when to extend
  does not appear to exist in this data. 3.0 stays. That is a finding, not
  a failure — it means the parameter is not a lever worth trading, and a
  parameter that cannot be improved is a parameter that cannot be
  overfitted on either.
