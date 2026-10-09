"""Render the plain graph and animated snake from one GitHub calendar."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from github_contributions import Day, read_days

COLORS = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CELL = re.compile(
    r'<rect class="c(?: c[0-9a-z]+)?" x="(?P<x>\d+)" y="(?P<y>\d+)" rx="2" ry="2"/>'
)


def calendar_svg(source: str, days: list[Day]) -> str:
    first = days[0][0]
    last = days[-1][0]
    first_sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    by_date = {day: (count, level) for day, count, level in days}
    columns = max(int(match.group("x")) for match in CELL.finditer(source)) // 16 + 1

    def replace_cell(match: re.Match[str]) -> str:
        x, y = int(match.group("x")), int(match.group("y"))
        current = first_sunday + timedelta(days=(x // 16) * 7 + (y - 2) // 16)
        if current not in by_date:
            raise ValueError(f"The snake has a calendar cell outside the GitHub response: {current}")
        count, level = by_date[current]
        noun = "contribution" if count == 1 else "contributions"
        return (
            f'<rect class="c" x="{x}" y="{y}" rx="2" ry="2" '
            f'style="fill:{COLORS[level]}">'
            f'<title>{current.isoformat()}: {count} {noun}</title></rect>'
        )

    svg, replaced = CELL.subn(replace_cell, source)
    if replaced != len(days):
        raise ValueError(f"Snake has {replaced} cells but GitHub returned {len(days)} days")
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
    noun = "contribution" if total == 1 else "contributions"
    labels = [f'<text x="-48" y="-48" font-size="15" fill="#c9d1d9">{total} {noun} in the last year</text>']
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
            f'<text x="-45" y="{row * 16 + 11}" font-size="12" fill="#8b949e">{name}</text>'
        )
    labels.append('<text x="620" y="153" font-size="12" fill="#8b949e">Less</text>')
    for level, color in enumerate(COLORS):
        labels.append(
            f'<rect x="{651 + level * 16}" y="143" width="11" height="11" rx="2" fill="{color}"/>'
        )
    labels.append('<text x="741" y="153" font-size="12" fill="#8b949e">More</text>')
    return svg.replace(
        "</svg>",
        '<g font-family="Arial,Helvetica,sans-serif">' + "".join(labels) + "</g></svg>",
        1,
    )


def main() -> None:
    path = Path("assets/contribution-snake.svg")
    days = read_days()
    snake = calendar_svg(path.read_text(encoding="utf-8"), days)
    path.write_text(snake, encoding="utf-8")

    graph, segments = re.subn(r'<rect class="s s[0-9a-z]+"[^>]*/>', "", snake)
    if segments != 4:
        raise ValueError(f"Expected four snake segments, found {segments}")
    graph = graph.replace(
        "<desc>Generated with https://github.com/Platane/snk</desc>",
        "<title>GitHub contribution graph</title><desc>Current contribution days from GitHub's profile calendar.</desc>",
        1,
    )
    Path("assets/contribution-graph.svg").write_text(graph, encoding="utf-8")
    print(f"Updated graph and snake from the same {len(days)} GitHub contribution days")


if __name__ == "__main__":
    main()
