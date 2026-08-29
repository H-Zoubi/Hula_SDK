"""
Pure RTP/H.264 depacketization (RFC 6184), independent of sockets or any
decoder -- this is the part of hula_sdk's own video pipeline that's fully
unit-testable without hardware. See hula_sdk/video.py for the part that
actually receives packets and feeds a decoder.

pyhula's own bundled ffmpeg wrapper is broken here (see the README's "The
camera/video pipeline") -- confirmed via a raw packet capture showing the
RTP stream itself is complete and correctly formed (0% loss, SPS/PPS
present). This reassembles that same stream correctly.
"""

FU_A = 28
STAP_A = 24


def rtp_payload(packet: bytes):
    """Strip a 12(+4*CSRC)-byte RTP header off a raw UDP datagram and
    return the payload, or None if the packet is too short to be valid
    RTP."""
    if len(packet) < 12:
        return None
    cc = packet[0] & 0x0F
    payload_start = 12 + 4 * cc
    return packet[payload_start:]


class NalReassembler:
    """Feed it RTP payloads (post rtp_payload()); it hands back complete
    H.264 NAL units as it reassembles them -- unwrapping FU-A fragments
    and STAP-A aggregates, passing single-NAL packets through untouched.
    """

    def __init__(self):
        self._fu_buffer = bytearray()
        self._fu_active = False

    def feed(self, payload: bytes):
        """Returns a list of zero or more complete NAL units (each
        without a start code -- callers prepend \\x00\\x00\\x00\\x01
        themselves for Annex-B)."""
        if not payload:
            return []
        nal_type = payload[0] & 0x1F

        if nal_type == FU_A:
            return self._feed_fu_a(payload)
        if nal_type == STAP_A:
            return self._feed_stap_a(payload)
        return [payload]

    def _feed_fu_a(self, payload: bytes):
        if len(payload) < 2:
            return []
        fu_indicator, fu_header = payload[0], payload[1]
        start = bool(fu_header & 0x80)
        end = bool(fu_header & 0x40)
        inner_type = fu_header & 0x1F
        fragment = payload[2:]

        if start:
            nal_ref_idc = fu_indicator & 0x60
            self._fu_buffer = bytearray([nal_ref_idc | inner_type])
            self._fu_active = True

        if not self._fu_active:
            # Fragment arrived without ever seeing its start fragment
            # (e.g. the start was dropped) -- nothing sane to do with it.
            return []

        self._fu_buffer.extend(fragment)

        if end:
            nal = bytes(self._fu_buffer)
            self._fu_active = False
            self._fu_buffer = bytearray()
            return [nal]
        return []

    def _feed_stap_a(self, payload: bytes):
        nals = []
        offset = 1  # skip the STAP-A header byte itself
        while offset + 2 <= len(payload):
            size = (payload[offset] << 8) | payload[offset + 1]
            offset += 2
            if offset + size > len(payload):
                break
            nals.append(payload[offset:offset + size])
            offset += size
        return nals


def to_annex_b(nal: bytes) -> bytes:
    """Prefixes a raw NAL unit with the Annex-B start code."""
    return b"\x00\x00\x00\x01" + nal
