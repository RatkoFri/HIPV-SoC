#!/usr/bin/env python3
"""Build the SoC test program image.

The program runs from address 0 and exercises every slave: RAM (through
both windows), GPIO, timer and UART. Results are reported by
transmitting bytes over the UART, so the testbench can check them at the
SoC pins without reaching inside the design.

Note the unified memory: the IMEM and DMEM windows alias the same RAM,
so the data area must sit above the code. It is placed at byte offset
DATA (word 128), well clear of the program.

Assembling uses a two-pass label resolver; `label(name)` marks a spot and
jump/branch targets are given as label names.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from rv32i import (NOP, addi, add, lw, sw, andi, beq, bne, jal, jalr, lui,
                   write_mem)

# --- SoC address map (mirrors config/hipv_soc_pkg.sv) -----------------
DMEM = 0x1000_0000
UART = 0x2000_0000
TIMER = 0x2000_1000
GPIO = 0x2000_2000

# UART register offsets
U_SPEED, U_TX, U_STATUS = 0x04, 0x08, 0x10
BAUD_LIMIT = 16                    # clock cycles per bit

# timer register offsets
T_CONF, T_CMP_LO, T_CMP_HI = 0x00, 0x0C, 0x10
TIMER_COMPARE = 200

# GPIO register offsets
G_GPO = 0x00
GPIO_VALUE = 0xA5

DATA = 0x200                       # data area, word 128
FIRST_INSTR_BYTE = 0xB7            # low byte of word 0 (lui x3, 0x10000)

# register usage
#   x3 DMEM base   x4 GPIO base   x6 UART base   x9 TIMER base
#   x1 return address   x5 byte to transmit   x20/x21 scratch in send


def assemble(items):
    """Two-pass assembler: items are ints, ('label', name) or callables."""
    labels = {}
    addr = 0
    for it in items:                                  # pass 1: positions
        if isinstance(it, tuple) and it[0] == "label":
            labels[it[1]] = addr
        else:
            addr += 4
    words, addr = [], 0
    for it in items:                                  # pass 2: encode
        if isinstance(it, tuple) and it[0] == "label":
            continue
        words.append(it(addr, labels) if callable(it) else it)
        addr += 4
    return words


def jal_to(rd, name):
    return lambda pc, lbl: jal(rd, lbl[name] - pc)


def beq_to(rs1, rs2, name):
    return lambda pc, lbl: beq(rs1, rs2, lbl[name] - pc)


def bne_to(rs1, rs2, name):
    return lambda pc, lbl: bne(rs1, rs2, lbl[name] - pc)


def send(value_reg):
    """Call the send routine with the byte already in x5."""
    return jal_to(1, "send")


PROGRAM = [
    # --- base addresses ------------------------------------------------
    lui(3, DMEM >> 12),            # x3 = DMEM base   (word 0 of the image)
    lui(4, GPIO >> 12),            # x4 = GPIO base
    lui(6, UART >> 12),            # x6 = UART base
    lui(9, TIMER >> 12),           # x9 = TIMER base

    # --- UART: program the baud divider --------------------------------
    addi(7, 0, BAUD_LIMIT),
    sw(7, U_SPEED, 6),

    # --- GPIO: drive the output pins -----------------------------------
    addi(8, 0, GPIO_VALUE),
    sw(8, G_GPO, 4),

    # --- timer: compare then enable ------------------------------------
    addi(10, 0, TIMER_COMPARE),
    sw(10, T_CMP_LO, 9),
    sw(0, T_CMP_HI, 9),            # high word zero
    addi(11, 0, 1),                # enable
    sw(11, T_CONF, 9),

    # --- arithmetic, store to RAM, load back, report -------------------
    addi(12, 0, 42),
    sw(12, DATA, 3),               # mem[DATA] = 42
    lw(5, DATA, 3),                # read it back
    jal_to(1, "send"),             # report 42

    # --- read GPIO back through the bus and report ---------------------
    lw(5, G_GPO, 4),
    jal_to(1, "send"),             # report 0xA5

    # --- loop: sum 1..10, report ---------------------------------------
    addi(13, 0, 0),                # sum
    addi(14, 0, 1),                # i
    addi(15, 0, 11),               # limit
    ("label", "loop"),
    add(13, 13, 14),
    addi(14, 14, 1),
    bne_to(14, 15, "loop"),
    sw(13, DATA + 4, 3),           # mem[DATA+4] = 55
    addi(5, 13, 0),
    jal_to(1, "send"),             # report 55

    # --- aliasing: read instruction word 0 through the DMEM window -----
    lw(16, 0, 3),                  # x16 = image word 0
    andi(5, 16, 0xFF),             # low byte
    jal_to(1, "send"),             # report 0xB7

    ("label", "spin"),
    jal_to(0, "spin"),             # done: spin forever

    # --- send routine: byte in x5, returns via x1 ----------------------
    ("label", "send"),
    lw(20, U_STATUS, 6),
    andi(21, 20, 1),               # tx_empty
    beq_to(21, 0, "send"),         # wait until the transmitter is free
    sw(5, U_TX, 6),
    jalr(0, 1, 0),
]

# bytes the program transmits, in order
EXPECTED_UART = [42, GPIO_VALUE, 55, FIRST_INSTR_BYTE]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "prog.hex"
    words = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    prog = assemble(PROGRAM)
    write_mem(prog, path, words=words, pad=NOP)
    print(f"{path}: {len(prog)} instructions", file=sys.stderr)


if __name__ == "__main__":
    main()
