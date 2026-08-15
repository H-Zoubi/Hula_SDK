# hula-sdk

A working Python SDK for the [HighGreat](https://en.hg-fly.com) **HULA**
educational drone.

The vendor's own `pyhula` package has two undocumented bugs that make
`connect()` fail outright on Windows. `hula-sdk` wraps `pyhula`, patches
both bugs, and exposes a cleaner, typed API on top of it. Verified against
real hardware on both `pyhula` 1.0.8 and the current PyPI release,
1.1.4 -- see "Tested vs untested" for exactly which of the 47 `UserApi`
methods that covers (33 of them, as of this writing).

**This is not the official SDK.** `pyhula` itself is still HighGreat's,
unmodified, installed straight from PyPI. Everything built on top of it
here -- the `hula_sdk/` wrapper, the bug fixes above, the English
translation in `docs/`, and this README -- was written mainly by AI (with
a human driving, debugging against real hardware, and reviewing).

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
| [`extended_telemetry.py`](examples/extended_telemetry.py) | Reads every telemetry getter. Doesn't fly. |
| [`flight_tricks.py`](examples/flight_tricks.py) | Interactively exercises the untested flight methods (hover, turns, bounce, circle, spin, flip, curved flight, line-following) -- confirms each step before running it. |
| [`sensing_and_camera.py`](examples/sensing_and_camera.py) | Interactively exercises QR/tag/color sensing and camera/video/lighting methods. Ground-based. |
| [`attachments_and_extras.py`](examples/attachments_and_extras.py) | Interactively exercises arm/disarm, electromagnet, clamp, laser -- only meaningful if your drone has those attachments (this project's test unit doesn't). |
| [`wait_for_qrcode.py`](examples/wait_for_qrcode.py) | Polls `recognize_qrcode()` in a loop until it gets a match or you Ctrl+C -- works around the SDK's short (~300ms) single-shot recognition window. |
| [`camera_stream.py`](examples/camera_stream.py) | Tests (and disproves) a warmup-delay theory for the broken video pipeline. See "The camera/video pipeline" below. |

The middle three use a shared `_stepper.py` helper: at each maneuver, Enter
runs it, `s` skips it, `q` stops early. One step failing doesn't stop the
rest -- and `HulaDrone`'s context manager still lands the drone if you
quit early or something raises mid-sequence.

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

**A mobile phone is currently required**, separately from this SDK, for
two things: activating the drone, and handing it your home Wi-Fi
credentials. There's no SDK-level or PC-side way to do either -- only the
Hula phone app (`com.highgreat.hula`, on Google Play / the App Store)
talks to the drone for setup. Once that's done, everything else in this
repo runs from the PC.

The drone needs to be in **networking mode**, joined to the same Wi-Fi as
this PC -- not its own direct-connection hotspot.

- With the drone powered on, press the power button **three times
  quickly** to switch modes. Purple flashing = direct/AP mode, white
  flashing = networking mode, solid green = successfully joined a router.
- Handing the drone your Wi-Fi credentials is done through the phone app
  -- there's no SDK-level way to provision it.
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

    # telemetry -- all tested against real hardware
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

| Verified against real hardware | Wrapped, never called against hardware | Attempted, not confirmed working | Not wrapped |
|---|---|---|---|
| `connect`, `battery`, `coordinate`, `attitude`, `plane_id`, `takeoff`, `land`, `forward`, `back`, `left`, `right`, `up`, `down`, `turn_left`, `turn_right`, `hover`, `bounce`, `fly_to`, `circle`, `spin`, `flip`, `curve_to`, `obstacles`, `acceleration`, `velocity`, `tof_height`, `set_obstacle_avoidance`, `identify_tag`, `align_to_qrcode`, `recognize_qrcode`, `track_qrcode`, `read_color`, `set_light` | `follow_line`, `set_qr_positioning`, `fire_laser`, `laser_hit`, `set_electromagnet`, `set_clamp`, `arm`, `disarm`, non-zero `Led` values | `open_video_window`, `set_video_stream`, `set_recording`, `take_photo`, `set_camera_angle` -- see below | `Plane_fly_line_walking` (broken in `pyhula` itself -- see above) |

**The camera/video pipeline is broken, in at least two different ways
depending on call order.** Neither path has ever produced a usable
photo -- no image file has appeared anywhere in the repo, in the user's
Pictures folder, or at any hardcoded path findable by grepping the
compiled SDK modules for `.jpg`/`.png` strings.

- **`open_video_window()` / `take_photo()` called *without*
  `set_video_stream(True)` first:** fails fast with
  `Could not find codec parameters for stream 0 (Video: h264, none):
  unspecified size`, then a native assertion failure --
  `Assertion desc failed at libswscale/swscale_internal.h:677` -- which
  terminates the process on its own within a couple seconds. Not a hang.
- **Same calls, but *with* `set_video_stream(True)` called first:** a
  heavy, sustained flood of decoder errors (`non-existing PPS 0
  referenced`, `decode_slice_header error`, `no frame!`) and RTP
  packet-loss warnings (`RTP: missed 30 packets`, etc. -- so packets
  genuinely are arriving, just not cleanly). How this resolves has
  varied across runs: sometimes it never stops and Ctrl+C does nothing
  (native C loop, not Python -- `Stop-Process -Force` / Task Manager is
  the only way out); sometimes it eventually stops on its own; once,
  Ctrl+C landing at the right moment (during the stepper's `input()`
  prompt, which unlike the C loop *is* interruptible) did kill it. Not
  reliable enough to depend on any one behavior.

**Timing/warmup hypothesis: disproven.**
[`camera_stream.py`](examples/camera_stream.py) added a 3s delay after
`set_video_stream(True)` before touching the stream at all -- the flood
started anyway, during that *second* warmup wait, before `take_photo()`
was even called. That rules out call ordering or a slow-to-start encoder:
it's `open_video_window()` (or a background thread it kicks off) that
spams continuously on its own, independent of when anything downstream
actually asks for a frame. `take_photo()` itself returned cleanly that
run only because the flood happened to have quieted down by the time it
ran, not because anything was fixed -- still no photo produced.

At this point the evidence points at something on the drone's encoder or
the WiFi link itself (the RTP packet-loss warnings support this) rather
than anything fixable by changing call order or timing from the Python
side. Worth trying if you want to dig further: moving closer to the
router to rule out packet loss from marginal signal, since that's the
one variable not yet isolated.

There's also a `tmp.sdp` file (an RTP session description) that `pyhula`
writes to the working directory, whose connection line looks truncated
(`c=IN IP4 1` instead of a real address like `192.168.1.62`). That was
the first theory for the root cause, but the "missed N packets" logs
imply packets *are* reaching the decoder, which doesn't fit a totally
wrong destination -- so this is a real oddity worth noting, not a
confirmed explanation. Genuine root cause is still open. `tmp.sdp` is
gitignored regardless (it's a regenerated runtime artifact).

These five methods stay marked `@_untested` deliberately -- not raising
in Python, and even the process eventually returning control, isn't the
same as demonstrably working. If you want to chase this further: check
whether `pyhula` exposes any way to set the stream's target IP
explicitly (the SDP writer seems to be guessing). Note that
`get_image_array()`, which shows up in some vendor documentation as the
way to retrieve a captured frame directly, does **not** exist in the
installed 1.1.4 -- it's a 1.1.7-only method, same story as `speed`.

**`recognize_qrcode` is confirmed working, including genuine positive
recognition** -- [`wait_for_qrcode.py`](examples/wait_for_qrcode.py)
correctly detected a real QR panel multiple times. That confirms the
earlier theory: the SDK's single-shot ~300ms recognition window was the
whole problem, not a deeper bug -- a single call needs the panel already
in view at that exact instant, which is unrealistic to time by hand, but
trivial to solve by polling.

`identify_tag`/`align_to_qrcode`/`track_qrcode` are still only verified
for call mechanics, not confirmed for actual recognition -- they return
the documented shape without crashing, including two prior single-shot
attempts with real panels that came back `result: False` (most likely
the same timing issue, now that polling is confirmed to fix it for
`recognize_qrcode`). Worth trying the same polling approach on these
three next.

Also found while cross-referencing the vendor docs against the actually
installed 1.1.4: `single_fly_Optical_flow_alignment`,
`single_fly_Proactive_alignment`, and `single_fly_Anticipatory_recognition`
are documented in the Chinese V3 PDF but don't exist in any version
published to PyPI -- same story as the `speed` parameter, vendor-exclusive
1.1.7 only.

When you get a chance to test more of these (battery permitting): the
non-camera items left are `arm`/`disarm` (spins the propellers, so have
someone standing by -- `electromagnet`/`clamp`/`laser` in the same script
don't apply to this project's test unit, which doesn't have those
attachments), `follow_line` (needs an actual line under the drone), and
`set_qr_positioning` and non-zero `Led` colors (both now in
`sensing_and_camera.py`).

## Known limitations

- **Windows + Python 3.6 only**, inherited from `pyhula`'s compiled
  extension.
- **One drone per process.** The bind/connect patches are applied
  globally to `socket.socket`, and the connect-redirect target is a
  single module-level value -- controlling two physical drones
  concurrently from one Python process isn't supported. Use separate
  processes if you need that.
- **Activation currently requires the phone app**, not just Wi-Fi setup
  (see "Network setup" above) -- matching PyPI's `pyhula` page, which
  states the SDK "needs to be activated before it can be used." Once
  activated through the app, no further activation step has been hit
  from the SDK side -- connect, telemetry, and flight all work after
  that without one.
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
