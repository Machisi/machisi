"""Generate the profile's weekly graph and purple contribution snake.

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

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
COLORS = ("#231c33", "#4c1d95", "#6d28d9", "#a855f7", "#ddd6fe")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
Day = tuple[date, int, int]


def fetch_days(login: str, token: str) -> list[Day]:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
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


def render_snake(days: list[Day]) -> str:
    by_date = {day: (count, level) for day, count, level in days}
    first = min(by_date)
    last = max(by_date)
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    columns = (last - sunday).days // 7 + 1
    left, top, step = 68, 86, 20
    cells = []
    labels = []
    previous_month = None
    for column in range(columns):
        week_start = sunday + timedelta(days=column * 7)
        month = (week_start.year, week_start.month)
        if month != previous_month:
            labels.append(
                f'<text x="{left + column * step}" y="68" class="axis">'
                f"{MONTHS[week_start.month - 1]}</text>"
            )
            previous_month = month
        for row in range(7):
            current = week_start + timedelta(days=row)
            if current < first or current > last:
                continue
            count, level = by_date.get(current, (0, 0))
            x, y = left + column * step, top + row * step
            cells.append(
                f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" '
                f'fill="{COLORS[level]}"><title>{current.isoformat()}: '
                f'{count} contributions</title></rect>'
            )
    x_first, x_last = left + 6.5, left + (columns - 1) * step + 6.5
    path_parts = [f"M{x_first:.1f} {top + 6.5:.1f}"]
    for row in range(7):
        x = x_last if row % 2 == 0 else x_first
        y = top + row * step + 6.5
        path_parts.append(f"L{x:.1f} {y:.1f}")
        if row < 6:
            path_parts.append(f"L{x:.1f} {y + step:.1f}")
    path = " ".join(path_parts)
    motion = 'dur="35s" repeatCount="indefinite"'
    tail = []
    for index, color in enumerate(("#6d28d9", "#7c3aed", "#9333ea", "#a855f7"), 1):
        tail.append(
            f'<rect x="-6" y="-6" width="12" height="12" rx="4" fill="{color}" '
            f'opacity="{0.35 + index * 0.13:.2f}">'
            f'<animateMotion path="{path}" {motion} begin="{index * .16:.2f}s"/>'
            "</rect>"
        )
    head = (
        '<g><rect x="-8" y="-8" width="16" height="16" rx="5" fill="#d8b4fe"/>'
        '<circle cx="-3" cy="-2" r="1.25" fill="#24113b"/>'
        '<circle cx="3" cy="-2" r="1.25" fill="#24113b"/>'
        f'<animateMotion path="{path}" {motion} begin="0s"/></g>'
    )
    total = sum(count for _, count, _ in days)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="264" viewBox="0 0 1200 264" role="img" aria-labelledby="title desc">
<title id="title">Purple contribution snake</title>
<desc id="desc">An animated purple snake travels across Marc's public contribution calendar. {total} contributions in the period shown.</desc>
<defs><style>.axis{{font:14px Arial,Helvetica,sans-serif;fill:#a6b3ca}}</style></defs>
<rect width="1200" height="264" rx="18" fill="#0d1117"/>
<text x="68" y="36" fill="#e9d5ff" font-family="Arial,Helvetica,sans-serif" font-size="20" font-weight="700">Contribution calendar</text>
<text x="1132" y="36" text-anchor="end" fill="#c084fc" font-family="Arial,Helvetica,sans-serif" font-size="14">GitHub · Machisi</text>
{''.join(labels)}
{''.join(cells)}
{''.join(tail)}
{head}
<text x="68" y="242" class="axis">Less</text>
{''.join(f'<rect x="{126 + i * 19}" y="231" width="13" height="13" rx="3" fill="{color}"/>' for i, color in enumerate(COLORS))}
<text x="234" y="242" class="axis">More</text>
</svg>
'''


def write_visuals(days: list[Day]) -> None:
    folder = Path("assets")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "activity-graph.svg").write_text(render_graph(days), encoding="utf-8")
    (folder / "contribution-snake.svg").write_text(render_snake(days), encoding="utf-8")
    print("Updated assets/activity-graph.svg and assets/contribution-snake.svg")


def main() -> None:
    days = fetch_days(os.environ["GITHUB_USER"], os.environ["GITHUB_TOKEN"])
    write_visuals(days)


if __name__ == "__main__":
    main()
