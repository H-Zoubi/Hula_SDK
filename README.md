# HULA drone dev setup

`pyhula` (HighGreat/hg-fly's SDK for the HULA educational drone) only ships
compiled wheels for Python 3.6 on Windows and internally needs `tkinter`, so
it requires a full Python 3.6 install (not the embeddable zip).

This machine already has a per-user Python 3.6.8 install registered with the
`py` launcher (`py -3.6`), so `venv/` here was created from that instead of
reinstalling Python 3.6.7 from the bundled installer.

**Status: working.** Verified against the real drone — `connect()` returns
`True`, telemetry reads back, and the drone takes off / flies / lands under
script control.

## What's installed

`venv/` — Python 3.6 virtualenv with:

- **`pyhula` 1.0.8** — the version `HulaSetup.pdf` calls for, from
  `installation instructions/installation instructions/`. This matters: the
  API surface differs between versions (see "API version differences"
  below). A 1.1.7 wheel also shipped in this folder (copied to
  `wheels/pyhula-1.1.7-...whl`; the original download was named `...whl.zip`,
  which is just a renamed wheel) — it is *not* what's installed.
- `opencv-python` 4.6.0.66, `psutil` 7.0.0, `protobuf` 3.19.6,
  `onnxruntime` 1.10.0, `flatbuffers`, `lxml`, `fastcrc`, `pymavlink`,
  `numpy` — matching the versions in `HulaSetup.pdf`

`pyhula`'s own `userapi.py` adds its bundled `f09-lite-trans/` folder
(ffmpeg DLLs) to `PATH` at import time, so — unlike what `HulaSetup.pdf`
says — there was no need to extract `f09-dlls.zip` into
`C:\Windows\System32`. The VC++ runtime DLLs it also needs
(`msvcp140.dll`, `vcruntime140.dll`, `vcruntime140_1.dll`) were already
present in `C:\Windows\System32`, so `VC_redist.x64.exe` wasn't run either.

## Network setup

The drone runs in **networking mode** (joined to the same Wi-Fi as this PC),
not its own AP. To switch modes: with the drone powered on, press the power
button **three times quickly**. Purple flashing = direct/AP mode, white
flashing = networking mode, solid green = joined to a router successfully.
Handing the drone the Wi-Fi credentials is done through the **Hula phone
app** (`com.highgreat.hula`) — there's no SDK path for provisioning.

The drone currently appears on the LAN as **`hg-35` / `192.168.1.62`**, set
as `DRONE_IP` in the scripts. That's a DHCP lease, so it can change after a
reboot — if `connect()` starts failing, re-check the address in the router's
client list first. A DHCP reservation would pin it permanently.

## Running

```bash
venv/Scripts/python.exe test_connect.py
```

Connects and prints battery, coordinates, yaw/pitch/roll, and plane ID.
Does not fly.

```bash
venv/Scripts/python.exe src/square_flight.py
```

Takes off, flies a 60cm square, lands. Needs clear space.

Console output includes Chinese status strings (`连接成功` = connected).
On a `cp1252` console these can crash the SDK's own error paths with
`UnicodeEncodeError` — prefix with `PYTHONIOENCODING=utf-8` if that happens.

## Required workaround: `hula_net_fix.py`

pyhula has two hardcoded-address bugs that make `connect()` fail on Windows.
[hula_net_fix.py](hula_net_fix.py) patches both at the socket layer; call
`hula_net_fix.patch(DRONE_IP)` **before** `import pyhula`. Without it you get
`OSError: [WinError 10049] The requested address is not valid in its context`
from `UDP_RECIVE_THREAD` and the connection never completes.

1. **Local bind uses the wrong address.** Its UDP/TCP listener threads bind
   their *local* listening socket to the `server_ip` you passed to
   `connect()` — i.e. the drone's address — instead of this PC's own address
   or a wildcard. Windows rejects that (you can't bind a local socket to an
   address you don't own). Patched by rewriting every bind to `0.0.0.0`.
2. **TCP control channel ignores `server_ip`.** It always dials the literal
   `192.168.100.1:8888`, apparently a leftover default from the vendor's
   reference setup (that's the drone's address in its own AP mode). Patched
   by redirecting that exact address to the real `DRONE_IP`.

Neither is documented, and neither needs any change to Windows network
config — an earlier attempt using a static IP alias plus `netsh portproxy`
worked around #2 at the OS level, but it's unnecessary and it disabled DHCP
on the Wi-Fi adapter as a side effect. Keep the fix in code.

Two other SDK bugs show up in tracebacks but are cosmetic — they only mask
real errors rather than cause them:

- `AttributeError: type object 'socket' has no attribute 'error'` in
  `TCP_SERVER_THREAD` — the SDK shadowed the `socket` module with the
  `socket.socket` class, so its own `except socket.error` handler crashes.
- `UnicodeEncodeError` from `cp1252` when it tries to print a Chinese
  error message.

## API version differences (1.0.8 vs 1.1.7)

The two PDFs document **different API versions**, which is a live trap:

| | 1.0.8 (installed) | 1.1.7 |
|---|---|---|
| Directional methods | `single_fly_forward(distance, led)` | `single_fly_forward(distance, speed, led)` |
| Matching doc | `Hula_API_English.pdf` | `Hula Python接口说明 V3_20250724.pdf` |

Passing a speed value to 1.0.8 puts it in the `led` slot and fails with
`TypeError: 'int' object is not subscriptable` inside `setRgb` — mid-flight,
after takeoff. `src/square_flight.py` wraps its flight sequence in
`try/finally` so the drone still lands when that kind of error hits.

`led` (when given) is a dict: `{'r':0,'g':0,'b':0,'mode':1}`, where mode is
1/solid, 2/off, 4/RGB cycle, 16/rainbow, 32/flashing, 64/breathing.

Full method list with docstrings (in Chinese) is in
`venv/Lib/site-packages/pyhula/userapi.py` — that's the authoritative
signature reference for whichever version is actually installed.

## Note: activation

PyPI's `pyhula` page states the SDK "needs to be activated before it can be
used" and to contact the author (service@hg-fly.com). No activation check
has been hit in practice — connect, telemetry, and flight all work without
one.

## Note: another setup exists

`C:\dev\drone` has a separate, earlier setup (pyhula 1.1.5) built from the
same family of docs. It's independent — nothing here touched it.
