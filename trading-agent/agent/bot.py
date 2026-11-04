"""Hlavní smyčka živého agenta. Jedna iterace = `tick()`; vše deterministické a logované."""
from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable

from . import news as news_mod
from .review import TradeRecord, append_record
from .risk import RiskLimits, can_open, check_daily_loss, position_size, record_trade, roll_day
from .store import AgentState, Position, Store
from .strategy import StrategyParams, breakeven_stop, entry_context, generate_signals, trailing_stop

log = logging.getLogger(__name__)

NEWS_REFRESH_SECONDS = 300
MAX_CONSECUTIVE_ERRORS = 10
TIMEFRAME_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def timeframe_seconds(tf: str) -> int:
    return int(tf[:-1]) * TIMEFRAME_SECONDS[tf[-1]]


class TradingAgent:
    def __init__(self, cfg, broker, store: Store, params: StrategyParams,
                 bars_fn: Callable, news_fn: Callable | None = None, clock: Callable = _utcnow,
                 adapt_fn: Callable[[], StrategyParams | None] | None = None):
        self.cfg, self.broker, self.store, self.params = cfg, broker, store, params
        self.bars_fn, self.clock, self.adapt_fn = bars_fn, clock, adapt_fn
        self.news_fn = news_fn or (lambda: news_mod.fetch_headlines(cfg.news_feeds))
        self.limits = RiskLimits(cfg.risk_per_trade, cfg.max_position_pct, cfg.max_order_quote,
                                 cfg.max_daily_loss_pct, cfg.max_trades_per_day)
        self.state = store.load()
        self._news, self._news_at = None, 0.0
        self._closed_since_adapt = 0
        self._atr: float | None = None  # ATR poslední uzavřené svíčky (pro trailing stop)

    # --- pomocné -------------------------------------------------------------
    def _commit(self, state: AgentState) -> None:
        snap = self.broker.snapshot()
        self.state = replace(state, paper=snap or state.paper)
        self.store.save(self.state)

    def news(self) -> news_mod.NewsAssessment:
        if not self.cfg.news_feeds:
            return news_mod.NewsAssessment(False, False, 0.0, ("žádné feedy nenastaveny",), True)
        if self._news is None or time.monotonic() - self._news_at > NEWS_REFRESH_SECONDS:
            headlines, ok = self.news_fn()
            self._news = news_mod.assess(headlines, self.clock(), self.cfg.news_lookback_hours,
                                         (self.cfg.base_asset,), ok, self.cfg.news_fail_safe)
            self._news_at = time.monotonic()
            for r in self._news.reasons:
                log.info("Zprávy: %s", r)
        return self._news

    def _trade_record(self, pos: Position, fill, pnl: float, reason: str) -> TradeRecord:
        risk = pos.risk if pos.risk > 0 else float("nan")
        opened = datetime.fromisoformat(pos.opened_at)
        bars = int((self.clock() - opened).total_seconds() // timeframe_seconds(self.cfg.timeframe))
        hi, lo = max(pos.max_price, fill.price), min(pos.min_price or fill.price, fill.price)
        return TradeRecord(
            pos.opened_at, self.clock().isoformat(), pos.entry, fill.price, pos.initial_stop or pos.stop,
            fill.qty, round(pnl, 6), round(pnl / (fill.qty * risk), 3), round((hi - pos.entry) / risk, 3),
            round((lo - pos.entry) / risk, 3), bars, reason, pos.patterns, dict(pos.context), self.cfg.mode,
        )

    def _sell(self, state: AgentState, reason: str, equity: float) -> AgentState:
        pos = state.position
        fill = self.broker.market_sell(pos.qty)
        pnl = (fill.price - pos.entry) * fill.qty - self.cfg.fee_rate * fill.qty * (fill.price + pos.entry)
        if reason == "stop" and pos.stop >= pos.entry:
            reason = "trailing_stop" if self.params.trail_atr_mult else "breakeven"
        log.warning("EXIT %s: %.8f @ %.2f, PnL≈%.2f", reason, fill.qty, fill.price, pnl)
        self.store.journal(mode=self.cfg.mode, side="sell", symbol=self.cfg.symbol, qty=fill.qty,
                           price=fill.price, reason=reason, pnl=round(pnl, 4), equity=round(equity, 2),
                           notes=pos.patterns)
        append_record(self.store.trades_path, self._trade_record(pos, fill, pnl, reason))
        self._closed_since_adapt += 1
        return replace(state, position=None)

    def _buy(self, state: AgentState, sig, equity: float, quote_free: float, news_score: float) -> AgentState:
        price = self.broker.price()
        stop = float(sig["stop"])
        if price <= stop:
            log.info("Cena %.2f už pod stopem %.2f – vstup přeskočen", price, stop)
            return state
        qty = position_size(min(equity, quote_free), price, stop, self.limits)
        if qty <= 0:
            log.info("Velikost pozice vyšla 0 – vstup přeskočen")
            return state
        fill = self.broker.market_buy(qty)
        # take_profit = 0 znamená bez pevného cíle (trend-following nechává zisky běžet)
        tp = fill.price + self.params.take_profit_r * (fill.price - stop) if self.params.take_profit_r > 0 else 0.0
        ctx = {**entry_context(sig), "news_score": round(news_score, 1)}
        pos = Position(fill.qty, fill.price, stop, tp, self.clock().isoformat(), str(sig["patterns"]),
                       initial_stop=stop, max_price=fill.price, min_price=fill.price, context=ctx)
        log.warning("ENTRY %.8f @ %.2f | stop %.2f | tp %.2f | %s", fill.qty, fill.price, stop, tp, pos.patterns)
        self.store.journal(mode=self.cfg.mode, side="buy", symbol=self.cfg.symbol, qty=fill.qty,
                           price=fill.price, reason="signal", pnl="", equity=round(equity, 2),
                           notes=f"stop={stop:.2f} tp={tp:.2f} patterns={pos.patterns} ctx={ctx}")
        return replace(state, position=pos, day=record_trade(state.day))

    def _track(self, pos: Position, price: float) -> Position:
        """Průběžné max/min ceny (pro MFE/MAE) a případný posun stopu na nákupku."""
        hi = max(pos.max_price or pos.entry, price)
        lo = min(pos.min_price or pos.entry, price)
        stop = breakeven_stop(pos.stop, pos.entry, pos.initial_stop or pos.stop, hi,
                              self.params.breakeven_at_r, self.cfg.fee_rate)
        stop = trailing_stop(stop, hi, self._atr, self.params.trail_atr_mult)
        if stop != pos.stop:
            log.warning("Stop posunut nahoru: %.2f → %.2f", pos.stop, stop)
        return replace(pos, max_price=hi, min_price=lo, stop=stop)

    def _maybe_adapt(self) -> None:
        if not (self.cfg.auto_adapt and self.adapt_fn) or self._closed_since_adapt < self.cfg.adapt_every_trades:
            return
        self._closed_since_adapt = 0
        log.warning("Rozbor vlastních obchodů – hledám chyby a ověřuji úpravy pravidel…")
        new_params = self.adapt_fn()
        if new_params is not None and new_params != self.params:
            log.warning("Pravidla upravena: vypnuté patterny/blokace=%s, breakeven=%s",
                        new_params.blocked_contexts, new_params.breakeven_at_r)
            self.params = new_params

    # --- jedna iterace -------------------------------------------------------
    def tick(self) -> AgentState:
        state = self.state
        price = self.broker.price()
        quote_free, base_free = self.broker.balances()
        equity = quote_free + base_free * price
        day = check_daily_loss(roll_day(state.day, self.clock(), equity), equity, self.limits)
        state = replace(state, day=day)

        # 1) ochrana otevřené pozice – stop/take-profit hlídá agent každý tick
        if state.position:
            state = replace(state, position=self._track(state.position, price))
        pos = state.position
        if pos and price <= pos.stop:
            state = self._sell(state, "stop", equity)
        elif pos and pos.take_profit and price >= pos.take_profit:
            state = self._sell(state, "take_profit", equity)

        news = self.news()
        if state.position and news.panic and self.cfg.news_exit_on_panic:
            state = self._sell(state, "news_panic", equity)

        # 2) rozhodování jen na nové uzavřené svíčce
        bars = self.bars_fn()
        if bars.empty:
            self._commit(state)
            self._maybe_adapt()
            return self.state
        bar_id = bars.index[-1].isoformat()
        if bar_id != state.last_bar:
            sig = generate_signals(bars, self.params).iloc[-1]
            self._atr = float(sig["atr"]) if sig["atr"] == sig["atr"] else None
            if state.position and bool(sig["exit"]):
                state = self._sell(state, "signal", equity)
            elif not state.position and bool(sig["entry"]):
                ok, why = can_open(state.day, self.limits, self.cfg.state_dir)
                if not ok:
                    log.info("Vstupní signál ignorován: %s", why)
                elif news.block_entries:
                    log.info("Vstupní signál ignorován kvůli zprávám (skóre %.1f)", news.score)
                else:
                    state = self._buy(state, sig, equity, quote_free, news.score)
            state = replace(state, last_bar=bar_id)
            log.info("Svíčka %s | close %.2f | equity %.2f | pozice: %s", bar_id, bars['close'].iloc[-1],
                     equity, "ano" if state.position else "ne")
        self._commit(state)
        self._maybe_adapt()
        return self.state

    def run_forever(self) -> None:
        errors = 0
        log.warning("Agent startuje v režimu %s na %s %s", self.cfg.mode.upper(), self.cfg.symbol, self.cfg.timeframe)
        while True:
            try:
                self.tick()
                errors = 0
            except KeyboardInterrupt:
                log.warning("Ukončeno uživatelem. Otevřená pozice (pokud je) zůstává na burze!")
                raise
            except Exception:
                errors += 1
                log.exception("Chyba v iteraci (%d/%d)", errors, MAX_CONSECUTIVE_ERRORS)
                if errors >= MAX_CONSECUTIVE_ERRORS:
                    log.critical("Příliš mnoho chyb za sebou – agent se zastavuje.")
                    raise
            time.sleep(self.cfg.poll_seconds)
