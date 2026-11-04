import json

from agent.backtest import run_backtest
from agent.review import TradeRecord
from agent.risk import RiskLimits
from agent.selflearn import ADAPTATIONS_FILE, save_review, self_review
from agent.strategy import StrategyParams, blocked_mask, context_buckets, generate_signals
from conftest import make_ohlcv

LIMITS = RiskLimits(0.01, 0.5, 10_000, 0.03, 10)


def test_backtest_trades_carry_context_and_r():
    res = run_backtest(make_ohlcv(1500, seed=1, drift=0.001), StrategyParams(), LIMITS)
    assert res.trades
    for t in res.trades:
        assert set(t.context) >= {"rsi", "stretch", "volatility", "session", "volume"}
        assert t.mfe_r >= t.r_multiple - 0.05 and t.mae_r <= 0.01
        if t.reason == "take_profit":
            assert t.r_multiple > 1


def test_blocked_context_removes_entries():
    df = make_ohlcv(1500, seed=1, drift=0.001)
    sig = generate_signals(df, StrategyParams())
    blocked = generate_signals(df, StrategyParams(blocked_contexts=("session=europe",)))
    assert blocked["entry"].sum() < sig["entry"].sum()
    assert not blocked.loc[blocked["ctx_session"] == "europe", "entry"].any()


def test_blocked_mask_ignores_unknown_feature():
    sig = generate_signals(make_ohlcv(400), StrategyParams())
    assert not blocked_mask(sig, ("nonsense=x",)).any()


def test_context_buckets_cover_all_rows():
    sig = generate_signals(make_ohlcv(400), StrategyParams())
    assert set(sig["ctx_session"].unique()) <= {"asia", "europe", "us"}


def test_breakeven_reduces_losses_after_profit():
    df = make_ohlcv(3000, seed=7, drift=0.0005)
    res = run_backtest(df, StrategyParams(breakeven_at_r=1.0), LIMITS, fee_rate=0.0)
    assert all(t.r_multiple >= -0.01 for t in res.trades if t.reason == "breakeven")


def test_self_review_end_to_end(tmp_path):
    df = make_ohlcv(4000, seed=11, drift=0.0006)
    live = [TradeRecord("2025-01-01", "2025-01-01", 100, 95, 95, 1, -5, -1, 0.1, -1, 2, "stop", "hammer",
                        {"session": "asia"}, "live")]
    r = self_review(df, StrategyParams(), LIMITS, live, min_trades=10)
    assert r.report["overall"]["n"] >= 2 and r.live_report["overall"]["n"] == 1
    assert "Jen skutečné obchody" in r.markdown
    path = save_review(r, tmp_path)
    assert path.exists()
    written = (tmp_path / ADAPTATIONS_FILE).exists()
    assert written == r.validation["accepted"]
    if written:
        assert "validation" in json.loads((tmp_path / ADAPTATIONS_FILE).read_text())


def test_validation_rejects_when_candidate_has_too_few_trades():
    from agent.selflearn import _validate
    df = make_ohlcv(3000, seed=1, drift=0.001)
    base = StrategyParams()
    starved = StrategyParams(bullish_patterns=())  # žádné obchody
    v = _validate(df, base, starved, LIMITS, 1000, 0.001, {"disabled_patterns": ["x"]})
    assert not v["accepted"] and "málo obchodů" in v["why"]
