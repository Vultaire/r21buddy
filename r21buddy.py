import sys

def _int(lsb_str):
    # Not sure how to handle bytes in MSB order...
    # Just assuming we always run using LSB.
    result = 0
    for i in xrange(len(lsb_str)):
        result |= (ord(lsb_str[i]) << (8*i))
    return result

def _hex(i):
    return "%08X" % i


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


"""
Description of the Ogg Length Hack

It seems the hack takes the final Ogg Page frame and uses its
granulepos.

Additionally, the checksum gets modified...  This may be hard to
replicate, though at least there are C++ sources I can work from now
(itgoggpatch).

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
  direct algorithm ("DIRECT TABLE ALGORITHM"???),
  initial val and final XOR = 0,
  generator polynomial = 0x04c11db7

  Generator polynomial is equiv to pkzip... but not the whole thing?

  Yes, we have a custom CRC function for Ogg.  Lovely...
  Assuming no reflection, init/xor 0.

    Here is the specification for the CRC-32 algorithm which is reportedly
    used in PKZip, AUTODIN II, Ethernet, and FDDI.
    
       Name   : "CRC-32"
       Width  : 32        # 32-bit algorithm
       Poly   : 04C11DB7  # Note: "unreflected"
       Init   : FFFFFFFF  # Initial value
       RefIn  : True      # Reflect lsb/msb on input
       RefOut : True      # Reflect lsb/mbs on output
       XorOut : FFFFFFFF  # Applied after refout, just before final value
       Check  : CBF43926  # Checksum of string "123456789"


  Steps:
  - Apply over entire header (crc as 0)
  - Apply over data
  - Store into header

  REFER TO: http://www.ross.net/crc/download/crc_v3.txt
  (Still need to figure this stuff out...)


"""

def calc_crc(str):
    OGG_POLY = 0x04c11db7
    


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
        return _int(self.raw[4])
    @property
    def header_type_flag(self):
        return _int(self.raw[5])
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
        return _int(self.raw[26])
    @property
    def seg_table(self):
        return [_int(c) for c in self.raw[27:27+self.segments]]
    @property
    def payload(self):
        payload_index = 27 + self.segments
        return self.raw[payload_index:]
    def get_segment(self, i):
        payload_index = 27 + self.segments
        segment_index = payload_index + sum(self.seg_table[:i])
        return self.raw[segment_index:segment_index+self.seg_table[i]]
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

    def patch_length(self, new_length):
        current_length = self.get_length()
        print "> Current file length: {0:.2f} seconds".format(current_length)
        print "> Target file length:  {0:.2f} seconds".format(new_length)
        if new_length < current_length:
            new_granule_pos = self.id_header.audio_sample_rate * new_length

            print "**TO DO:** Patch bitstream to new length of {0:.2f} seconds".format(new_length)
            print "CURRENT GRANULE POS:", self.pages[-1].granule_pos
            print "NEW GRANULE POS    :", new_granule_pos


class VorbisHeader(object):
    def __init__(self, data):
        self.raw = data
        if self.raw[1:7] != "vorbis":
            raise ValueError("Invalid vorbis header")
    @property
    def packet_type(self):
        return _int(self.raw[0])


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
        return _int(self.raw[11])
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
        return pow(2, _int(self.raw[28]) & 0x0F)
    @property
    def blocksize_1(self):
        return pow(2, (_int(self.raw[28]) & 0xF0) >> 4)
    @property
    def framing_bit(self):
        return _int(self.raw[29]) & 0x01
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

        self.framing_bit = _int(self.raw[ptr]) & 0x1
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


def get_pages(infile):
    while True:
        try:
            yield OggPage(infile)
        except NoMorePages:
            break

def get_bitstreams(pages):
    while True:
        try:
            yield VorbisBitStream(pages)
        except NoMoreBitstreams:
            break

def main():
    with open(sys.argv[1], "rb") as infile:
        page_gen = get_pages(infile)
        bitstream_gen = get_bitstreams(page_gen)
        patched = False
        for bitstream in bitstream_gen:
            if bitstream.get_length() > 105:
                patched = True
                bitstream.patch_length(105)
        if patched:
            # Overwrite existing file.  **TO DO**
            print "TO DO: Save patched file to disk"


if __name__ == "__main__":
    main()
