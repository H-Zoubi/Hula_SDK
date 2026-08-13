"""
Tests for HulaDrone's @_untested warning mechanism -- the "test pending"
signal for methods that are implemented against the documented/installed
pyhula signature but have never been exercised against real hardware.

Uses a fake `_api` object so no pyhula install or hardware is required.
"""
import unittest
import warnings

from hula_sdk.client import HulaDrone, _warned_methods


class _FakeApi:
    def single_fly_hover_flight(self, seconds, led):
        return None

    def get_battery(self):
        return 50

    def get_accelerated_speed(self):
        return [0, 0, 0]


def _make_drone():
    # Bypasses __init__ (which imports pyhula and applies _netfix) --
    # these tests only care about the warning wrapper, not a real
    # connection.
    drone = HulaDrone.__new__(HulaDrone)
    drone._api = _FakeApi()
    drone.ip = "203.0.113.1"
    drone.connected = True
    drone._flying = False
    return drone


class TestUntestedWarning(unittest.TestCase):
    def test_untested_method_warns_once_per_process(self):
        _warned_methods.discard("HulaDrone.hover")
        drone = _make_drone()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            drone.hover(1)
            drone.hover(1)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        self.assertEqual(len(user_warnings), 1)
        self.assertIn("hover", str(user_warnings[0].message))
        self.assertIn("not been verified against real hardware", str(user_warnings[0].message))

    def test_tested_method_does_not_warn(self):
        drone = _make_drone()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            drone.battery()

        self.assertEqual(caught, [])


if __name__ == "__main__":
    unittest.main()
