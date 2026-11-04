"""Načtení a validace konfigurace z proměnných prostředí (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

LIVE_CONFIRM_PHRASE = "I_UNDERSTAND_THE_RISK"
VALID_MODES = ("paper", "testnet", "live")
# Taker poplatek za market objednávku na nejnižší úrovni objemu (konzervativně).
DEFAULT_FEES = {"binance": 0.001, "coinbase": 0.009}


class ConfigError(ValueError):
    """Neplatná konfigurace – agent se odmítne spustit."""


def load_dotenv(path: str | Path = ".env") -> None:
    """Minimalistický .env loader (nepřepisuje už nastavené proměnné)."""
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _float(env: dict, key: str, default: float) -> float:
    try:
        return float(env.get(key, default))
    except ValueError as exc:
        raise ConfigError(f"{key} musí být číslo") from exc


def _int(env: dict, key: str, default: int) -> int:
    try:
        return int(env.get(key, default))
    except ValueError as exc:
        raise ConfigError(f"{key} musí být celé číslo") from exc


def _bool(env: dict, key: str, default: bool) -> bool:
    return str(env.get(key, default)).strip().lower() in ("1", "true", "yes", "ano")


@dataclass(frozen=True)
class Config:
    exchange: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    mode: str = "paper"
    api_key: str = field(default="", repr=False)
    api_secret: str = field(default="", repr=False)
    risk_per_trade: float = 0.01
    max_position_pct: float = 0.25
    max_order_quote: float = 50.0
    max_daily_loss_pct: float = 0.03
    max_trades_per_day: int = 4
    stop_atr_mult: float = 2.0
    take_profit_r: float = 2.0
    paper_start_equity: float = 1000.0
    fee_rate: float = 0.001
    news_feeds: tuple[str, ...] = ()
    news_lookback_hours: float = 6.0
    news_exit_on_panic: bool = True
    news_fail_safe: str = "block"
    poll_seconds: int = 30
    state_dir: str = "state"
    auto_adapt: bool = True
    adapt_every_trades: int = 10
    adapt_min_trades: int = 15
    adapt_history_days: int = 730
    allow_altcoins: bool = False
    market_data: str = "exchange"
    strategy: str = "trend"
    entry_period: int = 20
    exit_period: int = 10
    trail_atr_mult: float = 3.0

    def validate(self) -> "Config":
        if self.mode not in VALID_MODES:
            raise ConfigError(f"MODE musí být jedno z {VALID_MODES}")
        if not 0 < self.risk_per_trade <= 0.05:
            raise ConfigError("RISK_PER_TRADE musí být v (0, 0.05] – víc než 5 % na obchod nepovolím")
        if not 0 < self.max_position_pct <= 1:
            raise ConfigError("MAX_POSITION_PCT musí být v (0, 1]")
        if not 0 < self.max_daily_loss_pct <= 0.2:
            raise ConfigError("MAX_DAILY_LOSS_PCT musí být v (0, 0.2]")
        if self.max_order_quote <= 0:
            raise ConfigError("MAX_ORDER_QUOTE musí být kladné")
        if self.news_fail_safe not in ("block", "ignore"):
            raise ConfigError("NEWS_FAIL_SAFE musí být 'block' nebo 'ignore'")
        if self.strategy not in ("trend", "patterns"):
            raise ConfigError("STRATEGY musí být 'trend' nebo 'patterns'")
        if self.exchange == "coinbase" and self.mode == "testnet":
            raise ConfigError("Coinbase nemá testnet – použij MODE=paper (simulace se živými daty)")
        if not 0 <= self.fee_rate < 0.05:
            raise ConfigError("FEE_RATE musí být v [0, 0.05)")
        if self.market_data not in ("exchange", "binance_vision"):
            raise ConfigError("MARKET_DATA musí být 'exchange' nebo 'binance_vision'")
        if self.base_asset != "BTC" and not self.allow_altcoins:
            raise ConfigError("Zatím obchodujeme jen BTC (pro jiné aktivum nastav ALLOW_ALTCOINS=true)")
        if self.adapt_every_trades < 1 or self.adapt_min_trades < 5:
            raise ConfigError("ADAPT_EVERY_TRADES musí být ≥ 1 a ADAPT_MIN_TRADES ≥ 5")
        if self.mode in ("testnet", "live") and not (self.api_key and self.api_secret):
            raise ConfigError("Pro testnet/live je potřeba API_KEY a API_SECRET")
        return self

    @property
    def base_asset(self) -> str:
        return self.symbol.split("/")[0]

    @property
    def quote_asset(self) -> str:
        return self.symbol.split("/")[1]


def config_from_env(env: dict | None = None) -> Config:
    env = dict(os.environ if env is None else env)
    feeds = tuple(f.strip() for f in env.get("NEWS_FEEDS", "").split(",") if f.strip())
    cfg = Config(
        exchange=env.get("EXCHANGE", "binance"),
        symbol=env.get("SYMBOL", "BTC/USDT"),
        timeframe=env.get("TIMEFRAME", "1h"),
        mode=env.get("MODE", "paper").lower(),
        api_key=env.get("API_KEY", ""),
        # Coinbase CDP klíč je víceřádkový PEM – v .env se zapisuje s \n
        api_secret=env.get("API_SECRET", "").replace("\\n", "\n"),
        risk_per_trade=_float(env, "RISK_PER_TRADE", 0.01),
        max_position_pct=_float(env, "MAX_POSITION_PCT", 0.25),
        max_order_quote=_float(env, "MAX_ORDER_QUOTE", 50.0),
        max_daily_loss_pct=_float(env, "MAX_DAILY_LOSS_PCT", 0.03),
        max_trades_per_day=_int(env, "MAX_TRADES_PER_DAY", 4),
        stop_atr_mult=_float(env, "STOP_ATR_MULT", 2.0),
        take_profit_r=_float(env, "TAKE_PROFIT_R", 2.0),
        paper_start_equity=_float(env, "PAPER_START_EQUITY", 1000.0),
        fee_rate=_float(env, "FEE_RATE", DEFAULT_FEES.get(env.get("EXCHANGE", "binance"), 0.001)),
        news_feeds=feeds,
        news_lookback_hours=_float(env, "NEWS_LOOKBACK_HOURS", 6.0),
        news_exit_on_panic=_bool(env, "NEWS_EXIT_ON_PANIC", True),
        news_fail_safe=env.get("NEWS_FAIL_SAFE", "block").lower(),
        poll_seconds=_int(env, "POLL_SECONDS", 30),
        state_dir=env.get("STATE_DIR", "state"),
        auto_adapt=_bool(env, "AUTO_ADAPT", True),
        adapt_every_trades=_int(env, "ADAPT_EVERY_TRADES", 10),
        adapt_min_trades=_int(env, "ADAPT_MIN_TRADES", 15),
        adapt_history_days=_int(env, "ADAPT_HISTORY_DAYS", 730),
        allow_altcoins=_bool(env, "ALLOW_ALTCOINS", False),
        market_data=env.get("MARKET_DATA", "exchange").lower(),
        strategy=env.get("STRATEGY", "trend").lower(),
        entry_period=_int(env, "ENTRY_PERIOD", 20),
        exit_period=_int(env, "EXIT_PERIOD", 10),
        trail_atr_mult=_float(env, "TRAIL_ATR_MULT", 3.0),
    ).validate()
    if cfg.mode == "live" and env.get("LIVE_CONFIRM") != LIVE_CONFIRM_PHRASE:
        raise ConfigError(f"Live režim vyžaduje LIVE_CONFIRM={LIVE_CONFIRM_PHRASE}")
    return cfg
