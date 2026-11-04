"""Knihovna svíčkových a cenových patternů.

Každý detektor bere DataFrame (open, high, low, close) a vrací bool Series –
True na svíčce, kde se pattern DOKONČIL. Žádný detektor nekouká do budoucnosti.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"

TREND_LOOKBACK = 10
DONCHIAN_PERIOD = 20


# --- pomocné míry svíčky -------------------------------------------------------
def _body(df):
    return (df["close"] - df["open"]).abs()


def _range(df):
    return (df["high"] - df["low"]).replace(0, float("nan"))


def _upper_wick(df):
    return df["high"] - df[["open", "close"]].max(axis=1)


def _lower_wick(df):
    return df[["open", "close"]].min(axis=1) - df["low"]


def _green(df):
    return df["close"] > df["open"]


def _red(df):
    return df["close"] < df["open"]


def _downtrend(df):
    return df["close"].shift(1) < df["close"].rolling(TREND_LOOKBACK).mean().shift(1)


def _uptrend(df):
    return df["close"].shift(1) > df["close"].rolling(TREND_LOOKBACK).mean().shift(1)


def _prev(s, n=1):
    return s.shift(n)


def _avg_body(df, n=TREND_LOOKBACK):
    return _body(df).rolling(n).mean().shift(1)


# --- jednosvíčkové ------------------------------------------------------------
def doji(df):
    return _body(df) <= 0.1 * _range(df)


def hammer(df):
    b = _body(df)
    return (_lower_wick(df) >= 2 * b) & (_upper_wick(df) <= 0.3 * b + 0.1 * _range(df)) & (b > 0) & _downtrend(df)


def inverted_hammer(df):
    b = _body(df)
    return (_upper_wick(df) >= 2 * b) & (_lower_wick(df) <= 0.3 * b + 0.1 * _range(df)) & (b > 0) & _downtrend(df)


def shooting_star(df):
    b = _body(df)
    return (_upper_wick(df) >= 2 * b) & (_lower_wick(df) <= 0.3 * b + 0.1 * _range(df)) & (b > 0) & _uptrend(df)


def hanging_man(df):
    b = _body(df)
    return (_lower_wick(df) >= 2 * b) & (_upper_wick(df) <= 0.3 * b + 0.1 * _range(df)) & (b > 0) & _uptrend(df)


def bullish_marubozu(df):
    return _green(df) & (_body(df) >= 0.9 * _range(df)) & (_body(df) > 1.5 * _avg_body(df))


def bearish_marubozu(df):
    return _red(df) & (_body(df) >= 0.9 * _range(df)) & (_body(df) > 1.5 * _avg_body(df))


# --- dvousvíčkové -------------------------------------------------------------
def bullish_engulfing(df):
    return (
        _prev(_red(df)) & _green(df)
        & (df["open"] <= _prev(df["close"])) & (df["close"] >= _prev(df["open"]))
        & (_body(df) > _prev(_body(df)))
    )


def bearish_engulfing(df):
    return (
        _prev(_green(df)) & _red(df)
        & (df["open"] >= _prev(df["close"])) & (df["close"] <= _prev(df["open"]))
        & (_body(df) > _prev(_body(df)))
    )


def bullish_harami(df):
    return (
        _prev(_red(df)) & _green(df) & _downtrend(df)
        & (df["open"] > _prev(df["close"])) & (df["close"] < _prev(df["open"]))
    )


def bearish_harami(df):
    return (
        _prev(_green(df)) & _red(df) & _uptrend(df)
        & (df["open"] < _prev(df["close"])) & (df["close"] > _prev(df["open"]))
    )


def piercing_line(df):
    mid = (_prev(df["open"]) + _prev(df["close"])) / 2
    return (
        _prev(_red(df)) & _green(df) & (df["open"] < _prev(df["close"]))
        & (df["close"] > mid) & (df["close"] < _prev(df["open"]))
    )


def dark_cloud_cover(df):
    mid = (_prev(df["open"]) + _prev(df["close"])) / 2
    return (
        _prev(_green(df)) & _red(df) & (df["open"] > _prev(df["close"]))
        & (df["close"] < mid) & (df["close"] > _prev(df["open"]))
    )


def tweezer_bottom(df):
    tol = 0.001 * df["close"]
    return _prev(_red(df)) & _green(df) & ((df["low"] - _prev(df["low"])).abs() <= tol) & _downtrend(df)


def tweezer_top(df):
    tol = 0.001 * df["close"]
    return _prev(_green(df)) & _red(df) & ((df["high"] - _prev(df["high"])).abs() <= tol) & _uptrend(df)


# --- třísvíčkové --------------------------------------------------------------
def morning_star(df):
    first_mid = (_prev(df["open"], 2) + _prev(df["close"], 2)) / 2
    return (
        _prev(_red(df), 2) & (_prev(_body(df)) < 0.5 * _prev(_body(df), 2))
        & _green(df) & (df["close"] > first_mid)
    )


def evening_star(df):
    first_mid = (_prev(df["open"], 2) + _prev(df["close"], 2)) / 2
    return (
        _prev(_green(df), 2) & (_prev(_body(df)) < 0.5 * _prev(_body(df), 2))
        & _red(df) & (df["close"] < first_mid)
    )


def three_white_soldiers(df):
    c = df["close"]
    return (
        _green(df) & _prev(_green(df)) & _prev(_green(df), 2)
        & (c > _prev(c)) & (_prev(c) > _prev(c, 2))
        & (_upper_wick(df) < 0.3 * _body(df))
    )


def three_black_crows(df):
    c = df["close"]
    return (
        _red(df) & _prev(_red(df)) & _prev(_red(df), 2)
        & (c < _prev(c)) & (_prev(c) < _prev(c, 2))
        & (_lower_wick(df) < 0.3 * _body(df))
    )


# --- cenové (chart) patterny ---------------------------------------------------
def donchian_breakout_up(df):
    return df["close"] > df["high"].rolling(DONCHIAN_PERIOD).max().shift(1)


def donchian_breakout_down(df):
    return df["close"] < df["low"].rolling(DONCHIAN_PERIOD).min().shift(1)


def inside_bar_breakout_up(df):
    inside = (_prev(df["high"]) < _prev(df["high"], 2)) & (_prev(df["low"]) > _prev(df["low"], 2))
    return inside & (df["close"] > _prev(df["high"], 2))


def inside_bar_breakout_down(df):
    inside = (_prev(df["high"]) < _prev(df["high"], 2)) & (_prev(df["low"]) > _prev(df["low"], 2))
    return inside & (df["close"] < _prev(df["low"], 2))


@dataclass(frozen=True)
class Pattern:
    name: str
    direction: str
    detect: Callable[[pd.DataFrame], pd.Series]


PATTERNS: tuple[Pattern, ...] = (
    Pattern("doji", NEUTRAL, doji),
    Pattern("hammer", BULLISH, hammer),
    Pattern("inverted_hammer", BULLISH, inverted_hammer),
    Pattern("bullish_marubozu", BULLISH, bullish_marubozu),
    Pattern("bullish_engulfing", BULLISH, bullish_engulfing),
    Pattern("bullish_harami", BULLISH, bullish_harami),
    Pattern("piercing_line", BULLISH, piercing_line),
    Pattern("tweezer_bottom", BULLISH, tweezer_bottom),
    Pattern("morning_star", BULLISH, morning_star),
    Pattern("three_white_soldiers", BULLISH, three_white_soldiers),
    Pattern("donchian_breakout_up", BULLISH, donchian_breakout_up),
    Pattern("inside_bar_breakout_up", BULLISH, inside_bar_breakout_up),
    Pattern("shooting_star", BEARISH, shooting_star),
    Pattern("hanging_man", BEARISH, hanging_man),
    Pattern("bearish_marubozu", BEARISH, bearish_marubozu),
    Pattern("bearish_engulfing", BEARISH, bearish_engulfing),
    Pattern("bearish_harami", BEARISH, bearish_harami),
    Pattern("dark_cloud_cover", BEARISH, dark_cloud_cover),
    Pattern("tweezer_top", BEARISH, tweezer_top),
    Pattern("evening_star", BEARISH, evening_star),
    Pattern("three_black_crows", BEARISH, three_black_crows),
    Pattern("donchian_breakout_down", BEARISH, donchian_breakout_down),
    Pattern("inside_bar_breakout_down", BEARISH, inside_bar_breakout_down),
)

PATTERN_BY_NAME = {p.name: p for p in PATTERNS}


def detect_all(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame bool sloupců – jeden sloupec na pattern."""
    return pd.DataFrame({p.name: p.detect(df).fillna(False).astype(bool) for p in PATTERNS}, index=df.index)


def active_patterns(df: pd.DataFrame, direction: str | None = None) -> list[str]:
    """Patterny dokončené na poslední svíčce DataFrame."""
    last = detect_all(df).iloc[-1]
    return [p.name for p in PATTERNS if last[p.name] and (direction is None or p.direction == direction)]
