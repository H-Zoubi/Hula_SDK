"""
Full integration test of hula_sdk.VideoStream against a synthetic H264
stream sent as fake RTP packets over loopback -- exercises the real
receive -> reassemble -> ffmpeg-decode path without needing the drone or
its battery. Needs a real ffmpeg on PATH; skipped otherwise.
"""
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from hula_sdk.video import VideoStream

FFMPEG = shutil.which("ffmpeg")
LISTEN_PORT = 19070  # distinct from the real drone's 9070, to avoid clashes


class _FakeDrone:
    def set_video_stream(self, enabled):
        pass


def _split_nals(data: bytes):
    """Split Annex-B H264 bytes on start codes into individual NAL units."""
    starts = []
    i, n = 0, len(data)
    while i < n - 3:
        if data[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append(i + 4)
            i += 4
        elif data[i:i + 3] == b"\x00\x00\x01":
            starts.append(i + 3)
            i += 3
        else:
            i += 1
    nals = []
    for idx, s in enumerate(starts):
        e = starts[idx + 1] - 4 if idx + 1 < len(starts) else n
        while e > s and data[e - 1] == 0:
            e -= 1
        nals.append(data[s:e])
    return nals


def _send_as_rtp(sock, nals, dest):
    seq = 1
    for nal in nals:
        if not nal:
            continue
        header = bytes([0x80, 0x62]) + seq.to_bytes(2, "big") + b"\x00" * 8
        sock.sendto(header + nal, dest)
        seq += 1
        time.sleep(0.005)


@unittest.skipUnless(FFMPEG, "ffmpeg not found on PATH")
class TestVideoStreamIntegration(unittest.TestCase):
    def test_decodes_a_real_frame_from_synthetic_rtp(self):
        with tempfile.TemporaryDirectory() as tmp:
            h264_path = Path(tmp) / "test.h264"
            subprocess.run(
                [
                    FFMPEG, "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=1",
                    "-pix_fmt", "yuv420p", "-profile:v", "main",
                    "-f", "h264", str(h264_path),
                ],
                check=True,
                timeout=30,
            )
            h264_data = h264_path.read_bytes()

        nals = _split_nals(h264_data)
        self.assertGreater(len(nals), 0)

        video = VideoStream(_FakeDrone(), listen_port=LISTEN_PORT)
        video.start()
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            for _ in range(5):  # a few passes so the decoder has enough to lock on
                _send_as_rtp(sender, nals, ("127.0.0.1", LISTEN_PORT))

            frame = video.read_frame(timeout=15)
            self.assertEqual(frame.shape, (240, 320, 3))
            # Not all-black/all-white -- genuinely decoded content.
            self.assertGreater(frame.std(), 1.0)

            # show_live()'s actual dependency: _wait_for_new_frame must
            # block for a genuinely *new* frame, not just return whatever
            # was already latest (which read_frame() alone would do,
            # instantly, since nothing clears its "a frame exists" state
            # once set -- that was the show_live() busy-spin bug).
            first_frame, first_seq = video._wait_for_new_frame(0, timeout=15)
            self.assertGreater(first_seq, 0)

            _send_as_rtp(sender, nals, ("127.0.0.1", LISTEN_PORT))
            second_frame, second_seq = video._wait_for_new_frame(first_seq, timeout=15)
            self.assertGreater(second_seq, first_seq)
        finally:
            sender.close()
            video.stop()


if __name__ == "__main__":
    unittest.main()
