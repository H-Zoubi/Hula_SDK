"""
Tests for hula_sdk._netfix.

These exercise the patch logic directly against real sockets -- no drone
or network access required. IP addresses used are from RFC 5737's
documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24),
which are guaranteed non-routable, so binding/"connecting" to them is
safe and won't touch real infrastructure.
"""
import socket
import unittest

from hula_sdk import _netfix


class TestBindPatch(unittest.TestCase):
    def test_bind_to_nonlocal_address_is_redirected_to_wildcard(self):
        _netfix.patch("203.0.113.5")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Without the patch this raises OSError (WSAEADDRNOTAVAIL /
            # WinError 10049 on Windows), since 203.0.113.5 is never a
            # local address on the test machine.
            sock.bind(("203.0.113.5", 0))
            self.assertEqual(sock.getsockname()[0], "0.0.0.0")
        finally:
            sock.close()


class TestConnectPatch(unittest.TestCase):
    def test_hardcoded_target_is_redirected_to_drone_ip(self):
        _netfix.patch("198.51.100.7")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("192.168.100.1", 8888))
            self.assertEqual(sock.getpeername(), ("198.51.100.7", 8888))
        finally:
            sock.close()

    def test_other_targets_are_left_alone(self):
        _netfix.patch("198.51.100.7")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("198.51.100.99", 12345))
            self.assertEqual(sock.getpeername(), ("198.51.100.99", 12345))
        finally:
            sock.close()

    def test_redirect_target_updates_on_repeated_patch_calls(self):
        _netfix.patch("198.51.100.7")
        _netfix.patch("192.0.2.9")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("192.168.100.1", 8888))
            self.assertEqual(sock.getpeername(), ("192.0.2.9", 8888))
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()
