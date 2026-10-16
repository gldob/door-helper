"""Freie Velos an ausgewählten Stationen via Nextbike-Live-Feed."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

import config

log = logging.getLogger(__name__)

NEXTBIKE_URL = "https://maps2.nextbike.net/maps/nextbike-live.json"
LOW_BIKES_THRESHOLD = 2


@dataclass(frozen=True)
class BikeStation:
    uid: int
    name: str
    bikes: int


def parse_feed(data: dict, stations: dict[int, str]) -> list[BikeStation]:
    """Sucht die gewünschten Stationen im Feed; Reihenfolge wie in der Konfiguration."""
    found = {}
    # Das JSON ist stark verschachtelt: countries -> cities -> places
    for country in data.get("countries", []):
        for city in country.get("cities", []):
            for place in city.get("places", []):
                uid = place.get("uid")
                if uid in stations:
                    found[uid] = BikeStation(uid, stations[uid], place.get("bikes_available_to_rent", 0))
    return [found[uid] for uid in stations if uid in found]


def fetch_stations(stations: dict[int, str] | None = None) -> list[BikeStation] | None:
    """Verfügbarkeit der konfigurierten Stationen, oder None bei einem Fehler."""
    stations = config.NEXTBIKE_STATIONS if stations is None else stations
    if not stations:
        return []
    try:
        response = requests.get(NEXTBIKE_URL, params={"domains": config.NEXTBIKE_DOMAIN}, timeout=config.HTTP_TIMEOUT)
        response.raise_for_status()
        return parse_feed(response.json(), stations)
    except (requests.RequestException, ValueError) as e:
        log.warning("Nextbike-Daten nicht verfügbar: %s", e)
        return None


def availability_alert(stations: list[BikeStation] | None, home_uid: int | None) -> str | None:
    """Symbol für den Home-Screen: "X" = keine Velos, "!" = nur noch wenige, sonst None."""
    home = next((s for s in stations or [] if s.uid == home_uid), None)
    if home is None:
        return None
    if home.bikes == 0:
        return "X"
    if home.bikes <= LOW_BIKES_THRESHOLD:
        return "!"
    return None
