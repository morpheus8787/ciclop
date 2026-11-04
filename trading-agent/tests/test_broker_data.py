import pytest

from agent.broker import ExchangeBroker, OrderRejected, PaperBroker
from agent.data import drop_unclosed, fetch_history, fetch_recent, to_frame

HOUR_MS = 3_600_000


class FakeExchange:
    def __init__(self, price=100.0, bars=50):
        self.price, self.created = price, []
        self.rows = [[i * HOUR_MS, 1, 2, 0.5, 1.5, 10] for i in range(bars)]

    def fetch_ticker(self, symbol):
        return {"last": self.price}

    def load_markets(self):
        pass

    def market(self, symbol):
        return {"base": "BTC", "quote": "USDT", "limits": {"amount": {"min": 0.001}, "cost": {"min": 5}}}

    def fetch_balance(self):
        return {"free": {"USDT": 1000.0, "BTC": 0.5}}

    def amount_to_precision(self, symbol, qty):
        return f"{qty:.3f}"

    def create_order(self, symbol, type_, side, amount):
        self.created.append((type_, side, amount))
        return {"id": "1", "filled": amount, "average": self.price}

    def parse_timeframe(self, tf):
        return 3600

    def milliseconds(self):
        return (len(self.rows) - 1) * HOUR_MS + 10  # uprostřed poslední svíčky

    def fetch_ohlcv(self, symbol, tf, since=None, limit=500):
        rows = [r for r in self.rows if since is None or r[0] >= since]
        return rows[:limit]


def test_paper_broker_buy_sell_with_fees():
    b = PaperBroker(FakeExchange(100), "BTC/USDT", cash=1000, fee_rate=0.01)
    b.market_buy(1)
    assert b.balances() == pytest.approx((899, 1))
    b.market_sell(5)  # prodá jen co má
    assert b.balances() == pytest.approx((899 + 99, 0))
    assert b.snapshot() == {"cash": pytest.approx(998), "base": 0}


def test_paper_broker_rejects_overspend_and_empty_sell():
    b = PaperBroker(FakeExchange(100), "BTC/USDT", cash=50)
    with pytest.raises(OrderRejected):
        b.market_buy(1)
    with pytest.raises(OrderRejected):
        b.market_sell(1)


def test_exchange_broker_places_market_orders():
    ex = FakeExchange(100)
    b = ExchangeBroker(ex, "BTC/USDT")
    assert b.balances() == (1000.0, 0.5)
    fill = b.market_buy(0.12345)
    assert ex.created[-1] == ("market", "buy", 0.123) and fill.price == 100
    b.market_sell(10)  # omezeno zůstatkem
    assert ex.created[-1] == ("market", "sell", 0.5)


def test_exchange_broker_rejects_below_minimum():
    b = ExchangeBroker(FakeExchange(100), "BTC/USDT")
    with pytest.raises(OrderRejected):
        b.market_buy(0.01)  # 1 USDT < min cost 5


def test_drop_unclosed_removes_open_candle():
    df = to_frame([[0, 1, 2, 0.5, 1.5, 1], [HOUR_MS, 1, 2, 0.5, 1.5, 1]])
    assert len(drop_unclosed(df, 3600, now_ms=HOUR_MS + 10)) == 1
    assert len(drop_unclosed(df, 3600, now_ms=2 * HOUR_MS)) == 2


def test_fetch_recent_and_history():
    ex = FakeExchange(bars=30)
    assert len(fetch_recent(ex, "BTC/USDT", "1h")) == 29  # poslední svíčka ještě otevřená
    hist = fetch_history(ex, "BTC/USDT", "1h", days=2)
    assert hist.index.is_monotonic_increasing and len(hist) == 29


class _Resp:
    def __init__(self, payload):
        import json
        self.body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body


def test_binance_vision_client_parses_klines_and_ticker():
    from agent.data import BinanceVisionData
    urls = []

    def opener(url):
        urls.append(url)
        if "klines" in url:
            return _Resp([[0, "1", "2", "0.5", "1.5", "10", 1, "0", 1, "0", "0", "0"]])
        return _Resp({"symbol": "BTCUSDT", "price": "78000.5"})

    c = BinanceVisionData(opener)
    assert c.fetch_ohlcv("BTC/USDT", "1h", since=5, limit=5000) == [[0, 1.0, 2.0, 0.5, 1.5, 10.0]]
    assert "symbol=BTCUSDT" in urls[0] and "startTime=5" in urls[0] and "limit=1000" in urls[0]
    assert c.fetch_ticker("BTC/USDT")["last"] == 78000.5
    assert c.parse_timeframe("4h") == 14400


def test_market_data_switch():
    from agent.config import config_from_env
    from agent.data import BinanceVisionData, make_market_data
    assert isinstance(make_market_data(config_from_env({"MARKET_DATA": "binance_vision"})), BinanceVisionData)
