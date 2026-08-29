"""hula_sdk's own video receiver, live: opens a window showing decoded
frames continuously. Press 'q' with the window focused to stop.

Confirmed working for single-frame capture (see working_video_stream.py)
-- this exercises continuous display specifically, which hasn't been
verified separately.

Ground-based -- doesn't take off.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once), plus a
real ffmpeg executable on PATH (not pyhula's bundled DLLs).
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    with drone.video() as video:
        print("Opening live preview -- press 'q' in the window to stop.")
        video.show_live()
