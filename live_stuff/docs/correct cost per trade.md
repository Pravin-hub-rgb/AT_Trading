Yes bhai. If your backtest has **INR risk fixed at ₹250**, and for every trade you have:

* `inr_usdt` = INR per 1 USDT, e.g. 92
* `entry` = BTC entry price
* `sl` = BTC stop price
* `risk_inr` = ₹250

then the clean calculation is this.

For BTCUSDT perpetual, P&L is in USDT, and Bybit's fee is based on the **position value × fee rate**. Current non-VIP base rates are 0.055% taker and 0.02% maker. ([Bybit][1])

### 1. Convert ₹250 risk to USDT

```python
risk_inr = 250
inr_usdt = 92

risk_usdt = risk_inr / inr_usdt
```

Result:

```text
250 / 92 = 2.7174 USDT
```

### 2. Calculate BTC stop distance

For a long:

```python
sl_distance = entry - sl
```

For a short:

```python
sl_distance = sl - entry
```

Better:

```python
sl_distance = abs(entry - sl)
```

Suppose:

```text
entry = 100000
sl    = 99400
```

Then:

```text
SL distance = $600
```

### 3. Calculate BTC quantity

This is the important part:

```python
qty_btc = risk_usdt / sl_distance
```

So:

```text
2.7174 / 600
= 0.004529 BTC
```

Your position would therefore be approximately:

```text
0.004529 BTC
```

### 4. Calculate position notional

```python
entry_notional = qty_btc * entry
```

```text
0.004529 × 100000
= 452.90 USDT
```

Notice something important:

**You are risking only ~$2.72, but controlling ~$453 of BTC.**

That's where leverage/margin comes in. Leverage doesn't define your actual SL risk; your **position size × price movement** does.

### 5. Calculate entry + exit fees

If you're assuming **taker on both sides**:

```python
taker_fee = 0.00055

entry_fee = qty_btc * entry * taker_fee
exit_fee = qty_btc * exit_price * taker_fee

total_fee = entry_fee + exit_fee
```

If the trade hits SL:

```python
exit_price = sl
```

So:

```text
Entry fee:
452.90 × 0.00055
= 0.2491 USDT

Exit fee:
450.18 × 0.00055
= 0.2476 USDT

Total:
≈ 0.4967 USDT
```

That's:

```text
0.4967 × 92
≈ ₹45.70
```

So a ₹250-risk trade has approximately:

```text
SL loss       ₹250
Trading fees  ₹45.70
--------------------
Total         ₹295.70
```

**That's why a fixed 0.15R cost can actually make sense in your case.**

₹45.70 / ₹250 = **0.183R**

But that's only for a trade that hits the SL and assuming both entry and exit are taker orders.

---

## The code I'd actually put in your backtester

```python
def calculate_trade_cost(
    entry,
    exit_price,
    sl,
    risk_inr=250,
    inr_usdt=92,
    fee_rate=0.00055,
):
    # ₹250 -> USDT
    risk_usdt = risk_inr / inr_usdt

    # Price distance from entry to SL
    sl_distance = abs(entry - sl)

    if sl_distance <= 0:
        raise ValueError("SL distance must be greater than 0")

    # BTC quantity required to risk exactly risk_inr
    qty_btc = risk_usdt / sl_distance

    # Position notional
    entry_notional = qty_btc * entry
    exit_notional = qty_btc * exit_price

    # Trading fees
    entry_fee_usdt = entry_notional * fee_rate
    exit_fee_usdt = exit_notional * fee_rate

    total_fee_usdt = entry_fee_usdt + exit_fee_usdt
    total_fee_inr = total_fee_usdt * inr_usdt

    # Gross P&L
    gross_pnl_usdt = qty_btc * abs(exit_price - entry)

    # Actual R before costs
    gross_R = gross_pnl_usdt / risk_usdt

    # Cost expressed in R
    fee_R = total_fee_usdt / risk_usdt

    # Net R
    net_R = gross_R - fee_R

    return {
        "risk_inr": risk_inr,
        "risk_usdt": risk_usdt,
        "qty_btc": qty_btc,
        "entry_notional_usdt": entry_notional,
        "exit_notional_usdt": exit_notional,
        "entry_fee_usdt": entry_fee_usdt,
        "exit_fee_usdt": exit_fee_usdt,
        "total_fee_usdt": total_fee_usdt,
        "total_fee_inr": total_fee_inr,
        "gross_R": gross_R,
        "fee_R": fee_R,
        "net_R": net_R,
    }
```

