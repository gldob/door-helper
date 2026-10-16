"""
Zeichnet die einzelnen Ansichten als 1-Bit-Bilder (250x122, Querformat).
Reine Funktionen ohne Hardware-Zugriff – testbar und als Vorschau renderbar.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from functools import cache

from PIL import Image, ImageDraw, ImageFont

import config
from sources.nextbike import BikeStation
from sources.transport import DepartureBoard
from sources.weather import Weather

WIDTH, HEIGHT = 250, 122
BLACK, WHITE = 0, 255

# Home-Screen: drei gleich breite Felder
COLUMN_WIDTH = WIDTH // 3
WASTE_BAR_HEIGHT = 22

# Zurück-Button oben links (Trefferfläche etwas grösser als die Zeichnung)
BACK_BUTTON_BOX = (5, 5, 85, 30)
BACK_BUTTON_HITBOX = (0, 0, 90, 40)

DEPARTURE_ROW_HEIGHT = 18
COUNTDOWN_THRESHOLD_SECONDS = 600  # darunter "In: 3m 12s", darüber die Uhrzeit


class Tile(Enum):
    DEPARTURES = 0
    WEATHER = 1
    BIKES = 2


TILE_LABELS = {Tile.DEPARTURES: "Abfahrten", Tile.WEATHER: "Wetter", Tile.BIKES: "Nextbike"}


@cache
def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(config.FONT_PATH, size)


def tile_at(x: int) -> Tile:
    return Tile(min(x // COLUMN_WIDTH, len(Tile) - 1))


def is_back_button(x: int, y: int) -> bool:
    left, top, right, bottom = BACK_BUTTON_HITBOX
    return left <= x < right and top <= y < bottom


def _canvas(back_button: bool = False) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("1", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)
    if back_button:
        draw.rectangle(BACK_BUTTON_BOX, outline=BLACK)
        draw.text((BACK_BUTTON_BOX[0] + 5, BACK_BUTTON_BOX[1] + 5), "< Zurück", font=font(12), fill=BLACK)
    return image, draw


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, sizes: tuple[int, ...]):
    """Erste Schriftgrösse, in die der Text passt; sonst mit der kleinsten kürzen."""
    for size in sizes:
        if draw.textlength(text, font=font(size)) <= max_width:
            return text, font(size)
    smallest = font(sizes[-1])
    while text and draw.textlength(text + "…", font=smallest) > max_width:
        text = text[:-1]
    return text.rstrip(" ,") + "…", smallest


def blank() -> Image.Image:
    return _canvas()[0]


def render_home(
    has_disruption: bool,
    weather: Weather | None,
    bike_alert: str | None,
    waste_hint: str | None,
) -> Image.Image:
    image, draw = _canvas()
    bar_top = HEIGHT - WASTE_BAR_HEIGHT if waste_hint else HEIGHT

    for i in (1, 2):
        draw.line([(i * COLUMN_WIDTH, 0), (i * COLUMN_WIDTH, bar_top)], fill=BLACK, width=2)

    def center(tile: Tile) -> int:
        return tile.value * COLUMN_WIDTH + COLUMN_WIDTH // 2

    for tile, label in TILE_LABELS.items():
        draw.text((center(tile), 10), label, font=font(14), fill=BLACK, anchor="mt")

    if has_disruption:
        draw.text((center(Tile.DEPARTURES), 68), "!", font=font(36), fill=BLACK, anchor="mm")

    if weather:
        draw.text((center(Tile.WEATHER), 55), weather.icon, font=font(30), fill=BLACK, anchor="mm")
        draw.text((center(Tile.WEATHER), 82), f"Max: {weather.max_temp}°C", font=font(12), fill=BLACK, anchor="mm")

    if bike_alert:
        draw.text((center(Tile.BIKES), 68), bike_alert, font=font(36), fill=BLACK, anchor="mm")

    # Abfuhr-Hinweis: invertierte Leiste am unteren Rand
    if waste_hint:
        draw.rectangle([(0, bar_top), (WIDTH, HEIGHT)], fill=BLACK)
        text, text_font = fit_text(draw, waste_hint, WIDTH - 10, (12, 10))
        draw.text((WIDTH // 2, bar_top + WASTE_BAR_HEIGHT // 2), text, font=text_font, fill=WHITE, anchor="mm")

    return image


def _format_departure(seconds_left: float, departure_time: datetime) -> str:
    if seconds_left < COUNTDOWN_THRESHOLD_SECONDS:
        minutes, seconds = divmod(int(seconds_left), 60)
        return f"In: {minutes}m {seconds}s"
    return departure_time.strftime("%H:%M")


def render_departures(board: DepartureBoard, now: datetime) -> Image.Image:
    image, draw = _canvas(back_button=True)
    if board.has_disruption:
        draw.text((WIDTH - 5, 10), "! Störung", font=font(12), fill=BLACK, anchor="ra")

    y = 32
    for departure in board.departures:
        if y > HEIGHT - DEPARTURE_ROW_HEIGHT:
            break
        seconds_left = departure.time_until(now).total_seconds()
        if seconds_left < 0:
            continue
        time_text = _format_departure(seconds_left, departure.time)
        time_left = WIDTH - 5 - draw.textlength(time_text, font=font(12))
        line, line_font = fit_text(draw, departure.line, 30, (12, 10))
        destination, destination_font = fit_text(draw, departure.destination, int(time_left) - 38 - 6, (12, 10))
        draw.text((5, y), line, font=line_font, fill=BLACK)
        draw.text((38, y), destination, font=destination_font, fill=BLACK)
        draw.text((WIDTH - 5, y), time_text, font=font(12), fill=BLACK, anchor="ra")
        y += DEPARTURE_ROW_HEIGHT

    if y == 32:
        draw.text((10, 50), "Keine Abfahrten", font=font(12), fill=BLACK)
    return image


def render_weather(weather: Weather | None) -> Image.Image:
    image, draw = _canvas(back_button=True)
    draw.text((100, 10), "Wetter", font=font(16), fill=BLACK)
    if weather is None:
        draw.text((10, 50), "Keine Daten", font=font(12), fill=BLACK)
        return image

    draw.text((10, 50), f"{weather.icon} Aktuell: {weather.current_temp}°C", font=font(16), fill=BLACK)
    draw.text((10, 80), f"Prognose: {weather.description}", font=font(12), fill=BLACK)
    draw.text((10, 100), f"Tagesmaximum: {weather.max_temp}°C", font=font(12), fill=BLACK)
    return image


def render_bikes(stations: list[BikeStation] | None) -> Image.Image:
    image, draw = _canvas(back_button=True)
    draw.text((100, 10), "Nextbike", font=font(16), fill=BLACK)
    if not stations:
        draw.text((10, 50), "Keine Daten", font=font(12), fill=BLACK)
        return image

    y = 50
    for station in stations:
        draw.text((10, y), station.name, font=font(12), fill=BLACK)
        draw.text((WIDTH - 20, y), str(station.bikes), font=font(12), fill=BLACK, anchor="ra")
        y += 25
    return image
