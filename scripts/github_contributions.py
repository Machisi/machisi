"""Read the GitHub calendar response captured while generating the snake."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

Day = tuple[date, int, int]
LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def read_days(path: str = ".contribution-calendar.json") -> list[Day]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [
        (
            date.fromisoformat(item["date"]),
            int(item["contributionCount"]),
            LEVELS[item["contributionLevel"]],
        )
        for week in weeks
        for item in week["contributionDays"]
    ]
    if not days:
        raise RuntimeError("GitHub returned no contribution days")
    return sorted(days)
