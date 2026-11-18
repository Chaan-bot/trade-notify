"""Pure dip-signal maths. No I/O."""

import math
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import config


@dataclass
class Signal:
    price: float
    window_high: float
    ma: float
    dd_high: float          # fraction below window high (0.025 == 2.5% below)
    dd_ma: float            # fraction below moving average (negative == above it)
    level: int              # 0 = no dip, 1 = -2% tier, 2 = -4% tier, ...
    fired: list[str] = field(default_factory=list)

    @property
    def strong(self) -> bool:
        return len(self.fired) == 2


def compute(closes: pd.Series, price: float, start: date) -> Signal:
    """
    closes: daily closes strictly before today, indexed by date.
    price:  today's (live) price.
    start:  first day of the current buy window.
    """
    in_window = closes[[d >= start for d in closes.index]]
    window_high = max([price, *in_window.tolist()])
    ma = float(closes.tail(config.MA_DAYS).mean())

    dd_high = 1 - price / window_high
    dd_ma = 1 - price / ma

    fired = []
    if dd_high + 1e-9 >= config.DIP_STEP:
        fired.append("window high")
    if dd_ma + 1e-9 >= config.DIP_STEP:
        fired.append(f"{config.MA_DAYS}-day avg")

    level = max(0, math.floor(max(dd_high, dd_ma) / config.DIP_STEP + 1e-9))
    return Signal(price, window_high, ma, dd_high, dd_ma, level, fired)
