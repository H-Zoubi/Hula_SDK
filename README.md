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

```python
from hula_sdk import HulaDrone, Led, LedMode

with HulaDrone(ip) as drone:
    drone.connected       # bool
    drone.takeoff(led=None)
    drone.land(led=None)
    drone.hover(seconds, led=None)
    drone.forward(distance_cm, speed=None, led=None)   # also .back / .left / .right / .up / .down
    drone.turn_left(angle_deg, led=None)                # also .turn_right
    drone.square(side_cm, speed=None)                   # forward -> right -> back -> left

    drone.battery()        # int, 0-100
    drone.coordinate()     # (x, y, z) cm, relative to takeoff
    drone.attitude()       # (yaw, pitch, roll) degrees
    drone.plane_id()       # int

    drone.raw              # underlying pyhula.UserApi, for anything not wrapped
                            # above (camera, QR/tag recognition, laser, etc.)
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
(`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) so they're safe to
run anywhere -- no drone or real network required.

## Repository layout

```
hula_sdk/        the package: client.py, led.py, exceptions.py, _netfix.py
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
