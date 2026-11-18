"""Tiny JSON state, committed back to the repo by the workflow."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "state.json"


@dataclass
class State:
    window_start: str | None = None
    alerted_level: int = 0
    fallback_sent: bool = False
    opened_sent: bool = False


def load(path: Path = DEFAULT_PATH) -> State:
    if not path.exists():
        return State()
    return State(**json.loads(path.read_text()))


def save(state: State, path: Path = DEFAULT_PATH) -> None:
    path.write_text(json.dumps(asdict(state), indent=2) + "\n")
