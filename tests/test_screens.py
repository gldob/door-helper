from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import config
from sources.nextbike import BikeStation
from sources.transport import Departure, DepartureBoard
from sources.weather import Weather
from ui import screens
from ui.screens import Tile

pytestmark = pytest.mark.skipif(not Path(config.FONT_PATH).exists(), reason="Schrift FONT_PATH nicht vorhanden")

TZ = ZoneInfo("Europe/Zurich")
NOW = datetime(2026, 10, 19, 7, 0, tzinfo=TZ)


def _assert_valid(image):
    assert image.size == (screens.WIDTH, screens.HEIGHT)
    assert image.mode == "1"


def test_render_home_variants():
    weather = Weather("☔", "Regen", 12, 14)
    _assert_valid(screens.render_home(True, weather, "!", "Morgen: Grüngut, Kehricht, Alteisen/Metall"))
    _assert_valid(screens.render_home(False, None, None, None))


def test_render_departures_and_details():
    board = DepartureBoard(
        [
            Departure("1", "Kriens", NOW + timedelta(minutes=3), realtime=True),
            Departure("IR 2600", "Sehr lange Destination mit Umsteigeort", NOW + timedelta(minutes=40), False),
        ],
        has_disruption=True,
    )
    _assert_valid(screens.render_departures(board, NOW))
    _assert_valid(screens.render_departures(DepartureBoard(), NOW))
    _assert_valid(screens.render_weather(Weather("☼", "Klar", 15, 21)))
    _assert_valid(screens.render_weather(None))
    _assert_valid(screens.render_bikes([BikeStation(1, "Zuhause", 3)]))
    _assert_valid(screens.render_bikes(None))


def test_format_departure():
    assert screens._format_departure(192, NOW) == "In: 3m 12s"
    assert screens._format_departure(600, NOW) == "07:00"


@pytest.mark.parametrize(
    ("x", "tile"), [(0, Tile.DEPARTURES), (82, Tile.DEPARTURES), (83, Tile.WEATHER), (249, Tile.BIKES)]
)
def test_tile_at(x, tile):
    assert screens.tile_at(x) is tile


def test_back_button_hitbox():
    assert screens.is_back_button(20, 15)
    assert not screens.is_back_button(120, 15)


def test_fit_text_truncates():
    image = screens.blank()
    draw = screens.ImageDraw.Draw(image)
    text, _ = screens.fit_text(draw, "x" * 200, 100, (12, 10))
    assert text.endswith("…")
    assert draw.textlength(text, font=screens.font(10)) <= 100
