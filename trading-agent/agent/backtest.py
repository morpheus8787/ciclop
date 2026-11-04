"""Backtest na historických svíčkách – stejné signály i stejné řízení rizika jako live."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .risk import RiskLimits, position_size
from .strategy import StrategyParams, breakeven_stop, entry_context, generate_signals


@dataclass(frozen=True)
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry: float
    exit: float
    qty: float
    pnl: float
    reason: str
    patterns: str
    stop: float = 0.0           # počáteční stop (definuje 1R)
    r_multiple: float = 0.0     # výsledek v násobcích rizika
    mfe_r: float = 0.0          # max. nerealizovaný zisk v R
    mae_r: float = 0.0          # max. nerealizovaná ztráta v R (záporné)
    bars_held: int = 0
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class BacktestResult:
    trades: tuple[Trade, ...]
    equity_curve: pd.Series
    start_equity: float

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1]) if len(self.equity_curve) else self.start_equity

    def summary(self) -> dict:
        pnls = [float(t.pnl) for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        curve = self.equity_curve
        dd = float(((curve - curve.cummax()) / curve.cummax()).min()) if len(curve) else 0.0
        return {
            "trades": len(pnls),
            "win_rate": round(len(wins) / len(pnls), 3) if pnls else 0.0,
            "expectancy_r": round(float(sum(t.r_multiple for t in self.trades)) / len(pnls), 3) if pnls else 0.0,
            "total_return_pct": round((self.final_equity / self.start_equity - 1) * 100, 2),
            "max_drawdown_pct": round(dd * 100, 2),
            "profit_factor": round(sum(wins) / -sum(losses), 2) if losses and sum(losses) < 0 else None,
            "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "final_equity": round(self.final_equity, 2),
        }


@dataclass
class _Open:
    """Interní (mutovatelný jen uvnitř smyčky backtestu) stav otevřené pozice."""
    qty: float
    entry: float
    stop: float
    initial_stop: float
    tp: float
    t: pd.Timestamp
    i: int
    patterns: str
    context: dict
    hi: float
    lo: float


def run_backtest(ohlcv: pd.DataFrame, params: StrategyParams, limits: RiskLimits,
                 start_equity: float = 1000.0, fee_rate: float = 0.001) -> BacktestResult:
    sig = generate_signals(ohlcv, params)
    cash = start_equity
    pos: _Open | None = None
    trades: list[Trade] = []
    equity = []
    idx = sig.index

    def close_pos(i, px, reason):
        nonlocal cash, pos
        proceeds = pos.qty * px * (1 - fee_rate)
        cost = pos.qty * pos.entry * (1 + fee_rate)
        risk = pos.entry - pos.initial_stop
        trades.append(Trade(
            pos.t, idx[i], pos.entry, px, pos.qty, proceeds - cost, reason, pos.patterns,
            stop=pos.initial_stop, r_multiple=round((proceeds - cost) / (pos.qty * risk), 3),
            mfe_r=round((pos.hi - pos.entry) / risk, 3), mae_r=round((pos.lo - pos.entry) / risk, 3),
            bars_held=i - pos.i, context=pos.context,
        ))
        cash += proceeds
        pos = None

    for i in range(1, len(sig)):
        prev, bar = sig.iloc[i - 1], sig.iloc[i]
        # 1) rozhodnutí z uzavřené svíčky i-1 → provedení na open svíčky i
        if pos and prev["exit"]:
            close_pos(i, bar["open"], "signal")
        elif pos is None and prev["entry"]:
            px, s = bar["open"], prev["stop"]
            q = position_size(cash, px, s, limits)
            if q > 0 and px > s and q * px * (1 + fee_rate) <= cash:
                cash -= q * px * (1 + fee_rate)
                pos = _Open(q, px, s, s, px + params.take_profit_r * (px - s), idx[i], i,
                            prev["patterns"], entry_context(prev), px, px)
        # 2) stop / take-profit uvnitř svíčky (konzervativně: stop má přednost)
        if pos:
            pos.hi, pos.lo = max(pos.hi, bar["high"]), min(pos.lo, bar["low"])
            if bar["low"] <= pos.stop:
                reason = "breakeven" if pos.stop >= pos.entry else "stop"
                close_pos(i, min(pos.stop, bar["open"]), reason)
            elif bar["high"] >= pos.tp:
                close_pos(i, max(pos.tp, bar["open"]), "take_profit")
            else:  # posun stopu platí až od další svíčky
                pos.stop = breakeven_stop(pos.stop, pos.entry, pos.initial_stop, pos.hi,
                                          params.breakeven_at_r, fee_rate)
        equity.append(cash + (pos.qty * bar["close"] if pos else 0.0))

    if pos:
        close_pos(len(sig) - 1, sig.iloc[-1]["close"], "end")
        equity[-1] = cash
    return BacktestResult(tuple(trades), pd.Series(equity, index=idx[1:]), start_equity)
