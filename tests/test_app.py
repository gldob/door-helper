"""Zustandsautomat mit Attrappen für Display, Touch, Uhr und Datenquellen."""

import pytest

import app as app_module
from app import DoorHelperApp, Screen
from sources.nextbike import BikeStation
from sources.transport import DepartureBoard
from sources.weather import Weather


class FakeDisplay:
    def __init__(self):
        self.shown = []  # (Bild, partial)
        self.sleeps = 0

    def show(self, image, partial=False):
        self.shown.append((image, partial))

    def sleep(self):
        self.sleeps += 1


class FakeTouch:
    def __init__(self):
        self.pending = []

    def read(self):
        return self.pending.pop(0) if self.pending else None

    def flush(self):
        pass


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FakeWeatherClient:
    weather = Weather("☼", "Klar", 15, 21)

    def get(self):
        return self.weather


class FakeWaste:
    hint = None

    def pickup_hint(self):
        return self.hint


@pytest.fixture
def sources(monkeypatch):
    state = {"board": DepartureBoard([], has_disruption=False), "stations": [BikeStation(1, "Zuhause", 5)]}
    monkeypatch.setattr(app_module.transport, "fetch_departures", lambda: state["board"])
    monkeypatch.setattr(app_module.nextbike, "fetch_stations", lambda: state["stations"])
    monkeypatch.setattr(app_module.config, "NEXTBIKE_HOME_STATION", 1)
    # Ansichten als einfache Tupel statt Bilder: kein Font nötig
    monkeypatch.setattr(app_module.screens, "render_home", lambda *args: ("home", *args))
    monkeypatch.setattr(app_module.screens, "render_departures", lambda board, now: ("departures", board))
    monkeypatch.setattr(app_module.screens, "render_weather", lambda weather: ("weather", weather))
    monkeypatch.setattr(app_module.screens, "render_bikes", lambda stations: ("bikes", stations))
    return state


@pytest.fixture
def app(sources):
    return DoorHelperApp(FakeDisplay(), FakeTouch(), FakeWeatherClient(), FakeWaste(), clock=FakeClock())


def names(app):
    return [image[0] for image, _ in app.display.shown]


def test_home_redraws_only_on_change(app, sources):
    app.tick()
    assert names(app) == ["home"]
    assert app.display.sleeps == 1

    app._clock.now += 60
    app.tick()
    assert names(app) == ["home"]  # nichts geändert

    sources["stations"] = [BikeStation(1, "Zuhause", 0)]
    app._clock.now += 60
    app.tick()
    assert names(app) == ["home", "home"]
    assert app.display.shown[-1][0][3] == "X"


def test_home_polls_only_every_interval(app, sources):
    app.tick()
    sources["board"] = DepartureBoard([], has_disruption=True)
    app._clock.now += 59
    app.tick()
    assert len(app.display.shown) == 1


def test_departures_full_then_partial_refresh(app):
    app.tick()
    app.touch.pending.append((10, 60))  # linkes Feld
    app.tick()
    assert app.screen is Screen.DEPARTURES
    assert app.display.shown[-1] == (("departures", app_module.transport.fetch_departures()), False)

    app._clock.now += 10
    app.tick()
    assert app.display.shown[-1][1] is True  # Teil-Aktualisierung
    assert app.display.sleeps == 1  # nur nach dem Home-Screen


@pytest.mark.parametrize(("x", "screen", "view"), [(120, Screen.WEATHER, "weather"), (230, Screen.BIKES, "bikes")])
def test_static_screens_sleep_after_drawing(app, x, screen, view):
    app.tick()
    app.touch.pending.append((x, 60))
    app.tick()
    assert app.screen is screen
    assert names(app)[-1] == view
    assert app.display.sleeps == 2


def test_back_button_and_timeout(app):
    app.tick()
    app.touch.pending.append((120, 60))
    app.tick()

    app.touch.pending.append((20, 15))  # Zurück-Button
    app.tick()
    assert app.screen is Screen.HOME
    assert names(app)[-1] == "home"  # sofort neu gezeichnet

    app.touch.pending.append((230, 60))
    app.tick()
    app._clock.now += 59
    app.tick()
    assert app.screen is Screen.BIKES
    app._clock.now += 1
    app.tick()
    assert app.screen is Screen.HOME
