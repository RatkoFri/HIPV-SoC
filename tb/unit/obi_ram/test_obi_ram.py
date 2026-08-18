# cocotb testbench for obi_ram: one dual-port RAM behind two OBI ports.
#
# Port A serves the instruction window, port B the data window; both
# alias the same physical words. Built with ADDR_WIDTH=8 (256 words) and
# initialised from mem_init.hex through INIT_FILE (see gen_init.py).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

from gen_init import IMAGE, PAD

A, B = "A", "B"


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for p in (A, B):
        getattr(dut, f"ObiReq{p}").value = 0
        getattr(dut, f"ObiAddr{p}").value = 0
        getattr(dut, f"ObiWe{p}").value = 0
        getattr(dut, f"ObiBe{p}").value = 0
        getattr(dut, f"ObiWdata{p}").value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


CLK_NS = 10


async def access(dut, port, addr, write=False, wdata=0, be=0xF, timeout=20):
    """One OBI transaction on port A or B.

    Returns (read data, latency), where latency is the number of clock
    cycles from the accepted address phase to the response — the number
    the design is specified in. It is measured from simulation time, so
    it does not depend on the phase the caller happened to start in.
    """
    req = getattr(dut, f"ObiReq{port}")
    gnt = getattr(dut, f"ObiGnt{port}")
    rvalid = getattr(dut, f"ObiRvalid{port}")
    rdata = getattr(dut, f"ObiRdata{port}")
    getattr(dut, f"ObiAddr{port}").value = addr
    getattr(dut, f"ObiWe{port}").value = 1 if write else 0
    getattr(dut, f"ObiBe{port}").value = be
    getattr(dut, f"ObiWdata{port}").value = wdata
    req.value = 1
    # grant is combinational, so settle before sampling instead of
    # burning a cycle on a clock edge first
    for _ in range(timeout):
        await Timer(1, unit="ns")
        if gnt.value:
            break
        await FallingEdge(dut.clk)
    else:
        raise AssertionError(f"port {port}: no grant for {hex(addr)}")
    await RisingEdge(dut.clk)              # address phase accepted here
    t_accept = cocotb.utils.get_sim_time("ns")
    req.value = 0
    getattr(dut, f"ObiWe{port}").value = 0
    for _ in range(timeout):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if rvalid.value:
            latency = round((cocotb.utils.get_sim_time("ns") - t_accept)
                            / CLK_NS)
            return int(rdata.value), latency
    raise AssertionError(f"port {port}: no response for {hex(addr)}")


# --- initialization ---------------------------------------------------

@cocotb.test()
async def test_init_image(dut):
    """The INIT_FILE image is visible at reset on both ports."""
    await start(dut)
    for word, expected in sorted(IMAGE.items()):
        got, _ = await access(dut, A, word * 4)
        assert got == expected, \
            f"word {word}: A read {got:#010x}, image has {expected:#010x}"
        got, _ = await access(dut, B, word * 4)
        assert got == expected, f"word {word}: B read {got:#010x}"
    # a word not in the image holds the pad value
    got, _ = await access(dut, A, 100 * 4)
    assert got == PAD, f"padding word read {got:#010x}"


# --- basic accesses ---------------------------------------------------

@cocotb.test()
async def test_word_write_read(dut):
    """Word write then read back, on each port."""
    await start(dut)
    await access(dut, B, 0x20, write=True, wdata=0x11223344)
    got, _ = await access(dut, B, 0x20)
    assert got == 0x11223344, f"B read {got:#010x}"
    await access(dut, A, 0x24, write=True, wdata=0x55667788)
    got, _ = await access(dut, A, 0x24)
    assert got == 0x55667788, f"A read {got:#010x}"


@cocotb.test()
async def test_timing(dut):
    """Response latency: 1 cycle for reads and word writes, 2 for RMW."""
    await start(dut)
    _, lat = await access(dut, B, 0x30)
    assert lat == 1, f"read latency {lat} cycles"
    _, lat = await access(dut, B, 0x30, write=True, wdata=0x1)
    assert lat == 1, f"word write latency {lat} cycles"
    _, lat = await access(dut, B, 0x30, write=True, wdata=0x2, be=0x1)
    assert lat == 2, f"sub-word write latency {lat} cycles (expect RMW)"


# --- byte enables (read-modify-write) ---------------------------------

