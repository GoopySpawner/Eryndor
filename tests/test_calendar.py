import importlib.util
from pathlib import Path
import unittest


CALENDAR_PATH = Path(__file__).parents[1] / "calendar.py"
CALENDAR_SPEC = importlib.util.spec_from_file_location(
    "eryndor_campaign_calendar",
    CALENDAR_PATH,
)
if CALENDAR_SPEC is None or CALENDAR_SPEC.loader is None:
    raise ImportError(f"Unable to load campaign calendar from {CALENDAR_PATH}")

campaign_calendar = importlib.util.module_from_spec(CALENDAR_SPEC)
CALENDAR_SPEC.loader.exec_module(campaign_calendar)


class CampaignCalendarTests(unittest.TestCase):
    def test_full_moons_recur_every_29_days_across_months(self):
        full_moons = (
            (1, 1, 1),
            (1, 2, 2),
            (1, 3, 3),
        )

        for year, month, day in full_moons:
            with self.subTest(year=year, month=month, day=day):
                display = campaign_calendar.get_calendar_display({
                    "year": year,
                    "month": month,
                    "day": day,
                    "segment": 1,
                    "total_encounters": 0,
                })
                self.assertTrue(display["isFullMoon"])

        indexes = [
            campaign_calendar._days_since_epoch(year, month, day)
            for year, month, day in full_moons
        ]
        self.assertEqual([right - left for left, right in zip(indexes, indexes[1:])], [29, 29])

    def test_calendar_display_marks_current_month_full_moon_days(self):
        display = campaign_calendar.get_calendar_display({
            "year": 1,
            "month": 2,
            "day": 2,
            "segment": 1,
            "total_encounters": 0,
        })

        self.assertEqual(display["fullMoonDays"], [2])
        self.assertTrue(display["isFullMoon"])

    def test_days_28_apart_are_not_repeated_full_moons(self):
        display = campaign_calendar.get_calendar_display({
            "year": 1,
            "month": 2,
            "day": 1,
            "segment": 1,
            "total_encounters": 0,
        })

        self.assertFalse(display["isFullMoon"])


if __name__ == "__main__":
    unittest.main()
