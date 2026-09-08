# hula-sdk

A working Python SDK for the [HighGreat](https://en.hg-fly.com) **HULA**
educational drone.

The vendor's own `pyhula` package has two undocumented bugs that make
`connect()` fail outright on Windows, and its camera/video methods don't
work at all. `hula-sdk` wraps `pyhula`, patches the connection bugs,
exposes a cleaner typed API on top of it, and ships its own video
receiver to replace the broken one. Verified against real hardware on
both `pyhula` 1.0.8 and the current PyPI release, 1.1.4 -- see "Tested vs
untested" for exactly which of the 47 `UserApi` methods that covers (33
of them, as of this writing), and "The camera/video pipeline" for the
video receiver.

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
| [`camera_stream.py`](examples/camera_stream.py) | Tests (and disproves) a warmup-delay theory for `pyhula`'s broken video pipeline. See "The camera/video pipeline" below. |
| [`working_video_stream.py`](examples/working_video_stream.py) | `hula_sdk`'s own video receiver -- bypasses `pyhula`'s broken one entirely. Confirmed working: captures and saves a real photo. Needs a real `ffmpeg` on PATH. |
| [`live_preview.py`](examples/live_preview.py) | Same receiver, continuous display in a window instead of one photo. Confirmed working against real hardware. |
| [`qr_in_air.py`](examples/qr_in_air.py) | Takes off and scans continuously for a QR code using `hula_sdk`'s own video stream + OpenCV (not the vendor's `recognize_qrcode()`), with a live preview window. |
| [`land_on_qrcode.py`](examples/land_on_qrcode.py) | Takes off, calls `align_to_qrcode(sensor=OPTICAL_FLOW)` in a background thread with a bounded wait for a code on the floor, then lands regardless of whether it confirms. **This call's own completion signal has reliably failed to arrive** (though the alignment maneuver itself appears to complete) -- see "Tested vs untested" below. |

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
- A real `ffmpeg` executable on PATH, **only** if you want `drone.video()`
  (see "The camera/video pipeline"). Nothing else in `hula-sdk` needs it.

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

**`pyhula`'s own camera/video methods are broken, in at least two
different ways depending on call order** -- `set_video_stream`,
`open_video_window`, `set_recording`, `take_photo`, `set_camera_angle`
all stay marked `@_untested`, and this is now a closed investigation, not
an open one:

- **Without `set_video_stream(True)` first:** fails fast with
  `Could not find codec parameters for stream 0`, then a native assertion
  crash (`Assertion desc failed at libswscale/swscale_internal.h:677`)
  that ends the process within a couple seconds.
- **With `set_video_stream(True)` first:** a heavy, sustained flood of
  decoder errors (`non-existing PPS 0 referenced`, `decode_slice_header
  error`, `no frame!`), starting as soon as `open_video_window()` runs --
  before anything downstream even asks for a frame. How it resolves is
  inconsistent: sometimes it never stops (Ctrl+C does nothing -- it's a
  native C loop, not Python; `Stop-Process -Force` / Task Manager is the
  only way out), sometimes it stops on its own.

Two hypotheses were each tested directly and disproven, not just
suspected:

1. **Timing/warmup** -- [`camera_stream.py`](examples/camera_stream.py)
   added a delay after enabling the stream before touching it. The flood
   started anyway, during the warmup wait itself. Ruled out call
   ordering or a slow-to-start encoder.
