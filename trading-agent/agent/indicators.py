"""Technické indikátory nad pandas Series/DataFrame (sloupce open, high, low, close, volume)."""
from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI s Wilderovým vyhlazováním."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    out = 100 - 100 / (1 + rs)
    return out.where(avg_loss != 0, 100.0).where(avg_gain.notna())


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Vrátí NOVÝ DataFrame s přidanými indikátory (vstup nemění)."""
    return df.assign(
        ema_fast=ema(df["close"], 50),
        ema_slow=ema(df["close"], 200),
        rsi=rsi(df["close"], 14),
        atr=atr(df, 14),
        vol_sma=sma(df["volume"], 20),
    )
