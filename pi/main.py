"""Einstiegspunkt: Logging, Hardware und Datenquellen aufsetzen und die App starten."""

from __future__ import annotations

import logging
import signal
import sys

import config
from app import DoorHelperApp
from sources.waste import WasteCalendar
from sources.weather import WeatherClient

log = logging.getLogger("door-helper")


def _handle_sigterm(signum, frame):
    # systemd beendet den Dienst mit SIGTERM – gleich behandeln wie Strg+C
    raise KeyboardInterrupt


def main() -> int:
    logging.basicConfig(
        level=config.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    signal.signal(signal.SIGTERM, _handle_sigterm)
    for warning in config.WARNINGS:
        log.warning(warning)

    log.info("Starte door-helper")
    # Hardware-Module erst hier importieren: sie greifen beim Import auf SPI/I2C/GPIO zu
    from ui.epaper import EInkDisplay
    from ui.touch import TouchInput

    try:
        display = EInkDisplay()  # vor TouchInput, siehe EInkDisplay.__init__
        touch = TouchInput()
    except Exception:
        log.exception("Display konnte nicht initialisiert werden")
        return 1

    app = DoorHelperApp(display, touch, WeatherClient(), WasteCalendar.from_config())
    try:
        app.run()
    except KeyboardInterrupt:
        log.info("Programm wird beendet")
    finally:
        display.close()
        log.info("Display freigegeben")
    return 0


if __name__ == "__main__":
    sys.exit(main())
