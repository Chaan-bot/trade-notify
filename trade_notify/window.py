"""Buy-window date logic: windows run from the 15th to the 15th of the next month."""

from datetime import date, timedelta
from functools import lru_cache

import exchange_calendars as xc

from . import config


@lru_cache(maxsize=1)
def _calendar():
    return xc.get_calendar(config.EXCHANGE)


def window_start(d: date) -> date:
    """First day of the window containing d."""
    if d.day >= config.WINDOW_DAY:
        return date(d.year, d.month, config.WINDOW_DAY)
    if d.month == 1:
        return date(d.year - 1, 12, config.WINDOW_DAY)
    return date(d.year, d.month - 1, config.WINDOW_DAY)


def window_end(d: date) -> date:
    """The 15th that closes the window containing d (exclusive: it opens the next window)."""
    start = window_start(d)
    if start.month == 12:
        return date(start.year + 1, 1, config.WINDOW_DAY)
    return date(start.year, start.month + 1, config.WINDOW_DAY)


def is_trading_day(d: date) -> bool:
    return bool(_calendar().is_session(d.isoformat()))


def deadline(d: date) -> date:
    """The Nth-last Euronext trading day before the window containing d closes."""
    end = window_end(d)
    sessions = _calendar().sessions_in_range(
        (end - timedelta(days=21)).isoformat(), (end - timedelta(days=1)).isoformat()
    )
    return sessions[-config.DEADLINE_TRADING_DAYS].date()