### But one correction to your backtest

**Don't hardcode `0.15R` per trade.**

Calculate it **trade by trade**:

```python
fee_R = total_fee_usdt / risk_usdt
net_R = gross_R - fee_R
```

because your `entry` changes, your `SL` distance changes, your exit changes, and therefore your position size and fees change.

And if you're holding BTC perpetuals overnight, you should also account for **funding**, because Bybit perpetuals have funding payments separate from trading fees. ([Bybit][2])

So your final engine should conceptually be:

```python
net_R = gross_R - trading_fee_R - slippage_R - funding_R
```

**That's the version I'd trust for your 330-trade / +331R backtest.** The ~285R result may actually be reasonable, but we should calculate the costs per trade rather than assume 0.15R.

[1]: https://www.bybit.com/en/help-center/article/Futures-Contracts-Fees-Explained?utm_source=chatgpt.com "Futures Contracts: Fees Explained - Help Center"
[2]: https://www.bybit.com/en/help-center/article/FAQ-USDT-Perpetual-and-Expiry-Contracts?utm_source=chatgpt.com "FAQ — USDT Perpetual and Expiry Contracts - Help Center"
Exactly bhai. Order type matters a lot for your cost calculation, and your setup is actually quite different from “market entry + market SL.”

Your strategy:

Entry = Market
SL = Limit
potentially TP = whatever order type you choose

For Bybit, a Market order is taker. A Limit order can be maker or taker depending on whether it executes immediately. Bybit's current VIP 0 derivatives rates are 0.055% taker vs 0.02% maker.

So for your exact setup

Suppose:

Entry = $100,000
SL    = $99,400
Risk  = ₹250
USD/INR = 92

Your position size is:

₹250 / 92 = $2.717 risk

SL distance = $600

BTC quantity = 2.717 / 600
             = 0.004529 BTC

Entry notional:

0.004529 × 100,000
= $452.90
Entry: Market

Taker fee:

$452.90 × 0.055%
= $0.2491
SL: Limit

If that SL limit actually rests on the book and gets filled as a maker, then:

SL notional ≈ $450.18

Maker fee:
$450.18 × 0.02%
= $0.0900

Total trading fees:

$0.2491 + $0.0900
= $0.3391

In INR:

$0.3391 × 92
≈ ₹31.20

So:

Actual planned SL loss ≈ ₹250
Fees                 ≈ ₹31
Total                ≈ ₹281

That's only:

₹31 / ₹250 = 0.124R

That's already lower than the 0.15R assumption.

BUT there's a big catch with your SL

This is the part I'd be careful about.

If you're saying:

"Price reaches my SL → I send a Limit order at the SL price"

that does not guarantee you'll get filled.

Price can move through your limit and leave you sitting there with an open position while the market continues against you.

Bybit supports conditional/TP-SL mechanisms, and for an entire-position SL the system can execute a market close; partial-position TP/SL can use market or limit execution depending on the configuration.

So there's a trade-off:

Market SL

Much better execution certainty
Taker fee
Possible slippage
Better for strict risk control

Limit SL

Potentially lower maker fee
Potentially less/slower execution
Can miss the exit
Your actual loss can become much larger than your calculated ₹250

For your strategy, where you're explicitly targeting something like ₹250 fixed risk, I'd prioritize getting out over saving a few rupees in fees.

And there's an important distinction:

A limit order is not automatically a maker order.

Bybit explicitly says Limit orders can execute as either maker or taker. If you want to force maker behavior, Bybit recommends Post-Only; an immediately executable Post-Only limit is cancelled rather than becoming a taker.

