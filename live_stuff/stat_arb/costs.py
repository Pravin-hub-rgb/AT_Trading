"""Pre-registered cost model for the stat-arb spread book (Binance perp).

- Taker fee 0.04% per side; entry slip 0.5 bps; exit slip 1.0 bps
  => 0.095% of combined leg notional per round trip.
- Funding FLAT 0.01% / 8h per leg notional (longs pay, shorts receive),
  accrued every 15m bar as 0.01% * 900/28800 = 3.125e-6 on signed dollars.
- Fixed sizing: BTC leg $10,000; hedge legs = $10k * h_i / h_0 (h_0 > 0).
- 1R: risk$ = (10000 / h0) * sigma_entry * (stop_z - entry_z_param);
  R = (leg P&L - costs + funding cashflow) / risk$.
"""
from __future__ import annotations

FEE = 0.0004
SLIP_ENTRY = 0.00005
SLIP_EXIT = 0.0001
FUND_8H = 0.0001
BAR_SEC = 900
LEG_BTC = 10000.0
FUND_BAR = FUND_8H * BAR_SEC / 28800.0


def round_trip_pct():
    return 2.0 * FEE + SLIP_ENTRY + SLIP_EXIT


def trade_r(h, dirn, log_entry, log_exit, sigma_e, entry_z, stop_z, bars_held):
    scale = LEG_BTC / h[0]
    legs = [dirn * scale * hi for hi in h]
    gross = sum(n * (xe - x0) for n, x0, xe in zip(legs, log_entry, log_exit))
    cost = round_trip_pct() * sum(abs(n) for n in legs)
    funding = -FUND_BAR * sum(legs) * bars_held
    risk = scale * sigma_e * (stop_z - entry_z)
    r = (gross - cost + funding) / risk if risk > 1e-12 else 0.0
    return {"gross": gross, "cost": cost, "funding": funding,
            "risk": risk, "r": r}
