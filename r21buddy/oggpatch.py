"""
r21buddy.py: Pure Python version of the R21 Ogg Length Hack

Description of the Ogg Length Hack:

The hack modifies the granule_pos field of the final Ogg page of a
Vorbis bitstream.

Additionally, the checksum gets modified using a custom CRC algorithm.
It's similar to crc32 but with a few differences, so I've implemented
the algorithm myself.  It's slow, but is fast enough for our purposes.


Notes for those who are curious:

Granulepos:
  As defined by Vorbis spec:
    For headers: 0
    For Vorbis audio:
    - # of PCM audio samples (per channel - stereo increases at same rate as mono)
    - Represents end PCM sample position of last completed packet.
    - Will be -1 if a packet spans a full page and extends onto the next page.
    - Page 0 may infer a non-zero starting point if granulepos !=
      count of PCM samples in completed packets.
    - granule_pos on last frame can be used to prematurely end the
      stream.  (This is what the hack utilizes... the size check is
      based off of the final granule position.)

  Basically: Audio sample rate * 105 seconds = final granulepos
  Audio sample rate: Extract from Vorbis ID header

CRC checksum used for Ogg:
  Direct algorithm.  No bit reversals.
  Initial register value is all zeroes.  No final XOR performed at the end.
  The generator polynomial, the value used in the XOR operations, is 0x04c11db7.

  For a detailed explanation, refer to:
  http://www.ross.net/crc/download/crc_v3.txt This doc is not
  completely straightforward but it did enable me to write what I have
  so far.

"""

from __future__ import absolute_import


TARGET_LENGTH = 105  # Default length to patch

import sys, argparse
from cStringIO import StringIO
from r21buddy import crc

def _int(lsb_str):
    # Not sure how to handle bytes in MSB order...
    # Just assuming we always run using LSB.
    result = 0
    for i in xrange(len(lsb_str)):
        result |= (ord(lsb_str[i]) << (8*i))
    return result


class NoMorePages(Exception):
    pass
class NoMoreBitstreams(Exception):
    pass
class UnexpectedContinuedPacket(Exception):
    pass
class UnterminatedPacket(Exception):
    pass
class InvalidFramingBit(Exception):
    pass


class OggPage(object):
    def __init__(self, infile):
        static_header = infile.read(27)
        capture_pattern = static_header[:4]
        if len(capture_pattern) == 0:
            raise NoMorePages()
        if capture_pattern != "OggS":
            raise ValueError("Invalid capture pattern", capture_pattern)
        segments = _int(static_header[-1])
        seg_table = infile.read(segments)
        seg_table_lens = [_int(c) for c in seg_table]
        raw_data = []
        for i in seg_table_lens:
            raw_data.append(infile.read(i))
        payload = "".join(raw_data)

        self.raw = static_header + seg_table + payload

    @property
    def capture_pattern(self):
        return self.raw[:4]
    @property
    def stream_structure_version(self):
        return ord(self.raw[4])
    @property
    def header_type_flag(self):
        return ord(self.raw[5])
    @property
    def continued_packet(self):
        return bool(self.header_type_flag & 0x01)
    @property
    def first_page(self):
        return bool(self.header_type_flag & 0x02)
    @property
    def last_page(self):
        return bool(self.header_type_flag & 0x04)
    @property
    def granule_pos(self):
        return _int(self.raw[6:14])
    @property
    def serial(self):
        return _int(self.raw[14:18])
    @property
    def page_seq(self):
        return _int(self.raw[18:22])
    @property
    def checksum(self):
        return _int(self.raw[22:26])
    @property
    def segments(self):
        return ord(self.raw[26])
    @property
    def seg_table(self):
        return [ord(c) for c in self.raw[27:27+self.segments]]
    @property
    def payload(self):
        payload_index = 27 + self.segments
        return self.raw[payload_index:]
    def get_segment(self, i):
        payload_index = 27 + self.segments
        segment_index = payload_index + sum(self.seg_table[:i])
        return self.raw[segment_index:segment_index+self.seg_table[i]]
    def get_data_without_crc(self):
        return "".join([self.raw[:22], chr(0) * 4, self.raw[26:]])
    def get_data_with_new_length(self, granulepos):
        """Returns patched packet data."""
        def int_to_bytes(i, num_bytes):
            result = []
            for j in xrange(num_bytes):
                byte = (i >> (j*8)) & 0xFF
                result.append(chr(byte))
            return "".join(result)

        data = "".join([self.raw[:6],
                        int_to_bytes(granulepos, 8),
                        self.raw[14:22],
                        chr(0) * 4,
                        self.raw[26:]])
        checksum = crc.bit_by_bit(data)
        return "".join([self.raw[:6],
                        int_to_bytes(granulepos, 8),
                        self.raw[14:22],
                        int_to_bytes(checksum, 4),
                        self.raw[26:]])
    def __str__(self):
        return """\
Ogg Page:
    Capture Pattern: {0}
    Stream Structure Version: {1}
    Header Type Flag: {2:X} (continued packet: {3}, first page: {4}, last page: {5})
    Granule Position: {6}
    Serial: {7}
    Page Seq: {8}
    Checksum: {9}
    Segments: {10}
    Segment Table: {11}
    Payload: {12} bytes, repr: {13}""".format(
        self.capture_pattern,
        self.stream_structure_version,
        self.header_type_flag,
        self.continued_packet,
        self.first_page,
        self.last_page,
        self.granule_pos,
        self.serial,
        self.page_seq,
        self.checksum,
        self.segments,
        self.seg_table,
        len(self.payload),
        repr(self.payload))
    def __repr__(self):
        return "<OggPage FirstPage:{0:5s} LastPage:{1:5s} ContinuedPacket:{2:5s}>".format(str(self.first_page), str(self.last_page), str(self.continued_packet))


