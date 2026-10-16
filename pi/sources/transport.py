"""Abfahrten und Störungen einer Haltestelle via OJP 2.0 (opentransportdata.swiss)."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import requests

import config

log = logging.getLogger(__name__)

XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<OJP xmlns="http://www.vdv.de/ojp" xmlns:siri="http://www.siri.org.uk/siri" version="2.0">
  <OJPRequest>
    <siri:ServiceRequest>
      <siri:RequestTimestamp>{timestamp}</siri:RequestTimestamp>
      <siri:RequestorRef>{requestor_ref}</siri:RequestorRef>
      <OJPStopEventRequest>
        <siri:RequestTimestamp>{timestamp}</siri:RequestTimestamp>
        <siri:MessageIdentifier>SER-1a2</siri:MessageIdentifier>
        <Location>
          <PlaceRef>
            <siri:StopPointRef>{stop_point_ref}</siri:StopPointRef>
            <Name>
              <Text>{stop_name}</Text>
            </Name>
          </PlaceRef>
          <DepArrTime>{departure_time}</DepArrTime>
        </Location>
        <Params>
          <NumberOfResults>{number_of_results}</NumberOfResults>
          <StopEventType>departure</StopEventType>
          <IncludeRealtimeData>true</IncludeRealtimeData>
        </Params>
      </OJPStopEventRequest>
    </siri:ServiceRequest>
  </OJPRequest>
</OJP>"""


@dataclass(frozen=True)
class Departure:
    line: str
    destination: str
    time: datetime  # zeitzonenbehaftet
    realtime: bool  # True = Echtzeitprognose, False = Fahrplanzeit

    def time_until(self, now: datetime) -> timedelta:
        return self.time - now


@dataclass(frozen=True)
class DepartureBoard:
    departures: list[Departure] = field(default_factory=list)
    has_disruption: bool = False


def build_request(now_utc: datetime) -> str:
    return XML_TEMPLATE.format(
        # UTC ISO-Format mit Z gemäss OJP 2.0
        timestamp=now_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        departure_time=now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        requestor_ref=escape(config.OJP_REQUESTOR_REF),
        stop_point_ref=escape(config.OJP_STOP_POINT_REF or ""),
        stop_name=escape(config.OJP_STOP_NAME),
        number_of_results=config.OJP_NUMBER_OF_RESULTS,
    )


def fetch_departures() -> DepartureBoard | None:
    """Aktuelle Abfahrten inkl. Störungsstatus, oder None bei einem Fehler."""
    headers = {
        "Content-Type": "application/xml; charset=utf-8",
        "Authorization": f"Bearer {config.OJP_API_KEY}",
    }
    body = build_request(datetime.now(timezone.utc)).encode("utf-8")
    try:
        response = requests.post(config.OJP_API_URL, headers=headers, data=body, timeout=config.HTTP_TIMEOUT)
        response.raise_for_status()
        return parse_response(response.content, datetime.now(ZoneInfo(config.TIMEZONE)))
    except requests.RequestException as e:
        log.warning("ÖV-API nicht erreichbar: %s", e)
    except ET.ParseError as e:
        log.warning("Ungültige Antwort der ÖV-API: %s", e)
    return None


def _parse_time(value: str, tz: ZoneInfo) -> datetime:
    # Python 3.9 versteht weder "Z" noch Sekundenbruchteile beliebiger Länge
    value = re.sub(r"\.\d+", "", value.strip()).replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(tz)


def _text(node: ET.Element, path: str) -> str:
    element = node.find(f"{path}/Text")
    if element is None:
        element = node.find(path)
    return element.text if element is not None and element.text else "Unbekannt"


def parse_response(content: bytes, now: datetime) -> DepartureBoard:
    """Parst eine OJP-StopEvent-Antwort. Vergangene Abfahrten werden verworfen."""
    root = ET.fromstring(content)
    # XML-Namensräume entfernen für einfacheres Parsen
    for element in root.iter():
        if "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]

    departures = []
    for event in root.iter("StopEventResult"):
        estimated = event.find(".//ServiceDeparture/EstimatedTime")
        timetabled = event.find(".//ServiceDeparture/TimetabledTime")
        time_element = estimated if estimated is not None else timetabled
        if time_element is None or not time_element.text:
            continue

        departure = Departure(
            line=_text(event, ".//PublishedServiceName"),
            destination=_text(event, ".//DestinationText"),
            time=_parse_time(time_element.text, now.tzinfo),
            realtime=estimated is not None,
        )
        if departure.time >= now:
            departures.append(departure)

    departures.sort(key=lambda d: d.time)
    has_disruption = root.find(".//PtSituation") is not None
    return DepartureBoard(departures, has_disruption)
