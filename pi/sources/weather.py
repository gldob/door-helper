"""Wetter via Open-Meteo (kein API-Key nötig)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

import config

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO-Wettercodes (https://open-meteo.com/en/docs) -> (Symbol, Beschreibung).
# Nur Zeichen, die in DejaVu Sans Bold enthalten sind (Emojis wie 🌤 fehlen dort).
WMO_CODES = {
    0: ("☼", "Klar"),
    1: ("☼", "Überwiegend klar"),
    2: ("☁", "Teilweise bewölkt"),
    3: ("☁", "Bedeckt"),
    45: ("≈", "Nebel"),
    48: ("≈", "Raureifnebel"),
    51: ("☂", "Leichter Nieselregen"),
    53: ("☂", "Nieselregen"),
    55: ("☂", "Starker Nieselregen"),
    56: ("☂", "Gefrierender Nieselregen"),
    57: ("☂", "Gefrierender Nieselregen"),
    61: ("☔", "Leichter Regen"),
    63: ("☔", "Regen"),
    65: ("☔", "Starker Regen"),
    66: ("☔", "Gefrierender Regen"),
    67: ("☔", "Gefrierender Regen"),
    71: ("❄", "Leichter Schneefall"),
    73: ("❄", "Schneefall"),
    75: ("❄", "Starker Schneefall"),
    77: ("❄", "Schneegriesel"),
    80: ("☂", "Leichte Regenschauer"),
    81: ("☂", "Regenschauer"),
    82: ("☔", "Heftige Regenschauer"),
    85: ("❄", "Schneeschauer"),
    86: ("❄", "Starke Schneeschauer"),
    95: ("⚡", "Gewitter"),
    96: ("⚡", "Gewitter mit Hagel"),
    99: ("⚡", "Gewitter mit Hagel"),
}


@dataclass(frozen=True)
class Weather:
    icon: str
    description: str
    current_temp: int
    max_temp: int


def parse_forecast(data: dict) -> Weather:
    current = data["current"]
    icon, description = WMO_CODES.get(current.get("weather_code"), ("?", "Unbekannt"))
    if icon == "☼" and not current.get("is_day", 1):
        icon = "☾"
    return Weather(
        icon=icon,
        description=description,
        current_temp=round(current["temperature_2m"]),
        max_temp=round(data["daily"]["temperature_2m_max"][0]),
    )


class WeatherClient:
    """Holt das Wetter und hält es WEATHER_CACHE_SECONDS lang im Cache."""

    def __init__(self, cache_seconds: float = config.WEATHER_CACHE_SECONDS, clock=time.monotonic):
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._cached: Weather | None = None
        self._fetched_at = float("-inf")

    def get(self) -> Weather | None:
        """Aktuelles Wetter; bei einem Fehler die letzten bekannten Daten (oder None)."""
        if self._cached is not None and self._clock() - self._fetched_at < self._cache_seconds:
            return self._cached

        params = {
            "latitude": config.WEATHER_LAT,
            "longitude": config.WEATHER_LON,
            "current": "temperature_2m,weather_code,is_day",
            "daily": "temperature_2m_max",
            "timezone": config.TIMEZONE,
            "forecast_days": 1,
        }
        try:
            response = requests.get(OPEN_METEO_URL, params=params, timeout=config.HTTP_TIMEOUT)
            response.raise_for_status()
            self._cached = parse_forecast(response.json())
            self._fetched_at = self._clock()
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as e:
            # Lieber veraltete Daten anzeigen als einen Fehler; nächster Versuch beim nächsten Aufruf
            log.warning("Wetterdaten nicht verfügbar: %s", e)
        return self._cached
