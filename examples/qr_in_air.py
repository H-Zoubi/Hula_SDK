"""Detects a QR code while airborne, using hula_sdk's own video stream
(see hula_sdk/video.py) rather than pyhula's built-in recognize_qrcode,
which only has a ~300ms recognition window per call (see
wait_for_qrcode.py). This decodes every frame as it arrives, so it
catches the code whenever it drifts into view -- and shows a live
window the whole time so you can see what the drone sees while aiming
it at the code.

Takes off, hovers in place, and scans continuously (window open) until
a QR code is found, 'q' is pressed, or DETECT_TIMEOUT_SECONDS pass with
no frames at all, then lands either way.

Saves a frame to DEBUG_DIR roughly once a second while nothing's been
found (plus the final frame), so a failed run leaves behind real
in-flight images to inspect -- useful for telling apart "code wasn't
actually in view", "too small/far", "motion blur", or "just needs more
time" instead of guessing.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once), plus a
real ffmpeg executable on PATH (not pyhula's bundled DLLs).
"""
from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"
DETECT_TIMEOUT_SECONDS = 20
DEBUG_DIR = "qr_debug_frames"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    with drone.video() as video:
        drone.takeoff()
        try:
            print("Airborne -- scanning for a QR code, live window open (press 'q' to give up early)...")
            try:
                result = video.scan_qrcode_live(timeout=DETECT_TIMEOUT_SECONDS, debug_dir=DEBUG_DIR)
            except TimeoutError:
                result = None

            if result is not None:
                data, points = result
                print(f"FOUND: {data!r}")
                print("corners:", points)
            else:
                print(f"No QR code found. Check {DEBUG_DIR}/ for saved frames.")
        finally:
            drone.land()
