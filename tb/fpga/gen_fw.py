#!/usr/bin/env python3
"""Program image for the FPGA wrapper testbench.

Reuses the SoC test program (tb/soc/gen_prog.py) so the wrapper is
checked against exactly the behaviour the SoC testbench already
verifies: GPIO driven to 0xA5, four bytes over the UART, timer started.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "soc"))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

from gen_prog import PROGRAM, assemble, EXPECTED_UART, GPIO_VALUE, BAUD_LIMIT  # noqa: E402
from rv32i import NOP, write_mem                                              # noqa: E402


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "firmware.hex"
    words = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    write_mem(assemble(PROGRAM), path, words=words, pad=NOP)
    print(f"{path}: {len(assemble(PROGRAM))} instructions", file=sys.stderr)


if __name__ == "__main__":
    main()
