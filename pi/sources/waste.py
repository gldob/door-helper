"""Abfuhrtermine aus iCalendar-Dateien (z.B. Export von REAL Luzern)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import config

log = logging.getLogger(__name__)

Pickup = tuple[datetime, str]  # (Abfuhrzeitpunkt, Kurzname)


def _unfold(text: str) -> list[str]:
    # RFC 5545: Fortsetzungszeilen beginnen mit Leerzeichen oder Tab
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def _parse_dtstart(prop: str, value: str, tz: ZoneInfo) -> datetime:
    params = dict(p.split("=", 1) for p in prop.split(";")[1:] if "=" in p)
    if len(value) == 8:  # Ganztägig (VALUE=DATE)
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=tz)
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(tz)
    event_tz = ZoneInfo(params["TZID"]) if "TZID" in params else tz
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=event_tz)


def _short_name(summary: str) -> str:
    # "Kartonsammlung" -> "Karton", "Alteisen/Metallsammlung" -> "Alteisen/Metall"
    summary = summary.replace("\\,", ",").replace("\\;", ";").strip()
    return re.sub(r"sammlung$", "", summary, flags=re.IGNORECASE) or summary


def parse_ics(text: str, tz: ZoneInfo) -> list[Pickup]:
    events = []
    start = name = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            start = name = None
        elif line == "END:VEVENT":
            if start and name:
                events.append((start, name))
        elif ":" in line:
            prop, value = line.split(":", 1)
            key = prop.split(";", 1)[0].upper()
            if key == "DTSTART":
                start = _parse_dtstart(prop, value.strip(), tz)
            elif key == "SUMMARY":
                name = _short_name(value)
    return sorted(events)


class WasteCalendar:
    def __init__(
        self,
        events: list[Pickup],
        tz: ZoneInfo,
        lookahead_hours: float = config.WASTE_LOOKAHEAD_HOURS,
        after_pickup_hours: float = config.WASTE_AFTER_PICKUP_HOURS,
    ):
        self._events = sorted(events)
        self._tz = tz
        self._lookahead = timedelta(hours=lookahead_hours)
        self._after_pickup = timedelta(hours=after_pickup_hours)
        self._warned_empty = False

    @classmethod
    def from_config(cls) -> WasteCalendar:
        tz = ZoneInfo(config.TIMEZONE)
        events: list[Pickup] = []
        for name in config.WASTE_CALENDAR_FILES:
            path = Path(name)
            if not path.is_absolute():
                path = config.BASE_DIR / path
            try:
                events += parse_ics(path.read_text(encoding="utf-8"), tz)
            except (OSError, ValueError) as e:
                log.error("Abfuhrkalender %s konnte nicht gelesen werden: %s", path, e)
        log.info("Abfuhrkalender: %d Termine geladen", len(events))
        return cls(events, tz)

    def pickup_hint(self, now: datetime | None = None) -> str | None:
        """
        Text für den Home-Screen, z.B. "Morgen: Karton, Kehricht".
        Sichtbar von lookahead_hours vor bis after_pickup_hours nach der Abfuhr, sonst None.
        """
        if not self._events:
            return None
        now = now or datetime.now(self._tz)
        if self._events[-1][0] < now and not self._warned_empty:
            log.warning("Abfuhrkalender enthält keine künftigen Termine mehr – neue .ics-Datei hinterlegen.")
            self._warned_empty = True

        window_start, window_end = now - self._after_pickup, now + self._lookahead
        upcoming = [(start, name) for start, name in self._events if window_start <= start <= window_end]
        if not upcoming:
            return None

        day = upcoming[0][0].date()
        names = list(dict.fromkeys(name for start, name in upcoming if start.date() == day))

        if day == now.date():
            label = "Heute"
        elif day == now.date() + timedelta(days=1):
            label = "Morgen"
        else:
            label = day.strftime("%d.%m.")
        return f"{label}: {', '.join(names)}"
