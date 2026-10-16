from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sources import transport

TZ = ZoneInfo("Europe/Zurich")
NOW = datetime(2026, 10, 19, 7, 0, tzinfo=TZ)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(line: str, destination: str, timetabled: datetime, estimated: datetime | None = None) -> str:
    estimated_xml = f"<EstimatedTime>{_iso(estimated)}</EstimatedTime>" if estimated else ""
    return f"""
    <StopEventResult><StopEvent><ThisCall><CallAtStop><ServiceDeparture>
        <TimetabledTime>{_iso(timetabled)}</TimetabledTime>{estimated_xml}
    </ServiceDeparture></CallAtStop></ThisCall><Service>
        <PublishedServiceName><Text>{line}</Text></PublishedServiceName>
        <DestinationText><Text>{destination}</Text></DestinationText>
    </Service></StopEvent></StopEventResult>"""


def _response(*events: str, disruption: bool = False) -> bytes:
    situation = "<PtSituation><Summary>Störung</Summary></PtSituation>" if disruption else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <OJP xmlns="http://www.vdv.de/ojp" xmlns:siri="http://www.siri.org.uk/siri" version="2.0">
      <OJPResponse><siri:ServiceDelivery><OJPStopEventDelivery>
        {situation}{"".join(events)}
      </OJPStopEventDelivery></siri:ServiceDelivery></OJPResponse>
    </OJP>""".encode()


def test_parse_sorts_by_time_and_prefers_realtime():
    content = _response(
        _event("8", "Biregghof", NOW + timedelta(minutes=5), estimated=NOW + timedelta(minutes=7)),
        _event("1", "Kriens", NOW + timedelta(minutes=6)),
    )
    board = transport.parse_response(content, NOW)

    assert [(d.line, d.realtime) for d in board.departures] == [("1", False), ("8", True)]
    assert board.departures[1].time == NOW + timedelta(minutes=7)
    assert board.departures[0].time.tzinfo == TZ
    assert board.has_disruption is False


def test_parse_drops_past_departures_and_detects_disruption():
    content = _response(
        _event("X", "Vergangen", NOW - timedelta(minutes=1)),
        _event("2", "Emmenbrücke", NOW + timedelta(minutes=1)),
        disruption=True,
    )
    board = transport.parse_response(content, NOW)

    assert [d.line for d in board.departures] == ["2"]
    assert board.has_disruption is True


def test_parse_time_handles_fractional_seconds():
    parsed = transport._parse_time("2026-10-19T05:00:00.1234567Z", TZ)
    assert parsed == datetime(2026, 10, 19, 7, 0, tzinfo=TZ)


def test_build_request_escapes_stop_name(monkeypatch):
    monkeypatch.setattr(transport.config, "OJP_STOP_NAME", "Bahnhof <Süd> & Co")
    monkeypatch.setattr(transport.config, "OJP_STOP_POINT_REF", "8503000")
    xml = transport.build_request(datetime(2026, 10, 19, 5, 0, tzinfo=timezone.utc))

    assert "Bahnhof &lt;Süd&gt; &amp; Co" in xml
    assert "<siri:StopPointRef>8503000</siri:StopPointRef>" in xml
    assert "<DepArrTime>2026-10-19T05:00:00Z</DepArrTime>" in xml
