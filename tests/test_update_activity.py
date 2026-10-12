import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_activity import calendar_table, readme_section, streaks


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.weeks = [
            [
                {"date": "2026-10-04", "weekday": 0, "count": 0, "level": 0},
                {"date": "2026-10-05", "weekday": 1, "count": 2, "level": 1},
                {"date": "2026-10-06", "weekday": 2, "count": 1, "level": 1},
                {"date": "2026-10-07", "weekday": 3, "count": 0, "level": 0},
            ],
            [
                {"date": "2026-10-11", "weekday": 0, "count": 1, "level": 1},
                {"date": "2026-10-12", "weekday": 1, "count": 0, "level": 0},
            ],
        ]

    def test_streak_uses_yesterday_when_today_is_unfinished(self):
        self.weeks[1][0]["count"] = 1
        self.assertEqual(streaks(self.weeks), (1, 2))

    def test_calendar_has_date_specific_hover_labels(self):
        markup = calendar_table("Machisi", self.weeks)
        self.assertIn('title="2026-10-05: 2 contributions"', markup)
        self.assertIn('title="2026-10-06: 1 contribution"', markup)
        self.assertIn('from=2026-10-05&amp;to=2026-10-05', markup)
        self.assertIn('>🟩</a>', markup)

    def test_readme_section_has_no_statistic_images(self):
        activity = {"total": 4, "weeks": self.weeks}
        repos = {"repositoryCount": 2, "stars": 3, "languages": [{"name": "Python"}]}
        section = readme_section("Machisi", activity, repos, pages_enabled=True)
        self.assertIn("Contribution calendar", section)
        self.assertIn("**4**", section)
        self.assertNotIn("<img", section)
        self.assertIn("machisi.github.io/machisi/", section)

    def test_disabled_pages_does_not_link_to_unpublished_site(self):
        activity = {"total": 4, "weeks": self.weeks}
        repos = {"repositoryCount": 2, "stars": 3, "languages": []}
        section = readme_section("Machisi", activity, repos, pages_enabled=False)
        self.assertNotIn("machisi.github.io", section)
        self.assertIn("View the interactive page's source code", section)


if __name__ == "__main__":
    unittest.main()