@cocotb.test()
async def test_byte_enables(dut):
    """sb/sh style writes modify only the enabled bytes."""
    await start(dut)
    await access(dut, B, 0x40, write=True, wdata=0x00000000)

    await access(dut, B, 0x40, write=True, wdata=0x000000AB, be=0x1)
    got, _ = await access(dut, B, 0x40)
    assert got == 0x000000AB, f"byte 0 write: {got:#010x}"

    await access(dut, B, 0x40, write=True, wdata=0x00CD0000, be=0x4)
    got, _ = await access(dut, B, 0x40)
    assert got == 0x00CD00AB, f"byte 2 write did not merge: {got:#010x}"

    await access(dut, B, 0x40, write=True, wdata=0xEF120000, be=0xC)
    got, _ = await access(dut, B, 0x40)
    assert got == 0xEF1200AB, f"halfword write did not merge: {got:#010x}"

    await access(dut, B, 0x40, write=True, wdata=0x99887766, be=0xF)
    got, _ = await access(dut, B, 0x40)
    assert got == 0x99887766, f"full word write: {got:#010x}"


# --- the point of the design: one memory, two windows -----------------

@cocotb.test()
async def test_aliasing(dut):
    """Both ports address the same physical memory."""
    await start(dut)
    await access(dut, B, 0x50, write=True, wdata=0xCAFEBABE)
    got, _ = await access(dut, A, 0x50)
    assert got == 0xCAFEBABE, \
        f"port A sees {got:#010x}; ports are not the same memory"
    # and the other way round (self-modifying code direction)
    await access(dut, A, 0x54, write=True, wdata=0x0BADF00D)
    got, _ = await access(dut, B, 0x54)
    assert got == 0x0BADF00D, f"port B sees {got:#010x}"


@cocotb.test()
async def test_concurrent_ports(dut):
    """Both ports are granted, and respond, in the same cycles.

    The two ports are driven by hand here rather than through access(),
    so that both bus phases can be observed: the address phase lives
    between the falling and the rising edge, so a background monitor
    sampling on clock edges would miss it.
    """
    await start(dut)
    await access(dut, A, 0x60, write=True, wdata=0xAAAA1111)
    await access(dut, B, 0x64, write=True, wdata=0xBBBB2222)

    # let both port FSMs leave their response state and return to IDLE
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)

    # address phase on both ports at once
    dut.ObiAddrA.value = 0x60
    dut.ObiAddrB.value = 0x64
    dut.ObiBeA.value = 0xF
    dut.ObiBeB.value = 0xF
    dut.ObiReqA.value = 1
    dut.ObiReqB.value = 1
    await Timer(1, unit="ns")
    assert dut.ObiGntA.value and dut.ObiGntB.value, \
        "the two ports were not granted in the same cycle"

    await RisingEdge(dut.clk)          # both accepted on this edge
    dut.ObiReqA.value = 0
    dut.ObiReqB.value = 0

    # response phase, one cycle later, on both ports at once
    await FallingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.ObiRvalidA.value and dut.ObiRvalidB.value, \
        "the two ports did not respond in the same cycle"
    assert int(dut.ObiRdataA.value) == 0xAAAA1111, \
        f"A read {int(dut.ObiRdataA.value):#010x}"
    assert int(dut.ObiRdataB.value) == 0xBBBB2222, \
        f"B read {int(dut.ObiRdataB.value):#010x}"


@cocotb.test()
async def test_write_while_fetch(dut):
    """A store on port B while port A fetches: both complete correctly."""
    await start(dut)
    await access(dut, A, 0x70, write=True, wdata=0x1234ABCD)

    results = {}

    async def fetch():
        results["instr"] = (await access(dut, A, 0x70))[0]

    async def store():
        await access(dut, B, 0x74, write=True, wdata=0x5A5A5A5A)
        results["stored"] = (await access(dut, B, 0x74))[0]

    f = cocotb.start_soon(fetch())
    s = cocotb.start_soon(store())
    await f
    await s
    assert results["instr"] == 0x1234ABCD, "fetch disturbed by the store"
    assert results["stored"] == 0x5A5A5A5A, "store lost"


@cocotb.test()
async def test_back_to_back(dut):
    """A stream of accesses keeps the port FSMs in step."""
    await start(dut)
    for i in range(8):
        await access(dut, B, 0x80 + 4 * i, write=True, wdata=0xD000 + i)
    for i in range(8):
        got, _ = await access(dut, A, 0x80 + 4 * i)
        assert got == 0xD000 + i, f"word {i}: {got:#010x}"
