# cocotb testbench for the timer wrapper around the obi_timer core.
#
# Register map: 0x00 CONF {bit1: reset counter, bit0: enable},
# 0x04 COUNT_LO (ro), 0x08 COUNT_HI (ro), 0x0C CMP_LO, 0x10 CMP_HI.
# Overflow is a level: count >= {CMP_HI, CMP_LO}.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles, Timer

from obi_master import obi_read, obi_write

CONF, COUNT_LO, COUNT_HI, CMP_LO, CMP_HI = 0x00, 0x04, 0x08, 0x0C, 0x10
ENABLE, CLEAR = 0x1, 0x2


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.ObiReq, dut.ObiAddr, dut.ObiWe, dut.ObiBe, dut.ObiWdata):
        sig.value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def count64(dut):
    """Read the 64-bit counter (low word first)."""
    lo = await obi_read(dut, COUNT_LO)
    hi = await obi_read(dut, COUNT_HI)
    return (hi << 32) | lo


@cocotb.test()
async def test_registers(dut):
    """CONF and the compare registers read back what was written."""
    await start(dut)
    await obi_write(dut, CMP_LO, 0x1234_5678)
    await obi_write(dut, CMP_HI, 0x9ABC_DEF0)
    assert await obi_read(dut, CMP_LO) == 0x1234_5678
    assert await obi_read(dut, CMP_HI) == 0x9ABC_DEF0
    await obi_write(dut, CONF, ENABLE)
    assert await obi_read(dut, CONF) == ENABLE


@cocotb.test()
async def test_disabled_by_default(dut):
    """The counter does not run until CONF.enable is set."""
    await start(dut)
    first = await count64(dut)
    await ClockCycles(dut.clk, 20)
    assert await count64(dut) == first, "counter ran while disabled"


@cocotb.test()
async def test_counts_when_enabled(dut):
    """With enable set the counter increments once per clock."""
    await start(dut)
    await obi_write(dut, CMP_LO, 0xFFFF_FFFF)   # keep Overflow away
    await obi_write(dut, CMP_HI, 0xFFFF_FFFF)
    await obi_write(dut, CONF, ENABLE)

    a = await count64(dut)
    await ClockCycles(dut.clk, 10)
    b = await count64(dut)
    assert b > a, f"counter did not advance: {a} -> {b}"

    # the increment matches the elapsed cycles between two reads
    t0 = cocotb.utils.get_sim_time("ns")
    c = await count64(dut)
    t1 = cocotb.utils.get_sim_time("ns")
    d = await count64(dut)
    elapsed = round((cocotb.utils.get_sim_time("ns") - t1) / 10)
    delta = d - c
    assert abs(delta - elapsed) <= 2, \
        f"counter advanced {delta} over ~{elapsed} cycles"


@cocotb.test()
async def test_stop_and_resume(dut):
    """Clearing enable freezes the counter; setting it resumes."""
    await start(dut)
    await obi_write(dut, CMP_LO, 0xFFFF_FFFF)
    await obi_write(dut, CMP_HI, 0xFFFF_FFFF)
    await obi_write(dut, CONF, ENABLE)
    await ClockCycles(dut.clk, 10)

    await obi_write(dut, CONF, 0)               # stop
    held = await count64(dut)
    await ClockCycles(dut.clk, 20)
    assert await count64(dut) == held, "counter ran while stopped"

    await obi_write(dut, CONF, ENABLE)          # resume
    await ClockCycles(dut.clk, 5)
    assert await count64(dut) > held, "counter did not resume"


@cocotb.test()
async def test_counter_reset(dut):
    """CONF.reset clears the counter back to zero."""
    await start(dut)
    await obi_write(dut, CMP_LO, 0xFFFF_FFFF)
    await obi_write(dut, CMP_HI, 0xFFFF_FFFF)
    await obi_write(dut, CONF, ENABLE)
    await ClockCycles(dut.clk, 20)
    assert await count64(dut) > 0

    await obi_write(dut, CONF, CLEAR)           # reset, counting disabled
    assert await count64(dut) == 0, "counter not cleared"


@cocotb.test()
async def test_synchronous_reset(dut):
    """Asserting reset mid-operation clears the registers.

    The std-lib primitives use synchronous reset in this project, so the
    clock must be running for reset to take effect — that is what this
    checks: state is established, reset is pulsed with the clock live,
    and every register is back at its reset value afterwards.
    """
    await start(dut)
    await obi_write(dut, CMP_LO, 0xDEAD_BEEF)
    await obi_write(dut, CMP_HI, 0x0BAD_F00D)
    await obi_write(dut, CONF, ENABLE)
    await ClockCycles(dut.clk, 20)
    assert await count64(dut) > 0, "counter did not start"

    dut.reset.value = 1                     # clock keeps running
    await ClockCycles(dut.clk, 2)
    dut.reset.value = 0
    await FallingEdge(dut.clk)

    assert await obi_read(dut, CMP_LO) == 0, "CMP_LO not cleared by reset"
    assert await obi_read(dut, CMP_HI) == 0, "CMP_HI not cleared by reset"
    assert await obi_read(dut, CONF) == 0, "CONF not cleared by reset"
    assert await count64(dut) == 0, "counter not cleared by reset"


@cocotb.test()
async def test_overflow_is_a_level(dut):
    """Overflow asserts when count reaches the compare value.

    Note it is a comparison, not a sticky flag: it stays high while
    count >= compare, and both compare registers reset to 0, so it is
    already high out of reset.
    """
    await start(dut)
    await Timer(1, unit="ns")
    assert dut.Overflow.value == 1, \
        "with compare = 0 the level compare should be true from reset"

    # program a compare a little ahead of the counter, then count up to it
    await obi_write(dut, CMP_HI, 0)
    await obi_write(dut, CMP_LO, 40)
    await Timer(1, unit="ns")
    assert dut.Overflow.value == 0, "Overflow high before reaching compare"

    await obi_write(dut, CONF, ENABLE)
    for _ in range(80):
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if dut.Overflow.value:
            break
    else:
        raise AssertionError("Overflow never asserted")

    count = await count64(dut)
    assert count >= 40, f"Overflow asserted at count {count}, compare is 40"


@cocotb.test()
async def test_overflow_across_32_bits(dut):
    """The compare spans the full 64 bits, not just the low word."""
    await start(dut)
    # compare high word non-zero: unreachable in this test, so the
    # counter passing 0xFFFFFFFF in the low word must not trigger it
    await obi_write(dut, CMP_HI, 1)
    await obi_write(dut, CMP_LO, 0)
    await obi_write(dut, CONF, ENABLE)
    await ClockCycles(dut.clk, 50)
    await Timer(1, unit="ns")
    assert dut.Overflow.value == 0, \
        "Overflow ignored the high compare word"
