import pytest

from sources.nextbike import BikeStation, availability_alert, parse_feed

FEED = {
    "countries": [
        {
            "cities": [
                {"places": [{"uid": 2, "bikes_available_to_rent": 4}, {"uid": 99, "bikes_available_to_rent": 7}]},
                {"places": [{"uid": 1, "bikes_available_to_rent": 0}]},
            ]
        }
    ]
}


def test_parse_feed_keeps_configured_order_and_names():
    stations = parse_feed(FEED, {1: "Zuhause", 2: "Bahnhof", 3: "Fehlt"})
    assert stations == [BikeStation(1, "Zuhause", 0), BikeStation(2, "Bahnhof", 4)]


@pytest.mark.parametrize(("bikes", "expected"), [(0, "X"), (1, "!"), (2, "!"), (3, None)])
def test_availability_alert(bikes, expected):
    assert availability_alert([BikeStation(1, "Zuhause", bikes)], home_uid=1) == expected


def test_availability_alert_without_data():
    assert availability_alert(None, home_uid=1) is None
    assert availability_alert([BikeStation(2, "Bahnhof", 0)], home_uid=1) is None