So when we redo your backtest costs, we should actually model your strategy as:

ENTRY
Market → Taker 0.055%

EXIT
SL → determine whether you're actually using
     Market = Taker
     Limit = potentially Maker/Taker

TP
same thing depending on order type

Don't use one universal 0.15R anymore. Your actual order types can materially change the result.

If your real execution plan is market entry + limit TP + market emergency SL, that's also worth modelling separately because that may be much closer to what you'd actually trade.

Ummmm what does the professional bot do then???

Yeah bhai. Professional bots usually don't do “everything as limit because maker fee is cheaper.” They separate execution certainty from fee optimization.

For a strategy like yours, the professional-style setup would generally be:

Your strategy

Signal appears → enter immediately

So:

ENTRY → Market / aggressive limit → Taker

That's because your backtest says “enter here”, and waiting for a maker fill can completely change the trade.

Then:

POSITION OPEN
       │
       ├── TP → Limit / maker where practical
       │
       └── SL → protective stop, usually Market

Bybit itself supports TP/SL with market or limit execution depending on the TP/SL configuration. For an entire-position TP/SL, Bybit says the position is closed via Market when triggered; partial-position TP/SL can use Market or Limit.

Why professionals don't normally use a passive limit SL

Imagine you're long BTC:

Entry       100,000
SL           99,400

BTC suddenly dumps:

99,600
99,500
99,400
99,300
99,000

If your SL is a limit sell at 99,400, there is no guarantee someone buys from you at 99,400. Bybit explicitly warns that conditional limit orders can remain unfilled after triggering.

A professional risk system generally thinks:

“I need OUT.”

not:

“I need to save 0.035% on the exit fee.”

Because getting stuck with a ₹250 planned loss that becomes ₹500 is much worse than paying a few extra rupees.

Where maker orders actually make a lot of sense

TP.

Suppose your long goes:

100,000 entry
103,000 TP

You already know where you want to take profit.

You can place a reduce-only limit TP at the desired price. Bybit's Reduce-Only option is specifically designed to ensure a closing order doesn't accidentally create/reverse a position.

And if you specifically want maker execution, Post-Only ensures the limit order enters the order book rather than immediately executing as taker; if it would execute immediately, Bybit cancels it.

So a sensible bot could be:

                    BTC SIGNAL
                        │
                        ▼
                MARKET ENTRY
                  Taker fee
                        │
                ┌───────┴───────┐
                │               │
                ▼               ▼
          LIMIT TP          PROTECTIVE SL
        Reduce-Only          Market
          Maker*              Taker

* Maker only if the TP actually rests in the book. A normal limit isn't automatically maker; Bybit says a limit order can be either maker or taker depending on execution.

And this changes YOUR backtest

This is why I wouldn't use:

cost = 0.15 * R

anymore.

I'd model your actual intended execution:

entry_fee = entry_notional * taker_fee

if exit_reason == "SL":
    exit_fee = exit_notional * taker_fee

elif exit_reason == "TP":
    exit_fee = exit_notional * maker_fee

Then:

total_fee = entry_fee + exit_fee

fee_R = total_fee / risk_usdt

net_R = gross_R - fee_R

And then add slippage and funding separately.

For your particular strategy, this could make the real result better than your blanket 0.15R deduction, especially if a substantial percentage of winners exit through maker TP.

But I would not assume all TP orders get maker fees in the backtest. If your real bot uses Post-Only, model that behavior specifically; otherwise conservatively classify the execution based on what your bot actually does.

That's much closer to how I'd build the execution model for your 330-trade BTC perp backtest.

So if tick goes the in code set price we exit at market too ... Just for example assumption what will that cost??

Yes bhai. If your bot does:

Price touches the SL → immediately close the position with a Market order

then for our example:

Risk = ₹250
INR/USDT = 92
Entry = $100,000
SL = $99,400
SL distance = $600

Position size:

₹250 / 92 = $2.717 risk

Qty = 2.717 / 600
    = 0.004529 BTC
Fees

