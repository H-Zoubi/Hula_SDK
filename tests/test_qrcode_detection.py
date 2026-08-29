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


def _motion_blur_and_flatten(frame):
    """Stands in for an in-flight frame: directional motion blur (drone
    drift/vibration -- unlike the ground test's held-steady shot) plus
    squashed contrast (exposure). Parameters were picked by search to
    land exactly where OpenCV's raw detector misses but the enhanced
    retry pass (CLAHE contrast + sharpen) recovers -- not an arbitrary
    "add some blur", since mild blur alone turned out not to trip up
    the raw detector at all in testing."""
    import numpy as np

    length, angle_deg = 17, 10
    kernel = np.zeros((length, length))
    kernel[length // 2, :] = 1.0
    rotation = cv2.getRotationMatrix2D((length / 2 - 0.5, length / 2 - 0.5), angle_deg, 1)
    kernel = cv2.warpAffine(kernel, rotation, (length, length))
    kernel /= kernel.sum()
    blurred = cv2.filter2D(frame, -1, kernel)
    return (blurred.astype("float32") * 0.3 + 105).clip(0, 255).astype("uint8")


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

    def test_detect_qrcode_recovers_a_blurred_low_contrast_frame(self):
        # Regression: airborne frames (vibration, motion, exposure) are
        # blurrier/flatter than the steady ground shot this was
        # developed against, and that alone was enough to make the raw
        # detector miss a code that's plainly in view. detect_qrcode()
        # must retry with the enhanced pass rather than giving up on the
        # first miss.
        degraded = _motion_blur_and_flatten(_qrcode_frame("flight-blur", module_px=14))

        raw_only = self.video._decode_qr_frame(degraded)
        self.assertIsNone(raw_only, "test frame isn't degraded enough to exercise the retry path")

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
