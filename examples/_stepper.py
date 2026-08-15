"""Shared helper for the example scripts below: runs each step
interactively so you can watch what the drone does and confirm before the
next one, and so one step failing doesn't stop the rest from being tried.
"""


def step(description, action):
    print(f"\n--- {description} ---")
    choice = input("Press Enter to run, 's' to skip, 'q' to stop: ").strip().lower()
    if choice == "q":
        raise KeyboardInterrupt("stopped by user")
    if choice == "s":
        print("skipped")
        return None
    try:
        result = action()
        if result is not None:
            print("result:", result)
        return result
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        return None
