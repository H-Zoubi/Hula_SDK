import pyhula

ver = pyhula.get_version()
print("version")
print(ver)

api = pyhula.UserApi()
if not api.connect():
    print("connect error")
else:
    print("connection to station by wifi")
api.single_fly_takeoff()
api.single_fly_touchdown()
