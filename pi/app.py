"""Zustandsautomat: Home-Screen mit Hintergrund-Abfrage und Detailansichten mit Timeout."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

import config
from sources import nextbike, transport
from sources.waste import WasteCalendar
from sources.weather import Weather, WeatherClient
from ui import screens
from ui.screens import Tile

log = logging.getLogger(__name__)


class Screen(Enum):
    HOME = "home"
    DEPARTURES = "departures"
    WEATHER = "weather"
    BIKES = "bikes"


TILE_SCREENS = {Tile.DEPARTURES: Screen.DEPARTURES, Tile.WEATHER: Screen.WEATHER, Tile.BIKES: Screen.BIKES}


@dataclass(frozen=True)
class HomeStatus:
    """Alles, was auf dem Home-Screen sichtbar ist. Neu gezeichnet wird nur bei Änderungen."""

    has_disruption: bool
    weather: Weather | None
    bike_alert: str | None
    waste_hint: str | None


class DoorHelperApp:
    def __init__(self, display, touch, weather: WeatherClient, waste: WasteCalendar, clock=time.monotonic):
        self.display = display
        self.touch = touch
        self.weather = weather
        self.waste = waste
        self._clock = clock
        self._tz = ZoneInfo(config.TIMEZONE)

        self.screen = Screen.HOME
        self._home_status: HomeStatus | None = None
        self._next_home_poll = float("-inf")
        self._next_departures_poll = float("-inf")
        self._departures_shown = False
        self._screen_until = float("-inf")

    # --- Hauptschleife ---

    def run(self) -> None:
        log.info("Zeige Home-Screen")
        while True:
            self.tick()
            time.sleep(config.LOOP_INTERVAL)

    def tick(self) -> None:
        point = self.touch.read()
        if point:
            self._on_touch(*point)

        if self.screen is Screen.HOME:
            self._update_home()
        elif self._clock() >= self._screen_until:
            log.info("Timeout – zurück zum Home-Screen")
            self.go_home()
        elif self.screen is Screen.DEPARTURES:
            self._update_departures()

    # --- Navigation ---

    def _on_touch(self, x: int, y: int) -> None:
        self._screen_until = self._clock() + config.SCREEN_TIMEOUT
        if self.screen is Screen.HOME:
            self._open(TILE_SCREENS[screens.tile_at(x)])
        elif screens.is_back_button(x, y):
            log.info("Zurück-Button")
            self.go_home()

    def _open(self, screen: Screen) -> None:
        log.info("Öffne %s", screen.value)
        self.screen = screen
        if screen is Screen.DEPARTURES:
            self._departures_shown = False
            self._next_departures_poll = float("-inf")
        elif screen is Screen.WEATHER:
            self._show(screens.render_weather(self.weather.get()), sleep=True)
        elif screen is Screen.BIKES:
            self._show(screens.render_bikes(nextbike.fetch_stations()), sleep=True)

    def go_home(self) -> None:
        self.screen = Screen.HOME
        self._home_status = None  # erzwingt ein Neuzeichnen (volle Aktualisierung entfernt Geisterbilder)
        self._next_home_poll = float("-inf")

    # --- Ansichten ---

    def _update_home(self) -> None:
        if self._clock() < self._next_home_poll:
            return
        self._next_home_poll = self._clock() + config.HOME_POLL_INTERVAL

        board = transport.fetch_departures()
        stations = nextbike.fetch_stations()
        status = HomeStatus(
            has_disruption=bool(board and board.has_disruption),
            weather=self.weather.get(),
            bike_alert=nextbike.availability_alert(stations, config.NEXTBIKE_HOME_STATION),
            waste_hint=self.waste.pickup_hint(),
        )
        if status == self._home_status:
            log.debug("Keine sichtbaren Änderungen – Display bleibt unangetastet")
            return

        log.info("Home-Screen neu zeichnen: %s", status)
        self._home_status = status
        self._show(
            screens.render_home(status.has_disruption, status.weather, status.bike_alert, status.waste_hint),
            sleep=True,
        )

    def _update_departures(self) -> None:
        if self._clock() < self._next_departures_poll:
            return
        self._next_departures_poll = self._clock() + config.DEPARTURES_REFRESH_INTERVAL

        board = transport.fetch_departures()
        if board is None:
            return
        # Erste Ansicht voll, danach schnelle Teil-Aktualisierung; das Display bleibt dabei wach
        self._show(screens.render_departures(board, datetime.now(self._tz)), partial=self._departures_shown)
        self._departures_shown = True

    def _show(self, image, partial: bool = False, sleep: bool = False) -> None:
        self.display.show(image, partial=partial)
        if sleep:
            self.display.sleep()
        self.touch.flush()
