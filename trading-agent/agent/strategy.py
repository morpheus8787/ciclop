"""Pravidlová strategie (jen long, spot). Stejný kód používá backtest i živý agent."""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from .indicators import with_indicators
from .patterns import BEARISH, BULLISH, PATTERNS, detect_all

WARMUP_BARS = 210  # EMA200 + rezerva
CONTEXT_FEATURES = ("rsi", "stretch", "volatility", "session", "volume")


@dataclass(frozen=True)
class StrategyParams:
    rsi_min: float = 40.0
    rsi_max: float = 70.0
    stop_atr_mult: float = 2.0
    take_profit_r: float = 2.0
    bullish_patterns: tuple[str, ...] = tuple(p.name for p in PATTERNS if p.direction == BULLISH)
    bearish_patterns: tuple[str, ...] = tuple(p.name for p in PATTERNS if p.direction == BEARISH)
    blocked_contexts: tuple[str, ...] = ()   # např. ("stretch=>2ATR", "session=asia")
    breakeven_at_r: float | None = None      # posun stopu na nákupku po zisku X R
    kind: str = "patterns"                   # "patterns" nebo "trend"
    entry_period: int = 20                   # trend: nákup při průrazu N-denního maxima
    exit_period: int = 10                    # trend: prodej při průrazu N-denního minima
    trail_atr_mult: float | None = None      # trailing stop: nejvyšší cena − X × ATR

    def with_learned(self, path: str | Path) -> "StrategyParams":
        """Použije jen patterny, které prošly `learn` (pokud soubor existuje)."""
        p = Path(path)
        if not p.exists():
            return self
        data = json.loads(p.read_text(encoding="utf-8"))
        # Když učení nenašlo žádný bullish pattern s výhodou, agent NEOBCHODUJE (prázdná n-tice).
        bull = tuple(data.get("selected_bullish", ()))
        bear = tuple(data.get("selected_bearish", ())) or self.bearish_patterns
        return replace(self, bullish_patterns=bull, bearish_patterns=bear)

    def with_adaptations(self, adapt: dict | str | Path | None) -> "StrategyParams":
        """Aplikuje závěry z rozboru vlastních obchodů. Jen zpřísňuje – riziko nikdy nezvyšuje."""
        if adapt is None:
            return self
        if not isinstance(adapt, dict):
            p = Path(adapt)
            if not p.exists():
                return self
            adapt = json.loads(p.read_text(encoding="utf-8"))
        disabled = set(adapt.get("disabled_patterns", ()))
        be = adapt.get("breakeven_at_r")
        return replace(
            self,
            bullish_patterns=tuple(n for n in self.bullish_patterns if n not in disabled),
            blocked_contexts=tuple(sorted(set(self.blocked_contexts) | set(adapt.get("blocked_contexts", ())))),
            breakeven_at_r=float(be) if be else self.breakeven_at_r,
        )


