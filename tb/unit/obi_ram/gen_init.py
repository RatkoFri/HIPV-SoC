#!/usr/bin/env python3
"""Generate the memory image used by the obi_ram testbench.

Mirrors what a synthesis flow does: build the image, then hand it to the
RTL through INIT_FILE. The test checks these exact values, so the image
generator and the expectations stay in one place.
"""

import sys

# word index -> value; everything else is padded with NOP
IMAGE = {
    0: 0x00000013,   # nop (reset vector)
    1: 0xDEADBEEF,
    2: 0x00C0FFEE,
    3: 0x12345678,
    16: 0xA5A5A5A5,
    255: 0xFFFFFFFF,  # last word of the 256-word memory
}
WORDS = 256
PAD = 0x00000013


def image_words():
    return [IMAGE.get(i, PAD) for i in range(WORDS)]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "mem_init.hex"
    with open(path, "w") as f:
        for w in image_words():
            f.write(f"{w:08x}\n")


if __name__ == "__main__":
    main()
