"""hula_sdk -- a working Python SDK for the HighGreat HULA educational drone.

Wraps the vendor's `pyhula` package, patching two undocumented Windows
socket bugs that otherwise make `connect()` fail (see `hula_sdk._netfix`
for details), and exposes a friendlier, typed API on top of it.
"""
from .client import HulaDrone
from .constants import FlipDirection, QrSensor
from .exceptions import HulaConnectionError, HulaError
from .led import Led, LedMode

__all__ = [
    "HulaDrone",
    "HulaError",
    "HulaConnectionError",
    "Led",
    "LedMode",
    "FlipDirection",
    "QrSensor",
]
__version__ = "0.1.0"