def context_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Zařadí každou svíčku do přihrádek kontextu (pro rozbor obchodů a blokace)."""
    stretch = (df["close"] - df["ema_fast"]) / df["atr"]
    vol_pct = df["atr"] / df["close"] * 100
    hours = df.index.hour if isinstance(df.index, pd.DatetimeIndex) else np.zeros(len(df), dtype=int)
    vol_ratio = df["volume"] / df["vol_sma"]
    return pd.DataFrame({
        "ctx_rsi": np.select([df["rsi"] < 40, df["rsi"] < 50, df["rsi"] < 60, df["rsi"] <= 70],
                             ["<40", "40-50", "50-60", "60-70"], ">70"),
        "ctx_stretch": np.select([stretch < 1, stretch <= 2], ["<1ATR", "1-2ATR"], ">2ATR"),
        "ctx_volatility": np.select([vol_pct < 0.5, vol_pct <= 1.0], ["low", "mid"], "high"),
        "ctx_session": np.select([hours < 8, hours < 16], ["asia", "europe"], "us"),
        "ctx_volume": np.where(vol_ratio >= 1, "high", "low"),
    }, index=df.index)


def blocked_mask(ctx: pd.DataFrame, blocked: tuple[str, ...]) -> pd.Series:
    mask = pd.Series(False, index=ctx.index)
    for item in blocked:
        feature, _, bucket = item.partition("=")
        col = f"ctx_{feature}"
        if col in ctx:
            mask |= ctx[col] == bucket
    return mask


def _take_profit(df: pd.DataFrame, stop: pd.Series, params: StrategyParams) -> pd.Series:
    if params.take_profit_r and params.take_profit_r > 0:
        return df["close"] + params.take_profit_r * (df["close"] - stop)
    return pd.Series(np.nan, index=df.index)  # bez pevného cíle – zisky nechat běžet


def _trend_signals(ohlcv: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """Trend-following: průraz N-denního maxima nad EMA200, výstup při průrazu M-denního minima."""
    df = with_indicators(ohlcv)
    ctx = context_buckets(df)
    breakout = df["close"] > df["high"].rolling(params.entry_period).max().shift(1)
    entry = breakout & (df["close"] > df["ema_slow"]) & df["atr"].notna()
    entry &= ~blocked_mask(ctx, params.blocked_contexts)
    exit_ = df["close"] < df["low"].rolling(params.exit_period).min().shift(1)
    stop = df["close"] - params.stop_atr_mult * df["atr"]
    out = pd.concat([df, ctx], axis=1).assign(
        entry=entry.fillna(False), exit=exit_.fillna(False), stop=stop,
        take_profit=_take_profit(df, stop, params), patterns=f"breakout_{params.entry_period}")
    out.loc[out.index[:WARMUP_BARS], ["entry"]] = False
    return out


def generate_signals(ohlcv: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """Vrátí nový DataFrame se sloupci entry, exit, stop, take_profit, patterns a ctx_*.

    Signál na řádku i znamená: svíčka i je UZAVŘENÁ a obchod se provede na otevření i+1.
    """
    if params.kind == "trend":
        return _trend_signals(ohlcv, params)
    df = with_indicators(ohlcv)
    ctx = context_buckets(df)
    pats = detect_all(ohlcv)
    bull_hits = pats[list(params.bullish_patterns)] if params.bullish_patterns else pats.iloc[:, :0]
    bear_hits = pats[list(params.bearish_patterns)] if params.bearish_patterns else pats.iloc[:, :0]

    trend_up = (df["close"] > df["ema_slow"]) & (df["ema_fast"] > df["ema_slow"])
    rsi_ok = df["rsi"].between(params.rsi_min, params.rsi_max)
    any_bull = bull_hits.any(axis=1)
    entry = trend_up & rsi_ok & any_bull & df["atr"].notna() & ~blocked_mask(ctx, params.blocked_contexts)

    trend_broken = df["close"] < df["ema_fast"]
    exit_ = (bear_hits.any(axis=1) & trend_broken) | (df["close"] < df["ema_slow"])

    stop = df["close"] - params.stop_atr_mult * df["atr"]
    take_profit = _take_profit(df, stop, params)
    names = bull_hits.apply(lambda r: ",".join(r.index[r.values]), axis=1) if len(bull_hits.columns) else ""

    out = pd.concat([df, ctx], axis=1).assign(entry=entry.fillna(False), exit=exit_.fillna(False),
                                              stop=stop, take_profit=take_profit, patterns=names)
    out.loc[out.index[:WARMUP_BARS], ["entry"]] = False
    return out


def entry_context(row: pd.Series) -> dict:
    """Kontext vstupu uložený k obchodu – podklad pro pozdější rozbor."""
    ctx = {f: str(row.get(f"ctx_{f}", "")) for f in CONTEXT_FEATURES}
    ctx["rsi_value"] = round(float(row.get("rsi", float("nan"))), 1)
    return ctx


def breakeven_stop(stop: float, entry: float, initial_stop: float, max_price: float,
                   breakeven_at_r: float | None, fee_rate: float) -> float:
    """Posune stop na nákupní cenu (+ poplatky), jakmile cena došla do zisku `breakeven_at_r` × R."""
    if not breakeven_at_r:
        return stop
    risk = entry - initial_stop
    if risk > 0 and max_price >= entry + breakeven_at_r * risk:
        return max(stop, entry * (1 + 2 * fee_rate))
    return stop


def trailing_stop(stop: float, max_price: float, atr: float | None, trail_atr_mult: float | None) -> float:
    """Stop se jen posouvá nahoru: nejvyšší dosažená cena − X × ATR."""
    if not trail_atr_mult or atr is None or not np.isfinite(atr):
        return stop
    return max(stop, max_price - trail_atr_mult * atr)
