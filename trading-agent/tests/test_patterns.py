from agent.patterns import (PATTERNS, active_patterns, bearish_engulfing, bullish_engulfing, detect_all, doji,
                            hammer, morning_star, three_white_soldiers)
from conftest import candles, make_ohlcv

DOWN = [(110 - i, 111 - i, 108 - i, 109 - i) for i in range(12)]  # klesající trend


def test_bullish_engulfing_detected():
    df = candles(DOWN + [(98, 98.5, 96, 96.5), (96, 100, 95.5, 99.5)])
    assert bullish_engulfing(df).iloc[-1]
    assert not bearish_engulfing(df).iloc[-1]


def test_hammer_requires_downtrend_and_long_lower_wick():
    df = candles(DOWN + [(97, 97.6, 93, 97.5)])
    assert hammer(df).iloc[-1]


def test_doji():
    df = candles([(100, 102, 98, 100.1)])
    assert doji(df).iloc[-1]


def test_morning_star():
    df = candles(DOWN + [(99, 99.5, 94, 94.5), (94, 94.8, 93.5, 94.3), (94.5, 98.5, 94.2, 98)])
    assert morning_star(df).iloc[-1]


def test_three_white_soldiers():
    df = candles([(100, 102, 99.9, 101.9), (101.9, 104, 101.8, 103.9), (103.9, 106, 103.8, 105.9)])
    assert three_white_soldiers(df).iloc[-1]


def test_no_lookahead_bias():
    df = make_ohlcv(300)
    full = detect_all(df)
    partial = detect_all(df.iloc[:200])
    assert full.iloc[:200].equals(partial)


def test_registry_has_unique_names_and_valid_directions():
    names = [p.name for p in PATTERNS]
    assert len(names) == len(set(names)) >= 20
    assert {p.direction for p in PATTERNS} <= {"bullish", "bearish", "neutral"}


def test_active_patterns_filters_by_direction():
    df = candles(DOWN + [(98, 98.5, 96, 96.5), (96, 100, 95.5, 99.5)])
    assert "bullish_engulfing" in active_patterns(df, "bullish")
    assert "bullish_engulfing" not in active_patterns(df, "bearish")
