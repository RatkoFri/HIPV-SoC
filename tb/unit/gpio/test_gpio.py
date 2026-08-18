# cocotb testbench for the gpio wrapper around the obi_gpio core.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge

from obi_master import obi_read, obi_write

GPO, GPI = 0x0, 0x4


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.ObiReq, dut.ObiAddr, dut.ObiWe, dut.ObiBe,
                dut.ObiWdata, dut.GpioIn):
        sig.value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


@cocotb.test()
async def test_output_register(dut):
    """A write to GPO drives the pins and reads back."""
    await start(dut)
    assert int(dut.GpioOut.value) == 0, "outputs not zero after reset"
    await obi_write(dut, GPO, 0xA5)
    assert int(dut.GpioOut.value) == 0xA5, f"pins={int(dut.GpioOut.value):#x}"
    got = await obi_read(dut, GPO)
    assert got == 0xA5, f"GPO read-back {got:#x}"


@cocotb.test()
async def test_input_register(dut):
    """GPI reflects the input pins (registered once)."""
    await start(dut)
    dut.GpioIn.value = 0x3C
    await RisingEdge(dut.clk)          # one capture stage in the IP
    got = await obi_read(dut, GPI)
    assert got == 0x3C, f"GPI read {got:#x}"
    dut.GpioIn.value = 0x81
    await RisingEdge(dut.clk)
    got = await obi_read(dut, GPI)
    assert got == 0x81, f"GPI read {got:#x}"


@cocotb.test()
async def test_byte_enable(dut):
    """A write with be=0 clears masked bits (mask, not merge, in this IP)."""
    await start(dut)
    await obi_write(dut, GPO, 0xFF)
    await obi_write(dut, GPO, 0xFF, be=0x0)
    got = await obi_read(dut, GPO)
    # the IP stores wdata & mask, so a byte-disabled write zeroes the bits
    assert got == 0x00, f"expected mask-to-zero behaviour, got {got:#x}"


@cocotb.test()
async def test_back_to_back(dut):
    """Repeated transactions keep the 2-phase FSM in step."""
    await start(dut)
    for v in (0x01, 0x02, 0x40, 0x80):
        await obi_write(dut, GPO, v)
        assert await obi_read(dut, GPO) == v
