"""HulaDrone -- a friendlier wrapper around the vendor `pyhula` SDK."""
import inspect
from typing import Optional, Tuple

from . import _netfix
from .exceptions import HulaConnectionError
from .led import Led


class HulaDrone:
    """A connection to one HULA drone.

    Usage:
        with HulaDrone("192.168.1.62") as drone:
            drone.takeoff()
            drone.forward(60)
            drone.land()

    Or without the context manager:
        drone = HulaDrone("192.168.1.62")
        drone.connect()
        ...
        drone.land()
    """

    def __init__(self, ip: str):
        self.ip = ip
        _netfix.patch(ip)

        # Imported lazily so `import hula_sdk` doesn't require pyhula to
        # be installed just to use e.g. hula_sdk.Led.
        import pyhula

        self._pyhula = pyhula
        self._api = pyhula.UserApi()
        self.connected = False
        self._flying = False

    # -- connection -------------------------------------------------------

    def connect(self) -> "HulaDrone":
        """Connect to the drone. Raises HulaConnectionError on failure."""
        self.connected = bool(self._api.connect(self.ip))
        if not self.connected:
            raise HulaConnectionError(f"Failed to connect to drone at {self.ip}")
        return self

    def __enter__(self) -> "HulaDrone":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        # Best-effort landing if we're leaving the context while still
        # airborne (e.g. an exception mid-flight) -- there's no explicit
        # disconnect() in the underlying SDK.
        if self.connected and self._flying:
            try:
                self.land()
            except Exception:
                pass

    # -- flight -------------------------------------------------------------

    def takeoff(self, led: Optional[Led] = None) -> None:
        self._api.single_fly_takeoff(self._led_arg(led))
        self._flying = True

    def land(self, led: Optional[Led] = None) -> None:
        self._api.single_fly_touchdown(self._led_arg(led))
        self._flying = False

    def hover(self, seconds: float, led: Optional[Led] = None) -> None:
        self._api.single_fly_hover_flight(seconds, self._led_arg(led))

    def forward(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_forward", distance_cm, speed, led)

    def back(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_back", distance_cm, speed, led)

    def left(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_left", distance_cm, speed, led)

    def right(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_right", distance_cm, speed, led)

    def up(self, height_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_up", height_cm, speed, led)

    def down(self, height_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_down", height_cm, speed, led)

    def turn_left(self, angle_deg: int, led: Optional[Led] = None) -> None:
        self._api.single_fly_turnleft(angle_deg, self._led_arg(led))

    def turn_right(self, angle_deg: int, led: Optional[Led] = None) -> None:
        self._api.single_fly_turnright(angle_deg, self._led_arg(led))

    def square(self, side_cm: int, speed: Optional[int] = None) -> None:
        """Convenience: fly a square of the given side length, ending back
        near the starting point and heading."""
        for leg in (self.forward, self.right, self.back, self.left):
            leg(side_cm, speed)

    # -- telemetry ----------------------------------------------------------

    def battery(self) -> int:
        """Battery percentage, 0-100."""
        return self._api.get_battery()

    def coordinate(self) -> Tuple[int, int, int]:
        """Drone's [x, y, z] position in cm, relative to takeoff."""
        return tuple(self._api.get_coordinate())

    def attitude(self) -> Tuple[int, int, int]:
        """[yaw, pitch, roll] in degrees."""
        return tuple(self._api.get_yaw())

    def plane_id(self) -> int:
        return self._api.get_plane_id()

    # -- escape hatch ---------------------------------------------------------

    @property
    def raw(self):
        """The underlying `pyhula.UserApi` instance, for methods this
        wrapper doesn't cover (camera, QR/tag recognition, laser, etc.)."""
        return self._api

    # -- internals ------------------------------------------------------------

    def _led_arg(self, led: Optional[Led]):
        return led.to_dict() if led is not None else 0

    def _move(self, method_name: str, distance: int, speed: Optional[int], led: Optional[Led]) -> None:
        method = getattr(self._api, method_name)
        led_arg = self._led_arg(led)
        params = inspect.signature(method).parameters
        if "speed" in params:
            method(distance, speed if speed is not None else 100, led_arg)
        elif speed is not None:
            raise TypeError(
                f"This pyhula version's {method_name}() has no speed parameter "
                f"(installed: {self._pyhula.get_version()})"
            )
        else:
            method(distance, led_arg)
