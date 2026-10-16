import pytest
import requests

from sources import weather
from sources.weather import Weather, WeatherClient

FORECAST = {
    "current": {"temperature_2m": 14.6, "weather_code": 0, "is_day": 0},
    "daily": {"temperature_2m_max": [21.4]},
}


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_parse_forecast_uses_night_icon():
    assert weather.parse_forecast(FORECAST) == Weather(icon="☾", description="Klar", current_temp=15, max_temp=21)


def test_parse_forecast_unknown_code():
    data = {**FORECAST, "current": {"temperature_2m": 1, "weather_code": 1234}}
    assert weather.parse_forecast(data).icon == "?"


@pytest.fixture
def requests_get(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        result = fake_get.result
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)

    fake_get.result = FORECAST
    fake_get.calls = calls
    monkeypatch.setattr(weather.requests, "get", fake_get)
    return fake_get


def test_client_caches(requests_get):
    clock = FakeClock()
    client = WeatherClient(cache_seconds=1800, clock=clock)

    first = client.get()
    clock.now = 1799
    assert client.get() is first
    assert len(requests_get.calls) == 1

    clock.now = 1800
    client.get()
    assert len(requests_get.calls) == 2


def test_client_keeps_stale_data_on_error(requests_get):
    clock = FakeClock()
    client = WeatherClient(cache_seconds=60, clock=clock)
    cached = client.get()

    clock.now = 120
    requests_get.result = requests.ConnectionError("offline")
    assert client.get() == cached


def test_client_returns_none_without_data(requests_get):
    requests_get.result = requests.ConnectionError("offline")
    assert WeatherClient().get() is None
