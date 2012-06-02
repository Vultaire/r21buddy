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
        return [_int(c) for c in self.raw[27:]]
    @property
    def payload(self):
        payload_index = 27 + self.segments
        return self.raw[payload_index:]
    def __str__(self):
        return "<OggPage FirstPage:{0:5s} LastPage:{1:5s} ContinuedPacket:{2:5s}>".format(str(self.first_page), str(self.last_page), str(self.continued_packet))


class BitStream(object):
    def __init__(self, pages):

        def get_packets(pages):
            """Generates packets from pages until a last page marker is found."""
            data = []
            for i, page in enumerate(pages):
                # Push finished packets to packet list
                if not page.continued_packet and len(data) > 0:
                    yield "".join(data)
                    data = []
                #print i, page.first_page, page.last_page, page.continued_packet, repr(page.payload)
                print "{0:4d}".format(i), page
                data.append(page.payload)
                if page.last_page:
                    break
            # Yield final packet
            if len(data) > 0:
                yield "".join(data)

        packet_gen = get_packets(pages)
        try:
            first_packet = packet_gen.next()
        except StopIteration:
            raise NoMoreBitstreams

        try:
            self.id_header = IdHeader(first_packet)
            print str(self.id_header)
            self.comments_header = CommentsHeader(packet_gen.next())
            print str(self.comments_header)
        except StopIteration:
            raise Exception("Unexpected end of bitstream detected.")

        # Store all remaining packets in the bitstream
        self.data_packets = list(packet_gen)


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
    def __str__(self):
        return "<CommentsHeader raw:%s>" % (repr(self.raw),)


class SetupHeader(VorbisHeader):
    def __init__(self, data):
        VorbisHeader.__init__(self, data)
        if self.packet_type != 5:
            raise ValueError("Invalid packet type", self.packet_type)


def get_pages(infile):
    while True:
        try:
            yield OggPage(infile)
        except NoMorePages:
            break

def get_bitstreams(pages):
    while True:
        try:
            yield BitStream(pages)
        except NoMoreBitstreams:
            break

def main():
    with open(sys.argv[1], "rb") as infile:
        page_gen = get_pages(infile)
        bitstream_gen = get_bitstreams(page_gen)
        for i, bitstream in enumerate(bitstream_gen):
            print i, bitstream

if __name__ == "__main__":
    main()
