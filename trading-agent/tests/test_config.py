import pytest

from agent.config import ConfigError, config_from_env

BASE = {"MODE": "paper"}


def test_defaults_are_valid():
    cfg = config_from_env(BASE)
    assert cfg.mode == "paper" and cfg.symbol == "BTC/USDT"


def test_live_requires_explicit_confirmation():
    env = {"MODE": "live", "API_KEY": "k", "API_SECRET": "s"}
    with pytest.raises(ConfigError):
        config_from_env(env)
    assert config_from_env({**env, "LIVE_CONFIRM": "I_UNDERSTAND_THE_RISK"}).mode == "live"


def test_exchange_modes_need_keys():
    with pytest.raises(ConfigError):
        config_from_env({"MODE": "testnet"})


def test_excessive_risk_is_rejected():
    with pytest.raises(ConfigError):
        config_from_env({**BASE, "RISK_PER_TRADE": "0.2"})


def test_secret_not_in_repr():
    cfg = config_from_env({"MODE": "testnet", "API_KEY": "kkk", "API_SECRET": "sss"})
    assert "sss" not in repr(cfg) and "kkk" not in repr(cfg)


def test_feeds_parsed():
    cfg = config_from_env({**BASE, "NEWS_FEEDS": "a, b ,"})
    assert cfg.news_feeds == ("a", "b")


def test_load_dotenv_does_not_override(tmp_path, monkeypatch):
    from agent.config import load_dotenv
    f = tmp_path / ".env"
    f.write_text("SYMBOL=ETH/USDT  # komentář\nFOO_TEST_X=1\n")
    monkeypatch.setenv("SYMBOL", "BTC/USDT")
    monkeypatch.delenv("FOO_TEST_X", raising=False)
    load_dotenv(f)
    import os
    assert os.environ["SYMBOL"] == "BTC/USDT" and os.environ["FOO_TEST_X"] == "1"


@pytest.mark.parametrize("env", [{"MODE": "x"}, {"RISK_PER_TRADE": "abc"}, {"MAX_TRADES_PER_DAY": "1.5"},
                                 {"NEWS_FAIL_SAFE": "maybe"}, {"MAX_ORDER_QUOTE": "0"}])
def test_invalid_values_rejected(env):
    with pytest.raises(ConfigError):
        config_from_env(env)


def test_only_btc_by_default():
    with pytest.raises(ConfigError):
        config_from_env({**BASE, "SYMBOL": "ETH/USDT"})
    assert config_from_env({**BASE, "SYMBOL": "ETH/USDT", "ALLOW_ALTCOINS": "true"}).symbol == "ETH/USDT"
