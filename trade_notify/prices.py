"""Price fetching via yfinance."""

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from . import config


class PriceUnavailable(RuntimeError):
    """No price for the requested day (market not open yet, or Yahoo has no data)."""


def _last_per_day(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    s = pd.Series(df["Close"].to_numpy(), index=[ts.date() for ts in df.index]).dropna()
    return s.groupby(level=0).last()


def fetch(today: date) -> tuple[pd.Series, float]:
    """
    Returns (closes strictly before `today`, price on `today`).

    For the live run, today's row is the intraday (~15 min delayed) price.
    For a simulated past date, it is that day's close.

    Yahoo's daily bars for IWDA.AS sometimes skip a day or lag behind intraday data,
    so missing days are filled from hourly bars (last bar of each day).
    """
    ticker = yf.Ticker(config.TICKER)
    kw = dict(
        start=(today - timedelta(days=75)).isoformat(),
        end=(today + timedelta(days=1)).isoformat(),
        auto_adjust=False,
    )
    daily = _last_per_day(ticker.history(interval="1d", **kw))
    hourly = _last_per_day(ticker.history(interval="1h", **kw))

    closes = daily.combine_first(hourly).sort_index()
    closes = closes[[d <= today for d in closes.index]]
    if closes.empty:
        raise PriceUnavailable(f"No price data returned for {config.TICKER}")
    if closes.index[-1] != today:
        raise PriceUnavailable(
            f"No {config.TICKER} price for {today} yet (latest is {closes.index[-1]})"
        )
    return closes.iloc[:-1], float(closes.iloc[-1])
