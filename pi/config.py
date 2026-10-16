"""Zentrale Konfiguration. Werte kommen aus Umgebungsvariablen bzw. der Datei .env."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
_ENV_FILE = BASE_DIR / ".env"

# Meldungen beim Laden; werden von main.py nach dem Einrichten des Loggings ausgegeben
WARNINGS: list[str] = []

try:
    from dotenv import load_dotenv

    load_dotenv(_ENV_FILE)
except ImportError:
    # python-dotenv ist optional, z.B. wenn systemd die Variablen per EnvironmentFile setzt
    if _ENV_FILE.exists():
        WARNINGS.append(".env gefunden, aber python-dotenv ist nicht installiert (pip3 install -r requirements.txt)")


def _get(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        WARNINGS.append(f"Umgebungsvariable {name} ist nicht gesetzt (siehe .env.example)")
    return value


def _parse_stations(raw: str) -> dict[int, str]:
    """Parst "uid:Name,uid:Name" zu {uid: Name}."""
    stations = {}
    for entry in filter(None, (part.strip() for part in raw.split(","))):
        uid, _, name = entry.partition(":")
        stations[int(uid)] = name.strip() or uid
    return stations


# --- ÖV (OJP 2.0, opentransportdata.swiss) ---
OJP_API_URL = _get("OJP_API_URL", "https://api.opentransportdata.swiss/ojp20")
OJP_API_KEY = _get("OJP_API_KEY", required=True)
OJP_REQUESTOR_REF = _get("OJP_REQUESTOR_REF", "door-helper")
OJP_STOP_POINT_REF = _get("OJP_STOP_POINT_REF", required=True)
OJP_STOP_NAME = _get("OJP_STOP_NAME", "")
OJP_NUMBER_OF_RESULTS = int(_get("OJP_NUMBER_OF_RESULTS", "10"))

# --- Wetter (Open-Meteo, kein API-Key nötig) ---
WEATHER_LAT = _get("WEATHER_LAT", required=True)
WEATHER_LON = _get("WEATHER_LON", required=True)

# --- Nextbike ---
NEXTBIKE_DOMAIN = _get("NEXTBIKE_DOMAIN", "ch")
NEXTBIKE_STATIONS = _parse_stations(_get("NEXTBIKE_STATIONS", ""))
_home_station = _get("NEXTBIKE_HOME_STATION")
NEXTBIKE_HOME_STATION = int(_home_station) if _home_station else None

# --- Abfuhrkalender (.ics, kommagetrennt; relative Pfade ab dem pi/-Ordner) ---
WASTE_CALENDAR_FILES = [p.strip() for p in _get("WASTE_CALENDAR_FILES", "").split(",") if p.strip()]
# Wie viele Stunden vor der Abfuhr der Hinweis erscheint (15 h: bei Abfuhr um 06:45 ab 15:45 am Vortag)
WASTE_LOOKAHEAD_HOURS = float(_get("WASTE_LOOKAHEAD_HOURS", "15"))
# Wie viele Stunden der Hinweis nach dem Abfuhrzeitpunkt noch sichtbar bleibt
WASTE_AFTER_PICKUP_HOURS = float(_get("WASTE_AFTER_PICKUP_HOURS", "2"))

# --- System / Hardware ---
TIMEZONE = _get("TIMEZONE", "Europe/Zurich")
WAVESHARE_LIB_PATH = _get("WAVESHARE_LIB_PATH", "/home/pi/Touch_e-Paper_HAT/python/lib")
FONT_PATH = _get("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
LOG_LEVEL = _get("LOG_LEVEL", "INFO")

# --- Verhalten (Sekunden) ---
HOME_POLL_INTERVAL = 60  # Hintergrund-Abfrage auf dem Home-Screen
DEPARTURES_REFRESH_INTERVAL = 10  # Live-Aktualisierung in der Abfahrtsansicht
SCREEN_TIMEOUT = 60  # Rückkehr zum Home-Screen ohne Berührung
WEATHER_CACHE_SECONDS = 30 * 60
TOUCH_DEBOUNCE = 1.0
LOOP_INTERVAL = 0.1
HTTP_TIMEOUT = 10
# Nach so vielen Teil-Aktualisierungen folgt eine volle, um Geisterbilder zu entfernen
MAX_PARTIAL_REFRESHES = 20
