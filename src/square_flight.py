"""
Fly the HULA drone in a 60cm square and land.

1. Power on the drone and make sure this PC is on the same Wi-Fi network
   as the drone (networking mode).
2. Update DRONE_IP below if the drone's address on your network changes.
3. Run: venv/Scripts/python.exe src/square_flight.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hula_net_fix

DRONE_IP = "192.168.1.62"
hula_net_fix.patch(DRONE_IP)

import pyhula

# Note: pyhula 1.0.8's directional methods are (distance, led) -- there is
# no speed parameter (that only exists in later versions like 1.1.7).
SIDE_CM = 60

api = pyhula.UserApi()

print("Connecting...")
if not api.connect(DRONE_IP):
    raise SystemExit("connect() failed - check Wi-Fi connection to the drone")

print("battery:", api.get_battery())

try:
    print("Taking off...")
    api.single_fly_takeoff()

    for leg in ("forward", "right", "back", "left"):
        print(f"Flying {leg} {SIDE_CM}cm...")
        getattr(api, f"single_fly_{leg}")(SIDE_CM)
finally:
    print("Landing...")
    api.single_fly_touchdown()
