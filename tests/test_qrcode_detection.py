"""Unit tests for VideoStream.detect_qrcode()/wait_for_qrcode() -- no
drone, network, or ffmpeg needed. Generates a QR code with OpenCV's own
encoder and feeds it straight in as a decoded frame.
"""
import threading
import time
import unittest

import cv2

from hula_sdk.video import VideoStream


class _FakeDrone:
    def set_video_stream(self, enabled):
        pass


def _qrcode_frame(data: str, module_px: int = 10):
    encoder = cv2.QRCodeEncoder_create()
    qr = encoder.encode(data)  # single-channel module bitmap, no quiet zone
    # The detector needs a white quiet-zone border and enough pixels per
    # module to work with -- the raw encoder output is neither.
    quiet = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
    scaled = cv2.resize(quiet, None, fx=module_px, fy=module_px, interpolation=cv2.INTER_NEAREST)
    return cv2.cvtColor(scaled, cv2.COLOR_GRAY2BGR)


def _motion_blur_and_flatten(frame, length=17, gain=0.3, offset=105, angle_deg=10):
    """Stands in for an in-flight frame: directional motion blur (drone
    drift/vibration -- unlike the ground test's held-steady shot) plus
    squashed contrast (exposure). Mild blur alone turned out not to trip
    up the raw detector at all, hence the fairly aggressive defaults.

    How degraded a frame has to be before the raw detector gives up is a
    property of the installed OpenCV, not of hula_sdk -- 5.x reads
    blur that 4.6 could not -- so the parameters are arguments rather
    than constants, and _find_rescue_point() searches them at run time
    instead of any single tuning being baked in here."""
    import numpy as np

    if length <= 1:
        blurred = frame
    else:
        kernel = np.zeros((length, length))
        kernel[length // 2, :] = 1.0
        rotation = cv2.getRotationMatrix2D((length / 2 - 0.5, length / 2 - 0.5), angle_deg, 1)
        kernel = cv2.warpAffine(kernel, rotation, (length, length))
        kernel /= kernel.sum()
        blurred = cv2.filter2D(frame, -1, kernel)
    return (blurred.astype("float32") * gain + offset).clip(0, 255).astype("uint8")


# (module_px, blur length, contrast gain, brightness offset, blur angle).
# Ordered cheapest-and-most-likely-first: the leading entry is the point
# this regression was originally found and tuned at under opencv 4.6, so
# that build stops searching immediately.
_DEGRADATION_GRID = [
    (module_px, length, gain, offset, angle)
    for module_px in (14, 11, 8, 18)
    for length in (17, 13, 15, 19, 23, 27, 29)
    for gain, offset in ((0.3, 105), (1.0, 0), (0.6, 60), (0.45, 85), (0.8, 30), (0.2, 130))
    for angle in (10, 35, 70)
]


def _find_rescue_point(video):
    """Searches for a degradation the raw detector misses but the
    enhanced retry pass recovers, and returns the degraded frame -- or
    None if this OpenCV build has no such point.

    Searched rather than hardcoded on purpose. The band where the retry
    pass earns its keep is narrow and it *moves between OpenCV
    versions*: the (14, 17, 0.3, 10) point heading the grid above is a
    genuine rescue under opencv-python 4.6.0.66 (what this project
    pins) and a both-passes-fail point under 5.0.0 -- which is exactly
    how a hardcoded version of this test came to fail on a newer build
    while detect_qrcode() itself was working fine on both.
    """
    for module_px, length, gain, offset, angle in _DEGRADATION_GRID:
        frame = _motion_blur_and_flatten(
            _qrcode_frame("flight-blur", module_px=module_px),
            length=length, gain=gain, offset=offset, angle_deg=angle,
        )
        if video._decode_qr_frame(frame) is not None:
            continue  # raw pass got it -- the retry never runs, nothing to prove
        if video._decode_qr_frame(video._enhance_for_qr(frame)) is not None:
            return frame
    return None


class TestQrCodeDetection(unittest.TestCase):
    def _new_video(self):
        # Bypasses start()/stop() (no socket, no ffmpeg process) --
        # these methods only touch frame state, not the pipeline.
        return VideoStream.__new__(VideoStream)

    def setUp(self):
        self.video = self._new_video()
        self.video._qr_detector = None
        self.video._qr_clahe = None
        self.video._frame_cond = threading.Condition()
        self.video._latest_frame = None
        self.video._frame_seq = 0

    def test_detect_qrcode_on_explicit_frame(self):
        frame = _qrcode_frame("hula-sdk-test")
        result = self.video.detect_qrcode(frame)
        self.assertIsNotNone(result)
        data, points = result
        self.assertEqual(data, "hula-sdk-test")
        self.assertEqual(points.shape, (1, 4, 2))

    def test_detect_qrcode_returns_none_for_blank_frame(self):
        import numpy as np

        blank = np.zeros((100, 100, 3), dtype="uint8")
        self.assertIsNone(self.video.detect_qrcode(blank))

    def test_detect_qrcode_retries_enhanced_when_the_raw_pass_misses(self):
        # Regression: airborne frames (vibration, motion, exposure) are
        # blurrier/flatter than the steady ground shot this was
        # developed against, and that alone was enough to make the raw
        # detector miss a code that's plainly in view. detect_qrcode()
        # must retry with the enhanced pass rather than giving up on the
        # first miss.
        #
        # This asserts the control flow only -- that the retry happens,
        # on an enhanced frame, and that its result is what gets
        # returned. Whether the enhancement can actually rescue any
        # given frame depends on the installed OpenCV's detector; that's
        # the separate test below. Keeping them apart means a detector
        # improvement upstream can't make this contract look broken.
        seen = []
        sentinel = ("rescued-by-retry", "points")

        def fake_decode(frame):
            seen.append(frame)
            return None if len(seen) == 1 else sentinel

        self.video._decode_qr_frame = fake_decode
        frame = _qrcode_frame("flight-blur")

        self.assertEqual(self.video.detect_qrcode(frame), sentinel)
        self.assertEqual(len(seen), 2, "raw miss should be retried exactly once")
        self.assertIs(seen[0], frame, "first pass should see the untouched frame")
        self.assertIsNot(seen[1], frame, "retry should see an enhanced frame, not the original")

    def test_detect_qrcode_recovers_a_blurred_low_contrast_frame(self):
        # The other half: the enhancement pass genuinely recovers codes
        # the raw detector can't read, end to end through the public
        # method. The exact degradation that demonstrates this is
        # OpenCV-version-dependent, so it's searched for rather than
        # hardcoded -- see _find_rescue_point().
        degraded = _find_rescue_point(self.video)
        if degraded is None:
            self.skipTest(
                "no degradation in the search grid that OpenCV %s's raw detector "
                "misses but the enhanced pass recovers -- the retry pass buys "
                "nothing measurable on this build" % cv2.__version__
            )

        # Guaranteed by the search, restated so a failure here reads as
        # "detect_qrcode didn't use the retry" rather than a bad fixture.
        self.assertIsNone(self.video._decode_qr_frame(degraded))

        result = self.video.detect_qrcode(degraded)
        self.assertIsNotNone(result)
        data, _points = result
        self.assertEqual(data, "flight-blur")

    def test_detect_qrcode_swallows_opencv_degenerate_contour_error(self):
        # Regression: on some frames without a clean code, OpenCV's
        # detect() finds a zero-area contour and decode() raises
        # cv2.error instead of reporting "not found" -- seen live
        # mid-flight. detect_qrcode() must treat that as None, not let
        # it blow up the caller's scan loop.
        class _RaisingDetector:
            def detectAndDecode(self, frame):
                raise cv2.error("degenerate contour")

        self.video._qr_detector = _RaisingDetector()
        frame = _qrcode_frame("irrelevant")
        self.assertIsNone(self.video.detect_qrcode(frame))

    def test_wait_for_qrcode_blocks_until_a_frame_has_one(self):
        blank_frame = None
        import numpy as np

        blank_frame = np.zeros((100, 100, 3), dtype="uint8")
        qr_frame = _qrcode_frame("airborne-scan")

        def feed():
            time.sleep(0.05)
            with self.video._frame_cond:
                self.video._latest_frame = blank_frame
                self.video._frame_seq += 1
                self.video._frame_cond.notify_all()
            time.sleep(0.05)
            with self.video._frame_cond:
                self.video._latest_frame = qr_frame
                self.video._frame_seq += 1
                self.video._frame_cond.notify_all()

        threading.Thread(target=feed, daemon=True).start()
        data, points = self.video.wait_for_qrcode(timeout=5)
        self.assertEqual(data, "airborne-scan")

    def test_wait_for_qrcode_times_out_with_no_matching_frame(self):
        with self.assertRaises(TimeoutError):
            self.video.wait_for_qrcode(timeout=0.2)

    def test_scan_qrcode_live_returns_as_soon_as_a_frame_matches(self):
        import unittest.mock as mock

        blank_frame = __import__("numpy").zeros((100, 100, 3), dtype="uint8")
        qr_frame = _qrcode_frame("live-scan")
        self.video._latest_frame = blank_frame

        def feed():
            time.sleep(0.05)
            with self.video._frame_cond:
                self.video._latest_frame = qr_frame
                self.video._frame_seq += 1
                self.video._frame_cond.notify_all()

        threading.Thread(target=feed, daemon=True).start()

        # Stub the GUI calls -- no real window in a headless test run --
        # while still exercising the loop's own find-or-quit decisions.
        with mock.patch("cv2.imshow"), \
             mock.patch("cv2.waitKey", return_value=-1), \
             mock.patch("cv2.getWindowProperty", return_value=1), \
             mock.patch("cv2.destroyWindow"):
            result = self.video.scan_qrcode_live(timeout=5)

        self.assertIsNotNone(result)
        data, points = result
        self.assertEqual(data, "live-scan")

    def test_scan_qrcode_live_stops_on_quit_key(self):
        import unittest.mock as mock
        import numpy as np

        self.video._latest_frame = np.zeros((100, 100, 3), dtype="uint8")

        def feed():
            for _ in range(20):
                time.sleep(0.01)
                with self.video._frame_cond:
                    self.video._latest_frame = np.zeros((100, 100, 3), dtype="uint8")
                    self.video._frame_seq += 1
                    self.video._frame_cond.notify_all()

        threading.Thread(target=feed, daemon=True).start()

        with mock.patch("cv2.imshow"), \
             mock.patch("cv2.waitKey", return_value=ord("q")), \
             mock.patch("cv2.getWindowProperty", return_value=1), \
             mock.patch("cv2.destroyWindow"):
            result = self.video.scan_qrcode_live(timeout=5)

        self.assertIsNone(result)

    def test_scan_qrcode_live_saves_debug_frames_when_nothing_found(self):
        import glob
        import tempfile
        import unittest.mock as mock
        import numpy as np

        self.video._latest_frame = np.zeros((100, 100, 3), dtype="uint8")

        def feed():
            for _ in range(5):
                time.sleep(0.02)
                with self.video._frame_cond:
                    self.video._latest_frame = np.zeros((100, 100, 3), dtype="uint8")
                    self.video._frame_seq += 1
                    self.video._frame_cond.notify_all()

        threading.Thread(target=feed, daemon=True).start()

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("cv2.imshow"), \
                 mock.patch("cv2.waitKey", return_value=ord("q")), \
                 mock.patch("cv2.getWindowProperty", return_value=1), \
                 mock.patch("cv2.destroyWindow"):
                self.video.scan_qrcode_live(timeout=5, debug_dir=tmp, debug_interval=0.0)

            saved = glob.glob(f"{tmp}/*.jpg")
            self.assertGreater(len(saved), 0)
            self.assertTrue(any(name.endswith("_last.jpg") for name in saved))


if __name__ == "__main__":
    unittest.main()