class VorbisBitStream(object):
    def __init__(self, pages):

        def get_packets(pages):
            """Generates packets from pages until a last page marker is found."""
            data = []
            for i, page in enumerate(pages):
                #print "{0:4d}".format(i), page
                if page.continued_packet and len(data) == 0:
                    raise UnexpectedContinuedPacket()

                for j in xrange(page.segments):
                    segment = page.get_segment(j)
                    data.append(segment)
                    if page.seg_table[j] < 255:
                        yield "".join(data)
                        data = []
                        
                if page.last_page:
                    break
            if len(data) > 0:
                raise UnterminatedPacket("".join(data))

        self.pages = list(pages)  # Needed to recreate stream with updated final page

        packet_gen = get_packets(self.pages)
        try:
            first_packet = packet_gen.next()
        except StopIteration:
            raise NoMoreBitstreams

        self.id_header = IdHeader(first_packet)
        for packet in packet_gen:
            pass

        # Here's how we -really- would decode a vorbis packet stream:
        # # 1. Pull headers
        # try:
        #     self.id_header = IdHeader(first_packet)
        #     print str(self.id_header)
        #     self.comments_header = CommentsHeader(packet_gen.next())
        #     print str(self.comments_header)
        #     self.setup_header = SetupHeader(packet_gen.next())
        #     print str(self.setup_header)
        # except StopIteration:
        #     raise Exception("Unexpected end of bitstream detected.")
        # # 2. Store all remaining packets in the bitstream
        # self.data_packets = list(packet_gen)

    def get_length(self):
        sample_rate = self.id_header.audio_sample_rate
        current_granule_pos = self.pages[-1].granule_pos
        return float(current_granule_pos) / sample_rate

    def patch_length(self, new_length, verbose=True):
        current_length = self.get_length()
        if new_length < current_length:
            new_granule_pos = self.id_header.audio_sample_rate * new_length

            last_page = self.pages[-1]
            if verbose:
                print "Current granule position:", last_page.granule_pos
                print "New granule position:    ", new_granule_pos

            # Replace last page with patched version
            new_page_data = last_page.get_data_with_new_length(new_granule_pos)
            self.pages[-1] = OggPage(StringIO(new_page_data))

    def write_to_file(self, outfile):
        for page in self.pages:
            outfile.write(page.raw)


