# Homework 1, Task 1: Zba/Zbb subset on the full core.
#
#   make MODULE=test_zbb                  required instructions
#   make MODULE=test_zbb HW1_BONUS=1      also the bonus instructions
#                                         (docs/LectureNotes/HW1_bonus.md)
#
# Every test runs a program on hipv_core and compares the stored results
# with tb/common/hw1_model.py. See docs/LectureNotes/HW1.md.

import os
import random

import cocotb

from rv32i import (program, li, sw, add, sub, xor, sll, srl, sra, slli,
                   srli, srai, andi, ori, sh1add, sh2add, sh3add, andn,
                   orn, xnor, min_, minu, max_, maxu, clz, cpop, ctz,
                   sext_b, sext_h, zext_h, rol, ror, rori, orc_b, rev8)
from hw1_model import BINARY, UNARY, EDGE, M32
from hw1_util import SPIN, run, vector_program, budget, check

BONUS = os.environ.get("HW1_BONUS", "0") == "1"

RNG = random.Random(11)
PAIRS = [(a, b) for a in EDGE for b in EDGE[::3]] + \
        [(RNG.getrandbits(32), RNG.getrandbits(32)) for _ in range(8)]
# rotate amounts must cover 0, 31, and values above 31 (only [4:0] counts)
SHIFT_PAIRS = [(a, b) for a in EDGE[:6] for b in (0, 1, 15, 16, 31, 32, 63, 0xFFFFFFE1)]


async def run_vectors(dut, ops, pairs):
    instrs, expected = vector_program(ops, pairs)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, expected)


@cocotb.test()
async def test_zba(dut):
    """sh1add, sh2add, sh3add."""
    await run_vectors(dut, [("sh1add", sh1add), ("sh2add", sh2add),
                            ("sh3add", sh3add)], PAIRS)


@cocotb.test()
async def test_logic_with_negate(dut):
    """andn, orn, xnor."""
    await run_vectors(dut, [("andn", andn), ("orn", orn), ("xnor", xnor)], PAIRS)


@cocotb.test()
async def test_min_max(dut):
    """min, minu, max, maxu (signed and unsigned compares)."""
    await run_vectors(dut, [("min", min_), ("minu", minu), ("max", max_),
                            ("maxu", maxu)], PAIRS)


@cocotb.test()
async def test_forwarding_chain(dut):
    """New instructions feeding each other back to back (forwarding paths)."""
    a, b = 0x8000FFFF, 0x00F0000F
    r3 = BINARY["andn"](a, b)
    r4 = BINARY["min"](r3, a)
    r5 = BINARY["sh1add"](r4, r3)
    r6 = BINARY["sh2add"](r5, r3)
    r7 = BINARY["xnor"](r6, b)
    r8 = BINARY["maxu"](r7, r5)
    instrs = li(1, a) + li(2, b) + [
        andn(3, 1, 2),
        min_(4, 3, 1),
        sh1add(5, 4, 3),
        sh2add(6, 5, 3),
        xnor(7, 6, 2),
        maxu(8, 7, 5),
        sw(6, 0, 0),
        sw(8, 4, 0),
        SPIN,
    ]
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, {0: (r6, "sh2add result"), 4: (r8, "maxu result")})


@cocotb.test()
async def test_rv32i_still_works(dut):
    """RV32I instructions that share funct3 with the new ones.

    clz/cpop share OP-IMM funct3=001 with slli, rori shares funct3=101
    with srli/srai, andn/orn/xnor share funct7=0100000 with sub/sra.
    A decoder that looks at too few bits breaks these.
    """
    a, b = 0x8765F0F1, 0x0000000B
    cases = [
        (add(3, 1, 2),     (a + b) & M32,               "add"),
        (sub(3, 1, 2),     (a - b) & M32,               "sub"),
        (xor(3, 1, 2),     a ^ b,                       "xor"),
        (sll(3, 1, 2),     (a << (b & 31)) & M32,       "sll"),
        (srl(3, 1, 2),     a >> (b & 31),               "srl"),
        (sra(3, 1, 2),     ((a - (1 << 32)) >> (b & 31)) & M32, "sra"),
        (slli(3, 1, 4),    (a << 4) & M32,              "slli"),
        (srli(3, 1, 4),    a >> 4,                      "srli"),
        (srai(3, 1, 4),    ((a - (1 << 32)) >> 4) & M32, "srai"),
        (andi(3, 1, 0x0F0), a & 0x0F0,                  "andi"),
        (ori(3, 1, 0x00F), a | 0x00F,                   "ori"),
    ]
    instrs = li(1, a) + li(2, b)
    expected = {}
    for i, (word, value, label) in enumerate(cases):
        instrs += [word, sw(3, 4 * i, 0)]
        expected[4 * i] = (value, label)
    instrs.append(SPIN)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, expected)


# --- bonus ------------------------------------------------------------

@cocotb.test(skip=not BONUS)
async def test_bonus_unary(dut):
    """clz, cpop, ctz, sext.b, sext.h, zext.h, orc.b, rev8."""
    singles = [(a, 0) for a in EDGE] + \
              [(1 << i, 0) for i in range(32)] + \
              [(RNG.getrandbits(32), 0) for _ in range(8)]
    await run_vectors(dut, [("clz", clz), ("cpop", cpop), ("ctz", ctz),
                            ("sext.b", sext_b), ("sext.h", sext_h),
                            ("zext.h", zext_h), ("orc.b", orc_b), ("rev8", rev8)],
                      singles)


@cocotb.test(skip=not BONUS)
async def test_bonus_rotate(dut):
    """rol and ror (the rotate amount is rs2[4:0])."""
    await run_vectors(dut, [("rol", rol), ("ror", ror)], SHIFT_PAIRS)


@cocotb.test(skip=not BONUS)
async def test_bonus_rori(dut):
    """rori with several immediate rotate amounts."""
    instrs = li(1, 0x12345678)
    expected = {}
    for i, sh in enumerate((0, 1, 4, 16, 31)):
        instrs += [rori(3, 1, sh), sw(3, 4 * i, 0)]
        expected[4 * i] = (BINARY["ror"](0x12345678, sh), f"rori(0x12345678, {sh})")
    instrs.append(SPIN)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, expected)
