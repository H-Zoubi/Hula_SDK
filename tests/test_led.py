import unittest

from hula_sdk import Led, LedMode
from hula_sdk.client import HulaDrone


class TestLed(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(Led().to_dict(), {"r": 0, "g": 0, "b": 0, "mode": 1})

    def test_custom_values(self):
        led = Led(r=16, g=15, b=100, mode=LedMode.RAINBOW)
        self.assertEqual(led.to_dict(), {"r": 16, "g": 15, "b": 100, "mode": 16})


class _FakeApi:
    def __init__(self):
        self.lamplight_calls = []

    def single_fly_lamplight(self, *args):
        self.lamplight_calls.append(args)
        return True


def _make_drone(api):
    # Bypasses __init__ (which imports pyhula and applies _netfix) -- this
    # only cares about what set_light passes through to the fake _api, not
    # a real connection.
    drone = HulaDrone.__new__(HulaDrone)
    drone._api = api
    drone.ip = "203.0.113.1"
    drone.connected = True
    drone._flying = False
    return drone


class TestSetLightArgumentOrder(unittest.TestCase):
    """single_fly_lamplight has an undocumented argument-order bug --
    confirmed against real hardware that asking for red produces green and
    asking for green produces blue. set_light must send (g, b, r) to
    compensate, not (r, g, b) -- see the comment on HulaDrone.set_light."""

    def test_sends_g_b_r_not_r_g_b(self):
        api = _FakeApi()
        drone = _make_drone(api)

        drone.set_light(Led(r=255, g=0, b=0, mode=LedMode.SOLID), seconds=3)

        self.assertEqual(api.lamplight_calls, [(0, 0, 255, 3, 1)])


if __name__ == "__main__":
    unittest.main()
