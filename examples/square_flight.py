"""Fly the HULA drone in a 60cm square and land.

1. `venv\\Scripts\\python.exe -m pip install -e .` from the repo root, once.
2. Power on the drone, same Wi-Fi network as this PC (networking mode).
3. Update DRONE_IP below to match the drone's current address.
4. Run from the repo root:
   venv\\Scripts\\python.exe examples\\square_flight.py

Needs clear space -- it actually flies. If anything goes wrong mid-square,
HulaDrone's context manager lands it anyway (see hula_sdk/client.py).
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"
SIDE_CM = 60

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    print("Taking off...")
    drone.takeoff()

    print(f"Flying a {SIDE_CM}cm square...")
    drone.square(SIDE_CM)

    print("Landing...")
    drone.land()