Assuming Bybit VIP 0 taker = 0.055%:

Entry market fee

0.004529 × $100,000 × 0.00055
= $0.249
≈ ₹22.9

SL market exit fee

0.004529 × $99,400 × 0.00055
= $0.248
≈ ₹22.8

So:

Entry fee       ≈ ₹22.9
SL exit fee     ≈ ₹22.8
-----------------------
Total fees      ≈ ₹45.7

Your actual loss becomes approximately:

SL loss         ₹250
Trading fees    ₹45.7
-----------------------
Total           ₹295.7

In R:

₹45.7 / ₹250 = 0.183R

So market entry + market SL = roughly 0.18R in fees alone in this particular example.

And this is before slippage and funding.

One important thing

If your backtest says:

330 trades
331R gross

and you simply deduct:

0.15R × 330 = 49.5R

you're actually underestimating costs for this example if both entry and SL are market.

But don't blindly use 0.18R either. Your SL distance changes every trade, which changes position size and therefore the notional/fees.

The correct backtest is:

risk_usdt = risk_inr / inr_usdt

sl_distance = abs(entry - sl)

qty = risk_usdt / sl_distance

entry_fee = qty * entry * taker_fee
exit_fee  = qty * actual_exit_price * taker_fee

fee_usdt = entry_fee + exit_fee
fee_R = fee_usdt / risk_usdt

net_R = gross_R - fee_R

Then add slippage separately.

So yeah: if your actual bot is market entry + market SL, I'd model exactly that. That's the conservative and much safer assumption for your strategy.

Ahh yes — **this is the important part for your strategy.** If your algo doesn't have a fixed TP and instead **trails the SL as price moves**, then you don't have just:

`Entry → TP/SL`

You have:

`Entry → dynamically moving SL → eventual exit`

And **every trade only has TWO actual executions**:

1. **Entry**
2. **Final exit** when the trailing SL gets hit

The intermediate trailing-SL updates are **not trades and don't incur fees**.

### Example

Suppose:

```text
Risk       = ₹250
Entry      = $100,000
Initial SL = $99,400
```

Your algo enters:

```text
BUY 0.004529 BTC @ $100,000
        ↓
Market entry → TAKER FEE
```

Then price moves:

```text
100,000 entry
    ↓
100,500
    ↓
101,000
    ↓
101,500
```

Your algo keeps moving the SL upward:

```text
Initial SL → 99,400

price 100,500 → SL becomes 100,000
price 101,000 → SL becomes 100,500
price 101,500 → SL becomes 101,000
```

Those SL **modifications cost no trading fee** because you're not executing anything.

Then BTC falls:

```text
101,500
    ↓
101,300
    ↓
101,100
    ↓
101,000  ← trailing SL triggered
```

Your bot closes the position:

```text
SELL 0.004529 BTC @ ~101,000
        ↓
Market exit → TAKER FEE
```

So your cost calculation is simply:

```python
entry_fee = entry_notional * entry_taker_fee

exit_fee = exit_notional * exit_taker_fee

total_fee = entry_fee + exit_fee
```

There is **no TP fee** because you don't have a TP.

---

## And here's the really important backtest detail

Your **exit price should be the actual price at which the trailing SL is executed**, not necessarily the SL level stored by your algorithm.

For example:

```text
Trailing SL = $101,000

Next candle:
High = 101,100
Low  = 100,850
```

If your backtest says the SL triggers when price crosses $101,000, then you need to define your execution assumption.

### Conservative/simple model

```python
exit_price = trailing_sl
```

So:

```text
exit = $101,000
```

Then calculate the exit fee from that.

### More realistic market-execution model

If you have sufficiently granular data (your 1-minute BTC data), you can model:

```text
SL trigger = $101,000
market execution = perhaps $100,990 / $100,970 / etc.
```

That difference is **slippage**, and it should be modeled separately.

So:

```python
gross_pnl = qty * (exit_price - entry)
```

then:

```python
entry_fee = entry * qty * entry_taker_fee
exit_fee = exit_price * qty * exit_taker_fee

net_pnl = gross_pnl - entry_fee - exit_fee - slippage - funding
```

