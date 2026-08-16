# cocotb testbench for obi_xbar.
#
# The testbench plays both masters (driving the flattened master ports)
# and all five slaves (a simple memory per slave port, with
# configurable latency). Ports are packed vectors, so master m and
# slave s are accessed through the slice helpers below.
#
# Run:  make               (fixed priority, data over fetch)
#       make ARB_POLICY=1  (round robin)

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

from socmap import (MASTER_D, MASTER_I, SLAVE, NUM_MASTERS, NUM_SLAVES,
                    REGIONS, base)

POLICY = int(os.environ.get("ARB_POLICY", "0"))


# --- helpers for the flattened ports ---------------------------------
#
# Reading a DUT *output* is fine. Driving one field of a packed *input*
# is not: a read-modify-write of sig.value returns the value from before
# any assignment made in this same delta, so two writes in one delta
# would clobber each other. Every driven vector therefore has a Python
# shadow register, and only the shadow is ever read back.

def get_field(sig, idx, width):
    """Read slice [idx*width +: width] out of a packed DUT output."""
    return (int(sig.value) >> (idx * width)) & ((1 << width) - 1)


def get_bit(sig, idx):
    return (int(sig.value) >> idx) & 1


class Shadow:
    """Python-side mirror of a packed input vector."""

    def __init__(self, sig):
        self.sig = sig
        self.val = 0
        self.sig.value = 0

    def set_field(self, idx, width, value):
        mask = ((1 << width) - 1) << (idx * width)
        self.val = (self.val & ~mask) | \
            ((value & ((1 << width) - 1)) << (idx * width))
        self.sig.value = self.val

    def set_bit(self, idx, value):
        self.val = (self.val | (1 << idx)) if value else (self.val & ~(1 << idx))
        self.sig.value = self.val

    def set(self, value):
        self.val = value
        self.sig.value = value


# --- slave models -----------------------------------------------------

async def slave_bank(dut, drv, mems, latency=1):
    """One simple memory per slave port, all served in parallel."""
    pending = [None] * NUM_SLAVES          # [cycles_left, data]
    while True:
        await FallingEdge(dut.clk)
        gnt = 0
        rvalid = 0
        for s in range(NUM_SLAVES):
            # response channel
            if pending[s] is not None and pending[s][0] == 0:
                rvalid |= 1 << s
                drv["SRdata"].set_field(s, 32, pending[s][1])
                pending[s] = None
            elif pending[s] is not None:
                pending[s][0] -= 1
            # address channel
            if pending[s] is None and get_bit(dut.SReq, s):
                gnt |= 1 << s
                addr = get_field(dut.SAddr, s, 32) & ~3
                if get_bit(dut.SWe, s):
                    be = get_field(dut.SBe, s, 4)
                    wd = get_field(dut.SWdata, s, 32)
                    mask = sum(0xFF << (8 * i) for i in range(4) if (be >> i) & 1)
                    mems[s][addr] = (mems[s].get(addr, 0) & ~mask) | (wd & mask)
                    pending[s] = [latency - 1, 0]
                else:
                    pending[s] = [latency - 1, mems[s].get(addr, 0)]
        drv["SGnt"].set(gnt)
        drv["SRvalid"].set(rvalid)


async def start(dut, mems=None, latency=1):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    drv = {name: Shadow(getattr(dut, name))
           for name in ("MReq", "MAddr", "MWe", "MBe", "MWdata",
                        "SGnt", "SRvalid", "SRdata")}
    if mems is None:
        mems = [dict() for _ in range(NUM_SLAVES)]
    cocotb.start_soon(slave_bank(dut, drv, mems, latency))
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)
    return drv, mems


# --- master driver ----------------------------------------------------

async def master_access(dut, drv, m, addr, write=False, wdata=0, be=0xF,
                        timeout=50):
    """Run one full OBI transaction on master port m; return read data."""
    drv["MAddr"].set_field(m, 32, addr)
    drv["MWe"].set_bit(m, write)
    drv["MBe"].set_field(m, 4, be)
    drv["MWdata"].set_field(m, 32, wdata)
    drv["MReq"].set_bit(m, 1)
    # address phase: hold req until granted
    for _ in range(timeout):
        await Timer(1, unit="ns")
        if get_bit(dut.MGnt, m):
            break
        await FallingEdge(dut.clk)
    else:
        raise AssertionError(f"master {m}: no grant for {hex(addr)}")
    await RisingEdge(dut.clk)
    drv["MReq"].set_bit(m, 0)
    # Response phase. The slave model drives SRvalid on the falling edge
    # and this coroutine wakes on the same edge, so settle first —
    # otherwise we may sample MRvalid before the slave's write lands.
    for _ in range(timeout):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if get_bit(dut.MRvalid, m):
            return get_field(dut.MRdata, m, 32)
    raise AssertionError(f"master {m}: no response for {hex(addr)}")


# --- tests ------------------------------------------------------------


@cocotb.test()
async def test_routing_per_slave(dut):
    """Each master reaches every slave, and data comes back correctly."""
    drv, mems = await start(dut)
    for name, idx in SLAVE.items():
        mems[idx][base(name)] = 0x1000_0000 + idx
    for m in (MASTER_D, MASTER_I):
        for name, idx in SLAVE.items():
            got = await master_access(dut, drv, m, base(name))
            assert got == 0x1000_0000 + idx, \
                f"master {m} read {hex(got)} from {name}"


