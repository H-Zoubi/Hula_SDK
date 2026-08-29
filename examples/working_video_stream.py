"""hula_sdk's own video receiver -- bypasses pyhula's broken bundled
ffmpeg wrapper entirely (see README's "The camera/video pipeline").
Receives and reassembles the RTP/H.264 stream itself, then decodes it
with a real, separately-installed ffmpeg on PATH.

Ground-based -- doesn't take off.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once), plus a
real ffmpeg executable on PATH (not pyhula's bundled DLLs).
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    with drone.video() as video:
        print("Waiting for a decoded frame...")
        frame = video.read_frame(timeout=10)
        print("Got a frame:", frame.shape)

        video.save_photo("photo.jpg")
        print("Saved photo.jpg")
