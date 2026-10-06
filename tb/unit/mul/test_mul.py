# cocotb testbench for the mul module (homework 1, Task 2).
#
# The testbench plays the Execute stage: it pulses Start with the
# operands, waits for Done and acknowledges the result. It checks the
# interface contract written in the header of rtl/core/ieu/mul.sv:
#
#   - A, B and Funct3 are valid only in the Start cycle. After Start the
#     testbench drives random garbage on them, so a unit that does not
#     capture its operands fails here.
#   - Busy is 1 from the cycle after Start until the result is acked.
#   - Done/Result stay stable until Ack, and Done rises within
#     MAX_LATENCY cycles of Start.
#   - Busy is 0 again in the cycle after Ack.
#
# Results are compared against tb/common/hw1_model.py.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge

from hw1_model import BINARY, MUL_FUNCT3, EDGE

MAX_LATENCY = 8


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.Start.value = 0
    dut.Ack.value = 0
    dut.A.value = 0
    dut.B.value = 0
    dut.Funct3.value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def tick(dut):
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)


def scramble(dut, rng):
    """Drive garbage on the operand inputs (they are only valid at Start)."""
    dut.A.value = rng.getrandbits(32)
    dut.B.value = rng.getrandbits(32)
    dut.Funct3.value = rng.getrandbits(3)


async def multiply(dut, a, b, funct3, rng, ack_delay=0):
    """Run one operation through the unit; return its latency in cycles."""
    name = MUL_FUNCT3[funct3]
    what = f"{name}({a:#010x}, {b:#010x})"
    assert dut.Busy.value == 0, f"{what}: Busy must be 0 before Start"
    assert dut.Done.value == 0, f"{what}: Done must be 0 while idle"

    dut.Start.value = 1
    dut.A.value = a
    dut.B.value = b
    dut.Funct3.value = funct3
    await tick(dut)
    dut.Start.value = 0

    latency = 1
    while not dut.Done.value:
        assert dut.Busy.value == 1, \
            f"{what}: Busy must stay 1 while the operation runs"
        assert latency < MAX_LATENCY, \
            f"{what}: Done did not rise within {MAX_LATENCY} cycles of Start"
        scramble(dut, rng)
        await tick(dut)
        latency += 1

    expected = BINARY[name](a, b)
    result = int(dut.Result.value)
    assert result == expected, \
        f"{what} = {result:#010x}, expected {expected:#010x}"

    # the result must hold while the pipeline is not ready to take it
    for _ in range(ack_delay):
        scramble(dut, rng)
        await tick(dut)
        assert dut.Done.value == 1, f"{what}: Done dropped before Ack"
        assert int(dut.Result.value) == expected, \
            f"{what}: Result changed before Ack"

    dut.Ack.value = 1
    await tick(dut)
    dut.Ack.value = 0
    assert dut.Busy.value == 0, f"{what}: Busy must be 0 in the cycle after Ack"
    return latency


@cocotb.test()
async def test_edge_cases(dut):
    """All four instructions on sign-boundary and 16-bit-seam operands."""
    await start(dut)
    rng = random.Random(1)
    for funct3 in MUL_FUNCT3:
        for a in EDGE:
            for b in EDGE:
                await multiply(dut, a, b, funct3, rng)


@cocotb.test()
async def test_random(dut):
    """Random operands, random acknowledge delays."""
    await start(dut)
    rng = random.Random(2)
    worst = 0
    for _ in range(400):
        funct3 = rng.choice(list(MUL_FUNCT3))
        lat = await multiply(dut, rng.getrandbits(32), rng.getrandbits(32),
                             funct3, rng, ack_delay=rng.randint(0, 3))
        worst = max(worst, lat)
    dut._log.info("worst-case latency Start -> Done: %d cycles", worst)


@cocotb.test()
async def test_latency(dut):
    """Report the Start -> Done latency of each instruction (for the report)."""
    await start(dut)
    rng = random.Random(3)
    for funct3, name in MUL_FUNCT3.items():
        lat = await multiply(dut, 0x12345678, 0x9ABCDEF0, funct3, rng)
        dut._log.info("%-6s latency: %d cycles", name, lat)


@cocotb.test()
async def test_back_to_back(dut):
    """A new Start in the cycle right after Ack."""
    await start(dut)
    rng = random.Random(4)
    for _ in range(50):
        await multiply(dut, rng.getrandbits(32), rng.getrandbits(32),
                       rng.choice(list(MUL_FUNCT3)), rng)
