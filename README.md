# trade-notify

Telegram alerts that help time a monthly ETF purchase within a fixed buy window.

|                |                                                                                  |
| -------------- | -------------------------------------------------------------------------------- |
| **Instrument** | iShares Core MSCI World UCITS ETF (Acc). Ticker **IWDA**, ISIN IE00B4L5Y983      |
| **Exchange**   | Euronext Amsterdam (`IWDA.AS` on Yahoo Finance), priced in EUR                   |
| **Strategy**   | Dollar-cost averaging: one buy per month                                         |
| **Output**     | Telegram messages: window opened, dip alerts, a fallback "buy now", run failures |
| **Runs on**    | GitHub Actions (free), once per trading day at about 15:00 Amsterdam time        |

---

## 1. Goal

I buy the same ETF every month. Each buy window runs from **the 15th to the 15th of the next month**. Within that window I want to buy on a relatively cheap day rather than a fixed date.

Nobody can know the cheapest day in advance. So the project doesn't try to predict. It watches the price each day and nudges me when the price is noticeably below recent levels. If that never happens, it makes sure I still buy before the window closes.

### In scope

- Track one ETF (`IWDA.AS`, configurable).
- Fixed calendar buy windows (15th → 15th).
- Daily dip detection using two simple, explainable signals.
- Escalating alerts when a dip deepens.
- A guaranteed fallback "buy now" reminder before the window closes.
- Euronext trading calendar awareness (weekends and exchange holidays).
- Telegram delivery, plus a ping when a run fails.
- Hands-off hosting on GitHub Actions with state kept in the repo.

### Out of scope (deliberately)

