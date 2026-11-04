"""Tržní data a připojení k burze přes ccxt."""
from __future__ import annotations

import time

import pandas as pd

COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
PAGE_LIMIT = 1000


def make_exchange(cfg):
    import ccxt

    if not hasattr(ccxt, cfg.exchange):
        raise ValueError(f"Neznámá burza: {cfg.exchange}")
    params = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
    if cfg.api_key:
        params.update(apiKey=cfg.api_key, secret=cfg.api_secret)
    ex = getattr(ccxt, cfg.exchange)(params)
    if cfg.mode == "testnet":
        ex.set_sandbox_mode(True)
    return ex


def to_frame(rows: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df.drop_duplicates("timestamp").set_index("timestamp").astype(float).sort_index()


def drop_unclosed(df: pd.DataFrame, timeframe_seconds: int, now_ms: int | None = None) -> pd.DataFrame:
    """Odstraní poslední svíčku, pokud ještě není uzavřená (rozhodujeme jen na uzavřených)."""
    if df.empty:
        return df
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    last_open_ms = int(df.index[-1].timestamp() * 1000)
    if last_open_ms + timeframe_seconds * 1000 > now_ms:
        return df.iloc[:-1]
    return df


def fetch_recent(ex, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    rows = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
    return drop_unclosed(to_frame(rows), ex.parse_timeframe(timeframe), ex.milliseconds())


def fetch_history(ex, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    since = ex.milliseconds() - days * 86_400_000
    rows: list[list] = []
    while since < ex.milliseconds():
        page = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=PAGE_LIMIT)
        if not page:
            break
        rows.extend(page)
        since = page[-1][0] + tf_ms
        if len(page) < 2:
            break
    return drop_unclosed(to_frame(rows), ex.parse_timeframe(timeframe), ex.milliseconds())
