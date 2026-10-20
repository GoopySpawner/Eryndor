import json
import random
from pathlib import Path
from typing import Any


CALENDAR_PATH = (
    Path(__file__).parent / "Saved-Data" / "campaign_calendar.json"
)
CALENDAR_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Undecimber",
)
CALENDAR_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
CALENDAR_TIME_SLOTS = (
    "10:01 PM-4:00 AM",
    "4:01 AM-10:00 AM",
    "10:01 AM-4:00 PM",
    "4:01 PM-10:00 PM",
)
CALENDAR_SEGMENT_NAMES = (
    "Late Night",
    "Early Morning",
    "Midday",
    "Evening",
)
FULL_MOON_CYCLE_DAYS = 29


def _days_since_epoch(year: int, month: int, day: int) -> int:
    return (
        (year - 1) * len(CALENDAR_MONTHS) * 28
        + (month - 1) * 28
        + day
        - 1
    )


def _full_moon_days(year: int, month: int) -> list[int]:
    month_start = _days_since_epoch(year, month, 1)
    return [
        day
        for day in range(1, 29)
        if (month_start + day - 1) % FULL_MOON_CYCLE_DAYS == 0
    ]


def _new_calendar() -> dict[str, int]:
    return {
        "year": 1,
        "month": random.randint(4, 6),
        "day": random.randint(1, 28),
        "segment": 1,
        "total_encounters": 0,
    }


def save_calendar(calendar: dict[str, int]) -> None:
    """Persist the campaign date and encounter count."""
    CALENDAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = CALENDAR_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as calendar_file:
        json.dump(calendar, calendar_file, indent=2)
        calendar_file.write("\n")
    temporary_path.replace(CALENDAR_PATH)


def load_calendar() -> dict[str, int]:
    """Load the campaign calendar or create its initial spring date once."""
    try:
        with CALENDAR_PATH.open(encoding="utf-8") as calendar_file:
            calendar = json.load(calendar_file)
    except FileNotFoundError:
        calendar = _new_calendar()
        save_calendar(calendar)
        return calendar

    legacy_fields = {
        "year",
        "month",
        "day",
        "encounters_toward_day",
        "total_encounters",
    }
    if isinstance(calendar, dict) and set(calendar) == legacy_fields:
        if (
            type(calendar["encounters_toward_day"]) is not int
            or not 0 <= calendar["encounters_toward_day"] <= 2
        ):
            raise ValueError("Campaign calendar contains an invalid encounter count.")
        calendar = {
            "year": calendar["year"],
            "month": calendar["month"],
            "day": calendar["day"],
            "segment": calendar["encounters_toward_day"] + 1,
            "total_encounters": calendar["total_encounters"],
        }
        _validate_calendar(calendar)
        save_calendar(calendar)
        return calendar

    if not isinstance(calendar, dict) or set(calendar) != {
        "year",
        "month",
        "day",
        "segment",
        "total_encounters",
    }:
        raise ValueError("Campaign calendar has an invalid structure.")
    _validate_calendar(calendar)
    return calendar


def _validate_calendar(calendar: dict[str, int]) -> None:
    if any(type(value) is not int for value in calendar.values()):
        raise ValueError("Campaign calendar values must be integers.")
    if (
        not 1 <= calendar["month"] <= len(CALENDAR_MONTHS)
        or not 1 <= calendar["day"] <= 28
        or not 1 <= calendar["segment"] <= len(CALENDAR_TIME_SLOTS)
        or calendar["total_encounters"] < 0
    ):
        raise ValueError("Campaign calendar contains an invalid date or count.")


def get_calendar_display(calendar: dict[str, int]) -> dict[str, Any]:
    """Format the campaign date, weekday, time segment, and encounter total."""
    days_since_epoch = _days_since_epoch(
        calendar["year"],
        calendar["month"],
        calendar["day"],
    )
    return {
        "dateLabel": (
            f"{CALENDAR_MONTHS[calendar['month'] - 1]} {calendar['day']}, "
            f"Year {calendar['year']}"
        ),
        "monthName": CALENDAR_MONTHS[calendar["month"] - 1],
        "month": calendar["month"],
        "day": calendar["day"],
        "year": calendar["year"],
        "weekday": CALENDAR_WEEKDAYS[days_since_epoch % len(CALENDAR_WEEKDAYS)],
        "weekdays": list(CALENDAR_WEEKDAYS),
        "segment": calendar["segment"],
        "segmentName": CALENDAR_SEGMENT_NAMES[calendar["segment"] - 1],
        "timeSlot": CALENDAR_TIME_SLOTS[calendar["segment"] - 1],
        "timeSlots": list(CALENDAR_TIME_SLOTS),
        "totalEncounters": calendar["total_encounters"],
        "isFullMoon": days_since_epoch % FULL_MOON_CYCLE_DAYS == 0,
        "fullMoonDays": _full_moon_days(calendar["year"], calendar["month"]),
    }


def _move_segment(calendar: dict[str, int], direction: int) -> None:
    calendar["segment"] += direction
    if calendar["segment"] > len(CALENDAR_TIME_SLOTS):
        calendar["segment"] = 1
        calendar["day"] += 1
        if calendar["day"] > 28:
            calendar["day"] = 1
            calendar["month"] += 1
            if calendar["month"] > len(CALENDAR_MONTHS):
                calendar["month"] = 1
                calendar["year"] += 1
    elif calendar["segment"] < 1:
        calendar["segment"] = len(CALENDAR_TIME_SLOTS)
        calendar["day"] -= 1
        if calendar["day"] < 1:
            calendar["day"] = 28
            calendar["month"] -= 1
            if calendar["month"] < 1:
                calendar["month"] = len(CALENDAR_MONTHS)
                calendar["year"] -= 1


def adjust_calendar_segment(direction: int) -> dict[str, Any]:
    """Move time one segment forward or backward without adding an encounter."""
    if type(direction) is not int or direction not in (-1, 1):
        raise ValueError("Calendar direction must be -1 or 1.")
    calendar = load_calendar()
    _move_segment(calendar, direction)
    save_calendar(calendar)
    return get_calendar_display(calendar)


def take_long_rest(days: int = 3) -> dict[str, Any]:
    """Advance campaign time by whole days without changing its time segment."""
    if type(days) is not int or days < 0:
        raise ValueError("Long-rest duration must be a non-negative number of days.")
    calendar = load_calendar()
    calendar["day"] += days
    while calendar["day"] > 28:
        calendar["day"] -= 28
        calendar["month"] += 1
        if calendar["month"] > len(CALENDAR_MONTHS):
            calendar["month"] = 1
            calendar["year"] += 1
    save_calendar(calendar)
    return get_calendar_display(calendar)


def record_encounter_count() -> dict[str, Any]:
    """Count an encounter without advancing time, for a long-rest interruption."""
    calendar = load_calendar()
    calendar["total_encounters"] += 1
    save_calendar(calendar)
    return get_calendar_display(calendar)


def record_calendar_encounter() -> dict[str, Any]:
    """Count one generated encounter and advance campaign time one segment."""
    calendar = load_calendar()
    calendar["total_encounters"] += 1
    _move_segment(calendar, 1)
    save_calendar(calendar)
    return get_calendar_display(calendar)
