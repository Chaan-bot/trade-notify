"""Daily check: run once per trading day around 15:00 Amsterdam time."""

import argparse
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, prices, state as state_mod, telegram, window
from .signals import Signal, compute
from .state import State


def _pct(x: float) -> str:
    return f"{-x * 100:+.1f}%"


def _eur(x: float) -> str:
    return f"{config.CURRENCY}{x:,.2f}"


def _day(d: date) -> str:
    return d.strftime("%a %d %b")


def decide(today: date, st: State, sig: Signal | None) -> tuple[list[str], State]:
    """Pure decision logic: given today's state and signal, return messages and the new state."""
    start = window.window_start(today)
    end = window.window_end(today)
    dl = window.deadline(today)
    msgs: list[str] = []

    if st.window_start != start.isoformat():
        st = State(window_start=start.isoformat())

    if not st.opened_sent:
        msgs.append(
            f"🗓 New {config.TICKER} buy window: {start:%d %b} → {end:%d %b}\n"
            f"Fallback 'buy now' deadline: {_day(dl)}"
        )
        st = replace(st, opened_sent=True)

    if sig is None:
        return msgs, st

    detail = (
        f"Price: {_eur(sig.price)}\n"
        f"vs window high {_eur(sig.window_high)}: {_pct(sig.dd_high)}\n"
        f"vs {config.MA_DAYS}-day avg {_eur(sig.ma)}: {_pct(sig.dd_ma)}"
    )

    if sig.level >= 1 and sig.level > st.alerted_level:
        tier = sig.level * config.DIP_STEP * 100
        head = "💥 Strong dip (both signals)" if sig.strong else "📉 Dip"
        again = " (deeper than last alert)" if st.alerted_level else ""
        msgs.append(
            f"{head}: {config.TICKER} ≥{tier:.0f}% down{again}\n"
            f"{detail}\n"
            f"Triggered by: {', '.join(sig.fired)}\n"
            f"Window closes {end:%d %b} (deadline {_day(dl)})"
        )
        st = replace(st, alerted_level=sig.level)
    elif today >= dl and st.alerted_level == 0 and not st.fallback_sent:
        msgs.append(
            f"⏰ No dip this window. Buy {config.TICKER} now.\n{detail}\n"
            f"Window closes {end:%d %b}"
        )
        st = replace(st, fallback_sent=True)

    return msgs, st


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print messages, don't send or save state")
    ap.add_argument("--date", type=date.fromisoformat, help="simulate a day (YYYY-MM-DD)")
    ap.add_argument("--state", type=Path, default=state_mod.DEFAULT_PATH)
    args = ap.parse_args()

    today = args.date or datetime.now(ZoneInfo(config.TZ)).date()
    if not window.is_trading_day(today):
        print(f"{today}: Euronext closed, nothing to do.")
        return

    st = state_mod.load(args.state)
    try:
        closes, price = prices.fetch(today)
    except prices.PriceUnavailable as e:
        # Usually a delayed cron run that slipped past midnight, before Euronext opens.
        # Skip without touching state; the next run catches up (fallback included).
        print(f"{today}: skipping, {e}")
        return
    sig = compute(closes, price, window.window_start(today))
    print(
        f"{today}: price {price:.2f} high {sig.window_high:.2f} ({_pct(sig.dd_high)}) "
        f"ma {sig.ma:.2f} ({_pct(sig.dd_ma)}) level {sig.level} (last alerted {st.alerted_level})"
    )

    msgs, new_st = decide(today, st, sig)
    for m in msgs:
        print("---\n" + m)
        if not args.dry_run:
            telegram.send(m)

    if not args.dry_run:
        state_mod.save(new_st, args.state)


if __name__ == "__main__":
    main()
