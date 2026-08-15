"""Poll for a QR code repeatedly until it's recognized, or Ctrl+C.

Works around the SDK's short (~300ms) recognition window: a single
recognize_qrcode() call needs the panel in view at that exact instant,
which is hard to time by hand. This just keeps calling it so you have
as long as you need to hold the panel up in front of the camera.

Ground-based -- doesn't take off. Add a takeoff()/land() around the loop
if you want to test this while airborne instead.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
import time

from hula_sdk import HulaDrone

DRONE_IP = "192.168.1.62"
QR_ID = 0  # change to match a QR sticker you actually have
POLL_DELAY_SECONDS = 0.3

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())
    print(f"Polling for QR code {QR_ID} -- hold it up in front of the camera.")
    print("Ctrl+C to stop.\n")

    attempt = 0
    try:
        while True:
            attempt += 1
            try:
                result = drone.recognize_qrcode(QR_ID)
            except Exception as e:
                print(f"[{attempt}] call failed: {type(e).__name__}: {e}")
                time.sleep(POLL_DELAY_SECONDS)
                continue

            if result.get("result"):
                print(f"[{attempt}] FOUND: {result}")
                break

            print(f"[{attempt}] not found: {result}")
            time.sleep(POLL_DELAY_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped by user -- no match found.")
