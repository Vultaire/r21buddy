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
        capture_pattern = infile.read(4)
        if len(capture_pattern) == 0:
            raise EndOfFile()
        if capture_pattern != "OggS":
            raise ValueError("Invalid capture pattern", capture_pattern)
        self.stream_structure_version = _int(infile.read(1))
        header_type_flag = _int(infile.read(1))
        self.continued_packet = bool(header_type_flag & 0x01)
        self.first_page = bool(header_type_flag & 0x02)
        self.last_page = bool(header_type_flag & 0x04)
        self.granule_pos = _int(infile.read(8))
        self.serial = _int(infile.read(4))
        self.page_seq = _int(infile.read(4))
        self.checksum = _int(infile.read(4))
        self.segments = _int(infile.read(1))
        seg_table_str = infile.read(self.segments)
        seg_table = []
        for i, c in enumerate(seg_table_str):
            seg_table.append(_int(c))

        raw_data = []
        for i in seg_table:
            raw_data.append(infile.read(i))
        self.payload = "".join(raw_data)


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
        print len(bitstreams)

if __name__ == "__main__":
    main()
