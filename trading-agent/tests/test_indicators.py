import pandas as pd

from agent.indicators import atr, ema, rsi, with_indicators
from conftest import make_ohlcv


def test_rsi_is_100_when_price_only_rises():
    close = pd.Series(range(1, 50), dtype=float)
    assert rsi(close).iloc[-1] == 100.0


def test_rsi_stays_within_bounds():
    r = rsi(make_ohlcv()["close"]).dropna()
    assert r.between(0, 100).all()


def test_ema_of_constant_is_constant():
    assert (ema(pd.Series([5.0] * 30), 10).dropna() == 5.0).all()


def test_atr_equals_constant_range():
    df = pd.DataFrame({"open": [10.0] * 30, "high": [11.0] * 30, "low": [9.0] * 30, "close": [10.0] * 30})
    assert abs(atr(df).iloc[-1] - 2.0) < 1e-9


def test_with_indicators_does_not_mutate_input():
    df = make_ohlcv(300)
    cols = list(df.columns)
    out = with_indicators(df)
    assert list(df.columns) == cols
    assert {"ema_fast", "ema_slow", "rsi", "atr"} <= set(out.columns)
