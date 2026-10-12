"""Build the profile's text calendar and Pages data from GitHub's own APIs."""

from __future__ import annotations

import html
import json
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
GRAPHQL = """
query ($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            weekday
            contributionCount
            contributionLevel
          }
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
START = "<!-- github-activity:start -->"
END = "<!-- github-activity:end -->"


def api_json(url: str, token: str, body: dict | None = None) -> dict | list:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Machisi-profile-activity",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"GitHub API returned HTTP {error.code} for {url}") from error


def fetch_activity(login: str, token: str) -> dict:
    payload = api_json(
        "https://api.github.com/graphql",
        token,
        {"query": GRAPHQL, "variables": {"login": login}},
    )
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"No GitHub user found for {login}")
    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    weeks = [
        [
            {
                "date": day["date"],
                "weekday": day["weekday"],
                "count": day["contributionCount"],
                "level": LEVELS[day["contributionLevel"]],
            }
            for day in week["contributionDays"]
        ]
        for week in calendar["weeks"]
    ]
    if not weeks or not any(weeks):
        raise RuntimeError("GitHub returned an empty contribution calendar")
    return {
        "total": calendar["totalContributions"],
        "commits": collection["totalCommitContributions"],
        "pullRequests": collection["totalPullRequestContributions"],
        "issues": collection["totalIssueContributions"],
        "weeks": weeks,
    }


def fetch_public_repos(login: str, token: str) -> dict:
    repos = []
    page = 1
    while True:
        batch = api_json(
            f"https://api.github.com/users/{quote(login)}/repos?type=owner&per_page=100&page={page}",
            token,
        )
        repos.extend(repo for repo in batch if not repo["fork"] and not repo["archived"])
        if len(batch) < 100:
            break
        page += 1

    languages: Counter[str] = Counter()
    for repo in repos:
        sizes = api_json(repo["languages_url"], token)
        languages.update(sizes)
    return {
        "repositoryCount": len(repos),
        "stars": sum(repo["stargazers_count"] for repo in repos),
        "languageBytesTotal": sum(languages.values()),
        "languages": [
            {"name": name, "bytes": size} for name, size in languages.most_common(6)
        ],
    }


def streaks(weeks: list[list[dict]]) -> tuple[int, int]:
    days = [day for week in weeks for day in week]
    run = longest = 0
    for day in days:
        run = run + 1 if day["count"] else 0
        longest = max(longest, run)
    # An unfinished current day should not end yesterday's streak.
    current = run or (streak_before_last(days) if days[-1]["count"] == 0 else 0)
    return current, longest


def streak_before_last(days: list[dict]) -> int:
    run = 0
    for day in reversed(days[:-1]):
        if not day["count"]:
            break
        run += 1
    return run


def calendar_table(login: str, weeks: list[list[dict]]) -> str:
    names = ("", "Mon", "", "Wed", "", "Fri", "")
    months = []
    for index, week in enumerate(weeks):
        if not week:
            continue
        parsed = date.fromisoformat(week[-1]["date"])
        if not months or (parsed.year, parsed.month) != months[-1][:2]:
            months.append((parsed.year, parsed.month, index, parsed.strftime("%b")))
    month_cells = []
    for index, (_, _, start, label) in enumerate(months):
        next_start = months[index + 1][2] if index + 1 < len(months) else len(weeks)
        if next_start > start:
            month_cells.append(f'<th colspan="{next_start - start}">{label}</th>')
    prefix = months[0][2] if months else len(weeks)
    header = f'<tr><th></th><th colspan="{prefix}"></th>{"".join(month_cells)}</tr>'
    rows = []
    for weekday, name in enumerate(names):
        cells = []
        for week in weeks:
            match = next((day for day in week if day["weekday"] == weekday), None)
            if match is None:
                cells.append("<td></td>")
                continue
            count, day = match["count"], match["date"]
            square = "⬛" if count == 0 else "🟩"
            label = html.escape(f"{day}: {count} contribution{'s' if count != 1 else ''}", quote=True)
            url = html.escape(f"https://github.com/{login}?tab=overview&from={day}&to={day}", quote=True)
            cells.append(f'<td><a href="{url}" title="{label}">{square}</a></td>')
        rows.append(f'<tr><th>{name}</th>{"".join(cells)}</tr>')
    return "<table>\n<thead>" + header + "</thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>"


def readme_section(login: str, activity: dict, repos: dict) -> str:
    current, longest = streaks(activity["weeks"])
    languages = ", ".join(item["name"] for item in repos["languages"][:3]) or "—"
    return "\n".join(
        [
            START,
            "| Contributions (last year) | Current streak | Longest streak (last year) | Public projects | Stars |",
            "| :---: | :---: | :---: | :---: | :---: |",
            f'| **{activity["total"]}** | **{current} {"day" if current == 1 else "days"}** | **{longest} {"day" if longest == 1 else "days"}** | **{repos["repositoryCount"]}** | **{repos["stars"]}** |',
            "",
            f"**Most used languages in public projects:** {languages}.",
            "",
            "### Contribution calendar",
            "",
            "The squares below are generated from GitHub's daily contribution counts. Hover over or focus a day to see its exact count.",
            "",
            calendar_table(login, activity["weeks"]),
            "",
            f"[Open the interactive contribution snake and detailed analytics](https://{login.lower()}.github.io/{login.lower()}/) · [GitHub's original contribution graph](https://github.com/{login}?tab=overview)",
            "",
            "<sub>Updated by GitHub Actions each hour. Contributions follow GitHub's calendar; project languages and stars cover public, non-fork, non-archived repositories.</sub>",
            END,
        ]
    )


def update_readme(section: str) -> None:
    path = ROOT / "README.md"
    content = path.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1:
        raise RuntimeError("README needs exactly one GitHub activity marker pair")
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: section, content, flags=re.S)
    if updated != content:
        path.write_text(updated, encoding="utf-8")


def main() -> None:
    login = os.environ["GITHUB_USER"]
    token = os.environ["GITHUB_TOKEN"]
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        raise ValueError("Invalid GitHub username")
    activity = fetch_activity(login, token)
    repos = fetch_public_repos(login, token)
    output = {"user": login, **activity, **repos}
    destination = ROOT / "docs" / "activity.json"
    destination.write_text(json.dumps(output, separators=(",", ":")), encoding="utf-8")
    update_readme(readme_section(login, activity, repos))
    print(f"Updated {len(activity['weeks'])} weeks of GitHub activity")


if __name__ == "__main__":
    main()
