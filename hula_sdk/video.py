"""
hula_sdk's own video receiver -- bypasses pyhula's broken bundled ffmpeg
wrapper entirely (see README's "The camera/video pipeline" for how that
was diagnosed: a raw packet capture showed the RTP stream itself is
complete and correct -- 0% loss, SPS/PPS present -- so the bug is inside
pyhula's own demuxer, not the network or the drone's encoder).

This receives RTP packets directly, reassembles H.264 NAL units with
hula_sdk._rtp, and feeds them to a real, separately-installed ffmpeg
executable (NOT pyhula's bundled DLLs) to decode. ffmpeg outputs raw
decoded frames (bgr24) rather than re-encoding to a still-image format
per frame -- avoids a whole extra encode pass on frames that are often
about to be discarded as stale anyway (see read latency notes on
_stdout_loop).

Requires ffmpeg on PATH.
"""
import re
import shutil
import socket
import subprocess
import threading
from typing import Optional

from . import _rtp
from .exceptions import HulaError

_DIMENSIONS_RE = re.compile(rb"Video:.*?(\d{2,5})x(\d{2,5})")


class VideoStreamError(HulaError):
    """Raised when the video stream can't be started."""


class VideoStream:
    """Receives and decodes the drone's video stream.

    Usage:
        with HulaDrone(ip) as drone:
            with drone.video() as video:
                frame = video.read_frame()   # numpy BGR array (needs cv2)
                video.save_photo("photo.jpg")
    """

    def __init__(self, drone, listen_port: int = 9070, ffmpeg_path: Optional[str] = None):
        self._drone = drone
        self._listen_port = listen_port
        self._ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        if not self._ffmpeg_path:
            raise VideoStreamError(
                "ffmpeg not found on PATH. hula_sdk.video needs a real, "
                "separately-installed ffmpeg executable -- not pyhula's "
                "bundled DLLs, which are what's broken."
            )

        self._sock: Optional[socket.socket] = None
        self._proc: Optional[subprocess.Popen] = None
        self._recv_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()
        self._reassembler = _rtp.NalReassembler()

        self._dims_ready = threading.Event()
        self._frame_width = 0
        self._frame_height = 0

        # A Condition (not a plain Event) so show_live() can block until
        # specifically the *next new* frame, instead of busy-spinning:
        # read_frame() alone would return instantly on every call once
        # any frame has arrived, since nothing ever cleared the old
        # Event -- that redundantly re-decoded/re-displayed stale frames
        # far faster than the ~30fps source, burning CPU on the display
        # thread that the decode thread could've used instead.
        self._frame_cond = threading.Condition()
        self._latest_frame = None
        self._frame_seq = 0

        self._qr_detector = None  # lazy: cv2.QRCodeDetector(), only needed if QR methods are used
        self._qr_clahe = None  # lazy: cv2.CLAHE, contrast boost for the enhanced retry pass

    def __enter__(self) -> "VideoStream":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("0.0.0.0", self._listen_port))
        self._sock.settimeout(1.0)

        self._proc = subprocess.Popen(
            [
                self._ffmpeg_path,
                "-loglevel", "info",  # need the "Video: ... WxH" line on stderr
                "-probesize", "32",
                "-analyzeduration", "0",
                "-flags", "low_delay",
                "-threads", "1",  # avoid frame-parallel decoding's inherent latency
                "-f", "h264",
                "-i", "pipe:0",
                "-f", "rawvideo",
                "-pix_fmt", "bgr24",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self._stopping.clear()
        self._dims_ready.clear()
        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True)
        self._stdout_thread = threading.Thread(target=self._stdout_loop, daemon=True)
        self._recv_thread.start()
        self._stderr_thread.start()
        self._stdout_thread.start()

        self._drone.set_video_stream(True)

    def stop(self) -> None:
        self._stopping.set()
        try:
            self._drone.set_video_stream(False)
        except Exception:
            pass
        if self._sock is not None:
            self._sock.close()
        if self._proc is not None:
            try:
                self._proc.stdin.close()
            except Exception:
                pass
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        for t in (self._recv_thread, self._stderr_thread, self._stdout_thread):
            if t is not None:
                t.join(timeout=2)
        if self._proc is not None:
            # Only safe to close these once the reader threads have
            # actually stopped touching them (joined above).
            for pipe in (self._proc.stdout, self._proc.stderr):
                try:
                    pipe.close()
                except Exception:
                    pass

    def read_frame(self, timeout: Optional[float] = 5.0):
        """Returns the latest available frame immediately, or blocks
        until the first one arrives (raises TimeoutError past `timeout`).
        Returns a numpy BGR array."""
        with self._frame_cond:
            if self._latest_frame is None:
                if not self._frame_cond.wait_for(lambda: self._latest_frame is not None, timeout=timeout):
                    raise TimeoutError("No video frame decoded within timeout")
            return self._latest_frame

    def _wait_for_new_frame(self, after_seq: int, timeout: Optional[float]):
        """Blocks until a frame newer than `after_seq` is available (not
        just whatever's already latest) -- what show_live() uses so it
        genuinely waits for new data instead of busy-spinning on
        read_frame(), which would return the same stale frame instantly
        on every call once any frame has ever arrived."""
        with self._frame_cond:
            if not self._frame_cond.wait_for(lambda: self._frame_seq != after_seq, timeout=timeout):
                raise TimeoutError("No new video frame within timeout")
            return self._latest_frame, self._frame_seq

    def save_photo(self, path: str, timeout: Optional[float] = 5.0) -> None:
        """Convenience: read_frame() and write it out with cv2.imwrite."""
        import cv2

        frame = self.read_frame(timeout=timeout)
        cv2.imwrite(path, frame)

    def detect_qrcode(self, frame=None):
        """Runs OpenCV's QR detector on a single frame (defaults to the
        latest decoded one). Returns (data, points) if a code was found
        and decoded -- `points` is the 4-corner polygon in frame
        coordinates, handy for centering the drone on it -- or None if
        no QR code was found.

        This is separate from HulaDrone.recognize_qrcode(), which uses
        pyhula's built-in detector and only has a ~300ms recognition
        window per call. Decoding our own stream lets us check every
        frame as it arrives instead of polling blind.

        Airborne frames are routinely blurrier and lower-contrast than a
        held-steady ground shot (propeller vibration, hover drift,
        exposure) -- often just enough to stop the raw frame from
        decoding even though the code is plainly in view. So a failed
        raw pass gets one retry against a contrast-boosted, sharpened
        version of the same frame before this gives up on it."""
        if frame is None:
            frame = self.read_frame()
        result = self._decode_qr_frame(frame)
        if result is not None:
            return result
        return self._decode_qr_frame(self._enhance_for_qr(frame))

    def _decode_qr_frame(self, frame):
        import cv2

        if self._qr_detector is None:
            self._qr_detector = cv2.QRCodeDetector()
        try:
            data, points, _ = self._qr_detector.detectAndDecode(frame)
        except cv2.error:
            # OpenCV bug, not a real detection failure: on some frames
            # without a clean QR code, detect() finds degenerate corner
            # points (zero contour area) and decode() throws instead of
            # just reporting "not found". Treat it the same as "not
            # found" so one bad frame doesn't kill the whole scan.
            return None
        if not data:
            return None
        return data, points

    def _enhance_for_qr(self, frame):
        """Grayscale + local contrast boost (CLAHE) + a mild sharpening
        kernel -- cheap enough to run on every frame that fails the raw
        pass, and it's specifically local contrast and edge softness
        that motion blur/vibration degrade."""
        import cv2
        import numpy as np

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._qr_clahe is None:
            self._qr_clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        contrasted = self._qr_clahe.apply(gray)
        sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened = cv2.filter2D(contrasted, -1, sharpen_kernel)
        return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    def wait_for_qrcode(self, timeout: Optional[float] = None):
        """Decodes frames as they arrive and returns as soon as one
        contains a readable QR code: (data, points). Blocks until found,
        or raises TimeoutError once `timeout` seconds have elapsed
        (None waits forever)."""
        import time

        deadline = None if timeout is None else time.monotonic() + timeout
        last_seq = 0
        while True:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                raise TimeoutError("No QR code detected within timeout")
            frame, last_seq = self._wait_for_new_frame(last_seq, remaining)
            result = self.detect_qrcode(frame)
            if result is not None:
                return result

    def scan_qrcode_live(
        self,
        window_name: str = "Hula QR scan",
        quit_key: str = "q",
        timeout: Optional[float] = 20.0,
        debug_dir: Optional[str] = None,
        debug_interval: float = 1.0,
    ):
        """Like show_live(), but also runs detect_qrcode() on every
        frame and draws the result over the video as it displays.
        Returns (data, points) as soon as a QR code is found, or None
        if `quit_key` is pressed or the window is closed first. Raises
        TimeoutError if `timeout` seconds pass with no new frame at all
        (initial wait included) -- same as show_live().

        If `debug_dir` is set, saves an undetected frame there roughly
        every `debug_interval` seconds (and always the very last frame)
        as plain .jpg files -- for inspecting offline what the camera
        actually saw when detection isn't finding a code that's visibly
        in the live window, e.g. to check for motion blur, distance, or
        exposure problems specific to being airborne."""
        import time

        import cv2

        if debug_dir is not None:
            import os

            os.makedirs(debug_dir, exist_ok=True)

        last_seq = 0
        found = None
        last_debug_save = 0.0
        last_raw_frame = None
        try:
            while True:
                frame, last_seq = self._wait_for_new_frame(last_seq, timeout)
                last_raw_frame = frame
                result = self.detect_qrcode(frame)
                if result is not None:
                    data, points = result
                    frame = frame.copy()
                    pts = points.reshape(-1, 2).astype(int)
                    cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
                    cv2.putText(frame, data, tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                elif debug_dir is not None:
                    now = time.monotonic()
                    if now - last_debug_save >= debug_interval:
                        last_debug_save = now
                        cv2.imwrite(os.path.join(debug_dir, f"frame_{last_seq:05d}.jpg"), last_raw_frame)
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if result is not None:
                    found = result
                    break
                if key == ord(quit_key):
                    break
                # imshow() doesn't know the user clicked the window's own
                # close button -- it'll just silently recreate the window
                # next frame unless we explicitly check visibility here.
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            if debug_dir is not None and found is None and last_raw_frame is not None:
                cv2.imwrite(os.path.join(debug_dir, f"frame_{last_seq:05d}_last.jpg"), last_raw_frame)
            try:
                cv2.destroyWindow(window_name)
            except cv2.error:
                pass  # already gone if the user closed it via the X button
        return found

    def show_live(self, window_name: str = "Hula video", quit_key: str = "q", timeout: Optional[float] = 10.0) -> None:
        """Opens a window showing decoded frames as they arrive. Blocks
        until `quit_key` is pressed with the window focused (default
        'q'), or `timeout` seconds pass with no new frame at all (initial
        wait included)."""
        import cv2

        last_seq = 0
        try:
            while True:
                frame, last_seq = self._wait_for_new_frame(last_seq, timeout)
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord(quit_key):
                    break
                # imshow() doesn't know the user clicked the window's own
                # close button -- it'll just silently recreate the window
                # next frame unless we explicitly check visibility here.
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            try:
                cv2.destroyWindow(window_name)
            except cv2.error:
                pass  # already gone if the user closed it via the X button

    # -- internals ------------------------------------------------------

    def _receive_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                data, _addr = self._sock.recvfrom(65536)
            except OSError:
                break
            payload = _rtp.rtp_payload(data)
            if payload is None:
                continue
            for nal in self._reassembler.feed(payload):
                self._emit_nal(nal)

    def _emit_nal(self, nal: bytes) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        try:
            self._proc.stdin.write(_rtp.to_annex_b(nal))
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def _stderr_loop(self) -> None:
        """Finds the frame resolution from ffmpeg's own startup log line
        (e.g. "Video: h264 ..., 1280x720, ..."), then keeps draining
        stderr for the rest of the process's life so ffmpeg never blocks
        on a full stderr pipe."""
        stderr = self._proc.stderr
        for line in iter(stderr.readline, b""):
            if self._dims_ready.is_set():
                continue
            m = _DIMENSIONS_RE.search(line)
            if m:
                self._frame_width = int(m.group(1))
                self._frame_height = int(m.group(2))
                self._dims_ready.set()

    def _stdout_loop(self) -> None:
        import numpy as np

        if not self._dims_ready.wait(timeout=10):
            return  # never determined frame size; read_frame() will time out

        frame_size = self._frame_width * self._frame_height * 3
        # Read in frame-sized chunks rather than a fixed small size --
        # for any real resolution this is far fewer read() syscalls per
        # frame (a 1280x720 frame is ~2.7MB; at 64KB/read that's over 40
        # syscalls just to accumulate one frame).
        read_size = max(65536, frame_size)
        buffer = bytearray()
        while not self._stopping.is_set():
            chunk = self._proc.stdout.read(read_size)
            if not chunk:
                break
            buffer.extend(chunk)

            # For a *live* view we only care about the newest frame. If
            # decoding/reading has fallen behind, jump to the last
            # complete frame in the buffer rather than processing every
            # stale one in order.
            if len(buffer) < frame_size:
                continue
            frame_count = len(buffer) // frame_size
            latest_start = (frame_count - 1) * frame_size
            latest_end = frame_count * frame_size
            frame_bytes = bytes(buffer[latest_start:latest_end])
            del buffer[:latest_end]

            frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(
                (self._frame_height, self._frame_width, 3)
            )
            with self._frame_cond:
                self._latest_frame = frame
                self._frame_seq += 1
                self._frame_cond.notify_all()
