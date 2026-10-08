"""Generate the profile's weekly contribution graph.

Run in GitHub Actions with GITHUB_TOKEN and GITHUB_USER. The checked-in SVGs
also make the README work before the workflow has ever run.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""
YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
Day = tuple[date, int, int]


def fetch_days(login: str, token: str, year: int | None = None) -> list[Day]:
    if year is None:
        query = QUERY
        variables = {"login": login}
    else:
        query = YEAR_QUERY
        variables = {
            "login": login,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        }
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-visuals",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {login!r} was not found")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
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


def render_graph(days: list[Day]) -> str:
    weekly = defaultdict(int)
    for day, count, _ in days:
        sunday = day - timedelta(days=(day.weekday() + 1) % 7)
        weekly[sunday] += count
    weeks = sorted(weekly.items())
    values = [count for _, count in weeks]
    left, right, top, bottom = 70, 1130, 62, 228
    ceiling = max(4, max(values))
    points = [
        (
            left + (right - left) * i / max(1, len(weeks) - 1),
            bottom - (bottom - top) * count / ceiling,
        )
        for i, count in enumerate(values)
    ]
    line = " ".join(
        f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}"
        for i, (x, y) in enumerate(points)
    )
    area = f"{line} L{points[-1][0]:.1f} {bottom} L{left} {bottom} Z"
    grid = []
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        y = bottom - (bottom - top) * fraction
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            'stroke="#56436f" stroke-opacity=".4"/>'
        )
        grid.append(
            f'<text x="{left - 14}" y="{y + 5:.1f}" text-anchor="end" '
            f'class="axis">{round(ceiling * fraction)}</text>'
        )
    ticks = []
    previous = None
    for i, (day, _) in enumerate(weeks):
        month = (day.year, day.month)
        if month != previous:
            ticks.append(
                f'<text x="{points[i][0]:.1f}" y="263" class="axis">'
                f"{MONTHS[day.month - 1]}</text>"
            )
            previous = month
    total = sum(values)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="292" viewBox="0 0 1200 292" role="img" aria-labelledby="title desc">
<title id="title">Marc's contribution graph</title>
<desc id="desc">Public contributions per week over the past year: {total} total.</desc>
<defs>
  <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#a855f7" stop-opacity=".42"/><stop offset="1" stop-color="#a855f7" stop-opacity=".02"/></linearGradient>
  <style>.axis{{font:14px Arial,Helvetica,sans-serif;fill:#a6b3ca}}</style>
</defs>
<rect width="1200" height="292" rx="18" fill="#0d1117"/>
<text x="70" y="36" fill="#e9d5ff" font-family="Arial,Helvetica,sans-serif" font-size="20" font-weight="700">Weekly contributions</text>
{''.join(grid)}
<path d="{area}" fill="url(#fill)"/>
<path d="{line}" fill="none" stroke="#c084fc" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
{''.join(ticks)}
</svg>
'''


def write_graph(days: list[Day]) -> None:
    folder = Path("assets")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "activity-graph.svg").write_text(render_graph(days), encoding="utf-8")
    print("Updated assets/activity-graph.svg")


def main() -> None:
    days = fetch_days(os.environ["GITHUB_USER"], os.environ["GITHUB_TOKEN"])
    write_graph(days)


if __name__ == "__main__":
    main()
