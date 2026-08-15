"""EXPERIMENTAL, and the original hypothesis this was built to test has
already been DISPROVEN -- see README's "The camera/video pipeline".

This adds a warmup delay after enabling the video stream, on the theory
that the decoder was being asked for frames before the drone's encoder
produced a keyframe. That turned out to be wrong: the decoder error
flood starts as soon as open_video_window() runs (or a background thread
it kicks off), regardless of when anything downstream actually asks for
a frame -- so no amount of waiting before take_photo() changes anything.
Left in place as a known-negative result and a template for further
experiments (e.g. testing distance from the router, since RTP
packet-loss is the one variable not yet isolated).

This is a single attempt, not a loop -- if it floods or crashes, you'll
know exactly which line caused it. Be ready to force-kill the process
(PowerShell: Stop-Process -Force, or Task Manager) if it hangs; Ctrl+C is
not reliable against the native decoder (see README).

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
import time

from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"
WARMUP_SECONDS = 3

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    print("Enabling video stream...")
    drone.set_video_stream(True)

    print(f"Warming up for {WARMUP_SECONDS}s (letting the encoder produce a keyframe)...")
    time.sleep(WARMUP_SECONDS)

    try:
        print("Opening video window...")
        drone.open_video_window()

        print(f"Warming up {WARMUP_SECONDS}s more before take_photo()...")
        time.sleep(WARMUP_SECONDS)

        print("Taking photo...")
        drone.take_photo()

        print("take_photo() returned without incident.")
    finally:
        print("Disabling video stream...")
        drone.set_video_stream(False)