class VorbisHeader(object):
    def __init__(self, data):
        self.raw = data
        if self.raw[1:7] != "vorbis":
            raise ValueError("Invalid vorbis header")
    @property
    def packet_type(self):
        return ord(self.raw[0])


class IdHeader(VorbisHeader):
    def __init__(self, data):
        VorbisHeader.__init__(self, data)
        if self.packet_type != 1:
            raise ValueError("Invalid packet type", self.packet_type)
    @property
    def vorbis_version(self):
        return _int(self.raw[7:11])
    @property
    def audio_channels(self):
        return ord(self.raw[11])
    @property
    def audio_sample_rate(self):
        return _int(self.raw[12:16])
    @property
    def bitrate_maximum(self):
        return _int(self.raw[16:20])
    @property
    def bitrate_nominal(self):
        return _int(self.raw[20:24])
    @property
    def bitrate_minimum(self):
        return _int(self.raw[24:28])
    @property
    def blocksize_0(self):
        return pow(2, ord(self.raw[28]) & 0x0F)
    @property
    def blocksize_1(self):
        return pow(2, (ord(self.raw[28]) & 0xF0) >> 4)
    @property
    def framing_bit(self):
        return ord(self.raw[29]) & 0x01
    def __str__(self):
        return """\
ID Header:
    Vorbis Version: {0}
    Audio Channels: {1}
    Audio Sample Rate: {2}
    Bitrate Maximum: {3}
    Bitrate Nominal: {4}
    Bitrate Minimum: {5}
    Blocksize 0: {6}
    Blocksize 1: {7}
    Framing bit: {8}""".format(
        self.vorbis_version,
        self.audio_channels,
        self.audio_sample_rate,
        self.bitrate_maximum,
        self.bitrate_nominal,
        self.bitrate_minimum,
        self.blocksize_0,
        self.blocksize_1,
        self.framing_bit)
    def __repr__(self):
        return "<IdHeader version:%d channels:%d sample_rate:%d raw:%s>" % (
            self.vorbis_version, self.audio_channels,
            self.audio_sample_rate, repr(self.raw))


class CommentsHeader(VorbisHeader):
    # This is unnecessary for the length hack, but I had already
    # implemented it before I figured this out.  Leaving it in for
    # those who are curious.
    def __init__(self, data):
        VorbisHeader.__init__(self, data)
        if self.packet_type != 3:
            raise ValueError("Invalid packet type", self.packet_type)

        ptr = 7

        vendor_length = _int(self.raw[ptr:ptr+4])
        ptr += 4

        self.vendor_string = self.raw[ptr:ptr+vendor_length].decode("utf-8")
        ptr += vendor_length

        self.user_comment_list_length = _int(self.raw[ptr:ptr+4])
        ptr += 4

        self.user_strings = []
        for i in xrange(self.user_comment_list_length):
            _len = _int(self.raw[ptr:ptr+4])
            ptr += 4
            val = self.raw[ptr:ptr+_len]
            self.user_strings.append(val.decode("utf-8"))
            ptr += _len

        self.framing_bit = ord(self.raw[ptr]) & 0x1
        if self.framing_bit == 0:
            raise InvalidFramingBit()

    def __str__(self):
        lines = ["Comments Header:"]
        lines.append("    Vendor String: {0}".format(self.vendor_string))
        user_strings = ["    User String[{0}]: {1}".format(i, s)
                        for (i, s) in enumerate(self.user_strings)]
        if len(user_strings) > 0:
            lines.extend(user_strings),
        lines.append("    Framing bit: {0}".format(self.framing_bit))
        return "\n".join(lines)
    def __repr__(self):
        return "<CommentsHeader raw:%s>" % (repr(self.raw),)


