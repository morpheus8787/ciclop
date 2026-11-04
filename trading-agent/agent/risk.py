"""Tvrdé řízení rizika – tady se eliminují emoce. Nic z toho nejde obejít strategií."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

KILL_SWITCH_FILE = "STOP"


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade: float
    max_position_pct: float
    max_order_quote: float
    max_daily_loss_pct: float
    max_trades_per_day: int


@dataclass(frozen=True)
class DayState:
    day: str
    start_equity: float
    trades: int = 0
    halted: bool = False


def position_size(equity: float, entry: float, stop: float, limits: RiskLimits) -> float:
    """Množství base aktiva tak, aby ztráta při stopu = risk_per_trade * equity.

    Výsledek je dál omezen % účtu a absolutním stropem v quote měně.
    """
    if equity <= 0 or entry <= 0 or stop <= 0 or stop >= entry:
        return 0.0
    risk_qty = equity * limits.risk_per_trade / (entry - stop)
    pct_cap_qty = equity * limits.max_position_pct / entry
    abs_cap_qty = limits.max_order_quote / entry
    return max(0.0, min(risk_qty, pct_cap_qty, abs_cap_qty))


def roll_day(state: DayState | None, now: datetime, equity: float) -> DayState:
    today = now.strftime("%Y-%m-%d")
    if state is None or state.day != today:
        return DayState(day=today, start_equity=equity)
    return state


def check_daily_loss(state: DayState, equity: float, limits: RiskLimits) -> DayState:
    if not state.halted and equity <= state.start_equity * (1 - limits.max_daily_loss_pct):
        return replace(state, halted=True)
    return state


def can_open(state: DayState, limits: RiskLimits, state_dir: str | Path = ".") -> tuple[bool, str]:
    if (Path(state_dir) / KILL_SWITCH_FILE).exists():
        return False, f"kill-switch: existuje soubor {KILL_SWITCH_FILE}"
    if state.halted:
        return False, "denní limit ztráty dosažen – dnes už žádné obchody"
    if state.trades >= limits.max_trades_per_day:
        return False, "dosažen max. počet obchodů za den"
    return True, "ok"


def record_trade(state: DayState) -> DayState:
    return replace(state, trades=state.trades + 1)
