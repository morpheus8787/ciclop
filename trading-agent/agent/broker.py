"""Provádění objednávek: PaperBroker (simulace) a ExchangeBroker (testnet/live přes ccxt)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Fill:
    qty: float
    price: float


class OrderRejected(RuntimeError):
    pass


class PaperBroker:
    """Simulace s poplatky; zůstatky se ukládají do state přes `snapshot()`."""

    def __init__(self, exchange, symbol: str, cash: float, base: float = 0.0, fee_rate: float = 0.001):
        self.exchange, self.symbol, self.fee_rate = exchange, symbol, fee_rate
        self.cash, self.base = cash, base

    def price(self) -> float:
        return float(self.exchange.fetch_ticker(self.symbol)["last"])

    def balances(self) -> tuple[float, float]:
        return self.cash, self.base

    def market_buy(self, qty: float) -> Fill:
        px = self.price()
        cost = qty * px * (1 + self.fee_rate)
        if qty <= 0 or cost > self.cash:
            raise OrderRejected(f"nedostatek prostředků ({cost:.2f} > {self.cash:.2f})")
        self.cash -= cost
        self.base += qty
        return Fill(qty, px)

    def market_sell(self, qty: float) -> Fill:
        qty = min(qty, self.base)
        if qty <= 0:
            raise OrderRejected("není co prodat")
        px = self.price()
        self.base -= qty
        self.cash += qty * px * (1 - self.fee_rate)
        return Fill(qty, px)

    def snapshot(self) -> dict:
        return {"cash": self.cash, "base": self.base}


class ExchangeBroker:
    """Skutečné market objednávky. Respektuje přesnost a minimální velikost objednávky burzy."""

    def __init__(self, exchange, symbol: str):
        self.exchange, self.symbol = exchange, symbol
        exchange.load_markets()
        self.market = exchange.market(symbol)
        self.base_ccy, self.quote_ccy = self.market["base"], self.market["quote"]

    def price(self) -> float:
        return float(self.exchange.fetch_ticker(self.symbol)["last"])

    def balances(self) -> tuple[float, float]:
        bal = self.exchange.fetch_balance()
        free = bal.get("free", {})
        return float(free.get(self.quote_ccy) or 0), float(free.get(self.base_ccy) or 0)

    def _prepare(self, qty: float) -> float:
        amount = float(self.exchange.amount_to_precision(self.symbol, qty))
        limits = self.market.get("limits", {})
        min_amt = (limits.get("amount") or {}).get("min") or 0
        min_cost = (limits.get("cost") or {}).get("min") or 0
        if amount <= 0 or amount < min_amt or amount * self.price() < min_cost:
            raise OrderRejected(f"objednávka {amount} je pod minimem burzy (amount≥{min_amt}, cost≥{min_cost})")
        return amount

    def _send(self, side: str, qty: float) -> Fill:
        amount = self._prepare(qty)
        if side == "buy" and self.exchange.options.get("createMarketBuyOrderRequiresPrice"):
            # Coinbase: market nákup se zadává částkou v quote měně (EUR/USDC), ne množstvím BTC
            cost = float(self.exchange.cost_to_precision(self.symbol, amount * self.price()))
            order = self.exchange.create_market_buy_order_with_cost(self.symbol, cost)
        else:
            order = self.exchange.create_order(self.symbol, "market", side, amount)
        order = self._refresh(order)
        filled = float(order.get("filled") or amount)
        avg = float(order.get("average") or order.get("price") or self.price())
        log.info("%s %s %.8f @ %.2f (id=%s)", side.upper(), self.symbol, filled, avg, order.get("id"))
        return Fill(filled, avg)

    def _refresh(self, order: dict) -> dict:
        """Některé burzy (Coinbase) vrací po odeslání jen ID – dotáhneme skutečné plnění."""
        if order.get("filled") and order.get("average"):
            return order
        try:
            return self.exchange.fetch_order(order["id"], self.symbol) or order
        except Exception as exc:
            log.warning("Nepodařilo se načíst detail objednávky %s: %s", order.get("id"), exc)
            return order

    def market_buy(self, qty: float) -> Fill:
        return self._send("buy", qty)

    def market_sell(self, qty: float) -> Fill:
        _, base = self.balances()
        return self._send("sell", min(qty, base))

    def snapshot(self) -> dict:
        return {}
