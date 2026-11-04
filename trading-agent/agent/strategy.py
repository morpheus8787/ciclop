"""Pravidlová strategie (jen long, spot). Stejný kód používá backtest i živý agent."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .indicators import with_indicators
from .patterns import BEARISH, BULLISH, PATTERNS, detect_all

WARMUP_BARS = 210  # EMA200 + rezerva


@dataclass(frozen=True)
class StrategyParams:
    rsi_min: float = 40.0
    rsi_max: float = 70.0
    stop_atr_mult: float = 2.0
    take_profit_r: float = 2.0
    bullish_patterns: tuple[str, ...] = tuple(p.name for p in PATTERNS if p.direction == BULLISH)
    bearish_patterns: tuple[str, ...] = tuple(p.name for p in PATTERNS if p.direction == BEARISH)

    def with_learned(self, path: str | Path) -> "StrategyParams":
        """Použije jen patterny, které prošly `learn` (pokud soubor existuje)."""
        p = Path(path)
        if not p.exists():
            return self
        data = json.loads(p.read_text(encoding="utf-8"))
        # Když učení nenašlo žádný bullish pattern s výhodou, agent NEOBCHODUJE (prázdná n-tice).
        bull = tuple(data.get("selected_bullish", ()))
        bear = tuple(data.get("selected_bearish", ())) or self.bearish_patterns
        return StrategyParams(self.rsi_min, self.rsi_max, self.stop_atr_mult, self.take_profit_r, bull, bear)


def generate_signals(ohlcv: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """Vrátí nový DataFrame se sloupci entry, exit, stop, take_profit, patterns.

    Signál na řádku i znamená: svíčka i je UZAVŘENÁ a obchod se provede na otevření i+1.
    """
    df = with_indicators(ohlcv)
    pats = detect_all(ohlcv)
    bull_hits = pats[list(params.bullish_patterns)] if params.bullish_patterns else pats.iloc[:, :0]
    bear_hits = pats[list(params.bearish_patterns)] if params.bearish_patterns else pats.iloc[:, :0]

    trend_up = (df["close"] > df["ema_slow"]) & (df["ema_fast"] > df["ema_slow"])
    rsi_ok = df["rsi"].between(params.rsi_min, params.rsi_max)
    any_bull = bull_hits.any(axis=1)
    entry = trend_up & rsi_ok & any_bull & df["atr"].notna()

    trend_broken = df["close"] < df["ema_fast"]
    exit_ = (bear_hits.any(axis=1) & trend_broken) | (df["close"] < df["ema_slow"])

    stop = df["close"] - params.stop_atr_mult * df["atr"]
    take_profit = df["close"] + params.take_profit_r * (df["close"] - stop)
    names = bull_hits.apply(lambda r: ",".join(r.index[r.values]), axis=1) if len(bull_hits.columns) else ""

    out = df.assign(entry=entry.fillna(False), exit=exit_.fillna(False), stop=stop,
                    take_profit=take_profit, patterns=names)
    out.loc[out.index[:WARMUP_BARS], ["entry"]] = False
    return out
