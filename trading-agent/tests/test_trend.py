import math

import pandas as pd

from agent.backtest import run_backtest
from agent.config import ConfigError, config_from_env
from agent.risk import RiskLimits
from agent.store import AgentState, Position, Store
from agent.strategy import StrategyParams, generate_signals, trailing_stop
from conftest import make_ohlcv

TREND = StrategyParams(kind="trend", stop_atr_mult=3.0, take_profit_r=0, trail_atr_mult=3.0)
LIMITS = RiskLimits(0.01, 0.5, 100_000, 0.03, 10)


def test_trend_entry_is_breakout_above_ema200():
    sig = generate_signals(make_ohlcv(1500, seed=1, drift=0.001), TREND)
    e = sig[sig["entry"]]
    assert len(e) > 0
    prior_high = sig["high"].rolling(20).max().shift(1)
    assert (e["close"] > prior_high[e.index]).all() and (e["close"] > e["ema_slow"]).all()
    assert e["take_profit"].isna().all()


def test_trend_exit_on_channel_low():
    sig = generate_signals(make_ohlcv(800, seed=2), TREND)
    x = sig[sig["exit"]]
    assert (x["close"] < sig["low"].rolling(10).min().shift(1)[x.index]).all()


def test_trend_signals_have_no_lookahead():
    df = make_ohlcv(900, seed=3, drift=0.001)
    assert generate_signals(df, TREND)["entry"].iloc[:800].equals(generate_signals(df.iloc[:800], TREND)["entry"])


def test_trailing_stop_only_moves_up():
    assert trailing_stop(90, 120, 5, 3.0) == 105
    assert trailing_stop(110, 120, 5, 3.0) == 110
    assert trailing_stop(90, 120, None, 3.0) == 90
    assert trailing_stop(90, 120, 5, None) == 90


def test_trend_backtest_lets_winners_run():
    res = run_backtest(make_ohlcv(3000, seed=5, drift=0.0015), TREND, LIMITS, fee_rate=0.009)
    assert res.trades and not any(t.reason == "take_profit" for t in res.trades)
    assert max(t.r_multiple for t in res.trades) > 2  # bez stropu zisku
    assert {t.reason for t in res.trades} <= {"stop", "trailing_stop", "breakeven", "signal", "end"}


def test_bot_trailing_stop_and_no_take_profit(tmp_path):
    from test_bot import FakeBroker, make_agent
    Store(tmp_path).save(AgentState(position=Position(1.0, 100.0, 90.0, 0.0, "2025-03-01T12:00:00+00:00",
                                                      initial_stop=90.0, max_price=100, min_price=100)))
    agent = make_agent(tmp_path, FakeBroker(price=150.0, cash=0, base=1.0), bars=pd.DataFrame(), params=TREND)
    agent._atr = 5.0
    state = agent.tick()
    assert state.position is not None            # žádný take-profit → drží
    assert math.isclose(state.position.stop, 135.0)  # 150 − 3 × 5


def test_coinbase_config():
    cfg = config_from_env({"EXCHANGE": "coinbase", "SYMBOL": "BTC/EUR"})
    assert cfg.fee_rate == 0.009 and cfg.strategy == "trend"
    pem = config_from_env({"EXCHANGE": "coinbase", "MODE": "paper", "API_SECRET": "a\\nb"}).api_secret
    assert pem == "a\nb"
    try:
        config_from_env({"EXCHANGE": "coinbase", "MODE": "testnet", "API_KEY": "k", "API_SECRET": "s"})
        raise AssertionError("testnet na Coinbase musí selhat")
    except ConfigError:
        pass
