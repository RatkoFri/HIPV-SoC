# Homework 1, Task 2: Zmmul (mul, mulh, mulhsu, mulhu) on the full core.
#
#   make MODULE=test_zmmul
#
# The multiplier takes several cycles in Execute, so besides the results
# these tests stress the pipeline around it: forwarding into and out of
# a multiply, a multiply right after a slow load, branches next to a
# multiply, and back-to-back multiplies. See docs/LectureNotes/HW1.md.

import random

import cocotb

from rv32i import (program, li, lw, sw, add, addi, beq, mul, mulh, mulhsu,
                   mulhu, div, divu, rem, remu)
from hw1_model import BINARY, EDGE
from hw1_util import SPIN, run, vector_program, budget, check

MUL_OPS = [("mul", mul), ("mulh", mulh), ("mulhsu", mulhsu), ("mulhu", mulhu)]
RNG = random.Random(22)


@cocotb.test()
async def test_mul_edge(dut):
    """All four instructions on sign-boundary and 16-bit-seam operands."""
    pairs = [(a, b) for a in EDGE for b in EDGE[::2]]
    instrs, expected = vector_program(MUL_OPS, pairs)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, expected)


@cocotb.test()
async def test_mul_random(dut):
    """Random operands."""
    pairs = [(RNG.getrandbits(32), RNG.getrandbits(32)) for _ in range(24)]
    instrs, expected = vector_program(MUL_OPS, pairs)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, expected)


@cocotb.test()
async def test_mul_dependencies(dut):
    """Multiply results consumed immediately, and multiplies of fresh results."""
    a, b = 0xFFFF1234, 0x0001F00D
    r3 = BINARY["mul"](a, b)
    r4 = BINARY["mulh"](r3, a)        # mul -> mul, distance 1
    r5 = (r4 + r3) & 0xFFFFFFFF       # mul -> ALU, distances 1 and 2
    r6 = BINARY["mulhu"](r5, r5)      # ALU -> mul, both operands
    r7 = BINARY["mulhsu"](r6, r3)
    instrs = li(1, a) + li(2, b) + [
        mul(3, 1, 2),
        mulh(4, 3, 1),
        add(5, 4, 3),
        mulhu(6, 5, 5),
        mulhsu(7, 6, 3),
        sw(7, 0, 0),                  # mul -> store data
        sw(5, 4, 0),
        SPIN,
    ]
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, {0: (r7, "end of the dependency chain"), 4: (r5, "add of mul results")})


@cocotb.test()
async def test_mul_after_load_slow_memory(dut):
    """A multiply whose operands come from loads still in flight."""
    a, b, c = 0x89ABCDEF, 0xFEDCBA98, 0x00000007
    dmem = {0x100: a, 0x104: b}
    instrs = li(10, 0x100) + li(2, c) + [
        lw(1, 0, 10),
        mul(3, 1, 2),                 # load-use into the multiplier
        lw(4, 4, 10),
        mulhsu(5, 4, 1),              # both operands from loads
        addi(6, 0, 77),
        lw(7, 0, 10),                 # stalls M while x6 sits in W ...
        mulhu(8, 6, 4),               # ... and the multiply needs x6
        sw(3, 0x10, 10),
        sw(5, 0x14, 10),
        sw(8, 0x18, 10),
        SPIN,
    ]
    # fast fetch, slow data: the multiply reaches Execute while its load
    # is still waiting for the data memory
    await run(dut, program(instrs), dmem, budget(instrs, 60),
              dmem_delay=(3, 4))
    check(dmem, {
        0x110: (BINARY["mul"](a, c), "mul after lw"),
        0x114: (BINARY["mulhsu"](b, a), "mulhsu of two loads"),
        0x118: (BINARY["mulhu"](77, b), "mulhu behind a stalled load"),
    })


@cocotb.test()
async def test_mul_and_branches(dut):
    """A branch on a multiply result, and a multiply on a skipped path."""
    sentinel = 0x5A5A5A5A
    instrs = li(1, 6) + li(2, 7) + li(4, 42) + li(8, sentinel) + [
        mul(3, 1, 2),                 # 42
        beq(3, 4, 8),                 # taken: skip the next instruction
        addi(9, 0, 1),                # must not execute
        beq(0, 0, 8),                 # taken: skip the multiply
        mul(8, 1, 2),                 # must not execute (x8 keeps sentinel)
        sw(3, 0, 0),
        sw(9, 4, 0),
        sw(8, 8, 0),
        SPIN,
    ]
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, {0: (42, "mul result"), 4: (0, "instruction after taken branch"),
                 8: (sentinel, "multiply on the skipped path")})


@cocotb.test()
async def test_back_to_back(dut):
    """Independent multiplies one after another."""
    pairs = [(RNG.getrandbits(32), RNG.getrandbits(32)) for _ in range(6)]
    instrs = []
    expected = {}
    for i, (a, b) in enumerate(pairs):
        instrs += li(2 * i + 1, a) + li(2 * i + 2, b)
    for i, (a, b) in enumerate(pairs):
        name, enc = MUL_OPS[i % 4]
        instrs.append(enc(20 + i, 2 * i + 1, 2 * i + 2))
        expected[4 * i] = (BINARY[name](a, b), f"{name}({a:#010x}, {b:#010x})")
    instrs += [sw(20 + i, 4 * i, 0) for i in range(len(pairs))]
    instrs.append(SPIN)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, expected)


@cocotb.test()
async def test_div_rem_are_nops(dut):
    """Zmmul has no divide: div/divu/rem/remu must not write rd."""
    sentinel = 0x0BADC0DE
    instrs = li(1, 100) + li(2, 7)
    for rd in (3, 4, 5, 6):
        instrs += li(rd, sentinel)
    instrs += [div(3, 1, 2), divu(4, 1, 2), rem(5, 1, 2), remu(6, 1, 2)]
    instrs += [sw(rd, 4 * i, 0) for i, rd in enumerate((3, 4, 5, 6))]
    instrs.append(SPIN)
    dmem = {}
    await run(dut, program(instrs), dmem, budget(instrs))
    check(dmem, {4 * i: (sentinel, name) for i, name in
                 enumerate(("div", "divu", "rem", "remu"))})
