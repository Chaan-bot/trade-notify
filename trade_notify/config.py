"""All tunables in one place."""

TICKER = "IWDA.AS"          # iShares Core MSCI World, Euronext Amsterdam (IE00B4L5Y983)
CURRENCY = "€"
EXCHANGE = "XAMS"           # exchange_calendars code for Euronext Amsterdam
TZ = "Europe/Amsterdam"

WINDOW_DAY = 15             # buy window runs from the 15th to the 15th of next month
DIP_STEP = 0.02             # alert at -2%, then escalate at -4%, -6%, ...
MA_DAYS = 20                # moving-average length (trading days)
DEADLINE_TRADING_DAYS = 3   # fallback "buy now" N trading days before the window closes
