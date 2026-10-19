"""Raw Bybit V5 REST order + stop placement, bypassing pybit's serialisation.

Why this exists
---------------
pybit drops `tpSlMode` on the way out. Withholding it, Bybit answers:

    slOrderType can not have a value when tpSlMode is empty (ErrCode: 10001)

and passing it makes no difference, because the payload visibly contains it and
Bybit still reports it empty. Signing the request by hand removes the layer
between us and the exchange, which matters when the whole point of the test is
that the stop actually attaches.

The earlier `stopLoss=` parameter is worse than broken - it is silently
ignored. The market order fills, `stopOrder` comes back null, and the position
sits there NAKED with no stop at all. A test that is meant to measure stop
execution must not begin by failing to attach a stop.

Safety, unchanged and restated because this signs real requests:
  - demo host only (api-demo.bybit.com), hardcoded, no override
  - reads BYBIT_API_KEY/SECRET from live_stuff/.env
  - the same demo-seed wallet check gates the first order
  - every failure path flattens
"""

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request

DEMO_HOST = "https://api-demo.bybit.com"
RECV_WINDOW = 30000


def _load_env():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "..", "live_stuff", ".env")
    p = os.path.normpath(p)
    env = {}
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


class RawV5:
    def __init__(self):
        env = _load_env()
        self.key = env.get("BYBIT_API_KEY")
        self.sec = env.get("BYBIT_API_SECRET")
        if not self.key or not self.sec:
            raise RuntimeError("BYBIT_API_KEY/SECRET missing")
        self.drift = 0

    def _signed(self, method, path, params):
        """Sign and dispatch, adding the local-clock correction.

        The local clock runs ~1.2s ahead of Bybit's, which trips ErrCode 10002
        on every signed request. self.drift is measured against the exchange's
        own time and applied to each timestamp, rather than relying on a wide
        recvWindow - a wide window hides the problem, it does not fix it, and it
        stops being wide enough the moment the drift grows.
        """
        p = dict(params)
        p["timestamp"] = int((time.time() + self.drift) * 1000)
        p["recvWindow"] = RECV_WINDOW
        q = urllib.parse.urlencode(p)
        # V5 signing string is querystring + API KEY, hashed with the secret.
        # Signing the querystring alone gives ErrCode 10004, and the error
        # message helpfully echoes the expected string so you can see exactly
        # what is missing - which is how this was found.
        sig = hmac.new(self.sec.encode(), (q + self.key).encode(), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY": self.key,
            "X-BAPI-SIGN": sig,
            "X-BAPI-TIMESTAMP": str(p["timestamp"]),
            "X-BAPI-RECV-WINDOW": str(RECV_WINDOW),
            "User-Agent": "Mozilla/5.0",
        }
        if method == "GET":
            url = "%s%s?%s&sign=%s" % (DEMO_HOST, path, q, sig)
            req = urllib.request.Request(url, headers=headers)
        else:
            req = urllib.request.Request(DEMO_HOST + path, data=(q + "&sign=" + sig).encode(),
                                         headers=dict(headers,
                                                      **{"Content-Type": "application/x-www-form-urlencoded"}))
        try:
            with urllib.request.urlopen(req, timeout=25) as h:
                return json.loads(h.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            raise RuntimeError("HTTP %s %s -> %s" % (e.code, path, body))

    def _post(self, path, params):
        return self._signed("POST", path, params)

    def _get(self, path, params):
        return self._signed("GET", path, params)

    # -- public -----------------------------------------------------------
    def book(self, limit=200):
        u = "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=%d" % limit
        r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(r, timeout=20) as h:
            d = json.loads(h.read().decode())["result"]
        bids = sorted([[float(p), float(v)] for p, v in d["b"]], key=lambda x: -x[0])
        asks = sorted([[float(p), float(v)] for p, v in d["a"]], key=lambda x: x[0])
        return bids, asks

    def server_time(self):
        u = "https://api.bybit.com/v5/market/time"
        r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(r, timeout=20) as h:
            return int(json.loads(h.read().decode())["result"]["timeNano"]) // 10 ** 6

    def sync(self):
        """Fix local clock drift. The demo endpoint rejects requests signed with
        a timestamp a second ahead, and every call in this file is signed."""
        self.drift = (self.server_time() / 1000.0) - time.time()
        return self.drift

    # -- private ----------------------------------------------------------
    def wallet(self):
        return self._post("/v5/account/wallet-balance", {"accountType": "UNIFIED"})

    def positions(self):
        return self._post("/v5/position/list", {"category": "linear", "symbol": "BTCUSDT"})

    def open_orders(self, order_id=""):
        p = {"category": "linear", "symbol": "BTCUSDT"}
        if order_id:
            p["orderId"] = order_id
        return self._post("/v5/order/realtime", p)

    def executions(self, limit=20):
        return self._post("/v5/execution/list",
                          {"category": "linear", "symbol": "BTCUSDT", "limit": limit})

    def create_market_with_sl(self, side, qty, sl_trigger, sl_trigger_by="MarkPrice",
                              link=""):
        """Market entry with a real attached stop, the way V5 actually wants it.

        tpSlMode=Full, slOrderType=Market, slQty must all be present together.
        Passing the legacy stopLoss= instead produces an order with no stop at
        all and no error to tell you so.
        """
        return self._post("/v5/order/create", {
            "category": "linear", "symbol": "BTCUSDT", "side": side,
            "orderType": "Market", "qty": str(qty),
            "tpSlMode": "Full",
            "slTriggerBy": sl_trigger_by,
            "slTriggerPrice": str(sl_trigger),
            "slOrderType": "Market",
            "slQty": str(qty),
            "orderLinkId": link,
        })

    def flatten(self, side, qty):
        return self._post("/v5/order/create", {
            "category": "linear", "symbol": "BTCUSDT", "side": side,
            "orderType": "Market", "qty": str(qty),
            "reduceOnly": "true", "orderLinkId": "slipflat%d" % int(time.time() % 100000),
        })

    def size(self):
        try:
            d = self.positions()
            for x in (d.get("result") or {}).get("list", []):
                s = float(x.get("size") or 0)
                if s > 0:
                    return x.get("side"), s
        except Exception:
            pass
        return None, 0.0