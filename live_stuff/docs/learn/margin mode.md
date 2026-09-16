**Margin Mode Explained Simply**

### What is Margin Mode?

When you trade Perpetual Futures on Bybit, you must choose how your money (margin) is used to support your positions.

There are only **two modes**:

### 1. Cross Margin (Default on Unified Account)

- All your money is shared across **every** open position.
- If one trade goes very bad, it can take money from your other positions and even wipe your **entire account**.
- Higher risk of total account liquidation.

**Example:**
You have ₹50,000.
You open a Long and a Short.
If the Long gets liquidated badly, it can eat the margin of the Short too → both positions die + account can go to zero.

---

### 2. Isolated Margin (Recommended for you)

- Each position has its **own separate margin**.
- If one position gets liquidated, you only lose the money you allocated to **that** position.
- The rest of your account stays safe.

**Example:**
You risk ₹500 on a trade → only that ₹500 (plus a little buffer) is at risk.
Even if it liquidates, your other money is protected.

---

### Why This Matters for Your Bot

Your strategy:
- Has both Long and Short
- Sometimes holds for multiple days
- Uses fixed risk (₹500 per trade)

**Cross Margin is dangerous** for this style.  
One bad gap or funding + sudden move can cascade and destroy the whole account.

**Isolated Margin is the professional choice** for risk-based bots like yours.

---

### The Solution (What You Should Do)

Add these 3 things:

#### 1. Config
```python
# config.py
MARGIN_MODE = "isolated"   # "isolated" or "cross"
```

#### 2. Method in your trader class
```python
def set_margin_mode(self, mode: str = "isolated"):
    """
    mode: "isolated" or "cross"
    """
    trade_mode = 1 if mode == "isolated" else 0   # 1 = Isolated, 0 = Cross

    response = self.session.switch_margin_mode(
        category="linear",
        symbol="BTCUSDT",
        tradeMode=trade_mode,
        buyLeverage=str(self.max_leverage),
        sellLeverage=str(self.max_leverage)
    )
    return response
```

#### 3. Call it on startup (same place you set leverage)
```python
# In main.py or bot startup
trader.set_margin_mode(MARGIN_MODE)
logger.info(f"Margin mode set to: {MARGIN_MODE.upper()}")
```

---

### Final Recommendation

**Always use Isolated Margin** for your bot.

It matches your risk management philosophy (fixed ₹500 risk per trade) and protects the rest of your capital.

Would you like the complete ready-to-copy code for the `set_margin_mode` method + how to safely call it on startup?

**Yes — since it’s a one-trade-at-a-time algo, the difference is smaller, but Isolated is still better.**

### Why Isolated is still the right choice even with only 1 trade open:

| Situation                        | Cross Margin                          | Isolated Margin                      |
|----------------------------------|---------------------------------------|--------------------------------------|
| Only 1 trade open                | Almost same risk                      | Same risk                            |
| Trade gets liquidated            | Can still take extra money from account balance | Only loses the margin allocated to that trade |
| Gap / sudden wick                | Higher chance of wiping more capital  | Limited to that position’s margin    |
| Psychological + safety           | More dangerous                        | Cleaner & safer                      |
| Future-proof                     | Bad if you ever run 2 strategies      | Always safe                          |

### Real risk with Cross (even with 1 trade):

If a big gap happens and your Stop Loss is skipped (or delayed), Cross Margin can keep taking money from your available balance until the position is fully liquidated.  
Isolated stops at the margin you gave that position.

---

### Recommendation for your case:

Even though you only take **one trade at a time**, still set it to **Isolated**.

Reasons:
1. Safer by design
2. Matches your fixed-risk philosophy (₹500 risk)
3. No downside
4. Future-proof if you later run multiple bots or strategies

Just set it once on startup and forget about it.

Would you like me to give you the exact clean code to set Isolated Margin on startup?