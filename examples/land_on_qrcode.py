"""Aligns over a QR code placed on the floor, then lands on it -- using
pyhula's own onboard QR alignment, not hula_sdk's custom OpenCV
detector (see qr_in_air.py for that approach instead).

Uses sensor=OPTICAL_FLOW (the downward-facing sensor) -- appropriate
for a code on the floor.

align_to_qrcode(sensor=OPTICAL_FLOW) has reliably hung across multiple
real attempts, confirmed via traceback into pyhula's own compiled
TaskController._wait_state()/Event.wait_for_signal() -- the call's own
completion signal never arrives. BUT: one of those hangs, once Ctrl+C'd
past, landed the drone right on the code -- meaning the alignment
maneuver itself actually completes on the drone; it's specifically the
Python-side wait for confirmation that's broken, not the maneuver.

So instead of blocking on align_to_qrcode()'s return (and needing a
manual, well-timed Ctrl+C), this calls it in a background thread and
waits up to ALIGN_WAIT_SECONDS for a result. If that confirmation never
comes, it just proceeds to land() without it -- same thing you'd do by
hand, minus the raw KeyboardInterrupt landing wherever the interpreter
happened to be inside pyhula's compiled code (arguably riskier than
just letting that thread keep waiting on its own while the main thread
moves on). The background call is a daemon thread and is simply
abandoned if it never returns -- it won't block the process from
exiting.

Caveat: this hasn't been proven safe against overlapping vendor SDK
calls on the same connection -- if align_to_qrcode() is still
genuinely in flight (not just stuck on a dead wait) when land() fires,
that's two commands live on one socket at once, which could behave
unpredictably. The one real data point so far (a manually Ctrl+C'd
hang followed by a clean land()) suggests this is survivable in
practice, not that it's guaranteed safe -- still be ready to Ctrl+C if
land() itself doesn't return promptly.

Also exercises set_qr_positioning() (Plane_cmd_switch_QR, "QR code
positioning switch") -- wrapped but never called against hardware
before this project. Included since the name suggests it gates QR-based
positioning, but that's unconfirmed -- if alignment doesn't work, try
commenting it out to see if it's implicated.

There is no dedicated "land on QR" call in the vendor SDK -- this is
one align attempt (bounded), then a plain land() regardless of outcome.

Ground-based takeoff, real flight. Put a QR sticker matching QR_ID on
the floor under where the drone will hover.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
import queue
import threading

from hula_sdk import HulaDrone, QrSensor

DRONE_IP = "192.168.1.62"
QR_ID = 0  # change to match a QR sticker you actually have
ALIGN_WAIT_SECONDS = 8  # the physical maneuver appears to finish well within this; its own confirmation may never arrive though


def _log(msg):
    # flush=True: these are printed right before/around blocking vendor
    # SDK calls specifically so that if one of those calls hangs, the
    # very last line on screen tells you exactly which call it was
    # stuck in, rather than the ambiguous partial output a buffered
    # print could leave behind.
    print(msg, flush=True)


def _align_in_background(drone, qr_id, sensor, result_queue):
    try:
        result_queue.put(("ok", drone.align_to_qrcode(qr_id, sensor=sensor)))
    except Exception as e:
        result_queue.put(("error", e))


with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    _log("Calling set_qr_positioning(True)...")
    drone.set_qr_positioning(True)
    _log("set_qr_positioning(True) returned.")
    try:
        _log("Calling takeoff()...")
        drone.takeoff()
        _log(f"Airborne over QR code {QR_ID} on the floor.")

        _log(
            f"Calling align_to_qrcode(sensor=OPTICAL_FLOW) in the background, waiting up to "
            f"{ALIGN_WAIT_SECONDS}s for confirmation -- its own completion signal has failed to "
            "arrive before (see module docstring), so this doesn't block on it forever..."
        )
        result_queue = queue.Queue(maxsize=1)
        align_thread = threading.Thread(
            target=_align_in_background,
            args=(drone, QR_ID, QrSensor.OPTICAL_FLOW, result_queue),
            daemon=True,
        )
        align_thread.start()
        try:
            status, value = result_queue.get(timeout=ALIGN_WAIT_SECONDS)
        except queue.Empty:
            _log(
                f"No confirmation from align_to_qrcode() within {ALIGN_WAIT_SECONDS}s -- "
                "proceeding to land without waiting further for it."
            )
        else:
            if status == "error":
                print(f"align_to_qrcode() raised: {type(value).__name__}: {value}")
            else:
                _log(f"align_to_qrcode() returned: {value}")
                if value.get("result"):
                    print(f"Aligned: {value}")
                else:
                    print(f"Not aligned: {value} -- landing at current position anyway.")
    finally:
        _log("Calling land()...")
        drone.land()
        _log("Calling set_qr_positioning(False)...")
        drone.set_qr_positioning(False)
        _log("set_qr_positioning(False) returned.")
