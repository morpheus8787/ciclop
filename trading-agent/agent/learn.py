"""„Učení“ patternů: změří, které patterny mají na daném trhu skutečnou výhodu.

Data se rozdělí na trénovací a ověřovací část (out-of-sample). Pattern se vybere,
jen když má výhodu v OBOU částech – to omezuje přeučení (overfitting).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .patterns import BEARISH, BULLISH, PATTERNS, detect_all


@dataclass(frozen=True)
class PatternStat:
    name: str
    direction: str
    count: int
    win_rate: float
    mean_edge_pct: float  # průměrný pohyb ve směru patternu po `horizon` svíčkách


def pattern_stats(ohlcv: pd.DataFrame, horizon: int = 12) -> list[PatternStat]:
    hits = detect_all(ohlcv)
    fwd = ohlcv["close"].shift(-horizon) / ohlcv["close"] - 1
    out = []
    for p in PATTERNS:
        if p.direction not in (BULLISH, BEARISH):
            continue
        sign = 1 if p.direction == BULLISH else -1
        r = (fwd[hits[p.name]] * sign).dropna()
        out.append(PatternStat(p.name, p.direction, int(len(r)),
                               round(float((r > 0).mean()), 3) if len(r) else 0.0,
                               round(float(r.mean() * 100), 3) if len(r) else 0.0))
    return out


def select_patterns(ohlcv: pd.DataFrame, horizon: int = 12, min_count: int = 20,
                    min_edge_pct: float = 0.25, train_frac: float = 0.7) -> dict:
    split = int(len(ohlcv) * train_frac)
    train = {s.name: s for s in pattern_stats(ohlcv.iloc[:split], horizon)}
    test = {s.name: s for s in pattern_stats(ohlcv.iloc[split:], horizon)}

    def passes(s: PatternStat, need: int) -> bool:
        return s.count >= need and s.mean_edge_pct >= min_edge_pct and s.win_rate > 0.5

    selected = [n for n in train
                if passes(train[n], min_count) and passes(test[n], max(5, min_count // 3))]
    return {
        "horizon": horizon,
        "bars": len(ohlcv),
        "selected_bullish": [n for n in selected if train[n].direction == BULLISH],
        "selected_bearish": [n for n in selected if train[n].direction == BEARISH],
        "train": [asdict(s) for s in train.values()],
        "test": [asdict(s) for s in test.values()],
    }


def save(report: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
