from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from sources.waste import WasteCalendar, parse_ics

TZ = ZoneInfo("Europe/Zurich")

ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261019T064500
SUMMARY:Grüngutsammlung
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261019T064500
SUMMARY:Kehricht
 sammlung
END:VEVENT
BEGIN:VEVENT
DTSTART:20261024T054500Z
SUMMARY:Alteisen/Metallsammlung
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261102
SUMMARY:Papiersammlung
END:VEVENT
END:VCALENDAR
"""


def at(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


@pytest.fixture
def calendar() -> WasteCalendar:
    return WasteCalendar(parse_ics(ICS, TZ), TZ, lookahead_hours=15, after_pickup_hours=2)


def test_parse_ics_handles_folding_utc_and_all_day():
    events = parse_ics(ICS, TZ)
    assert events == [
        (at("2026-10-19 06:45"), "Grüngut"),
        (at("2026-10-19 06:45"), "Kehricht"),
        (at("2026-10-24 07:45"), "Alteisen/Metall"),
        (at("2026-11-02 00:00"), "Papier"),
    ]


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-10-18 15:44", None),
        ("2026-10-18 15:45", "Morgen: Grüngut, Kehricht"),
        ("2026-10-19 06:45", "Heute: Grüngut, Kehricht"),
        ("2026-10-19 08:45", "Heute: Grüngut, Kehricht"),
        ("2026-10-19 08:46", None),
        ("2026-11-01 12:00", "Morgen: Papier"),
    ],
)
def test_pickup_hint_window(calendar, now, expected):
    assert calendar.pickup_hint(at(now)) == expected


def test_pickup_hint_without_events():
    assert WasteCalendar([], TZ).pickup_hint(at("2026-10-18 20:00")) is None
