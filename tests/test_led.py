import unittest

from hula_sdk import Led, LedMode


class TestLed(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(Led().to_dict(), {"r": 0, "g": 0, "b": 0, "mode": 1})

    def test_custom_values(self):
        led = Led(r=16, g=15, b=100, mode=LedMode.RAINBOW)
        self.assertEqual(led.to_dict(), {"r": 16, "g": 15, "b": 100, "mode": 16})


if __name__ == "__main__":
    unittest.main()
