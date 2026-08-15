"""Interactively exercise attachment-related methods: arm/disarm,
electromagnet, clamp, laser. Only meaningful if your drone actually has
these physical attachments -- without them, expect a FAILED/no-op
result, not necessarily a crash.

arm() spins the propellers at low speed without taking off -- keep clear
of the drone for that step. This script doesn't take off at all.

At each step: Enter to run it, 's' to skip, 'q' to stop early.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
from hula_sdk import HulaDrone

from _stepper import step

DRONE_IP = "192.168.1.62"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    step("arm() -- propellers spin at low speed, stay clear", drone.arm)
    step("disarm()", drone.disarm)

    step("set_electromagnet(attract=True)", lambda: drone.set_electromagnet(True))
    step("set_electromagnet(attract=False)", lambda: drone.set_electromagnet(False))
    step("set_clamp(is_open=True)", lambda: drone.set_clamp(True))
    step("set_clamp(is_open=False)", lambda: drone.set_clamp(False))

    step("fire_laser: single shot", lambda: drone.fire_laser(0))
    step("laser_hit()", drone.laser_hit)
