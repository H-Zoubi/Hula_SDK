"""
Workarounds for two hardcoded-address bugs in pyhula on Windows.
Call patch(drone_ip) *before* `import pyhula`.

1. Its UDP/TCP listener threads bind their *local* listening socket to
   the server_ip you passed to connect() (the drone's address) instead
   of to this PC's own address / a wildcard. That always fails with
   WinError 10049 ("requested address is not valid in its context"),
   since you can't bind a local socket to an address that isn't your
   own. Fix: rewrite every bind's IP to "0.0.0.0" (all interfaces).

2. Its TCP control connection ignores the server_ip you pass entirely
   and always dials the literal "192.168.100.1:8888" (apparently a
   leftover default from the vendor's reference network). Fix: redirect
   that exact address to the drone's real IP on our network.
"""
import socket

_HARDCODED_TARGET = ("192.168.100.1", 8888)


def patch(drone_ip):
    original_bind = socket.socket.bind
    original_connect = socket.socket.connect

    def patched_bind(self, address):
        if isinstance(address, tuple) and len(address) == 2:
            address = ("0.0.0.0", address[1])
        return original_bind(self, address)

    def patched_connect(self, address):
        if address == _HARDCODED_TARGET:
            address = (drone_ip, address[1])
        return original_connect(self, address)

    socket.socket.bind = patched_bind
    socket.socket.connect = patched_connect
