"""Smyčka učení z vlastních chyb.

1. Backtest na trénovací části historie + všechny skutečné (paper/live) obchody → rozbor.
2. Z rozboru se odvodí adaptace (jen zpřísnění).
3. Adaptace se ověří na NOVĚJŠÍ části historie, kterou rozbor neviděl.
4. Přijme se jen tehdy, když na ověřovacích datech nezhorší výsledek ani drawdown.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .review import analyze, derive_adaptations, from_backtest, is_noop, render_markdown
from .risk import RiskLimits
from .strategy import WARMUP_BARS, StrategyParams

ADAPTATIONS_FILE = "adaptations.json"
TRADES_FILE = "trades.jsonl"
REVIEWS_DIR = "reviews"
MIN_VALIDATION_TRADES = 10  # méně obchodů na ověřovacích datech = nelze odlišit od náhody
MAX_DD_WORSENING_PCT = 1.0


@dataclass(frozen=True)
class SelfReview:
    report: dict
    adaptations: dict
    validation: dict
    live_report: dict | None
    markdown: str


def _validate(test_df, base: StrategyParams, cand: StrategyParams, limits, equity, fee, adapt) -> dict:
    b = run_backtest(test_df, base, limits, equity, fee).summary()
    c = run_backtest(test_df, cand, limits, equity, fee).summary()
    if is_noop(adapt):
        return {"accepted": False, "why": "není co měnit", "baseline": b, "candidate": c}
    if min(b["trades"], c["trades"]) < MIN_VALIDATION_TRADES:
        return {"accepted": False, "baseline": b, "candidate": c,
                "why": f"málo obchodů na ověření (původní {b['trades']}, upravená {c['trades']}, "
                       f"potřeba ≥ {MIN_VALIDATION_TRADES})"}
    better = c["expectancy_r"] >= b["expectancy_r"] and c["total_return_pct"] >= b["total_return_pct"]
    dd_ok = c["max_drawdown_pct"] >= b["max_drawdown_pct"] - MAX_DD_WORSENING_PCT
    why = ("zlepšuje průměr R i výnos a nezhoršuje drawdown" if better and dd_ok
           else "na nových datech by výsledek nezlepšila – nejspíš náhoda/přeučení")
    return {"accepted": better and dd_ok, "why": why, "baseline": b, "candidate": c}


def self_review(ohlcv: pd.DataFrame, base: StrategyParams, limits: RiskLimits, live_records=(),
                start_equity: float = 1000.0, fee_rate: float = 0.001, train_frac: float = 0.7,
                min_trades: int = 15) -> SelfReview:
    split = int(len(ohlcv) * train_frac)
    train_trades = run_backtest(ohlcv.iloc[:split], base, limits, start_equity, fee_rate).trades
    records = [from_backtest(t) for t in train_trades] + list(live_records)
    report = analyze(records)
    adapt = derive_adaptations(report, min_trades)
    test_df = ohlcv.iloc[max(0, split - WARMUP_BARS):]
    validation = _validate(test_df, base, base.with_adaptations(adapt), limits, start_equity, fee_rate, adapt)
    live_report = analyze(list(live_records)) if live_records else None
    md = render_markdown(report, adapt, validation, "Rozbor obchodů (historie + vlastní obchody)")
    if live_report:
        md += "\n\n" + render_markdown(live_report, title="Jen skutečné obchody agenta (paper/live)")
    return SelfReview(report, adapt, validation, live_report, md)


def save_review(result: SelfReview, state_dir: str | Path, now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    d = Path(state_dir) / REVIEWS_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"review-{now:%Y%m%d-%H%M}.md"
    path.write_text(result.markdown, encoding="utf-8")
    if result.validation["accepted"]:
        payload = {**result.adaptations, "accepted_at": now.isoformat(),
                   "validation": {k: result.validation[k] for k in ("baseline", "candidate")}}
        (Path(state_dir) / ADAPTATIONS_FILE).write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")
    return path
