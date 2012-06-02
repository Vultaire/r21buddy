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


class EndOfFile(Exception):
    """Custom EOF exception"""


class OggPage(object):
    def __init__(self, infile):
        static_header = infile.read(27)
        capture_pattern = static_header[:4]
        if len(capture_pattern) == 0:
            raise EndOfFile()
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
        


class BitStream(object):
    def __init__(self, packets):
        self.packets = packets

def get_pages(infile):
    while True:
        try:
            yield OggPage(infile)
        except EndOfFile:
            break

def pages_to_bitstreams(pages):
    data = []
    packets = []
    for i, page in enumerate(pages):
        # Push finished packets to packet list
        if not page.continued_packet:
            packets.append("".join(data))
            data = []
        # Pull data into new packet
        data.append(page.payload)
        if page.last_page:
            packets.append("".join(data))
            yield BitStream(packets)
            data = []
            packets = []
    if len(data) > 0:
        raise Exception("Orphan data detected", data)
    if len(packets) > 0:
        raise Exception("Orphan packets detected", packets)

def main():
    with open(sys.argv[1], "rb") as infile:
        page_gen = get_pages(infile)
        bitstream_gen = pages_to_bitstreams(page_gen)
        bitstreams = list(bitstream_gen)
        print bitstreams

if __name__ == "__main__":
    main()
