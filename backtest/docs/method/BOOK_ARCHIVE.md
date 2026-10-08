# book archive - retired, not deleted

Date: 2026-10-08. Every book here was removed from `EXPERIMENTS` by the
owner's rule. **None of them were deleted.** The definitions never left
their family modules.

## the two bars

> any book jisme IS ya OOS negative hai usko hata
> OOS 50R se low hai to hata

| bar | meaning | books |
|---|---|---:|
| `bar1_era_fitted` | BAR 1 - IS positive, OOS negative | 28 |
| `bar1_both_negative` | BAR 1 - negative in both eras | 1 |
| `bar1_inverse_IS_neg_OOS_pos` | BAR 1 - INVERSE: IS negative, OOS positive | 3 |
| `bar2_oos_under_50` | BAR 2 - 0 <= OOS < 50R | 52 |
| `alias_of_retired` | ALIAS - points at a retired book | 1 |

**236 entries -> 151 books.** 85 keys retired in total.

## how to run a retired book again

Two ways, both supported.

**1. Through the registry.** Delete the key from the right set in
`registry/retired.py`, fix the `assert` count, then:

```
python exp_registry_snapshot.py write _registry_before.json
python exp_fastcheck.py <book>
```

The definition never moved, so the pins will reproduce.

**2. Without touching the registry at all.** `_archive_list.json` holds
every retired book's full config and pins. The engine call is:

```
sim(c1h, sw, c15, sw15, fine_ltf=fine, **cfg["params"])
```

with `cfg["swing"]` picking the swing series. Both fields are in the JSON,
so this works with no restoration step.

## the 3 books that left by rule and not by measurement

`gap_campaign_max2`, `gap_campaign_markneg` and `gap_entry_cap2` are
negative IN SAMPLE and strongly positive OUT OF SAMPLE:

| book | IS avgR | OOS avgR | OOS net | OOS dd |
|---|---:|---:|---:|---:|
| gap_campaign_markneg | -0.060 | 0.4978571428571429 | 76.67 | 13.59 |
| gap_campaign_max2 | -0.057 | 0.49269736842105266 | 74.89 | 13.59 |
| gap_entry_cap2 | -0.060 | 0.4978571428571429 | 76.67 | 13.59 |

They were shown these numbers and the owner held the rule that a book
negative in either era comes out. The reason they left is the rule, not a
measurement, and `archived()` returns them with pins intact so the call
can be reversed without re-deriving anything.

## full table

See `_archive_list.md` for all 85 retired books with trades, net, average R
per trade, drawdown and retention in both eras, and
`_archive_list.json` for the runnable configs.