@cocotb.test()
async def test_write_routing(dut):
    """Writes land in the addressed slave only."""
    drv, mems = await start(dut)
    await master_access(dut, drv, MASTER_D, base("DMEM") + 8, write=True,
                        wdata=0xDEADBEEF)
    assert mems[SLAVE["DMEM"]].get(base("DMEM") + 8) == 0xDEADBEEF
    await master_access(dut, drv, MASTER_D, base("UART"), write=True,
                        wdata=0x41, be=0x1)
    assert mems[SLAVE["UART"]].get(base("UART")) == 0x41
    assert base("UART") not in mems[SLAVE["DMEM"]], "write leaked to DMEM"


@cocotb.test()
async def test_concurrent_different_slaves(dut):
    """Both masters access different slaves in the same cycles."""
    drv, mems = await start(dut)
    mems[SLAVE["IMEM"]][base("IMEM") + 0x40] = 0xAAAA_0001
    mems[SLAVE["DMEM"]][base("DMEM") + 0x40] = 0xBBBB_0002

    results = {}

    async def run(m, addr, key):
        results[key] = await master_access(dut, drv, m, addr)

    t0 = cocotb.utils.get_sim_time("ns")
    ti = cocotb.start_soon(run(MASTER_I, base("IMEM") + 0x40, "i"))
    td = cocotb.start_soon(run(MASTER_D, base("DMEM") + 0x40, "d"))
    await ti
    await td
    elapsed = cocotb.utils.get_sim_time("ns") - t0

    assert results["i"] == 0xAAAA_0001 and results["d"] == 0xBBBB_0002
    # a single access takes ~20ns; concurrency must not double that
    assert elapsed < 40, f"accesses serialised: {elapsed}ns"


@cocotb.test()
async def test_contention_same_slave(dut):
    """Both masters target one slave: both complete, one goes first."""
    drv, mems = await start(dut)
    mems[SLAVE["DMEM"]][base("DMEM")] = 0xC0FFEE

    order = []

    async def run(m):
        val = await master_access(dut, drv, m, base("DMEM"))
        order.append(m)
        assert val == 0xC0FFEE, f"master {m} got {hex(val)}"

    td = cocotb.start_soon(run(MASTER_D))
    ti = cocotb.start_soon(run(MASTER_I))
    await td
    await ti

    assert len(order) == 2, "both masters must complete"
    if POLICY == 0:
        assert order[0] == MASTER_D, \
            "fixed priority must serve the data master first"


@cocotb.test()
async def test_slave_busy_serialises(dut):
    """A slave is never given a second access before it responds."""
    drv, mems = await start(dut, latency=4)
    mems[SLAVE["DMEM"]][base("DMEM")] = 0x11
    mems[SLAVE["DMEM"]][base("DMEM") + 4] = 0x22

    async def watch():
        """SReq for DMEM must never be high while it owes a response."""
        s = SLAVE["DMEM"]
        outstanding = False
        for _ in range(80):
            await FallingEdge(dut.clk)
            await Timer(1, unit="ns")
            if outstanding:
                assert not get_bit(dut.SReq, s), \
                    "new request issued to a busy slave"
            if get_bit(dut.SReq, s) and get_bit(dut.SGnt, s):
                outstanding = True
            if get_bit(dut.SRvalid, s):
                outstanding = False

    w = cocotb.start_soon(watch())
    td = cocotb.start_soon(master_access(dut, drv, MASTER_D, base("DMEM"),
                                         timeout=100))
    ti = cocotb.start_soon(master_access(dut, drv, MASTER_I, base("DMEM") + 4,
                                         timeout=100))
    assert await td == 0x11
    assert await ti == 0x22
    w.cancel()


@cocotb.test()
async def test_decode_error(dut):
    """An unmapped address is answered by the error responder."""
    drv, mems = await start(dut)
    got = await master_access(dut, drv, MASTER_D, 0x8000_0000)
    assert got == 0, f"error response should read 0, got {hex(got)}"
    # no slave port may see the stray access
    assert int(dut.SReq.value) == 0, "error access reached a slave port"
    # and the bus still works afterwards
    mems[SLAVE["DMEM"]][base("DMEM")] = 0x5A5A
    got = await master_access(dut, drv, MASTER_D, base("DMEM"))
    assert got == 0x5A5A, "bus broken after a decode error"


@cocotb.test()
async def test_error_and_normal_concurrently(dut):
    """A decode error on one master does not disturb the other."""
    drv, mems = await start(dut)
    mems[SLAVE["IMEM"]][base("IMEM")] = 0x1234_5678

    results = {}

    async def run(key, m, addr):
        results[key] = await master_access(dut, drv, m, addr)

    a = cocotb.start_soon(run("bad", MASTER_D, 0xDEAD_0000))
    b = cocotb.start_soon(run("good", MASTER_I, base("IMEM")))
    await a
    await b
    assert results["bad"] == 0
    assert results["good"] == 0x1234_5678


@cocotb.test()
async def test_back_to_back(dut):
    """Repeated accesses from both masters stay correctly routed."""
    drv, mems = await start(dut)
    for i in range(8):
        mems[SLAVE["IMEM"]][base("IMEM") + 4 * i] = 0xA000 + i
        mems[SLAVE["DMEM"]][base("DMEM") + 4 * i] = 0xD000 + i

    async def fetch():
        for i in range(8):
            v = await master_access(dut, drv, MASTER_I, base("IMEM") + 4 * i)
            assert v == 0xA000 + i, f"fetch {i}: {hex(v)}"

    async def data():
        for i in range(8):
            v = await master_access(dut, drv, MASTER_D, base("DMEM") + 4 * i)
            assert v == 0xD000 + i, f"data {i}: {hex(v)}"

    f = cocotb.start_soon(fetch())
    d = cocotb.start_soon(data())
    await f
    await d
