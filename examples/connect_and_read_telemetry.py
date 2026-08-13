"""Connect to the drone and print telemetry. Does not fly.

1. `venv\\Scripts\\python.exe -m pip install -e .` from the repo root, once.
2. Power on the drone and make sure this PC is on the same Wi-Fi network
   as the drone (networking mode -- see README).
3. Update DRONE_IP below to match the drone's current address.
4. Run from the repo root:
   venv\\Scripts\\python.exe examples\\connect_and_read_telemetry.py
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())
    print("coordinate:", drone.coordinate())
    print("attitude (yaw/pitch/roll):", drone.attitude())
    print("plane id:", drone.plane_id())
