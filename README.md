# hula-sdk

A working Python SDK for the [HighGreat](https://en.hg-fly.com) **HULA**
educational drone.

The vendor's own `pyhula` package has two undocumented bugs that make
`connect()` fail outright on Windows. `hula-sdk` wraps `pyhula`, patches
both bugs, and exposes a cleaner, typed API on top of it. Verified against
real hardware on `pyhula` 1.0.8 (connect, telemetry, takeoff, flight,
landing) and re-verified on the current PyPI release, 1.1.4 (connect,
telemetry -- flight not yet re-tested on 1.1.4).

## Quickstart

```bash
git clone <this repo>
cd hula-sdk
py -3.6 -m venv venv
venv\Scripts\python.exe -m pip install -e .
```

```python
from hula_sdk import HulaDrone

with HulaDrone("192.168.1.62") as drone:
    print("battery:", drone.battery())
    drone.takeoff()
    drone.square(60)
    drone.land()
```

See `examples/` for runnable scripts:

| Script | What it does |
|---|---|
| [`connect_and_read_telemetry.py`](examples/connect_and_read_telemetry.py) | Connects and prints battery/coordinate/attitude/plane ID. Doesn't fly. |
| [`basic_takeoff_land.py`](examples/basic_takeoff_land.py) | Simplest possible flight: connect, take off, land. |
| [`square_flight.py`](examples/square_flight.py) | Flies a 60cm square and lands. |

## Requirements

- **Windows.** `pyhula` only ships compiled Windows wheels.
- **Python 3.6**, specifically -- this isn't a choice `hula-sdk` makes,
  it's forced by the vendor. Every `pyhula` wheel on PyPI, including the
  current latest (1.1.4), is built `cp36-cp36m`: Python 3.6 only, no
  forward-compatible ABI. It also needs `tkinter`, so it needs a full
  Python 3.6 install, not the embeddable zip.
- The drone and this PC on the **same Wi-Fi network** ("networking
  mode" -- see below). `hula-sdk` does not work with the drone's own
  direct-connection hotspot; see "The bugs this fixes."

All of `pyhula`'s own dependencies (`opencv-python`, `psutil`, `numpy`,
etc.) are kept at the newest version that still ships a `cp36` wheel.
`opencv-python` is the one exception worth knowing about: its newest
release (5.x) dropped prebuilt Python 3.6 wheels entirely, so installing
it means compiling from source with a full Visual Studio + CMake
toolchain. `opencv-python==4.6.0.66` is the last version with a working
prebuilt wheel, so that's what's pinned in practice (via `pyhula`'s own
`install_requires`, not `hula-sdk`'s).

## Network setup

The drone needs to be in **networking mode**, joined to the same Wi-Fi as
this PC -- not its own direct-connection hotspot.

- With the drone powered on, press the power button **three times
  quickly** to switch modes. Purple flashing = direct/AP mode, white
  flashing = networking mode, solid green = successfully joined a router.
- Handing the drone your Wi-Fi credentials is done through the **Hula
  phone app** (`com.highgreat.hula`, on Google Play / the App Store) --
  there's no SDK-level way to provision it.
- Once connected, find the drone's IP from your router's client list
  (it'll show up as something like `hg-<id>`). That's a DHCP lease, so it
  can change after a router reboot -- a static DHCP reservation on your
  router avoids that.

## The bugs this fixes

Both are patched in [`hula_sdk/_netfix.py`](hula_sdk/_netfix.py), applied
automatically by `HulaDrone` -- you don't need to call anything yourself.

1. **Local bind uses the wrong address.** `pyhula`'s UDP/TCP listener
   threads bind their *local* listening socket to the `server_ip` you
   pass to `connect()` -- i.e. the drone's address -- instead of to this
   PC's own address or a wildcard. Windows rejects that outright:
   ```
   OSError: [WinError 10049] The requested address is not valid in its context
   ```
   because you can't bind a local socket to an address you don't own.
   Fixed by rewriting every bind's IP to `0.0.0.0` (all interfaces).

2. **The TCP control channel ignores `server_ip` entirely** and always
   dials the literal `192.168.100.1:8888` -- apparently a leftover
   default from the vendor's own reference network (that's the drone's
   *own* address in its direct/AP Wi-Fi mode, which is why that mode
   looks like it should work and doesn't, once bug #1 is also in play).
   Fixed by redirecting that exact address to the real drone IP.

Two more bugs show up in tracebacks but are cosmetic -- they mask real
errors rather than cause them, and don't need patching:

- `AttributeError: type object 'socket' has no attribute 'error'` in
  `TCP_SERVER_THREAD` -- the SDK shadowed the `socket` module with the
  `socket.socket` class, so its own `except socket.error` handler
  crashes when it actually tries to handle an error.
- `UnicodeEncodeError` from `cp1252` when it prints a Chinese status
  message on a non-UTF-8 console. Run with `PYTHONIOENCODING=utf-8` if
  you hit this outside of `hula-sdk` (e.g. talking to `pyhula` directly).

## API version differences

`pyhula`'s two reference PDFs in `docs/` document **different API
versions**, and the difference isn't cosmetic:

| | Every version on PyPI (through 1.1.4) | 1.1.7 (vendor-distributed only, not on PyPI) |
|---|---|---|
| Directional methods | `single_fly_forward(distance, led)` | `single_fly_forward(distance, speed, led)` |
| Matching doc | `Hula_API_English.pdf` | `Hula_Python_API_V3_20250724_EN.md` |

`pip install pyhula` gets you the no-`speed` signature -- PyPI's latest
(1.1.4) still doesn't have it. The `speed`-capable 1.1.7 build only
exists as a wheel the vendor handed out directly (kept in `vendor/` here
for reference); it isn't published anywhere pip can reach.

Passing a speed value to a no-`speed` version lands in the `led` slot
instead and fails with `TypeError: 'int' object is not subscriptable`
inside `setRgb` -- *after* takeoff, mid-flight.

`HulaDrone`'s movement methods (`forward`, `back`, `left`, `right`, `up`,
`down`) handle this automatically: they inspect the installed `pyhula`'s
actual method signature and only pass `speed` through if that version
supports it, raising a clear `TypeError` up front if you ask for a speed
it can't do, rather than failing deep inside the SDK's LED-setting code
mid-flight.

## API overview

Every one of `pyhula`'s 47 `UserApi` methods is wrapped -- with one
deliberate exception, `Plane_fly_line_walking()`, whose own source in
`pyhula` references a bare `type` (the Python builtin) instead of an
actual parameter. That's a bug in the vendor SDK itself, not something
worth papering over here with a guessed fix; it's reachable via `.raw`
if you want to poke at it.

```python
from hula_sdk import HulaDrone, Led, LedMode, FlipDirection, QrSensor

with HulaDrone(ip) as drone:
    drone.connected       # bool

    # flight -- tested against real hardware
    drone.takeoff(led=None)
    drone.land(led=None)
    drone.forward(distance_cm, speed=None, led=None)   # also .back / .left / .right
    drone.square(side_cm, speed=None)                   # forward -> right -> back -> left

    # flight -- wrapped, not yet tested against hardware (warns on first call)
    drone.up(height_cm, speed=None, led=None)           # also .down
    drone.turn_left(angle_deg, led=None)                # also .turn_right
    drone.hover(seconds, led=None)
    drone.bounce(frequency, height_cm, led=None)
    drone.fly_to(x_cm, y_cm, z_cm, led=None)
    drone.circle(radius_cm, led=None)
    drone.spin(num_rotations, led=None)
    drone.flip(FlipDirection.FORWARD, led=None)
    drone.curve_to(x_cm, y_cm, z_cm, counterclockwise=True, led=None)

    # sensing -- wrapped, untested
    drone.set_obstacle_avoidance(enabled)
    drone.follow_line(distance_cm, line_color=0)
    drone.identify_tag(mode)
    drone.align_to_qrcode(qr_id, sensor=QrSensor.CAMERA)
    drone.recognize_qrcode(qr_id, sensor=QrSensor.CAMERA)
    drone.track_qrcode(qr_id, seconds)
    drone.read_color(mode=1)

    # lighting / camera / attachments -- wrapped, untested
    drone.set_light(Led(...), seconds)
    drone.open_video_window()
    drone.set_video_stream(enabled)
    drone.set_recording(enabled)
    drone.take_photo()
    drone.set_camera_angle(direction, angle)
    drone.set_qr_positioning(enabled)
    drone.fire_laser(laser_type, frequency=10, ammo=100)
    drone.laser_hit()
    drone.set_electromagnet(attract)
    drone.set_clamp(is_open, angle=0)
    drone.arm()
    drone.disarm()

    # telemetry -- battery/coordinate/attitude/plane_id tested,
    # the rest wrapped-but-untested
    drone.battery()         # int, 0-100
    drone.coordinate()      # (x, y, z) cm, relative to takeoff
    drone.attitude()        # (yaw, pitch, roll) degrees
    drone.plane_id()        # int
    drone.obstacles()       # {'forward'/'back'/'left'/'right': bool}
    drone.acceleration()    # (x, y, z)
    drone.velocity()        # (x, y, z)
    drone.tof_height()      # int

    drone.raw               # underlying pyhula.UserApi escape hatch
```

`led` parameters take an `hula_sdk.Led` (a typed version of the raw
`{'r':.., 'g':.., 'b':.., 'mode':..}` dict `pyhula` expects):

```python
Led(r=16, g=15, b=100, mode=LedMode.RAINBOW)
```

`HulaDrone` used as a context manager lands the drone automatically if an
exception is raised mid-flight (tracked via an internal "are we
airborne" flag, so it won't call touchdown on a drone that never took
off).

## Tested vs untested

Given that the small slice of the API exercised so far turned up two
real connection bugs, two cosmetic ones, and a process-killing
low-battery behavior, "the signature matches the docs" is not treated as
equivalent to "verified working" anywhere in this README or in the code.
Methods below `square()` in `client.py` are wrapped but genuinely
unverified against hardware -- calling any of them raises a `UserWarning`
the first time (once per method, per process), naming the method and
pointing back here.

| Verified against real hardware | Wrapped, never called against hardware | Not wrapped |
|---|---|---|
| `connect`, `battery`, `coordinate`, `attitude`, `plane_id`, `takeoff`, `land`, `forward`, `back`, `left`, `right` | `up`, `down`, `turn_left`, `turn_right`, `hover`, `bounce`, `fly_to`, `circle`, `spin`, `flip`, `curve_to`, `set_obstacle_avoidance`, `follow_line`, `identify_tag`, `align_to_qrcode`, `recognize_qrcode`, `track_qrcode`, `read_color`, `set_light`, `open_video_window`, `set_video_stream`, `set_recording`, `take_photo`, `set_camera_angle`, `set_qr_positioning`, `fire_laser`, `laser_hit`, `set_electromagnet`, `set_clamp`, `arm`, `disarm`, `obstacles`, `acceleration`, `velocity`, `tof_height`, non-zero `Led` values | `Plane_fly_line_walking` (broken in `pyhula` itself -- see above) |

Also found while cross-referencing the vendor docs against the actually
installed 1.1.4: `single_fly_Optical_flow_alignment`,
`single_fly_Proactive_alignment`, and `single_fly_Anticipatory_recognition`
are documented in the Chinese V3 PDF but don't exist in any version
published to PyPI -- same story as the `speed` parameter, vendor-exclusive
1.1.7 only.

When you do get a chance to test more of these (battery permitting):
low-risk first -- the telemetry getters (`obstacles`, `acceleration`,
`velocity`, `tof_height`) don't move the drone. Things like `arm()`
(spins the propellers) deserve someone standing by first.

## Known limitations

- **Windows + Python 3.6 only**, inherited from `pyhula`'s compiled
  extension.
- **One drone per process.** The bind/connect patches are applied
  globally to `socket.socket`, and the connect-redirect target is a
  single module-level value -- controlling two physical drones
  concurrently from one Python process isn't supported. Use separate
  processes if you need that.
- No activation issue has been hit in practice, despite PyPI's `pyhula`
  page stating the SDK "needs to be activated" -- connect, telemetry,
  and flight all work without one so far.
- **pyhula >=1.1.x hard-exits the whole process on low battery.** If the
  drone reports under 10%, `connect()` doesn't return `False` or raise --
  it prints `battery<10，退出程序` and terminates the process outright
  (looks like an `os._exit()` or similar buried in the compiled SDK).
  `HulaDrone.connect()`'s `HulaConnectionError` never gets a chance to
  fire in that case. Not something `hula-sdk` can intercept without
  knowing exactly which call does it; charge the drone above 10% before
  connecting.

## Development

```bash
venv\Scripts\python.exe -m unittest discover tests -v
```

Tests cover the `_netfix` patch logic and `Led` conversion directly
against real sockets, using RFC 5737 documentation-range addresses
(`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), plus the
`@_untested` warning mechanism against a fake `_api`. All of it is safe
to run anywhere -- no drone, no real network, no `pyhula` install
required.

## Repository layout

```
hula_sdk/        the package: client.py, led.py, constants.py, exceptions.py, _netfix.py
examples/        runnable scripts (see table above)
tests/           unit tests, no hardware required
docs/            vendor PDFs + an English translation of the Chinese one
vendor/          offline install media (Python 3.6 installer, DLLs, older
                 pyhula wheels) -- gitignored, kept locally for reference
venv/            Python 3.6 virtualenv -- gitignored
```

## See also

`C:\dev\drone` has a separate, independent setup (`pyhula` 1.1.5) built
earlier from the same family of vendor docs. It's unrelated to this repo.
