# cocotb testbench for the ifu module (Fetch stage, OBI master).
#
# The testbench acts as the OBI instruction-memory slave (req/gnt,
# rvalid/rdata) with configurable grant and response latency, and as
# the Decode stage on the valid/ready handshake.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge


def imem_word(addr):
    """Deterministic fake instruction for a given byte address."""
    return (addr * 2654435761 + 0x13) & 0xFFFFFFFF


async def obi_imem(dut, gnt_delay=0, rvalid_delay=1):
    """OBI slave model: one outstanding transaction, fixed latencies."""
    dut.ObiGntF.value = 0
    dut.ObiRvalidF.value = 0
    resp = None          # [cycles_until_rvalid, data]
    gnt_wait = gnt_delay
    while True:
        await FallingEdge(dut.clk)
        # response channel
        if resp is not None and resp[0] == 0:
            dut.ObiRvalidF.value = 1
            dut.ObiRdataF.value = resp[1]
            resp = None
        else:
            dut.ObiRvalidF.value = 0
            if resp is not None:
                resp[0] -= 1
        # address channel: grant a request when no response is pending
        if resp is None and dut.ObiReqF.value and not dut.ObiGntF.value:
            if gnt_wait == 0:
                dut.ObiGntF.value = 1
                resp = [rvalid_delay - 1, imem_word(int(dut.ObiAddrF.value))]
                gnt_wait = gnt_delay
            else:
                gnt_wait -= 1
        else:
            dut.ObiGntF.value = 0


async def start(dut, gnt_delay=0, rvalid_delay=1):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(obi_imem(dut, gnt_delay, rvalid_delay))
    dut.ReadyD.value = 1
    dut.PCSrcE.value = 0
    dut.PCTargetE.value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0


async def wait_valid(dut, max_cycles=50):
    """Wait for ValidF and return (PCF, InstrF)."""
    for _ in range(max_cycles):
        await FallingEdge(dut.clk)
        if dut.ValidF.value:
            return int(dut.PCF.value), int(dut.InstrF.value)
    raise AssertionError("timeout waiting for ValidF")


@cocotb.test()
async def test_first_fetch(dut):
    """First instruction after reset comes from address 0."""
    await start(dut)
    pc, instr = await wait_valid(dut)
    assert pc == 0, f"PCF={hex(pc)}"
    assert instr == imem_word(0), f"InstrF={hex(instr)}"


@cocotb.test()
async def test_sequential_fetch(dut):
    """With ReadyD high, instructions arrive from 0, 4, 8, ..."""
    await start(dut)
    for expected_pc in range(0, 6 * 4, 4):
        pc, instr = await wait_valid(dut)
        assert pc == expected_pc, f"PCF={hex(pc)}, expected {hex(expected_pc)}"
        assert instr == imem_word(expected_pc), f"InstrF={hex(instr)}"


@cocotb.test()
async def test_backpressure(dut):
    """ValidF and the instruction hold steady while ReadyD is low."""
    await start(dut)
    dut.ReadyD.value = 0
    pc, instr = await wait_valid(dut)
    for _ in range(4):
        await FallingEdge(dut.clk)
        assert dut.ValidF.value == 1, "ValidF dropped during backpressure"
        assert int(dut.PCF.value) == pc and int(dut.InstrF.value) == instr, \
            "stage output changed during backpressure"
    dut.ReadyD.value = 1
    pc2, instr2 = await wait_valid(dut)
    assert pc2 == pc + 4, f"PCF={hex(pc2)}, expected {hex(pc + 4)}"
    assert instr2 == imem_word(pc2)


@cocotb.test()
async def test_redirect(dut):
    """A redirect from Execute fetches from PCTargetE next."""
    await start(dut)
    target = 0x0000_1F00
    await wait_valid(dut)
    # pulse PCSrcE for one cycle while the stage output is valid
    dut.PCSrcE.value = 1
    dut.PCTargetE.value = target
    await FallingEdge(dut.clk)
    dut.PCSrcE.value = 0
    pc, instr = await wait_valid(dut)
    assert pc == target, f"PCF={hex(pc)}, expected {hex(target)}"
    assert instr == imem_word(target)
    pc2, _ = await wait_valid(dut)
    assert pc2 == target + 4, "fetch did not continue from target"


@cocotb.test()
async def test_redirect_midfetch(dut):
    """A redirect while a fetch is outstanding discards its response."""
    await start(dut, rvalid_delay=4)
    target = 0x0000_2A00
    # fetch of address 0 is in flight; redirect before rvalid arrives
    for _ in range(2):
        await FallingEdge(dut.clk)
    dut.PCSrcE.value = 1
    dut.PCTargetE.value = target
    await FallingEdge(dut.clk)
    dut.PCSrcE.value = 0
    pc, instr = await wait_valid(dut)
    assert pc == target, f"PCF={hex(pc)}, expected {hex(target)}"
    assert instr == imem_word(target), "stale response was not discarded"


@cocotb.test()
async def test_slow_memory(dut):
    """Sequential fetch still correct with slow grant and response."""
    await start(dut, gnt_delay=2, rvalid_delay=3)
    for expected_pc in range(0, 4 * 4, 4):
        pc, instr = await wait_valid(dut)
        assert pc == expected_pc, f"PCF={hex(pc)}, expected {hex(expected_pc)}"
        assert instr == imem_word(expected_pc)
