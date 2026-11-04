"""Sledování zpráv z RSS a jejich převod na jednoduché obchodní rozhodnutí.

Záměrně deterministické (slovník klíčových slov), aby se dalo auditovat.
Neřeší přihlášení k placeným zdrojům – používá veřejné RSS (včetně FT RSS titulků).
"""
from __future__ import annotations

import calendar
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

log = logging.getLogger(__name__)

SEVERE_NEGATIVE = (
    "hack", "hacked", "exploit", "drained", "bankrupt", "bankruptcy", "insolven",
    "halts withdrawals", "suspends withdrawals", "freeze withdrawals", "depeg", "collapse",
    "ponzi", "fraud charges", "sec sues", "sues binance", "sues coinbase", "ban on crypto",
    "bans crypto", "crypto ban", "emergency rate", "flash crash",
)
NEGATIVE = (
    "crash", "plunge", "plummet", "selloff", "sell-off", "slump", "tumble", "liquidation",
    "lawsuit", "probe", "investigation", "crackdown", "outflows", "recession", "fears",
    "rate hike", "hawkish", "downgrade", "warning",
)
POSITIVE = (
    "rally", "surge", "soar", "record high", "all-time high", "inflows", "approval", "approves",
    "etf approved", "adoption", "rate cut", "dovish", "upgrade", "bullish",
)
CRYPTO_TERMS = (
    "crypto", "bitcoin", "btc", "ether", "ethereum", "eth", "stablecoin", "tether", "usdt",
    "binance", "coinbase", "blockchain", "token", "defi", "solana",
)
MACRO_TERMS = ("federal reserve", "fed ", "inflation", "interest rate", "treasury", "ecb", "cpi")


@dataclass(frozen=True)
class Headline:
    title: str
    published: datetime
    source: str


@dataclass(frozen=True)
class NewsAssessment:
    block_entries: bool
    panic: bool
    score: float
    reasons: tuple[str, ...]
    feeds_ok: bool


def _contains(text: str, terms: Iterable[str]) -> list[str]:
    return [t for t in terms if re.search(r"(?<![a-z])" + re.escape(t), text)]


def score_headline(title: str, asset_terms: Iterable[str] = ()) -> tuple[float, bool, bool]:
    """Vrátí (skóre, je_relevantní, je_kritická)."""
    text = title.lower()
    relevant = bool(_contains(text, tuple(CRYPTO_TERMS) + tuple(t.lower() for t in asset_terms)))
    macro = bool(_contains(text, MACRO_TERMS))
    severe = bool(_contains(text, SEVERE_NEGATIVE))
    score = len(_contains(text, POSITIVE)) - len(_contains(text, NEGATIVE)) - 3 * severe
    weight = 1.0 if relevant else (0.5 if macro else 0.0)
    return score * weight, relevant or macro, severe and relevant


def assess(
    headlines: Iterable[Headline],
    now: datetime,
    lookback_hours: float,
    asset_terms: Iterable[str] = (),
    feeds_ok: bool = True,
    fail_safe: str = "block",
) -> NewsAssessment:
    if not feeds_ok and fail_safe == "block":
        return NewsAssessment(True, False, 0.0, ("zprávy nedostupné – fail-safe blokuje nákupy",), False)
    cutoff = now - timedelta(hours=lookback_hours)
    total, panic, reasons = 0.0, False, []
    for h in headlines:
        if h.published < cutoff or h.published > now + timedelta(minutes=5):
            continue
        s, relevant, severe = score_headline(h.title, asset_terms)
        if not relevant:
            continue
        total += s
        if severe:
            panic = True
            reasons.append(f"KRITICKÁ: [{h.source}] {h.title}")
        elif s < 0:
            reasons.append(f"negativní: [{h.source}] {h.title}")
    block = panic or total <= -3
    return NewsAssessment(block, panic, total, tuple(reasons[:10]), feeds_ok)


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc)
    return None


def fetch_headlines(feeds: Iterable[str], parser: Callable | None = None) -> tuple[list[Headline], bool]:
    """Stáhne titulky ze všech feedů. Vrací (titulky, alespoň_jeden_feed_funguje)."""
    if parser is None:
        import feedparser  # lazy import kvůli testům

        parser = feedparser.parse
    out: list[Headline] = []
    any_ok = False
    for url in feeds:
        try:
            parsed = parser(url)
        except Exception as exc:  # síť, DNS, parsování…
            log.warning("Feed %s selhal: %s", url, exc)
            continue
        entries = parsed.get("entries", []) if isinstance(parsed, dict) else getattr(parsed, "entries", [])
        if not entries:
            log.warning("Feed %s nevrátil žádné položky", url)
            continue
        any_ok = True
        for e in entries:
            ts = _entry_time(e)
            title = e.get("title", "").strip()
            if ts and title:
                out.append(Headline(title, ts, url))
    return out, any_ok
