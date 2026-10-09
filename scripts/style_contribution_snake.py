"""Add GitHub calendar labels and yearly views to the animated snake."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

from github_contributions import Day, fetch_days


FIRST_YEAR = 2024  # Machisi joined GitHub in 2024.
COLORS = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CELL = re.compile(
    r'<rect class="c(?: c[0-9a-z]+)?" x="(?P<x>\d+)" y="(?P<y>\d+)" rx="2" ry="2"/>'
)
README_START = "<!-- contribution-calendar:start -->"
README_END = "<!-- contribution-calendar:end -->"


def calendar_svg(source: str, days: list[Day], heading: str) -> str:
    if not days:
        raise ValueError("No contribution days to display")
    first = min(day for day, _, _ in days)
    last = max(day for day, _, _ in days)
    first_sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    by_date = {day: (count, level) for day, count, level in days}
    columns = max(int(match.group("x")) for match in CELL.finditer(source)) // 16 + 1

    def replace_cell(match: re.Match[str]) -> str:
        x, y = int(match.group("x")), int(match.group("y"))
        current = first_sunday + timedelta(days=(x // 16) * 7 + (y - 2) // 16)
        if current not in by_date:
            return ""
        count, level = by_date[current]
        noun = "contribution" if count == 1 else "contributions"
        return (
            f'<rect class="c" x="{x}" y="{y}" rx="2" ry="2" '
            f'style="fill:{COLORS[level]}">'
            f'<title>{current.isoformat()}: {count} {noun}</title></rect>'
        )

    svg, replaced = CELL.subn(replace_cell, source)
    if replaced < 300:
        raise ValueError(f"Snake SVG has only {replaced} calendar cells")
    svg = re.sub(r'<rect class="u u[0-9a-z]+"[^>]*/>', "", svg)

    opening = re.match(r'<svg\b[^>]*>', svg)
    if opening is None:
        raise ValueError("Snake generator did not produce an SVG")
    root = opening.group()
    root = re.sub(r'viewBox="[^"]+"', 'viewBox="-56 -68 920 240"', root)
    root = re.sub(r'width="[^"]+"', 'width="920"', root, count=1)
    root = re.sub(r'height="[^"]+"', 'height="240"', root, count=1)
    svg = root + '<rect x="-56" y="-68" width="920" height="240" fill="#0d1117"/>' + svg[opening.end() :]

    style_end = svg.find("</style>")
    if style_end < 0:
        raise ValueError("Snake SVG has no animation styles")
    style_end += len("</style>")
    svg = svg[:style_end] + '<style>rect.c{animation:none!important}</style>' + svg[style_end:]

    total = sum(count for _, count, _ in days)
    contribution_word = "contribution" if total == 1 else "contributions"
    labels = [
        f'<text x="-48" y="-48" font-size="15" fill="#c9d1d9">'
        f'{total} {contribution_word} {heading}</text>'
    ]
    month = date(first.year, first.month, 1)
    while month <= last:
        column = max(0, (month - first_sunday).days // 7)
        if columns - column >= 4:
            labels.append(
                f'<text x="{column * 16 + 2}" y="-21" font-size="12" '
                f'fill="#8b949e">{MONTHS[month.month - 1]}</text>'
            )
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    for name, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        labels.append(
            f'<text x="-45" y="{row * 16 + 11}" font-size="12" '
            f'fill="#8b949e">{name}</text>'
        )
    labels.append('<text x="620" y="153" font-size="12" fill="#8b949e">Less</text>')
    for level, color in enumerate(COLORS):
        labels.append(
            f'<rect x="{651 + level * 16}" y="143" width="11" height="11" '
            f'rx="2" fill="{color}"/>'
        )
    labels.append('<text x="741" y="153" font-size="12" fill="#8b949e">More</text>')
    svg = svg.replace(
        "</svg>",
        '<g font-family="Arial,Helvetica,sans-serif">' + "".join(labels) + "</g></svg>",
        1,
    )
    return svg


def update_readme(current_year: int, repository: str) -> None:
    readme = Path("README.md")
    content = readme.read_text(encoding="utf-8")
    if README_START not in content or README_END not in content:
        raise ValueError("README contribution calendar markers are missing")
    year_links = [f"<strong>{current_year}</strong>"]
    for year in range(current_year - 1, FIRST_YEAR - 1, -1):
        url = f"https://raw.githubusercontent.com/{repository}/main/assets/contribution-snake-{year}.svg"
        year_links.append(f'<a href="{url}">{year}</a>')
    block = (
        f"{README_START}\n"
        '<table><tr><td width="90%" valign="top">\n'
        '<img src="./assets/contribution-snake.svg" '
        'alt="Animated purple snake on Marc’s GitHub contribution calendar" width="100%" />\n'
        '</td><td valign="top"><strong>Years</strong><br />\n'
        + "<br />\n".join(year_links)
        + f"\n</td></tr></table>\n{README_END}"
    )
    start = content.index(README_START)
    end = content.index(README_END, start) + len(README_END)
    updated = content[:start] + block + content[end:]
    if updated != content:
        readme.write_text(updated, encoding="utf-8")


def main() -> None:
    login = os.environ["GITHUB_USER"]
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ.get("GITHUB_REPOSITORY", f"{login}/{login.lower()}")
    path = Path("assets/contribution-snake.svg")
    source = path.read_text(encoding="utf-8")
    rolling = fetch_days(login, token)
    current_year = max(day.year for day, _, _ in rolling)
    path.write_text(calendar_svg(source, rolling, "in the last year"), encoding="utf-8")
    for year in range(FIRST_YEAR, current_year):
        annual = [day for day in fetch_days(login, token, year) if day[0].year == year]
        output = Path(f"assets/contribution-snake-{year}.svg")
        annual_source = output.read_text(encoding="utf-8")
        output.write_text(calendar_svg(annual_source, annual, f"in {year}"), encoding="utf-8")
    update_readme(current_year, repository)
    print(f"Updated contribution calendars for {FIRST_YEAR}-{current_year}")


if __name__ == "__main__":
    main()
