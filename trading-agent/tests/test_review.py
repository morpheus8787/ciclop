import json

from agent.review import (TradeRecord, analyze, append_record, classify, derive_adaptations, is_noop,
                          load_records, render_markdown)
from agent.strategy import StrategyParams, breakeven_stop


def rec(r, mfe=0.5, mae=-0.5, bars=10, reason="stop", patterns="hammer", **ctx):
    context = {"rsi": "50-60", "stretch": "<1ATR", "volatility": "mid", "session": "europe", "volume": "high"}
    context.update(ctx)
    return TradeRecord("2025-01-01", "2025-01-02", 100, 100 + r * 5, 95, 1, r * 5, r, mfe, mae, bars,
                       reason, patterns, context)


def test_classify_quick_stop_and_never_worked():
    mistakes, good = classify(rec(-1, mfe=0.1, bars=2))
    assert {"quick_stop", "never_worked"} <= set(mistakes) and good == []


def test_classify_gave_back_profit():
    assert "gave_back" in classify(rec(-1, mfe=1.4, bars=20))[0]


def test_classify_chasing():
    assert "chased" in classify(rec(-1, stretch=">2ATR"))[0]


def test_classify_good_trade():
    mistakes, good = classify(rec(2, mfe=2, mae=-0.2, reason="take_profit"))
    assert mistakes == [] and set(good) == {"take_profit", "clean_win"}


def test_analyze_groups_by_pattern_and_context():
    rs = [rec(2, patterns="hammer,doji", reason="take_profit"), rec(-1, patterns="hammer", session="asia")]
    rep = analyze(rs)
    assert rep["overall"]["n"] == 2 and rep["overall"]["avg_r"] == 0.5
    assert rep["by_pattern"]["hammer"]["n"] == 2 and rep["by_pattern"]["doji"]["n"] == 1
    assert rep["by_context"]["session"]["asia"]["avg_r"] == -1
    assert rep["worst"][0]["r"] == -1 and rep["best"][0]["r"] == 2


def test_losing_pattern_gets_disabled():
    rs = [rec(-1, patterns="bad")] * 20 + [rec(1.5, patterns="good", reason="take_profit")] * 20
    adapt = derive_adaptations(analyze(rs), min_trades=15)
    assert adapt["disabled_patterns"] == ["bad"]


def test_small_sample_changes_nothing():
    adapt = derive_adaptations(analyze([rec(-1, patterns="bad")] * 5), min_trades=15)
    assert is_noop(adapt)


def test_bad_context_blocked_but_never_all_buckets():
    rs = [rec(-1, session="asia")] * 20 + [rec(1, session="us", reason="take_profit")] * 20
    adapt = derive_adaptations(analyze(rs), min_trades=15)
    assert "session=asia" in adapt["blocked_contexts"]
    everything_bad = [rec(-1, session="asia")] * 20 + [rec(-1, session="us")] * 20
    blocked = derive_adaptations(analyze(everything_bad), min_trades=15)["blocked_contexts"]
    assert not [b for b in blocked if b.startswith("session=")]


def test_gave_back_enables_breakeven():
    rs = [rec(-1, mfe=1.5, bars=20)] * 10 + [rec(2, reason="take_profit")] * 10
    assert derive_adaptations(analyze(rs), min_trades=15)["breakeven_at_r"] == 1.0


def test_records_roundtrip(tmp_path):
    p = tmp_path / "t.jsonl"
    append_record(p, rec(1))
    append_record(p, rec(-1))
    assert [r.r_multiple for r in load_records(p)] == [1, -1]
    assert load_records(tmp_path / "missing.jsonl") == []


def test_markdown_report_in_czech():
    rs = [rec(-1, mfe=1.5, bars=2)] * 10 + [rec(2, reason="take_profit")] * 10
    rep = analyze(rs)
    md = render_markdown(rep, derive_adaptations(rep, 15), {"accepted": True, "why": "ok", "baseline": {},
                                                             "candidate": {}})
    assert "Opakované chyby" in md and "Vrácený zisk" in md and "PŘIJATO" in md


def test_adaptations_only_tighten(tmp_path):
    base = StrategyParams(bullish_patterns=("hammer", "doji"))
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"disabled_patterns": ["doji"], "blocked_contexts": ["session=asia"],
                             "breakeven_at_r": 1.0}))
    new = base.with_adaptations(p)
    assert new.bullish_patterns == ("hammer",) and new.blocked_contexts == ("session=asia",)
    assert new.breakeven_at_r == 1.0 and new.stop_atr_mult == base.stop_atr_mult
    assert base.with_adaptations(tmp_path / "missing.json") == base


def test_breakeven_stop_moves_only_after_target():
    assert breakeven_stop(95, 100, 95, 104, 1.0, 0.0) == 95
    assert breakeven_stop(95, 100, 95, 105, 1.0, 0.001) == 100 * 1.002
    assert breakeven_stop(95, 100, 95, 200, None, 0.0) == 95
