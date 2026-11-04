"""Perzistentní stav (pozice, denní limity, paper zůstatky) a deník obchodů."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .risk import DayState

JOURNAL_FIELDS = ["time", "mode", "side", "symbol", "qty", "price", "reason", "pnl", "equity", "notes"]


@dataclass(frozen=True)
class Position:
    qty: float
    entry: float
    stop: float
    take_profit: float
    opened_at: str
    patterns: str = ""


@dataclass(frozen=True)
class AgentState:
    position: Position | None = None
    day: DayState | None = None
    last_bar: str | None = None
    paper: dict | None = None


class Store:
    def __init__(self, state_dir: str | Path):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.journal_path = self.dir / "journal.csv"

    def load(self) -> AgentState:
        if not self.state_path.exists():
            return AgentState()
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        pos = Position(**raw["position"]) if raw.get("position") else None
        day = DayState(**raw["day"]) if raw.get("day") else None
        return AgentState(pos, day, raw.get("last_bar"), raw.get("paper"))

    def save(self, state: AgentState) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
        tmp.replace(self.state_path)  # atomický zápis

    def journal(self, **row) -> None:
        new = not self.journal_path.exists()
        with self.journal_path.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=JOURNAL_FIELDS)
            if new:
                w.writeheader()
            w.writerow({"time": datetime.now(timezone.utc).isoformat(), **row})
