import time
from datetime import datetime, timedelta, timezone

from agent.news import Headline, assess, fetch_headlines, score_headline

NOW = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)


def h(title, hours_ago=1):
    return Headline(title, NOW - timedelta(hours=hours_ago), "test")


def test_severe_crypto_news_triggers_panic():
    a = assess([h("Major crypto exchange hacked, $400m drained")], NOW, 6)
    assert a.panic and a.block_entries


def test_irrelevant_news_is_ignored():
    a = assess([h("Football club hacked by fans' enthusiasm")], NOW, 6)
    assert not a.panic and a.score == 0


def test_old_news_is_ignored():
    a = assess([h("Bitcoin exchange hacked", hours_ago=48)], NOW, 6)
    assert not a.block_entries


def test_positive_news_does_not_block():
    a = assess([h("Bitcoin rally hits record high on ETF inflows")], NOW, 6)
    assert a.score > 0 and not a.block_entries


def test_accumulated_negative_news_blocks():
    a = assess([h("Bitcoin plunge deepens"), h("Crypto selloff as fears grow"), h("Ether slump")], NOW, 6)
    assert a.block_entries and not a.panic


def test_fail_safe_blocks_when_feeds_down():
    assert assess([], NOW, 6, feeds_ok=False, fail_safe="block").block_entries
    assert not assess([], NOW, 6, feeds_ok=False, fail_safe="ignore").block_entries


def test_word_boundary_avoids_false_positive():
    _, relevant, _ = score_headline("Method acting tips")  # 'eth' uvnitř slova
    assert not relevant


def test_fetch_headlines_survives_broken_feed():
    st = time.gmtime(NOW.timestamp())

    def parser(url):
        if url == "bad":
            raise OSError("network down")
        return {"entries": [{"title": "Bitcoin up", "published_parsed": st}]}

    items, ok = fetch_headlines(["bad", "good"], parser=parser)
    assert ok and len(items) == 1 and items[0].published == NOW


def test_fetch_headlines_reports_all_down():
    items, ok = fetch_headlines(["a"], parser=lambda u: {"entries": []})
    assert not ok and items == []
