from agent.backtest import run_backtest
from agent.learn import select_patterns
from agent.risk import RiskLimits
from agent.strategy import WARMUP_BARS, StrategyParams, generate_signals
from conftest import make_ohlcv

LIMITS = RiskLimits(0.01, 0.5, 10_000, 0.03, 10)


def test_no_entries_during_warmup():
    sig = generate_signals(make_ohlcv(400), StrategyParams())
    assert not sig["entry"].iloc[:WARMUP_BARS].any()


def test_signals_have_no_lookahead():
    df = make_ohlcv(500, seed=3)
    full = generate_signals(df, StrategyParams())
    part = generate_signals(df.iloc[:450], StrategyParams())
    assert full["entry"].iloc[:450].equals(part["entry"])


def test_uptrend_produces_entries_and_stops_below_price():
    sig = generate_signals(make_ohlcv(1500, seed=1, drift=0.001), StrategyParams())
    entries = sig[sig["entry"]]
    assert len(entries) > 0
    assert (entries["stop"] < entries["close"]).all()
    assert (entries["take_profit"] > entries["close"]).all()


def test_backtest_runs_and_is_consistent():
    df = make_ohlcv(1500, seed=1, drift=0.001)
    res = run_backtest(df, StrategyParams(), LIMITS, 1000, 0.001)
    s = res.summary()
    assert s["trades"] == len(res.trades) > 0
    assert (res.equity_curve > 0).all()
    assert abs(res.final_equity - (1000 + sum(t.pnl for t in res.trades))) < 1e-6


def test_backtest_per_trade_loss_is_bounded_by_risk():
    df = make_ohlcv(1500, seed=2, drift=0.0)
    res = run_backtest(df, StrategyParams(), LIMITS, 1000, 0.0)
    for t in res.trades:
        if t.reason == "stop":  # gap přes stop může ztrátu zvětšit; tady data gapy nemají
            assert t.pnl >= -1000 * 0.012


def test_downtrend_without_signals_keeps_equity():
    df = make_ohlcv(800, seed=5, drift=-0.003)
    res = run_backtest(df, StrategyParams(), LIMITS, 1000)
    assert res.summary()["trades"] == 0 and res.final_equity == 1000


def test_learn_report_structure():
    rep = select_patterns(make_ohlcv(3000, seed=4), horizon=12)
    assert set(rep) >= {"selected_bullish", "selected_bearish", "train", "test"}
    assert all(n in {s["name"] for s in rep["train"]} for n in rep["selected_bullish"])


def test_with_learned_uses_file(tmp_path):
    p = tmp_path / "l.json"
    p.write_text('{"selected_bullish": ["hammer"], "selected_bearish": []}')
    params = StrategyParams().with_learned(p)
    assert params.bullish_patterns == ("hammer",)
    assert len(params.bearish_patterns) > 1  # prázdný výběr → ponechá výchozí


def test_learned_with_no_bullish_patterns_disables_entries(tmp_path):
    p = tmp_path / "l.json"
    p.write_text('{"selected_bullish": [], "selected_bearish": []}')
    params = StrategyParams().with_learned(p)
    assert params.bullish_patterns == ()
    assert not generate_signals(make_ohlcv(1500, seed=1, drift=0.001), params)["entry"].any()
