from datetime import date

from trade_notify.window import deadline, is_trading_day, window_end, window_start


def test_window_boundaries():
    assert window_start(date(2026, 11, 15)) == date(2026, 11, 15)
    assert window_start(date(2026, 11, 14)) == date(2026, 10, 15)
    assert window_end(date(2026, 11, 14)) == date(2026, 11, 15)
    assert window_end(date(2026, 11, 15)) == date(2026, 12, 15)


def test_year_rollover():
    assert window_start(date(2027, 1, 3)) == date(2026, 12, 15)
    assert window_end(date(2026, 12, 20)) == date(2027, 1, 15)


def test_deadline_plain():
    # window closes Tue 15 Dec 2026 -> sessions 14, 11, 10 -> deadline Thu 10 Dec
    assert deadline(date(2026, 11, 18)) == date(2026, 12, 10)


def test_deadline_weekend_close():
    # window closes Sun 15 Nov 2026 -> sessions Fri 13, Thu 12, Wed 11
    assert deadline(date(2026, 11, 1)) == date(2026, 11, 11)


def test_deadline_skips_easter_holidays():
    # window closes Wed 15 Apr 2020; Good Friday 10 Apr and Easter Monday 13 Apr are closed
    # sessions before: 14, 9, 8 -> deadline Wed 8 Apr
    assert deadline(date(2020, 4, 1)) == date(2020, 4, 8)


def test_trading_days():
    assert is_trading_day(date(2026, 11, 18))
    assert not is_trading_day(date(2026, 11, 21))  # Saturday
    assert not is_trading_day(date(2026, 12, 25))  # Christmas
