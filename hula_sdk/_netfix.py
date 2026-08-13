"""
Workarounds for two hardcoded-address bugs in pyhula on Windows.

`patch(drone_ip)` is called automatically by `HulaDrone` before it talks to
the vendor SDK -- you shouldn't need to call this directly.

1. Local bind uses the wrong address. pyhula's UDP/TCP listener threads
   bind their *local* listening socket to the server_ip you passed to
   connect() -- the drone's address -- instead of to this PC's own
   address or a wildcard. Windows rejects that with
   `OSError: [WinError 10049] The requested address is not valid in its
   context`, since you can't bind a local socket to an address you don't
   own. Fixed by rewriting every bind's IP to "0.0.0.0" (all interfaces).

2. The TCP control channel ignores server_ip entirely and always dials
   the literal "192.168.100.1:8888" -- apparently a leftover default
   from the vendor's own reference setup (that's the drone's own address
   in its direct/AP Wi-Fi mode). Fixed by redirecting that exact address
   to the real drone IP.

Both patches are applied once, globally, to `socket.socket`. Only one
drone IP is active as the redirect target at a time -- see "Known
limitations" in the README if you need more than one drone from the same
process.
"""
import socket

_original_bind = socket.socket.bind
_original_connect = socket.socket.connect
_HARDCODED_TARGET = ("192.168.100.1", 8888)

_current_drone_ip = None
_installed = False


def _patched_bind(self, address):
    if isinstance(address, tuple) and len(address) == 2:
        address = ("0.0.0.0", address[1])
    return _original_bind(self, address)


def _patched_connect(self, address):
    if address == _HARDCODED_TARGET and _current_drone_ip is not None:
        address = (_current_drone_ip, address[1])
    return _original_connect(self, address)


def patch(drone_ip):
    """Install the socket patches (idempotent) and set the redirect target."""
    global _current_drone_ip, _installed
    _current_drone_ip = drone_ip
    if not _installed:
        socket.socket.bind = _patched_bind
        socket.socket.connect = _patched_connect
        _installed = True
