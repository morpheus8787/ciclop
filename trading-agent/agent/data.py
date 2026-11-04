"""Tržní data a připojení k burze přes ccxt."""
from __future__ import annotations

import os
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
    # ccxt nepřebírá proxy z proměnných prostředí – předáme ji explicitně (firemní síť, cloud)
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        params["httpsProxy"] = proxy
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


class BinanceVisionData:
    """Veřejná tržní data Binance z data-api.binance.vision (bez klíčů, bez omezení podle země).

    Implementuje jen to, co agent potřebuje pro data (stejná jména metod jako ccxt):
    fetch_ohlcv, fetch_ticker, parse_timeframe, milliseconds.
    """

    BASE_URL = "https://data-api.binance.vision/api/v3"
    TIMEOUT_SECONDS = 30

    def __init__(self, opener=None):
        import urllib.request

        self._open = opener or (lambda url: urllib.request.urlopen(url, timeout=self.TIMEOUT_SECONDS))

    def _get(self, path: str, **params):
        import json
        from urllib.parse import urlencode

        url = f"{self.BASE_URL}/{path}?{urlencode({k: v for k, v in params.items() if v is not None})}"
        with self._open(url) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _symbol(symbol: str) -> str:
        return symbol.replace("/", "").upper()

    @staticmethod
    def parse_timeframe(tf: str) -> int:
        units = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
        return int(tf[:-1]) * units[tf[-1]]

    @staticmethod
    def milliseconds() -> int:
        return int(time.time() * 1000)

    def fetch_ohlcv(self, symbol: str, timeframe: str, since: int | None = None, limit: int = 500):
        rows = self._get("klines", symbol=self._symbol(symbol), interval=timeframe,
                         startTime=since, limit=min(limit, PAGE_LIMIT))
        return [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])] for r in rows]

    def fetch_ticker(self, symbol: str) -> dict:
        data = self._get("ticker/price", symbol=self._symbol(symbol))
        return {"symbol": symbol, "last": float(data["price"])}


def make_market_data(cfg):
    """Zdroj tržních dat: vlastní burza (ccxt) nebo veřejné API binance.vision."""
    if cfg.market_data == "binance_vision":
        return BinanceVisionData()
    return make_exchange(cfg)
