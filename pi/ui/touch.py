"""Touch-Eingabe über den GT1151-Controller, umgerechnet auf die Querformat-Koordinaten der Ansichten."""

from __future__ import annotations

import logging
import time

import config
from ui import screens
from ui.waveshare import gt1151

log = logging.getLogger(__name__)


class TouchInput:
    def __init__(self, debounce: float = config.TOUCH_DEBOUNCE, clock=time.monotonic):
        self._gt = gt1151.GT1151()
        self._dev = gt1151.GT_Development()
        self._old = gt1151.GT_Development()
        self._gt.GT_Init()
        self._debounce = debounce
        self._clock = clock
        self._last_touch = float("-inf")

    def _scan(self) -> tuple[int, int] | None:
        """Rohkoordinaten (Hochformat) einer neuen Berührung, sonst None."""
        if self._gt.digital_read(self._gt.INT) != 0:
            return None
        self._dev.Touch = 1
        self._gt.GT_Scan(self._dev, self._old)
        if (self._old.X[0], self._old.Y[0], self._old.S[0]) == (self._dev.X[0], self._dev.Y[0], self._dev.S[0]):
            return None
        if not self._dev.TouchpointFlag:
            return None
        self._dev.TouchpointFlag = 0
        return self._dev.X[0], self._dev.Y[0]

    def read(self) -> tuple[int, int] | None:
        """Entprellte Berührung als (x, y) im Querformat, sonst None."""
        raw = self._scan()
        if raw is None:
            return None
        now = self._clock()
        if now - self._last_touch < self._debounce:
            return None
        self._last_touch = now
        raw_x, raw_y = raw
        point = (screens.WIDTH - raw_y, raw_x)
        log.debug("Touch bei %s", point)
        return point

    def flush(self) -> None:
        """Verwirft Berührungen, die während einer Display-Aktualisierung aufgelaufen sind."""
        self._scan()
        self._scan()
        self._last_touch = self._clock()
