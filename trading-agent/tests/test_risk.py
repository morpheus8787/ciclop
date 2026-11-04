from datetime import datetime, timezone

from agent.risk import DayState, RiskLimits, can_open, check_daily_loss, position_size, record_trade, roll_day

LIMITS = RiskLimits(risk_per_trade=0.01, max_position_pct=0.5, max_order_quote=10_000,
                    max_daily_loss_pct=0.03, max_trades_per_day=2)


def test_position_size_risks_exact_fraction():
    qty = position_size(1000, entry=100, stop=95, limits=LIMITS)
    assert abs(qty * 5 - 10) < 1e-9  # ztráta při stopu = 1 % z 1000


def test_position_size_capped_by_percent_of_equity():
    qty = position_size(1000, entry=100, stop=99.9, limits=LIMITS)
    assert qty * 100 <= 500 + 1e-9


def test_position_size_capped_by_absolute_quote_limit():
    limits = RiskLimits(0.01, 1.0, 50, 0.03, 2)
    assert position_size(100_000, 100, 90, limits) * 100 <= 50 + 1e-9


def test_invalid_stop_returns_zero():
    assert position_size(1000, 100, 100, LIMITS) == 0
    assert position_size(1000, 100, 105, LIMITS) == 0


def test_daily_loss_halts_trading():
    state = DayState("2025-01-01", 1000)
    halted = check_daily_loss(state, 969, LIMITS)
    assert halted.halted
    assert not state.halted  # immutabilita
    assert can_open(halted, LIMITS)[0] is False


def test_max_trades_per_day():
    s = record_trade(record_trade(DayState("2025-01-01", 1000)))
    assert can_open(s, LIMITS)[0] is False


def test_new_day_resets_state():
    s = DayState("2025-01-01", 1000, trades=5, halted=True)
    new = roll_day(s, datetime(2025, 1, 2, tzinfo=timezone.utc), 900)
    assert new == DayState("2025-01-02", 900)


def test_kill_switch(tmp_path):
    (tmp_path / "STOP").touch()
    ok, why = can_open(DayState("2025-01-01", 1000), LIMITS, tmp_path)
    assert not ok and "kill-switch" in why
