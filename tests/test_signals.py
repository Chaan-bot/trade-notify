from datetime import date, timedelta

import pandas as pd

from trade_notify.main import decide
from trade_notify.signals import compute
from trade_notify.state import State

START = date(2026, 11, 16)  # Monday, first trading day of the 15 Nov window


def closes(values, last_day):
    days = [last_day - timedelta(days=len(values) - 1 - i) for i in range(len(values))]
    return pd.Series(values, index=days)


def flat_then(window_values, today):
    """30 days at 100 before the window, then window_values up to yesterday."""
    pre = [100.0] * 30
    return closes(pre + window_values, today - timedelta(days=1))


def test_no_dip():
    today = date(2026, 11, 20)
    sig = compute(flat_then([100, 101, 100.5], today), 100.0, START)
    assert sig.level == 0 and sig.fired == []


def test_window_high_dip_level_1():
    today = date(2026, 11, 20)
    # high 105 in window, price 102.9 -> 2.0% below high; MA ~100.x so not below MA
    sig = compute(flat_then([105, 104, 103], today), 102.9, START)
    assert sig.level == 1
    assert sig.fired == ["window high"]
    assert not sig.strong


def test_ma_dip_only():
    today = date(2026, 11, 16)  # first day of window: window high == price
    sig = compute(closes([100.0] * 30, today - timedelta(days=3)), 97.5, START)
    assert sig.dd_high == 0
    assert sig.level == 1
    assert sig.fired == ["20-day avg"]


def test_strong_and_level_2():
    today = date(2026, 11, 20)
    sig = compute(flat_then([100, 100, 100], today), 95.9, START)
    assert sig.level == 2  # 4.1% down on both
    assert sig.strong


def _sig(level, fired=("window high",)):
    s = compute(flat_then([100], date(2026, 11, 20)), 100.0, START)
    s.level, s.fired = level, list(fired)
    return s


def test_opened_message_once_and_state_reset():
    today = date(2026, 11, 16)
    old = State(window_start="2026-10-15", alerted_level=2, fallback_sent=True, opened_sent=True)
    msgs, st = decide(today, old, _sig(0))
    assert len(msgs) == 1 and "New IWDA.AS buy window" in msgs[0]
    assert st == State(window_start="2026-11-15", opened_sent=True)
    msgs, st = decide(today, st, _sig(0))
    assert msgs == []


def test_escalation_fires_only_on_deeper_level():
    today = date(2026, 11, 20)
    st = State(window_start="2026-11-15", opened_sent=True)
    msgs, st = decide(today, st, _sig(1))
    assert len(msgs) == 1 and "≥2% down" in msgs[0]
    msgs, st = decide(today, st, _sig(1))
    assert msgs == []
    msgs, st = decide(today, st, _sig(2))
    assert len(msgs) == 1 and "≥4% down (deeper than last alert)" in msgs[0]
    assert st.alerted_level == 2


def test_fallback_on_deadline():
    st = State(window_start="2026-11-15", opened_sent=True)
    msgs, st = decide(date(2026, 12, 9), st, _sig(0))
    assert msgs == []
    msgs, st = decide(date(2026, 12, 10), st, _sig(0))
    assert len(msgs) == 1 and "No dip this window" in msgs[0]
    msgs, st = decide(date(2026, 12, 11), st, _sig(0))
    assert msgs == []  # only once


def test_fallback_catches_up_after_missed_deadline_run():
    st = State(window_start="2026-11-15", opened_sent=True)
    msgs, _ = decide(date(2026, 12, 11), st, _sig(0))
    assert "No dip this window" in msgs[0]


def test_fallback_suppressed_after_dip_alert():
    st = State(window_start="2026-11-15", opened_sent=True, alerted_level=1)
    msgs, _ = decide(date(2026, 12, 10), st, _sig(0))
    assert msgs == []