class SetupHeader(VorbisHeader):
    # This is unnecessary for the length hack, but I had already
    # implemented it before I figured this out.  Leaving it in for
    # those who are curious.
    def __init__(self, data):
        VorbisHeader.__init__(self, data)
        if self.packet_type != 5:
            raise ValueError("Invalid packet type", self.packet_type)

        # This gets really complicated, and appears unnecessary for
        # the Ogg length patch.  Skipping for now...

        # ptr = 7

        # # Cookbook configs
        # vorbis_cookbook_count = _int(self.raw[ptr:ptr+4])
        # ptr += 4
        # # TO DO: decode cookbooks

        # # Time-domain transform configs
        # vorbis_time_count = _int(self.raw[ptr:ptr+4])
        # ptr += 4
        # self.time_domain_transform_cfgs = []
        # for i in xrange(vorbis_time_count):
        #     self.time_domain_transform_cfgs.append(_int(self.raw[ptr:ptr+4]))
        #     ptr += 4
        # if any(v != 0 for v in self.time_domain_transform_cfgs):
        #     raise ValueError("Unexpected values for time-domain transform configs", 
        #                      self.time_domain_transform_cfgs)

        # # Floor configs
        # vorbis_floor_count = _int(self.raw[ptr:ptr+4])
        # ptr += 4
        
        # # Residue configs
        # # Channel mapping configs
        # # Mode configs
        # # Framing bit

    def __str__(self):
        return "<SetupHeader raw:%s>" % (repr(self.raw),)


def _get_pages(infile):
    while True:
        try:
            yield OggPage(infile)
        except NoMorePages:
            break

def _get_bitstreams(pages):
    while True:
        try:
            yield VorbisBitStream(pages)
        except NoMoreBitstreams:
            break

def get_bitstreams(infile):
    page_gen = _get_pages(infile)
    return _get_bitstreams(page_gen)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", help="Input file.")
    ap.add_argument("-o", "--output-file",
                    help="Output file.  (Default: overwrite input file)")
    ap.add_argument("-c", "--check", action="store_true",
                    help="Check length only; do not modify file")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Verbose output")
    ap.add_argument("-l", "--length", default=TARGET_LENGTH,
                    help="Desired max length to patch into the input file.  (Default: %(default)s)")
    return ap.parse_args()


def pprint_time(t):
    mins = t // 60
    secs = t % 60
    return "{0:d}:{1:05.2f}".format(int(mins), secs)


def patch_file(input_file, target_length=TARGET_LENGTH,
               output_file=None, verbose=True):
    patched = False
    if target_length < 0:
        print >> sys.stderr, "Bad length ({0}), not patching file".format(target_length)
        return
    with open(input_file, "rb") as infile:
        bitstreams = list(get_bitstreams(infile))
        for bitstream in bitstreams:
            length = bitstream.get_length()
        if verbose:
            print "Current file length: {0}".format(pprint_time(length))
            print "Target file length:  {0}".format(pprint_time(target_length))
        if length > target_length:
            patched = True
            bitstream.patch_length(target_length, verbose=verbose)
    if patched:
        if output_file is None:
            output_file = input_file
        if verbose:
            print "Writing patched file to", output_file
        with open(output_file, "wb") as outfile:
            for bitstream in bitstreams:
                bitstream.write_to_file(outfile)
    elif verbose:
        print "Not patching file; file already appears to be {0} or shorter.".format(
            pprint_time(target_length))

def check_file(input_file, target_length, verbose=True):
    if target_length < 0:
        print >> sys.stderr, "Bad length ({0}), not patching file".format(target_length)
        return
    with open(input_file, "rb") as infile:
        bitstreams = list(get_bitstreams(infile))
        for bitstream in bitstreams:
            length = bitstream.get_length()
            if verbose:
                print "Current file length: {0}".format(pprint_time(length))
                print "Target file length:  {0}".format(pprint_time(target_length))

            if length > target_length:
                print >> sys.stderr, "File exceeds {0}.  Length: {1}".format(
                    pprint_time(target_length), pprint_time(length))
                return False
            else:
                if verbose:
                    print "File passes length check."
            continue

    return True

def main():
    options = parse_args()
    if options.check:
        check_file(options.input_file, options.length, verbose=options.verbose)
    else:
        patch_file(options.input_file, options.length, output_file=options.output_file, verbose=options.verbose)


    return 0


if __name__ == "__main__":
    sys.exit(main())
