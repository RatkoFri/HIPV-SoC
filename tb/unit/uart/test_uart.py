# cocotb testbench for the uart wrapper around the obi_uart core.
#
# Register map: 0x00 CONF, 0x04 SPEED (baud limit, clk cycles/bit),
# 0x08 TX, 0x0C RX, 0x10 STATUS {bit1: rx available, bit0: tx empty}.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles

from obi_master import obi_read, obi_write

CONF, SPEED, TX, RX, STATUS = 0x00, 0x04, 0x08, 0x0C, 0x10
LIMIT = 16  # clk cycles per bit; must be a multiple of 16 for the receiver


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.ObiReq, dut.ObiAddr, dut.ObiWe, dut.ObiBe, dut.ObiWdata):
        sig.value = 0
    dut.Rx.value = 1                    # UART line idles high
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def tx_monitor(dut, frames, nframes=1):
    """Decode 8N1 frames from the Tx pin by mid-bit sampling."""
    for _ in range(nframes):
        while dut.Tx.value == 1:        # wait for a start bit
            await RisingEdge(dut.clk)
        await ClockCycles(dut.clk, LIMIT // 2)   # middle of start bit
        assert dut.Tx.value == 0, "start bit not low at mid-bit"
        byte = 0
        for i in range(8):              # LSB first
            await ClockCycles(dut.clk, LIMIT)
            byte |= int(dut.Tx.value) << i
        await ClockCycles(dut.clk, LIMIT)        # stop bit
        assert dut.Tx.value == 1, "stop bit not high"
        frames.append(byte)


@cocotb.test()
async def test_register_access(dut):
    """CONF and SPEED write and read back; STATUS after reset."""
    await start(dut)
    await obi_write(dut, SPEED, LIMIT)
    assert await obi_read(dut, SPEED) == LIMIT
    await obi_write(dut, CONF, 0x1)
    assert await obi_read(dut, CONF) == 0x1
    status = await obi_read(dut, STATUS)
    assert status & 1 == 1, "tx should be empty after reset"
    assert status & 2 == 0, "rx should be empty after reset"


@cocotb.test()
async def test_transmit_frame(dut):
    """A write to TX produces one correct 8N1 frame on the Tx pin."""
    await start(dut)
    await obi_write(dut, SPEED, LIMIT)
    frames = []
    mon = cocotb.start_soon(tx_monitor(dut, frames, nframes=1))
    await obi_write(dut, TX, 0x55)
    await ClockCycles(dut.clk, LIMIT * 12)
    assert frames, "no frame seen on Tx"
    assert frames[0] == 0x55, f"transmitted {frames[0]:#04x}, wrote 0x55"
    mon.cancel()


@cocotb.test()
async def test_transmit_two_bytes(dut):
    """Two writes produce two frames with the right bytes in order."""
    await start(dut)
    await obi_write(dut, SPEED, LIMIT)
    frames = []
    mon = cocotb.start_soon(tx_monitor(dut, frames, nframes=2))
    await obi_write(dut, TX, 0xA3)
    # wait for tx_empty before the second byte (single buffer)
    for _ in range(50):
        if (await obi_read(dut, STATUS)) & 1:
            break
        await ClockCycles(dut.clk, LIMIT)
    await obi_write(dut, TX, 0x5C)
    await ClockCycles(dut.clk, LIMIT * 14)
    assert frames == [0xA3, 0x5C], f"frames={[hex(f) for f in frames]}"
    mon.cancel()


@cocotb.test()
async def test_loopback(dut):
    """Tx looped to Rx: the receiver delivers the byte and STATUS shows it."""
    await start(dut)
    await obi_write(dut, SPEED, LIMIT)

    async def loop():
        while True:
            await RisingEdge(dut.clk)
            dut.Rx.value = dut.Tx.value

    lp = cocotb.start_soon(loop())
    await obi_write(dut, TX, 0x96)
    # frame time ~10 bits + receiver stop margin
    for _ in range(60):
        await ClockCycles(dut.clk, LIMIT)
        if (await obi_read(dut, STATUS)) & 2:
            break
    else:
        raise AssertionError("rx data never became available")
    got = await obi_read(dut, RX)
    assert got == 0x96, f"received {got:#04x}, sent 0x96"
    # reading RX clears the available flag
    status = await obi_read(dut, STATUS)
    assert status & 2 == 0, "rx-available flag did not clear"
    lp.cancel()
