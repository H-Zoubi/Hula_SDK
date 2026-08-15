"""HulaDrone -- a friendlier wrapper around the vendor `pyhula` SDK."""
import functools
import inspect
import warnings
from typing import Optional, Tuple

from . import _netfix
from .constants import FlipDirection, QrSensor
from .exceptions import HulaConnectionError
from .led import Led

_warned_methods = set()


def _untested(func):
    """Marks a wrapper method as implemented against the documented/actual
    pyhula signature but never exercised against real hardware. Calling it
    emits a UserWarning the first time, per method, per process -- see the
    "Tested vs untested" table in the README.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if func.__qualname__ not in _warned_methods:
            _warned_methods.add(func.__qualname__)
            warnings.warn(
                f"{func.__qualname__}() has not been verified against real "
                f"hardware yet -- see the README's 'Tested vs untested' table. "
                f"It matches the documented/installed pyhula signature, but "
                f"use with extra caution.",
                UserWarning,
                stacklevel=2,
            )
        return func(*args, **kwargs)

    return wrapper


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

    Methods below are grouped into: tested against real hardware, wrapped
    but untested (marked with @_untested -- they warn on first call), and
    telemetry (mostly untested too, marked accordingly). See the README
    for the full breakdown and for `.raw` -- the one pyhula method that
    isn't wrapped at all, because its own source references an undefined
    `type` builtin instead of a real parameter (a bug in pyhula itself,
    not something to paper over here).
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
        """Connect to the drone. Raises HulaConnectionError on failure.

        Note: pyhula >=1.1.x hard-exits the whole process (not a
        catchable error) if the drone reports under 10% battery -- see
        the README's "Known limitations".
        """
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

    # -- flight: tested -----------------------------------------------------

    def takeoff(self, led: Optional[Led] = None) -> None:
        self._api.single_fly_takeoff(self._led_arg(led))
        self._flying = True

    def land(self, led: Optional[Led] = None) -> None:
        self._api.single_fly_touchdown(self._led_arg(led))
        self._flying = False

    def forward(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_forward", distance_cm, speed, led)

    def back(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_back", distance_cm, speed, led)

    def left(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_left", distance_cm, speed, led)

    def right(self, distance_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_right", distance_cm, speed, led)

    def square(self, side_cm: int, speed: Optional[int] = None) -> None:
        """Convenience: fly a square of the given side length, ending back
        near the starting point and heading."""
        for leg in (self.forward, self.right, self.back, self.left):
            leg(side_cm, speed)

    # -- flight: tested -----------------------------------------------------

    def hover(self, seconds: float, led: Optional[Led] = None) -> None:
        self._api.single_fly_hover_flight(seconds, self._led_arg(led))

    def up(self, height_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_up", height_cm, speed, led)

    def down(self, height_cm: int, speed: Optional[int] = None, led: Optional[Led] = None) -> None:
        self._move("single_fly_down", height_cm, speed, led)

    def turn_left(self, angle_deg: int, led: Optional[Led] = None) -> None:
        self._api.single_fly_turnleft(angle_deg, self._led_arg(led))

    def turn_right(self, angle_deg: int, led: Optional[Led] = None) -> None:
        self._api.single_fly_turnright(angle_deg, self._led_arg(led))

    def bounce(self, frequency: int, height_cm: int, led: Optional[Led] = None) -> None:
        self._api.single_fly_bounce(frequency, height_cm, self._led_arg(led))

    def fly_to(self, x_cm: int, y_cm: int, z_cm: int, led: Optional[Led] = None) -> None:
        """Straight-line flight to relative coordinates (x, y, z) in cm."""
        self._api.single_fly_straight_flight(x_cm, y_cm, z_cm, self._led_arg(led))

    def circle(self, radius_cm: int, led: Optional[Led] = None) -> None:
        """Fly a circle of the given radius. Positive = counterclockwise,
        negative = clockwise."""
        self._api.single_fly_radius_around(radius_cm, self._led_arg(led))

    def spin(self, num_rotations: int, led: Optional[Led] = None) -> None:
        """Rotate in place. Positive = counterclockwise, negative =
        clockwise."""
        self._api.single_fly_autogyration360(num_rotations, self._led_arg(led))

    def flip(self, direction: FlipDirection, led: Optional[Led] = None) -> None:
        self._api.single_fly_somersault(int(direction), self._led_arg(led))

    def curve_to(
        self,
        x_cm: int,
        y_cm: int,
        z_cm: int,
        counterclockwise: bool = True,
        led: Optional[Led] = None,
    ) -> None:
        """Curved flight to relative coordinates. x: left(-)/right(+) of
        body, y: back(-)/front(+) of body, z: down(-)/up(+)."""
        self._api.single_fly_curvilinearFlight(x_cm, y_cm, z_cm, counterclockwise, self._led_arg(led))

    # -- sensing: tested (except follow_line) ------------------------------------

    def set_obstacle_avoidance(self, enabled: bool) -> None:
        self._api.single_fly_barrier_aircraft(enabled)

    @_untested
    def follow_line(self, distance_cm: int, line_color: int = 0):
        """Line-following. line_color: 0 = black, 255 = white. Returns 0
        on failure, 1 on success, 2 on success but hit an intersection."""
        return self._api.single_fly_Line_walking(0, distance_cm, line_color)

    def identify_tag(self, mode: int):
        """mode: 0-9 for digit tags, 10-13 for arrows (left/right/up/down),
        20 to end the task, 65-90 (ASCII) for uppercase letter tags.
        Returns a result with the tag's x/y/z/angle relative to the drone."""
        return self._api.single_fly_AiIdentifies(mode)

    def align_to_qrcode(self, qr_id: int, sensor: QrSensor = QrSensor.CAMERA):
        return self._api.single_fly_Qrcode_align(int(sensor), qr_id)

    def recognize_qrcode(self, qr_id: int, sensor: QrSensor = QrSensor.CAMERA):
        return self._api.single_fly_recognition_Qrcode(int(sensor), qr_id)

    def track_qrcode(self, qr_id: int, seconds: float):
        return self._api.single_fly_track_Qrcode(qr_id, seconds)

    def read_color(self, mode: int = 1):
        """Reads the color of one frame from the current video stream.
        Returns r/g/b plus a success flag."""
        return self._api.single_fly_getColor(mode)

    # -- lighting: tested -------------------------------------------------------

    def set_light(self, led: Led, seconds: float) -> bool:
        """Sets LED color/mode without blocking flight. Unlike the `led`
        parameters elsewhere, this takes a duration.

        pyhula's single_fly_lamplight has an undocumented argument-order bug:
        confirmed against real hardware that asking for red produces green
        and asking for green produces blue -- i.e. the (r, g, b) slots it
        takes aren't r, g, b. Working from those two swaps: what we'd pass
        as r drives the physical green channel, and what we'd pass as g
        drives physical blue, so by elimination b must drive physical red.
        Passing (g, b, r) compensates for that so callers still get the
        color they actually asked for."""
        return self._api.single_fly_lamplight(led.g, led.b, led.r, seconds, int(led.mode))

    # -- camera / video: wrapped, and *attempted* against hardware, but not
    # verified working -- see the README's "Known limitations" for what
    # happened. Still marked @_untested deliberately: something visibly
    # went wrong, so these don't get to claim "tested" just because they
    # didn't raise a Python exception.

    @_untested
    def open_video_window(self) -> None:
        """Opens the video stream window. Call set_video_stream(True) first."""
        self._api.single_fly_flip_rtp()

    @_untested
    def set_video_stream(self, enabled: bool) -> None:
        self._api.Plane_cmd_swith_rtp(0 if enabled else 1)

    @_untested
    def set_recording(self, enabled: bool) -> None:
        self._api.Plane_cmd_switch_video(0 if enabled else 1)

    @_untested
    def take_photo(self) -> None:
        """Requires the video stream to be enabled first."""
        self._api.Plane_fly_take_photo()

    @_untested
    def set_camera_angle(self, direction: int, angle: int) -> None:
        """direction: 0=up, 1=down (absolute), 2/3=algorithm-controlled,
        4=calibrate, 5/6=block up/down (relative). angle: 0-90."""
        self._api.Plane_cmd_camera_angle(direction, angle)

    # -- attachments / QR / laser: wrapped, untested ---------------------------

    @_untested
    def set_qr_positioning(self, enabled: bool) -> None:
        self._api.Plane_cmd_switch_QR(0 if enabled else 1)

    @_untested
    def fire_laser(self, laser_type: int, frequency: int = 10, ammo: int = 100) -> None:
        """laser_type: 0=single shot, 1=burst, 2=start laser receiving,
        3=stop laser receiving, 4=continuous burst (no ammo limit),
        5=stop emitting. frequency: shots/sec, 1-14. ammo: 1-255."""
        self._api.plane_fly_generating(laser_type, frequency, ammo)

    @_untested
    def laser_hit(self) -> bool:
        return self._api.plane_fly_laser_receiving()

    @_untested
    def set_electromagnet(self, attract: bool) -> None:
        self._api.Plane_cmd_electromagnet(2 if attract else 3)

    @_untested
    def set_clamp(self, is_open: bool, angle: int = 0) -> None:
        self._api.Plane_cmd_clamp(1 if is_open else 0, angle)

    @_untested
    def arm(self) -> None:
        """Starts the propellers spinning at low speed (does not take off)."""
        self._api.plane_fly_arm()

    @_untested
    def disarm(self) -> None:
        self._api.plane_fly_disarm()

    # -- telemetry: tested --------------------------------------------------

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

    def obstacles(self) -> dict:
        """{'forward': bool, 'back': bool, 'left': bool, 'right': bool} --
        True means an obstacle is present in that direction."""
        return self._api.Plane_getBarrier()

    def acceleration(self) -> Tuple[int, int, int]:
        """[x, y, z] acceleration."""
        return tuple(self._api.get_accelerated_speed())

    def velocity(self) -> Tuple[int, int, int]:
        """[x, y, z] body speed."""
        return tuple(self._api.get_plane_speed())

    def tof_height(self) -> int:
        """Time-of-flight sensor height reading."""
        return self._api.get_plane_distance()

    # -- escape hatch ---------------------------------------------------------

    @property
    def raw(self):
        """The underlying `pyhula.UserApi` instance, for anything this
        wrapper doesn't cover -- including `Plane_fly_line_walking()`,
        which is deliberately NOT wrapped above: its own source in pyhula
        references a bare `type` (the Python builtin) instead of an
        actual parameter, so it's broken in the vendor SDK itself, not
        just unwrapped here."""
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
