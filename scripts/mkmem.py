#!/usr/bin/env python3
"""Build a $readmemh memory image for the HIPV SoC RAM.

The image is applied at elaboration through the INIT_FILE parameter of
obi_ram / sync_dual_port_RAM, i.e. synthesis-time initialization: Vivado
folds it into the BRAM contents of the bitstream, and Verilator reads the
same file in simulation. No JTAG or SPI loader is involved.

Format: one 32-bit word per line, 8 hex digits, little-endian words in
ascending word-address order, starting at word 0.

Usage:
  mkmem.py --bin prog.bin -o mem_init.hex [--words 16384]
  mkmem.py --hex 00000013,00500093 -o mem_init.hex
  mkmem.py --fill 0 --words 16384 -o mem_init.hex
"""

import argparse
import sys

NOP = 0x00000013  # addi x0, x0, 0


def words_from_bin(path):
    """Read a raw little-endian binary into a list of 32-bit words."""
    data = open(path, "rb").read()
    if len(data) % 4:
        data += b"\x00" * (4 - len(data) % 4)
    return [int.from_bytes(data[i:i + 4], "little")
            for i in range(0, len(data), 4)]


def write_image(words, path, size=None, fill=NOP):
    """Write words as an 8-hex-digit-per-line $readmemh image."""
    if size is not None:
        if len(words) > size:
            raise SystemExit(f"image has {len(words)} words, memory holds {size}")
        words = list(words) + [fill] * (size - len(words))
    with open(path, "w") as f:
        for w in words:
            f.write(f"{w & 0xFFFFFFFF:08x}\n")
    return len(words)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--bin", help="raw little-endian binary (objcopy -O binary)")
    src.add_argument("--hex", help="comma-separated 32-bit words")
    src.add_argument("--fill", help="fill the whole image with this word")
    p.add_argument("-o", "--out", required=True, help="output image file")
    p.add_argument("--words", type=int, default=None,
                   help="pad to this many words (memory depth)")
    p.add_argument("--pad", default=hex(NOP),
                   help="padding word (default: nop)")
    args = p.parse_args()

    pad = int(args.pad, 0)
    if args.bin:
        words = words_from_bin(args.bin)
    elif args.hex:
        words = [int(x, 16) for x in args.hex.split(",") if x.strip()]
    else:
        if args.words is None:
            raise SystemExit("--fill requires --words")
        words = [int(args.fill, 0)] * args.words

    n = write_image(words, args.out, size=args.words, fill=pad)
    print(f"{args.out}: {n} words", file=sys.stderr)


if __name__ == "__main__":
    main()
