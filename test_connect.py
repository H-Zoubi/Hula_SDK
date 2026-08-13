import hula_net_fix

DRONE_IP = "192.168.1.62"
hula_net_fix.patch(DRONE_IP)

import pyhula

api = pyhula.UserApi()

print("Connecting...")
ok = api.connect(DRONE_IP)
print("connect() ->", ok)

if ok:
    print("battery:", api.get_battery())
    print("coordinate:", api.get_coordinate())
    print("yaw/pitch/roll:", api.get_yaw())
    print("plane id:", api.get_plane_id())
