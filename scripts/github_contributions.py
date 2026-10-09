"""Read GitHub's contribution calendar for the current or a past year."""

from __future__ import annotations

import json
from datetime import date
from urllib.request import Request, urlopen

Day = tuple[date, int, int]
LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def fetch_days(login: str, token: str, year: int | None = None) -> list[Day]:
    period = "" if year is None else "(from: $from, to: $to)"
    declarations = "" if year is None else ", $from: DateTime!, $to: DateTime!"
    query = f"""
    query($login: String!{declarations}) {{
      user(login: $login) {{
        contributionsCollection{period} {{
          contributionCalendar {{
            weeks {{ contributionDays {{ date contributionCount contributionLevel }} }}
          }}
        }}
      }}
    }}
    """
    variables = {"login": login}
    if year is not None:
        variables.update({
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        })
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "machisi-profile-visuals",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {login!r} was not found")
    days = [
        (date.fromisoformat(item["date"]), int(item["contributionCount"]), LEVELS[item["contributionLevel"]])
        for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]
        for item in week["contributionDays"]
    ]
    if not days:
        raise RuntimeError("GitHub returned no contribution days")
    return sorted(days)
