"""Bindet die Waveshare-Bibliothek (Touch_e-Paper_HAT) aus WAVESHARE_LIB_PATH ein."""

import sys

import config

if config.WAVESHARE_LIB_PATH not in sys.path:
    sys.path.append(config.WAVESHARE_LIB_PATH)

from TP_lib import epd2in13_V4, gt1151  # noqa: E402

__all__ = ["epd2in13_V4", "gt1151"]