2. **Malformed `tmp.sdp`** -- `pyhula` writes an RTP session description
   with a truncated connection address (`c=IN IP4 1` instead of a real
   IP). Pre-seeding a corrected file and making it **read-only** (so the
   native writer couldn't overwrite it) changed nothing -- confirmed via
   the file's own contents, untouched, after the exact same flood
   happened anyway. Ruled out the SDP address.

What actually settled it: a **raw RTP packet capture**, bypassing
`pyhula` entirely -- enable the stream, then read UDP port 9070 directly
with a plain Python socket instead of letting `pyhula`'s decoder touch
it. Result: **0% packet loss** (1356/1356 packets, fully contiguous
sequence numbers), a normal ~1.76 Mbps bitrate, and both SPS and PPS
genuinely present (7 of each, paired with 7 keyframes, over 8 seconds).
The stream is completely intact on the wire. `pyhula`'s own
`RTP: missed N packets` warnings were themselves wrong -- not a
reflection of real network loss. The bug is entirely inside `pyhula`'s
bundled ffmpeg wrapper's own demuxer/reassembly logic, which is compiled
native code, not something patchable from Python.

**So `hula_sdk` ships its own video receiver instead of trying to fix
`pyhula`'s** -- [`hula_sdk/video.py`](hula_sdk/video.py) /
[`hula_sdk/_rtp.py`](hula_sdk/_rtp.py), used via `drone.video()`. It
receives RTP directly (the exact same socket-reading approach the
diagnostic capture used), reassembles NAL units itself
(`hula_sdk/_rtp.py` -- FU-A fragments and STAP-A aggregates per RFC
6184, fully unit-tested with 10 tests, no hardware needed), and feeds the
result to a real, separately-installed `ffmpeg` on PATH -- deliberately
**not** `pyhula`'s bundled DLLs, which is what's actually broken.

```python
with HulaDrone(ip) as drone:
    with drone.video() as video:
        frame = video.read_frame()      # numpy BGR array
        video.save_photo("photo.jpg")
        video.show_live()               # continuous window, 'q' to quit
```

**Status: it works.** `save_photo()` -- and the whole receive → reassemble
→ decode pipeline underneath it -- is confirmed against real hardware:
[`working_video_stream.py`](examples/working_video_stream.py) captured
and saved a real photo, something `pyhula`'s own `take_photo()` has never
once managed to do across every attempt in this README. `show_live()`
(continuous display, [`live_preview.py`](examples/live_preview.py)) is
also confirmed working.

**Latency, round 1:** the first version had substantial lag vs. the
official app. Root cause: the decode loop processed every buffered JPEG
frame in arrival order rather than jumping to the newest one -- if
decoding fell even slightly behind the incoming ~30fps stream, the
backlog just grew and the lag compounded over time. Fixed by scanning
(cheap) past stale buffered frames to decode (expensive) only the latest
one. Confirmed better, but still noticeable.

**Latency, round 2:** switched ffmpeg's output from re-encoding every
frame to MJPEG (so `cv2.imdecode` could read it) to raw decoded frames
(`-f rawvideo -pix_fmt bgr24`) instead -- removes a whole extra encode
pass per frame, replacing a JPEG decode with a cheap memory reshape.
Frame dimensions are parsed once from ffmpeg's own stderr ("Video: ...
WxH") rather than hardcoded.

Two lower-latency ffmpeg flags were tried together (`-fflags nobuffer
-flags low_delay`) and broke decoding entirely -- confirmed via a
synthetic test, valid output without them, zero bytes with them. Testing
each flag in isolation (same synthetic test) found the actual culprit
was `-fflags nobuffer` alone; `-flags low_delay` on its own decodes
fine. So the final set is `-flags low_delay` plus `-threads 1` (avoids
frame-parallel decoding's inherent added latency) -- both individually
confirmed safe, and confirmed safe together, all without `-fflags
nobuffer`.

Also fixed: the preview window's close (X) button didn't actually close
it -- `cv2.imshow()` has no way to know a window was closed that way and
just silently recreates it next frame; now checks
`cv2.WND_PROP_VISIBLE` explicitly each loop.

Verified two ways before spending any more of the drone's battery: a
full integration test
([`tests/test_video_integration.py`](tests/test_video_integration.py),
skipped automatically if `ffmpeg` isn't on PATH) that exercises the real
`VideoStream` code end to end over loopback with a synthetic RTP feed --
and manual isolation of the broken flags against the same synthetic
stream. **Confirmed against the real drone: noticeably better** after
both latency rounds. Not quantified against the official app (no
side-by-side timing), and not necessarily fully closed, but no longer
the standout problem it was.

**Latency, round 3 (not yet re-confirmed against the drone):** two
further changes, both on the PC side rather than ffmpeg's:

- `show_live()` was busy-spinning: `read_frame()` returns instantly on
  every call once *any* frame has ever arrived (nothing cleared that
  state), so the display loop was redecoding/redrawing the same stale
  frame far faster than the ~30fps source, burning CPU the decode thread
  could've used instead. Replaced the plain Event with a
  `threading.Condition` + frame sequence counter, so `show_live()` now
  genuinely blocks for the *next new* frame instead of spinning. Verified
  directly: `tests/test_video_integration.py` now asserts the sequence
  number actually advances between waits, not just that a frame comes
  back.
- `_stdout_loop`'s read size was a fixed 64KB regardless of resolution --
  for anything above roughly 340x210 that's more than one syscall just
  to accumulate a single frame (a 1280x720 frame is ~2.7MB, over 40
  reads). Now reads in frame-sized chunks once dimensions are known.

Note: `get_image_array()`, which shows up in some vendor documentation
as a way to retrieve a frame directly from `pyhula` itself, does **not**
exist in the installed 1.1.4 -- it's a 1.1.7-only method, same story as
`speed`.

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

**`align_to_qrcode(sensor=QrSensor.OPTICAL_FLOW)` specifically has been
confirmed to hang reliably (multiple attempts), not just return
`result: False`** -- see [`land_on_qrcode.py`](examples/land_on_qrcode.py).
The traceback from Ctrl+C'ing it goes straight into `pyhula`'s own
compiled code (`TaskController._wait_state` -> `Event.wait_for_signal`
-> `threading.Condition.wait()`), meaning the task's completion signal
never arrives -- not a Python-side bug, the vendor SDK's own wait never
resolves for this call. `sensor=CAMERA` has not shown this; only the
optical-flow mode has been tried and hung so far.

Two things narrow down what's actually broken, though: on one hang,
Ctrl+C'ing past it landed the drone right on the code -- meaning the
*alignment maneuver itself* completes fine on the drone; only the
Python-side wait for its completion signal is broken. And the earlier
concern that interrupting the hang wedges the connection enough to
make the following `land()` call also hang didn't reproduce on a later
attempt -- `land()` returned cleanly. So the hang looks isolated to
this one call's own confirmation signal, not a systemic connection
problem, though `land()` needing a second Ctrl+C once is still a real
data point, not nothing. `land_on_qrcode.py` now calls
`align_to_qrcode()` in a background thread with a bounded wait instead
of blocking on it directly, and proceeds to land regardless of whether
confirmation ever arrives.

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
against real sockets (RFC 5737 documentation-range addresses --
`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), the `@_untested`
warning mechanism against a fake `_api`, `hula_sdk._rtp`'s H.264
reassembly (FU-A fragments, STAP-A aggregates) against hand-built RTP
payloads, and a full `VideoStream` integration test that generates a
synthetic H264 clip with `ffmpeg`'s own `testsrc` and feeds it through
the real receive/reassemble/decode path over loopback (skipped
automatically if `ffmpeg` isn't on PATH). None of it needs the drone or
its battery -- what's *not* covered is whatever's specific to talking to
the real drone's actual video encoder (see "The camera/video pipeline"
for what's been verified there manually instead).

One wrinkle worth knowing about in `tests/test_qrcode_detection.py`: how
badly a frame has to be degraded before OpenCV's raw QR detector gives
up is a property of the installed OpenCV, not of `hula_sdk`, and it
moved between versions -- 5.0.0 reads motion blur that the pinned
4.6.0.66 can't. So the test that proves `detect_qrcode()`'s enhanced
retry pass genuinely recovers unreadable frames *searches* a grid of
degradations for one where the raw pass fails and the enhanced pass
succeeds, rather than hardcoding a single tuned point (an earlier
version did hardcode one, and it passed on 4.6.0.66 while failing on
5.0.0 even though `detect_qrcode()` was fine on both). The separate
control-flow test -- that a raw miss is retried once, against an
enhanced frame -- uses a stub detector and is version-independent.

## Repository layout

```
hula_sdk/        the package: client.py, led.py, constants.py, exceptions.py,
                 _netfix.py (the connection bug fixes), _rtp.py + video.py
                 (hula_sdk's own video receiver)
examples/        runnable scripts (see table above)
tests/           unit + integration tests -- no drone required; the video
                 integration test needs ffmpeg on PATH (skips without it)
docs/            vendor PDFs + an English translation of the Chinese one
vendor/          offline install media (Python 3.6 installer, DLLs, older
                 pyhula wheels) -- gitignored, kept locally for reference
venv/            Python 3.6 virtualenv -- gitignored
```

## See also

`C:\dev\drone` has a separate, independent setup (`pyhula` 1.1.5) built
earlier from the same family of vendor docs. It's unrelated to this repo.
