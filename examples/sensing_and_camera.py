"""Sensing/camera/lighting methods. Ground-based -- doesn't take off,
since these don't require flight to call, only to produce meaningful
results (the camera/QR/tag methods likely need the drone airborne and
pointed at something to return anything useful; feel free to add a
takeoff() at the top and land() at the bottom once you're ready to test
that).

Lighting/obstacle/color/tag/QR call mechanics are verified working (see
README's "Tested vs untested") -- they return the documented shape
without crashing. Actual positive tag/QR *recognition* hasn't been
confirmed yet, though: two attempts holding real panels in front of the
drone both still came back with result: False (one had non-zero x/y/angle
in the reply, which might mean a partial/near miss, or might just be
stale data -- inconclusive). If you try again: the SDK docs say the
recognition window is only ~300ms after the call triggers, so the panel
needs to already be in view and steady *before* you press Enter on that
step, not held up afterward -- and it's not confirmed which physical
camera (front vs. any downward-facing one) these actually use, so try
presenting the panel to both if the front doesn't work.

The video/camera steps are NOT confirmed working, and fail differently
depending on what ran before them:
- Without set_video_stream(True) first: fails fast, with a native
  assertion crash (Assertion desc failed at libswscale/...) -- the
  process dies within a couple seconds on its own.
- With set_video_stream(True) first: a heavy, sustained flood of decoder
  errors that has been inconsistent to stop -- sometimes it stops on its
  own, sometimes Ctrl+C works if it lands during the stepper's input()
  prompt, sometimes neither works and you need
  Stop-Process -Force / Task Manager.

See the README for full details. Skip these steps ('s') unless you're
specifically trying to debug this, and be ready to force-kill the
process if it doesn't stop.

Some steps need props: an AI tag or a QR code sticker with a known ID in
view. Without them, expect a FAILED/no-op result, not a crash -- that's
still useful information.

At each step: Enter to run it, 's' to skip, 'q' to stop early.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
from hula_sdk import HulaDrone, Led, LedMode

from _stepper import step

DRONE_IP = "192.168.1.62"
QR_ID = 0  # change to match a QR sticker you actually have, if any

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    step("set_light: rainbow for 3s", lambda: drone.set_light(Led(mode=LedMode.RAINBOW), 3))
    step("set_light: solid red for 2s", lambda: drone.set_light(Led(r=255, g=0, b=0), 2))

    step("set_obstacle_avoidance(True)", lambda: drone.set_obstacle_avoidance(True))
    step("obstacles()", drone.obstacles)
    step("set_obstacle_avoidance(False)", lambda: drone.set_obstacle_avoidance(False))

    step("read_color()", drone.read_color)
    step("identify_tag(0) -- looks for digit tag '0'", lambda: drone.identify_tag(0))
    step(f"align_to_qrcode({QR_ID})", lambda: drone.align_to_qrcode(QR_ID))
    step(f"recognize_qrcode({QR_ID})", lambda: drone.recognize_qrcode(QR_ID))
    step(f"track_qrcode({QR_ID}, 3s)", lambda: drone.track_qrcode(QR_ID, 3))
    step("set_qr_positioning(True)", lambda: drone.set_qr_positioning(True))
    step("set_qr_positioning(False)", lambda: drone.set_qr_positioning(False))

    print("\n-- video/camera: not confirmed working, see docstring above --")
    step("set_video_stream(True)", lambda: drone.set_video_stream(True))
    step("open_video_window()", drone.open_video_window)
    step("take_photo()", drone.take_photo)
    step("set_camera_angle(down, 20deg)", lambda: drone.set_camera_angle(1, 20))
    step("set_recording(True)", lambda: drone.set_recording(True))
    step("set_recording(False)", lambda: drone.set_recording(False))
    step("set_video_stream(False)", lambda: drone.set_video_stream(False))