and finally:

```python
net_r = net_pnl / risk_usdt
```

---

### Therefore your actual strategy cost model is much simpler

For your trailing system:

```text
                 TRADE
                   │
                   ▼
            MARKET ENTRY
              Taker fee
                   │
                   ▼
             Position open
                   │
                   │
          trailing SL moves
          100 → 105 → 110...
          (NO FEES)
                   │
                   ▼
          SL gets triggered
                   │
                   ▼
            MARKET EXIT
              Taker fee
```

So **don't charge a fee every time your trailing stop moves.**

And don't create a separate "TP cost" either.

Your backtest should calculate **entry fee + final exit fee**, plus whatever slippage/funding assumptions you decide are realistic.

That actually makes your previous **~0.15R fixed cost assumption even more questionable**, because the fee in R will vary substantially depending on **initial SL distance and final trailing exit price**.

If you want, send me **the exact trailing logic/code you currently use**, and I can tell you exactly where the fee calculation should be inserted without changing your strategy logic.


Monthly average INR per USDT (proxy via USD/INR) from Jan 2023 to Sep 2026 is available and reliable for backtesting.
USDT tracks USD extremely closely (peg ≈ 1:1). On Bybit/P2P there can be small local premiums/discounts, but official monthly averages are the standard, high-quality series used for historical work. Your current Bybit quote (250 INR ≈ 2.615 USDT → ~95.60 INR per USDT) lines up with the live mid-market USD/INR rate of ~95.57–95.60 on 12 Sep 2026.
Source
Federal Reserve (FRED series EXINUS) — monthly averages of daily noon buying rates (INR per 1 USD). This is the cleanest public monthly series.

September 2026 is partial (data through ~11 Sep); average so far is ~94.9.
Monthly averages (INR per 1 USDT ≈ INR per 1 USD)
2023

Jan: 81.74
Feb: 82.60
Mar: 82.27
Apr: 81.97
May: 82.30
Jun: 82.23
Jul: 82.16
Aug: 82.81
Sep: 83.07
Oct: 83.22
Nov: 83.27
Dec: 83.25

2024

Jan: 83.11
Feb: 82.95
Mar: 83.02
Apr: 83.40
May: 83.39
Jun: 83.46
Jul: 83.59
Aug: 83.89
Sep: 83.79
Oct: 84.01
Nov: 84.33
Dec: 84.97

2025

Jan: 86.27
Feb: 87.06
Mar: 86.52
Apr: 85.58
May: 85.25
Jun: 85.88
Jul: 86.17
Aug: 87.57
Sep: 88.32
Oct: 88.37
Nov: 88.84
Dec: 90.04

2026

Jan: 90.90
Feb: 90.75
Mar: 92.82
Apr: 93.48
May: 95.53
Jun: 94.96
Jul: 95.86
Aug: 95.44
Sep (partial, through ~11 Sep): ~94.90

How to use for backtesting

Convert any INR amount to USDT with: USDT = INR / monthly_rate.
Example with your number: 250 INR at the current ~95.60 rate → ~2.615 USDT (matches what you quoted).
For a full month use the average above. If you need end-of-month or daily granularity, FRED also publishes the daily series (DEXINUS) and RBI reference rates are publicly available.

If you need more precision or Bybit-specific rates

Official monthly averages are already excellent for most strategy backtests.
Pure P2P/Bybit INR-USDT can trade at a small premium/discount (often 0.1–1 %+ depending on liquidity and local demand). Historical P2P series exist on some aggregator sites but are less complete and less clean than the Fed/RBI data.
You can adjust the series by a constant premium if your live Bybit quotes consistently differ from mid-market, or pull Bybit kline/trade history via their API for the exact pair if it is listed.

No approximation is required for 2023–Aug 2026; the numbers above are the actual monthly averages. September 2026 can be updated with the final monthly print when it is released (usually early next month).
If you want the data as a CSV, daily series, end-of-month values, or help turning this into a backtest table, just say.