- **Placing trades.** The tool only notifies; I place the order with my broker myself.
- **Backtesting or optimisation.** I chose not to backtest. The thresholds are sensible defaults, not proven optimal values (see [Limitations](#9-limitations--caveats)).
- **Price prediction, ML, technical-analysis indicators** beyond the two signals below.
- **Multiple ETFs or portfolios, position sizing, P&L tracking.**
- **Two-way bot interaction** (e.g. replying "bought"). Alerts are one-way.
- **Intraday monitoring.** One check per day is enough for a monthly buyer.

---

## 2. How it works

### Buy window

- A window opens on the **15th** and closes on the **15th of the next month**. The closing 15th is the first day of the next window.
- If the 15th falls on a weekend or holiday, the window still starts that day. The first check simply runs on the next trading day.

### Signals

Each check computes, from today's live price:

| Signal                      | Definition                                                            | Fires when |
| --------------------------- | --------------------------------------------------------------------- | ---------- |
| **A: below window high**    | `1 − price / highest close since the window opened (including today)` | ≥ 2%       |
| **B: below 20-day average** | `1 − price / mean of the last 20 daily closes (before today)`         | ≥ 2%       |

The signals are combined with **OR**: either one firing triggers an alert. If **both** fire, the alert is marked **"Strong dip"**.

### Escalation

The dip **level** is `floor(max(A, B) / 2%)`, so level 1 means ≥2% down, level 2 means ≥4%, level 3 means ≥6%, and so on.

- The first alert in a window is sent at level ≥ 1.
- Later alerts in the same window are sent **only when the level goes higher** than the last alert. The same dip never triggers a second alert.

### Fallback

If **no** dip alert has been sent by the **3rd-last Euronext trading day before the window closes**, a "No dip this window, buy now" message is sent.

- It is sent once per window.
- If the deadline-day run is missed (e.g. a GitHub outage), it is sent on the next run that happens before the window closes.
- It is skipped if a dip alert already went out in this window, since I've presumably bought.

### Window-opened message

On the first trading day of each window, a short message gives the window dates and the fallback deadline. It also works as a monthly sign that the bot is alive.

### Daily flow

```
cron (weekdays 13:30 UTC)
  └─ Euronext closed today? ─ yes → exit
  └─ load state.json ─ new window? → reset state
  └─ send "window opened" (once per window)
  └─ fetch ~75 days of daily prices (today's row = live price, ~15 min delayed)
  └─ compute signals A, B and level
  └─ level > last alerted level? → dip alert
     else on/after deadline and no alert yet and no fallback yet? → fallback
  └─ save state.json → workflow commits it if changed
  └─ any failure → Telegram "run failed" with link to the Actions run
```

---

## 3. Example messages

```
🗓 New IWDA.AS buy window: 15 Nov → 15 Dec
Fallback 'buy now' deadline: Thu 10 Dec
```

```
💥 Strong dip (both signals): IWDA.AS ≥6% down
Price: €93.52
vs window high €100.84: -7.3%
vs 20-day avg €98.68: -5.2%
Triggered by: window high, 20-day avg
Window closes 15 Apr (deadline Thu 10 Apr)
```

```
⏰ No dip this window. Buy IWDA.AS now.
Price: €128.25
vs window high €129.99: -1.3%
vs 20-day avg €129.89: -1.3%
Window closes 15 Dec
```

```
⚠️ trade-notify run failed: https://github.com/<you>/trade-notify/actions/runs/<id>
```

---

## 4. Design decisions

| Decision    | Choice                                               | Why                                                                                                                                                    |
| ----------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Scope       | Live notifier only                                   | Quick to build and useful immediately; a backtest can come later.                                                                                      |
| Dip signals | Window high **and** 20-day average, combined with OR | The window high catches "cheaper than earlier this month"; the average catches "cheaper than the recent trend", which works even on day 1 of a window. |
| Threshold   | 2%, escalating in 2% steps                           | IWDA moves about 0.8% on a typical day; a 2% dip happens in most months, so the fallback is the exception rather than the norm.                        |
| Escalation  | Alert again only when the dip reaches a deeper tier  | You still hear about a better price, without being spammed.                                                                                            |
| Fallback    | 3 trading days before the 15th                       | Allows for weekends and holidays and leaves time to place the order.                                                                                   |
| Check time  | ~15:00 Amsterdam, once a day                         | Uses the intraday price, so I can still buy the same day; once a day avoids noise.                                                                     |
| Channel     | Telegram bot                                         | Free, instant phone push, one HTTP call.                                                                                                               |
| Hosting     | GitHub Actions                                       | Free and serverless. The monthly state commit counts as activity, so GitHub's 60-day inactivity pause on scheduled workflows never kicks in.           |
| State       | `state.json` committed back to the repo              | No database needed; the history is visible in git.                                                                                                     |
| Language    | Python 3.12 + yfinance, pandas, exchange_calendars   | Best free tooling for EU ETF prices and exchange holidays.                                                                                             |

---

## 5. Project structure

```
trade_notify/
  config.py      # all tunables (ticker, thresholds, MA length, deadline, window day, timezone)
  window.py      # window start/end, fallback deadline, trading-day check (Euronext XAMS calendar)
  prices.py      # yfinance fetch → (previous closes, today's price); errors if today's price is missing
  signals.py     # pure maths: window high, moving average, drawdowns, level, fired signals
  state.py       # load/save state.json
  telegram.py    # send a message using the Bot API
  main.py        # decide() = pure alert logic; main() = CLI and orchestration
tests/
  test_window.py   # boundaries, year rollover, weekend/holiday deadlines (incl. Easter 2020)
  test_signals.py  # signal maths, escalation, fallback timing, catch-up, suppression
.github/workflows/check.yml   # daily cron, state commit, failure ping
state.json       # created by the first real run; one window at a time
requirements.txt # pinned dependencies
```

### State (`state.json`)

```json
{
  "window_start": "2026-11-15",
  "alerted_level": 0,
  "fallback_sent": false,
  "opened_sent": true
}
```

State resets automatically when a new window starts.

---

## 6. Setup

1. **Create the bot**: message [@BotFather](https://t.me/BotFather), run `/newbot`, and copy the token.
2. **Get your chat id**: send your bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `message.chat.id`.
3. **Create the repo**: fork or push this project to your own GitHub repo (public or private), then add the secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (Settings → Secrets and variables → Actions). To notify more than one person, have each of them message the bot, get their chat id the same way, and set `TELEGRAM_CHAT_ID` to a comma-separated list (e.g. `111111111,222222222`). Run-failure pings go only to the first id.
4. **Test it**: Actions → _daily-check_ → _Run workflow_. You should get the "window opened" message, and a `state.json` commit should appear.

After that it runs by itself every weekday.

---

## 7. Local use

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
.venv/bin/python -m trade_notify.main --dry-run                       # today, print only
.venv/bin/python -m trade_notify.main --dry-run --date 2025-04-07     # simulate a past day
.venv/bin/python -m trade_notify.main --dry-run --state /tmp/s.json   # use a scratch state file
```

| Flag                | Effect                                                           |
| ------------------- | ---------------------------------------------------------------- |
| `--dry-run`         | Prints messages; doesn't send them or write state                |
| `--date YYYY-MM-DD` | Runs as if it were that day, using that day's close as the price |
| `--state PATH`      | Uses a different state file                                      |

---

## 8. Configuration

Everything is in [trade_notify/config.py](trade_notify/config.py):

| Setting                 | Default            | Meaning                                                        |
| ----------------------- | ------------------ | -------------------------------------------------------------- |
| `TICKER`                | `IWDA.AS`          | Yahoo Finance ticker                                           |
| `EXCHANGE`              | `XAMS`             | exchange_calendars code used for trading days                  |
| `TZ`                    | `Europe/Amsterdam` | Timezone for "today"                                           |
| `WINDOW_DAY`            | `15`               | Day of the month the window opens and closes                   |
| `DIP_STEP`              | `0.02`             | First alert threshold and escalation step                      |
| `MA_DAYS`               | `20`               | Moving-average length in trading days                          |
| `DEADLINE_TRADING_DAYS` | `3`                | Fallback fires this many trading days before the window closes |

The run time is set by the cron line in [check.yml](.github/workflows/check.yml): `30 13 * * 1-5` UTC, which is 14:30 CET in winter and 15:30 CEST in summer.

---

## 9. Limitations & caveats

- **Not a prediction.** A 2% dip can keep falling. The tool tells you a price is cheaper than recent levels, not that it is the bottom.
- **Not backtested.** The thresholds are reasoned defaults. Review them after a few months.
- **Small expected edge.** For a long-term monthly buyer, timing within the month typically changes the result by a fraction of a percent per buy. The main value is buying with intent, never missing a month.
- **yfinance is unofficial.** It can break, be rate-limited, or have gaps. Any run failure triggers a Telegram ping.
- **Delayed data.** The live price is about 15 minutes behind the market.
- **GitHub cron timing** can drift by tens of minutes under load. That doesn't matter at this frequency.
- **Daily closes only.** The window high uses closing prices, not intraday highs or lows.

---

## 10. Possible future work

- A backtest to compare "dip rule + fallback" against "always buy on the 15th" on IWDA history and tune the thresholds.
- Telegram commands (`/status`, `/bought`) to see the current dip level or stop alerts for the window.
- Support for more than one ETF.
- A monthly recap: alert price vs. the window's actual low.
