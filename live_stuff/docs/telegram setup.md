Haan bhai, **Telegram bot + Telegram API se algo notifications free mein aa sakti hain**. Koi paid Telegram service ki zarurat nahi.

Basic flow:

```text
Your Algo
   ↓
Telegram Bot
   ↓
Telegram App
   ↓
You 📱
```

### 1. Telegram bot banao

Telegram mein **@BotFather** open karo:

```text
/start
/newbot
```

BotFather tumse bot ka naam aur username maangega.

Example:

```text
Name: My Algo Alerts
Username: my_algo_alerts_bot
```

Phir BotFather tumhe **Bot Token** dega:

```text
123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Token kisi ko mat dena.**

### 2. Apna Chat ID nikalo

Apne naye bot ko Telegram mein open karke:

```text
/start
```

send karo.

Phir browser mein ye URL open karo:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

Example:

```text
https://api.telegram.org/bot123456789:AAxxxx/getUpdates
```

Response mein kuch aisa milega:

```json
{
  "message": {
    "chat": {
      "id": 123456789,
      "type": "private"
    }
  }
}
```

`123456789` tumhara **chat_id** hai.

### 3. Algo se message bhejo

Python/FastAPI algo mein:

```python
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

message = "🚀 BTCUSDT LONG ENTERED\nEntry: 77331.20\nQty: 0.001 BTC"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(url, data={
    "chat_id": CHAT_ID,
    "text": message
})
```

Bas. Jab ye code execute hoga, **Telegram par message aa jayega**.

### Example algo notification

```text
🔔 TRADE ENTRY

BTCUSDT PERP
Direction: LONG
Entry: 77,331.20
Qty: 0.001 BTC
SL: 76,950
Risk: $5.00
Strategy: V5
```

Aur exit:

```text
🛑 TRADE EXIT

BTCUSDT PERP
Direction: LONG
Entry: 77,331.20
Exit: 77,850
Result: +1.35R
PnL: +$6.75
Reason: TRAILING SL
```

**Cost: ₹0** — Telegram bot/API itself is free. Your algo just needs internet access to make the HTTPS request.

If your algo is running on a **VPS**, this is actually a very clean setup: `algo → Telegram Bot → phone notification`.
