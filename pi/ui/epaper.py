"""
Ansteuerung des 2.13" E-Ink-Panels (epd2in13_V4) mit voller und teilweiser Aktualisierung.

- Volle Aktualisierung: flackert ~2 s, entfernt Geisterbilder. Das Bild wird in beide
  Bildspeicher des Controllers geschrieben und dient so als Basis für Teil-Aktualisierungen.
- Teil-Aktualisierung: ~0.5 s ohne Flackern, setzt eine gültige Basis voraus. Nach dem
  Tiefschlaf ist diese nicht mehr gesichert, deshalb folgt danach immer eine volle.
"""

from __future__ import annotations

import logging

from PIL import Image

import config
from ui import screens
from ui.waveshare import epd2in13_V4

log = logging.getLogger(__name__)

# Register des Displaycontrollers (SSD1680)
_WRITE_RAM_NEW = 0x24
_WRITE_RAM_OLD = 0x26


class EInkDisplay:
    def __init__(self, max_partial_refreshes: int = config.MAX_PARTIAL_REFRESHES):
        # Muss vor TouchInput erzeugt werden: der Konstruktor setzt die
        # I2C-Adresse des Touch-Controllers (epdconfig.address = 0x14).
        self._epd = epd2in13_V4.EPD()
        self._max_partial = max_partial_refreshes
        self._partial_count = 0
        self._has_base = False
        self._awake = False
        self.show(screens.blank())

    def show(self, image: Image.Image, partial: bool = False) -> None:
        """Zeigt ein Bild an. partial=True nutzt die schnelle Teil-Aktualisierung, wenn möglich."""
        buffer = self._epd.getbuffer(image)
        if partial and self._has_base and self._partial_count < self._max_partial:
            self._epd.displayPartial_Wait(buffer)
            self._partial_count += 1
        else:
            self._full_refresh(buffer)
        self._awake = True

    def _full_refresh(self, buffer) -> None:
        self._epd.init(self._epd.FULL_UPDATE)
        # Wie displayPartBaseImage(), aber als Block statt Byte für Byte übertragen
        self._epd.send_command(_WRITE_RAM_NEW)
        self._epd.send_data2(buffer)
        self._epd.send_command(_WRITE_RAM_OLD)
        self._epd.send_data2(buffer)
        self._epd.TurnOnDisplay()
        self._has_base = True
        self._partial_count = 0

    def sleep(self) -> None:
        """Tiefschlaf zum Schutz des Panels; der Bildinhalt bleibt sichtbar."""
        if self._awake:
            self._epd.sleep()
            self._awake = False
            self._has_base = False

    def close(self) -> None:
        """Display leeren, in Tiefschlaf versetzen und SPI/I2C/GPIO freigeben."""
        try:
            self.show(screens.blank())
            self.sleep()
        finally:
            self._epd.Dev_exit()
