from enum import IntEnum


class FlipDirection(IntEnum):
    """Direction for HulaDrone.flip() (pyhula's single_fly_somersault)."""

    FORWARD = 0
    BACK = 1
    LEFT = 2
    RIGHT = 3


class QrSensor(IntEnum):
    """Which sensor to use for QR alignment/recognition -- optical flow
    (downward sensor) or the front camera."""

    OPTICAL_FLOW = 0
    CAMERA = 1
