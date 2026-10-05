**Haan, possible hai**, lekin **ek saath poora 1 year nahi** milega. Upstox V3 Historical Candle Data API se 5-minute OHLCV data Nifty 50 ke liye download kar sakte ho.

### Important limits (V3 API):

| Cheez | Detail |
|-------|--------|
| **Interval** | `minutes/5` fully supported |
| **Data availability** | January 2022 se available |
| **Max per request (5-min)** | **Sirf 1 month** (kyunki 5 min ≤ 15 min interval hai) |
| **1 year data** | Multiple requests karke lo (≈12–13 calls, month-by-month) |
| **Instrument Key** | `NSE_INDEX\|Nifty 50` |

### Example API call (1 month ka data):

```
GET https://api.upstox.com/v3/historical-candle/NSE_INDEX%7CNifty%2050/minutes/5/2025-08-14/2025-07-15
Authorization: Bearer {your_access_token}
```

Response mein candles array aata hai:
`[timestamp, open, high, low, close, volume, oi]`

### 1 year data kaise download karein:

1. Access token lo (Upstox developer account se).
2. Loop chalao — har baar 1 month ka range do (`to_date` aur `from_date`).
3. Saare responses ko ek saath CSV/Parquet mein save kar lo.
4. Rate limit dhyan rakho (bahut aggressive requests mat bhejo).

**Note**:  
- Current day ka data alag se **Intraday Candle Data V3** API se aata hai.  
- Purana V2 API mein 5-min nahi tha, sirf 1-min / 30-min tha. Ab V3 mein custom intervals (1 se 300 minutes) available hain.

Agar chaho to main Python script bhi de sakta hoon jo automatically last 1 year (ya jitna chaho) 5-min Nifty 50 data download karke CSV bana de. Batao.