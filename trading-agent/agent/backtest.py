"""Backtest na historických svíčkách – stejné signály i stejné řízení rizika jako live."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .risk import RiskLimits, position_size
from .strategy import StrategyParams, generate_signals


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


@dataclass(frozen=True)
class BacktestResult:
    trades: tuple[Trade, ...]
    equity_curve: pd.Series
    start_equity: float

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1]) if len(self.equity_curve) else self.start_equity

    def summary(self) -> dict:
        pnls = [t.pnl for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        curve = self.equity_curve
        dd = float(((curve - curve.cummax()) / curve.cummax()).min()) if len(curve) else 0.0
        return {
            "trades": len(pnls),
            "win_rate": round(len(wins) / len(pnls), 3) if pnls else 0.0,
            "total_return_pct": round((self.final_equity / self.start_equity - 1) * 100, 2),
            "max_drawdown_pct": round(dd * 100, 2),
            "profit_factor": round(sum(wins) / -sum(losses), 2) if losses and sum(losses) < 0 else None,
            "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0.0,
            "final_equity": round(self.final_equity, 2),
        }


def run_backtest(ohlcv: pd.DataFrame, params: StrategyParams, limits: RiskLimits,
                 start_equity: float = 1000.0, fee_rate: float = 0.001) -> BacktestResult:
    sig = generate_signals(ohlcv, params)
    cash, qty = start_equity, 0.0
    entry_px = stop = tp = 0.0
    entry_t, entry_pats = None, ""
    trades: list[Trade] = []
    equity = []
    idx = sig.index

    def close_pos(t, px, reason):
        nonlocal cash, qty
        proceeds = qty * px * (1 - fee_rate)
        cost = qty * entry_px * (1 + fee_rate)
        trades.append(Trade(entry_t, t, entry_px, px, qty, proceeds - cost, reason, entry_pats))
        cash += proceeds
        qty = 0.0

    for i in range(1, len(sig)):
        prev, bar, t = sig.iloc[i - 1], sig.iloc[i], idx[i]
        # 1) rozhodnutí z uzavřené svíčky i-1 → provedení na open svíčky i
        if qty > 0 and prev["exit"]:
            close_pos(t, bar["open"], "signal")
        elif qty == 0 and prev["entry"]:
            px = bar["open"]
            s = prev["stop"]
            q = position_size(cash, px, s, limits)
            if q > 0 and q * px * (1 + fee_rate) <= cash:
                cash -= q * px * (1 + fee_rate)
                qty, entry_px, stop, tp = q, px, s, px + params.take_profit_r * (px - s)
                entry_t, entry_pats = t, prev["patterns"]
        # 2) stop / take-profit uvnitř svíčky (konzervativně: stop má přednost)
        if qty > 0:
            if bar["low"] <= stop:
                close_pos(t, min(stop, bar["open"]), "stop")
            elif bar["high"] >= tp:
                close_pos(t, max(tp, bar["open"]), "take_profit")
        equity.append(cash + qty * bar["close"])

    if qty > 0:
        close_pos(idx[-1], sig.iloc[-1]["close"], "end")
        equity[-1] = cash
    return BacktestResult(tuple(trades), pd.Series(equity, index=idx[1:]), start_equity)
