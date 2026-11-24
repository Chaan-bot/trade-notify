"""Send a Telegram message using the Bot API."""

import os

import requests


def chat_ids() -> list[str]:
    """TELEGRAM_CHAT_ID may hold several chat IDs, comma-separated."""
    return [c.strip() for c in os.environ["TELEGRAM_CHAT_ID"].split(",") if c.strip()]


def send(text: str) -> None:
    """Send `text` to every chat. Tries all of them before raising on any failure."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    errors = []
    for chat_id in chat_ids():
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            errors.append(f"chat {chat_id}: {e}")
    if errors:
        raise RuntimeError("Telegram send failed for " + "; ".join(errors))
