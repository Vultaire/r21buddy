import sys

def get_bits(message):
    """Yields bits of message in MSB to LSB order"""
    for char in message:
        byte = ord(char)
        for i in xrange(7, -1, -1):
            yield ((byte >> i) & 0x1)

def bit_by_bit(message, poly=0x04c11db7, width=32, init=0):
    reg = init
    #print "MESSAGE:", repr(message)
    #print "BITS:", list(get_bits(message))
    message += chr(0)*(width/8)  # Pad message for CRC width

    #print "MESSAGE:", repr(message)
    #print "BITS:", list(get_bits(message))

    for bit in get_bits(message):
        # Shift new bit in
        reg = (reg << 1) | bit
        # Handle and track register overflow
        do_xor = ((reg & 0x100000000) != 0)
        reg &= 0xFFFFFFFF
        # In case of overflow, perform xor
        if do_xor:
            reg ^= poly
        #print "REG: {0:08X}".format(reg)

    return reg

def direct_table_with_padding(message):
    return 0

def direct_table(message):
    return 0


def main():
    message = "123456789"
    for method in bit_by_bit, direct_table_with_padding, direct_table:
        crc = method(message)
        print "{0:50s}: {1:08X}".format(str(method), crc)


if __name__ == "__main__":
    sys.exit(main())

