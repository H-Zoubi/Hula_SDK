"""
Tests for hula_sdk._rtp -- pure RTP/H.264 depacketization, no sockets or
hardware involved. Synthesizes RTP payloads by hand per RFC 6184 and
checks the reassembled NAL units come out correctly.
"""
import unittest

from hula_sdk._rtp import NalReassembler, rtp_payload, to_annex_b


def _rtp_packet(payload: bytes, seq: int = 1) -> bytes:
    """Minimal valid 12-byte RTP header (no CSRC) + payload."""
    header = bytes([0x80, 0x62]) + seq.to_bytes(2, "big") + b"\x00" * 8
    return header + payload


class TestRtpPayload(unittest.TestCase):
    def test_strips_basic_header(self):
        packet = _rtp_packet(b"\x67\x01\x02\x03")
        self.assertEqual(rtp_payload(packet), b"\x67\x01\x02\x03")

    def test_strips_csrc_list(self):
        # CC=2 in the low nibble of byte 0 -> two extra 4-byte CSRC entries.
        header = bytes([0x82, 0x62]) + (1).to_bytes(2, "big") + b"\x00" * 8
        packet = header + b"\x00" * 8 + b"\x67\xAA"
        self.assertEqual(rtp_payload(packet), b"\x67\xAA")

    def test_too_short_returns_none(self):
        self.assertIsNone(rtp_payload(b"\x80\x62"))


class TestNalReassembler(unittest.TestCase):
    def test_single_nal_passthrough(self):
        # nal_type 7 (SPS), nal_ref_idc bits set, forbidden bit 0.
        nal = bytes([0x67, 0xAA, 0xBB, 0xCC])
        r = NalReassembler()
        self.assertEqual(r.feed(nal), [nal])

    def test_fu_a_reassembly(self):
        r = NalReassembler()
        # Original NAL: type=5 (IDR), nal_ref_idc=3 -> header byte 0x65.
        # FU indicator: F=0, NRI=3 (0x60), type=28 (FU_A) -> 0x7C.
        fu_indicator = 0x7C
        # FU header, start fragment: S=1, E=0, type=5 -> 0x85.
        start_header = 0x85
        mid_header = 0x05
        end_header = 0x45  # E=1, type=5

        out = r.feed(bytes([fu_indicator, start_header]) + b"\xAA\xAA")
        self.assertEqual(out, [])
        out = r.feed(bytes([fu_indicator, mid_header]) + b"\xBB\xBB")
        self.assertEqual(out, [])
        out = r.feed(bytes([fu_indicator, end_header]) + b"\xCC\xCC")

        self.assertEqual(len(out), 1)
        nal = out[0]
        # Reconstructed header: nal_ref_idc (0x60) | type (5) = 0x65.
        self.assertEqual(nal[0], 0x65)
        self.assertEqual(nal[1:], b"\xAA\xAA\xBB\xBB\xCC\xCC")

    def test_fu_a_fragment_without_start_is_dropped(self):
        r = NalReassembler()
        mid_header = 0x05  # S=0, E=0
        out = r.feed(bytes([0x7C, mid_header]) + b"\xAA\xAA")
        self.assertEqual(out, [])
        # Reassembler shouldn't have latched onto a fake in-progress unit.
        self.assertFalse(r._fu_active)

    def test_stap_a_aggregate(self):
        r = NalReassembler()
        nal1 = b"\x67\x01\x02"
        nal2 = b"\x68\x03\x04\x05"
        payload = (
            bytes([24])  # STAP-A header
            + len(nal1).to_bytes(2, "big") + nal1
            + len(nal2).to_bytes(2, "big") + nal2
        )
        self.assertEqual(r.feed(payload), [nal1, nal2])

    def test_truncated_stap_a_stops_cleanly(self):
        r = NalReassembler()
        nal1 = b"\x67\x01\x02"
        payload = bytes([24]) + len(nal1).to_bytes(2, "big") + nal1 + b"\x00\x99"  # dangling size, no data
        self.assertEqual(r.feed(payload), [nal1])

    def test_empty_payload(self):
        self.assertEqual(NalReassembler().feed(b""), [])


class TestAnnexB(unittest.TestCase):
    def test_adds_start_code(self):
        self.assertEqual(to_annex_b(b"\x67\xAA"), b"\x00\x00\x00\x01\x67\xAA")


if __name__ == "__main__":
    unittest.main()
