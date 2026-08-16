# cocotb testbench for obi_arbiter.
#
# Built with NUM_MASTERS=4 so the rotation is visible. Run both
# policies:  make            (fixed priority)
#            make ARB_POLICY=1   (round robin)

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

POLICY = int(os.environ.get("ARB_POLICY", "0"))
N = 4


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.Req.value = 0
    dut.Update.value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


def granted(dut):
    """Index of the granted master, or None."""
    g = int(dut.Grant.value)
    assert bin(g).count("1") <= 1, f"Grant={g:04b} is not one-hot"
    return None if g == 0 else g.bit_length() - 1


async def request(dut, mask):
    dut.Req.value = mask
    await Timer(1, unit="ns")
    return granted(dut)


async def serve(dut, mask):
    """Request, take the grant, and advance the arbiter one transfer."""
    who = await request(dut, mask)
    dut.Update.value = 1
    await RisingEdge(dut.clk)
    dut.Update.value = 0
    await FallingEdge(dut.clk)
    return who


@cocotb.test()
async def test_idle(dut):
    """No requests, no grant."""
    await start(dut)
    assert await request(dut, 0b0000) is None


@cocotb.test()
async def test_single_requester(dut):
    """A lone requester is always granted, whatever the policy."""
    await start(dut)
    for i in range(N):
        assert await request(dut, 1 << i) == i, f"master {i} not granted"


@cocotb.test()
async def test_onehot_always(dut):
    """Every request combination produces a one-hot (or zero) grant."""
    await start(dut)
    for mask in range(1 << N):
        who = await request(dut, mask)
        if mask == 0:
            assert who is None
        else:
            assert who is not None and (mask >> who) & 1, \
                f"mask={mask:04b} granted non-requesting master {who}"


@cocotb.test()
async def test_policy(dut):
    """Fixed priority always picks master 0; round robin rotates."""
    await start(dut)
    seen = []
    for _ in range(8):
        seen.append(await serve(dut, 0b1111))   # everyone always asking

    if POLICY == 0:
        assert seen == [0] * 8, f"fixed priority should starve: {seen}"
    else:
        assert seen == [0, 1, 2, 3, 0, 1, 2, 3], f"rotation wrong: {seen}"


@cocotb.test()
async def test_round_robin_skips_idle(dut):
    """Round robin skips masters that are not requesting."""
    await start(dut)
    if POLICY != 1:
        return                      # nothing to check for fixed priority
    seen = [await serve(dut, 0b1010) for _ in range(4)]
    assert seen == [1, 3, 1, 3], f"expected alternation of 1 and 3: {seen}"


@cocotb.test()
async def test_pointer_holds_without_update(dut):
    """Without Update the arbiter keeps offering the same master."""
    await start(dut)
    first = await request(dut, 0b1111)
    for _ in range(3):
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        assert granted(dut) == first, "grant moved without a transfer"
