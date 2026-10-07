<!-- prov: engine=2c463e9 measured=2026-10-07 harness=exp_cell_shape.py -->
# gate shape - 'chop_hi_atr_lo_gate' on fsent_champ_long

## persist grid, both eras

| persist | IS n | IS net | IS dd | IS dur | IS streak | OOS n | OOS net | OOS dd | OOS dur | OOS streak | d IS | d OOS | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 1 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 2 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 3 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 4 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 5 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 6 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |
| 7 | 144 | 116.0 | 25.2 | 34 | 12 | 58 | 37.6 | 11.0 | 14.0 | 13 | -417.4 | -202.0 | worse |

## The persist grid is flat because it CANNOT bind on this mode

Every row 0..7 is byte-identical, which is a structural result and not a
measurement to trust at face value. `chop_hi_atr_lo_gate` does `continue`
on any signal outside the cell, so `use` is never assigned for those
signals and the v19 hysteresis state (_rg_s / _rg_c) never advances on
them. The regime stickiness exp_persist controls only exists on signals
that survive the gate, and on a cell covering 14% of bars there is
almost nothing for it to stick to.

So `exp_persist` is structurally inert on any gate-shaped mode. That is a
property of the mode SHAPE, not of this threshold: sweeping persist on a
gate is not a question this engine can answer. Answering it would need a
gate that assigns `use="flip"` rather than skipping the signal.
