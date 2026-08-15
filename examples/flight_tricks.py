"""Interactively exercise the wrapped-but-untested flight methods, one
at a time, so you can watch each and stop if anything looks wrong.

Needs clear space -- it takes off and tries several maneuvers: hover,
turns, up/down, bounce, straight/curved flight to relative coordinates,
a circle, a spin, a flip, and line-following (only meaningful with an
actual line under the drone -- expect a FAILED/no-op result without one,
that's fine, not a crash).

At each step: Enter to run it, 's' to skip, 'q' to stop early. Landing
always runs regardless -- either explicitly at the end, or via
HulaDrone's context-manager safety net if you quit early or a step
raises.

Requires: venv\\Scripts\\python.exe -m pip install -e . (once)
"""
from hula_sdk import HulaDrone, FlipDirection

from _stepper import step

DRONE_IP = "192.168.1.62"

with HulaDrone(DRONE_IP) as drone:
    print("battery:", drone.battery())

    step("takeoff", drone.takeoff)
    step("hover 3s", lambda: drone.hover(3))
    step("turn_left 90deg", lambda: drone.turn_left(90))
    step("turn_right 90deg", lambda: drone.turn_right(90))
    step("up 30cm", lambda: drone.up(30))
    step("down 30cm", lambda: drone.down(30))
    step("bounce x3, 20cm", lambda: drone.bounce(3, 20))
    step("fly_to (50, 50, 0)", lambda: drone.fly_to(50, 50, 0))
    step("fly_to back to start (-50, -50, 0)", lambda: drone.fly_to(-50, -50, 0))
    step("circle, radius 50cm", lambda: drone.circle(50))
    step("spin 1 rotation", lambda: drone.spin(1))
    step("flip forward", lambda: drone.flip(FlipDirection.FORWARD))
    step("curve_to (50, 50, 0)", lambda: drone.curve_to(50, 50, 0))
    step("follow_line 100cm, black line", lambda: drone.follow_line(100, line_color=0))

    print("\nLanding...")
    drone.land()
