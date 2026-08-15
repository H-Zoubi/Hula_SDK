"""Read every telemetry getter -- all of them verified against hardware.
Doesn't fly -- safe to run any time the drone is reachable, battery
permitting.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())
    print("coordinate:", drone.coordinate())
    print("attitude (yaw/pitch/roll):", drone.attitude())
    print("plane id:", drone.plane_id())
    print("obstacles:", drone.obstacles())
    print("acceleration:", drone.acceleration())
    print("velocity:", drone.velocity())
    print("tof_height:", drone.tof_height())
