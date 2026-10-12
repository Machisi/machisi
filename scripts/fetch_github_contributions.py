"""Capture GitHub's contribution calendar for labeling Platane/snk's SVG."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

QUERY = """
query ($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
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


def main() -> None:
    login = os.environ["GITHUB_USER"]
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode("utf-8")
    request = Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Machisi-profile-snake",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors") or not payload.get("data", {}).get("user", {}).get(
        "contributionsCollection", {}
    ).get("contributionCalendar", {}).get("weeks"):
        raise RuntimeError("GitHub did not return a usable contribution calendar")
    Path(".contribution-calendar.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
