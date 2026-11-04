from datetime import datetime, timezone

import pandas as pd

from agent.bot import TradingAgent
from agent.broker import Fill
from agent.config import config_from_env
from agent.news import Headline
from agent.store import AgentState, Position, Store
from agent.strategy import StrategyParams
from conftest import make_ohlcv

NOW = datetime(2025, 3, 1, 12, tzinfo=timezone.utc)


class FakeBroker:
    def __init__(self, price=100.0, cash=1000.0, base=0.0):
        self._price, self.cash, self.base, self.orders = price, cash, base, []

    def price(self):
        return self._price

    def balances(self):
        return self.cash, self.base

    def market_buy(self, qty):
        self.orders.append(("buy", qty))
        self.cash -= qty * self._price
        self.base += qty
        return Fill(qty, self._price)

    def market_sell(self, qty):
        qty = min(qty, self.base)
        self.orders.append(("sell", qty))
        self.base -= qty
        self.cash += qty * self._price
        return Fill(qty, self._price)

    def snapshot(self):
        return {"cash": self.cash, "base": self.base}


def make_agent(tmp_path, broker, bars=None, headlines=(), feeds="f", params=None):
    cfg = config_from_env({"MODE": "paper", "STATE_DIR": str(tmp_path), "NEWS_FEEDS": feeds,
                           "MAX_ORDER_QUOTE": "500", "MAX_POSITION_PCT": "0.5"})
    bars = bars if bars is not None else make_ohlcv(300)
    return TradingAgent(cfg, broker, Store(tmp_path), params or StrategyParams(), bars_fn=lambda: bars,
                        news_fn=lambda: (list(headlines), True), clock=lambda: NOW)


def with_position(tmp_path, stop=95.0, tp=110.0, qty=1.0):
    Store(tmp_path).save(AgentState(position=Position(qty, 100.0, stop, tp, NOW.isoformat())))


def test_stop_loss_closes_position(tmp_path):
    with_position(tmp_path)
    broker = FakeBroker(price=94.0, cash=0, base=1.0)
    state = make_agent(tmp_path, broker).tick()
    assert state.position is None and broker.orders[0][0] == "sell"
    assert "stop" in (tmp_path / "journal.csv").read_text()


def test_take_profit_closes_position(tmp_path):
    with_position(tmp_path)
    broker = FakeBroker(price=111.0, cash=0, base=1.0)
    assert make_agent(tmp_path, broker).tick().position is None


def test_news_panic_exits_position(tmp_path):
    with_position(tmp_path)
    broker = FakeBroker(price=100.0, cash=0, base=1.0)
    panic = [Headline("Bitcoin exchange hacked, funds drained", NOW, "x")]
    state = make_agent(tmp_path, broker, headlines=panic).tick()
    assert state.position is None


def _entry_bars():
    """Data, jejichž poslední svíčka dává vstupní signál."""
    from agent.strategy import generate_signals
    for seed in range(50):
        df = make_ohlcv(1200, seed=seed, drift=0.001)
        sig = generate_signals(df, StrategyParams())
        hits = sig.index[sig["entry"]]
        if len(hits):
            return df.loc[:hits[-1]]
    raise AssertionError("nenalezen signál")


def test_entry_signal_opens_sized_position(tmp_path):
    bars = _entry_bars()
    broker = FakeBroker(price=float(bars["close"].iloc[-1]))
    state = make_agent(tmp_path, broker, bars=bars).tick()
    assert state.position is not None
    assert state.position.stop < state.position.entry < state.position.take_profit
    assert broker.orders[0][1] * broker.price() <= 500 + 1e-6  # tvrdý strop
    assert state.day.trades == 1


def test_kill_switch_blocks_entry(tmp_path):
    (tmp_path / "STOP").touch()
    bars = _entry_bars()
    broker = FakeBroker(price=float(bars["close"].iloc[-1]))
    assert make_agent(tmp_path, broker, bars=bars).tick().position is None
    assert broker.orders == []


def test_bad_news_blocks_entry(tmp_path):
    bars = _entry_bars()
    broker = FakeBroker(price=float(bars["close"].iloc[-1]))
    bad = [Headline("SEC sues Binance over crypto fraud", NOW, "x")]
    assert make_agent(tmp_path, broker, bars=bars, headlines=bad).tick().position is None


def test_same_bar_is_not_traded_twice(tmp_path):
    bars = _entry_bars()
    broker = FakeBroker(price=float(bars["close"].iloc[-1]))
    agent = make_agent(tmp_path, broker, bars=bars)
    agent.tick()
    agent.tick()
    assert [o[0] for o in broker.orders] == ["buy"]


def test_state_survives_restart(tmp_path):
    with_position(tmp_path, stop=50, tp=500)
    broker = FakeBroker(price=100.0, cash=0, base=1.0)
    make_agent(tmp_path, broker, bars=pd.DataFrame()).tick()
    assert Store(tmp_path).load().position.stop == 50
