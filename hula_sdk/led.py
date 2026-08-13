from enum import IntEnum
from typing import NamedTuple


class LedMode(IntEnum):
    """LED display modes accepted by the drone's `led` parameters."""

    SOLID = 1
    OFF = 2
    RGB_CYCLE = 4
    RAINBOW = 16
    FLASHING = 32
    BREATHING = 64


class Led(NamedTuple):
    """An LED color/mode setting, as pyhula's `led` parameters expect it.

    Converts to the `{'r':.., 'g':.., 'b':.., 'mode':..}` dict the
    underlying SDK takes.
    """

    r: int = 0
    g: int = 0
    b: int = 0
    mode: "LedMode" = LedMode.SOLID

    def to_dict(self):
        return {"r": self.r, "g": self.g, "b": self.b, "mode": int(self.mode)}
