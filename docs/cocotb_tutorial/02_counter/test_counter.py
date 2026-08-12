# Example 2: testing a synchronous circuit with cocotb.
#
# New concepts compared to example 1: a clock, reset, clock-edge
# triggers, the sample-on-falling-edge convention, and a background
# coroutine that monitors the DUT while the test drives it.
#
# Run with:  make        (add WAVES=1 for a dump.vcd)

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles

MAX = 15  # 4-bit counter


# ---------------------------------------------------------------------
# Every synchronous test starts the same way: start a clock, apply
# reset, release it. Put that in one helper and reuse it.
#
# Each test calls it as:   await start(dut)
#
# `start` is a plain helper, not cocotb API. Because it is `async def`,
# writing `start(dut)` alone only builds a coroutine object and runs
# nothing — the `await` is what executes it, inline, and suspends the
# calling test until it returns. Since it awaits clock edges inside,
# awaiting it is also what advances simulation time: with a 10 ns clock
# it takes the test from t=0 to t=15 ns (rising edges at 0 and 10,
# falling edge at 15), leaving reset released and Count == 0.
#
# Omit the `await` and Python only warns ("coroutine was never
# awaited"): no clock, no reset, 0 ns elapsed, and the test may still
# "pass" on Verilator's zero-initialised signals. See section 5 of
# docs/CocotbTutorial.md.
# ---------------------------------------------------------------------

async def start(dut, cycles=2):
    """Start the clock and apply a synchronous reset."""
    # start_soon schedules a coroutine to run in the background,
    # forever, in parallel with the test. Contrast with `await` below:
    # the clock must keep running after start() returns, so it is NOT
    # awaited; the reset sequence must complete first, so it IS.
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    dut.en.value = 0
    dut.reset.value = 1
    await ClockCycles(dut.clk, cycles)   # wait N rising edges
    dut.reset.value = 0
    await FallingEdge(dut.clk)           # settle on the falling edge


# ---------------------------------------------------------------------
# 1. Reset behaviour.
#
# Note the convention used throughout: drive inputs just after a rising
# edge, and sample outputs on the *falling* edge — safely away from the
# edge where flip-flops change. This avoids race conditions between the
# testbench and the DUT.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_reset(dut):
    """Reset forces the count to zero."""
    await start(dut)
    # After releasing reset and waiting for the falling edge, the synchronous
    # counter output should have settled to zero; this assertion verifies
    # that the DUT's Count signal is indeed 0 immediately after reset.
    assert dut.Count.value == 0, f"Count={dut.Count.value} after reset"


# ---------------------------------------------------------------------
# 2. Counting, and the enable input.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_count_up(dut):
    """With en high the counter increments once per clock."""
    # the start helper resets the DUT and leaves it ready to count
    await start(dut)
    dut.en.value = 1
    for expected in range(1, 8):
        await RisingEdge(dut.clk)   # the edge that increments
        await FallingEdge(dut.clk)  # sample away from the edge
        assert dut.Count.value == expected, \
            f"got {int(dut.Count.value)}, expected {expected}"


@cocotb.test()
async def test_enable_holds(dut):
    """With en low the counter holds its value."""
    await start(dut)
    dut.en.value = 1
    await ClockCycles(dut.clk, 3)
    await FallingEdge(dut.clk)
    held = int(dut.Count.value)

    dut.en.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
        assert dut.Count.value == held, "counter moved while disabled"

    dut.en.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    assert dut.Count.value == held + 1, "counter did not resume"


# ---------------------------------------------------------------------
# 3. Wraparound and a combinational flag.
#
# Wrap is combinational (en & Count == MAX), so it is visible in the
# same cycle as the last count value — before the edge that wraps.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_wrap(dut):
    """Wrap pulses for one cycle at MAX, then the count rolls over."""
    await start(dut)
    dut.en.value = 1

    # walk up to MAX
    for _ in range(MAX):
        await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)

    assert dut.Count.value == MAX, f"Count={int(dut.Count.value)}"
    assert dut.Wrap.value == 1, "Wrap not asserted at MAX"

    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    assert dut.Count.value == 0, "counter did not wrap to 0"
    assert dut.Wrap.value == 0, "Wrap stuck high"


@cocotb.test()
async def test_wrap_needs_enable(dut):
    """Wrap stays low at MAX while the counter is disabled."""
    await start(dut)
    dut.en.value = 1
    for _ in range(MAX):
        await RisingEdge(dut.clk)
    dut.en.value = 0
    await FallingEdge(dut.clk)
    assert dut.Count.value == MAX
    assert dut.Wrap.value == 0, "Wrap asserted without enable"


# ---------------------------------------------------------------------
# 4. Reset in the middle of operation.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_reset_midcount(dut):
    """Reset clears the counter at any time and it restarts from 0."""
    await start(dut)
    dut.en.value = 1
    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    assert dut.Count.value == 5

    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)
    assert dut.Count.value == 0, "reset did not clear the counter"

    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    assert dut.Count.value == 1, "counter did not restart"


# ---------------------------------------------------------------------
# 5. A background monitor.
#
# A coroutine started with start_soon runs in parallel with the test.
# This one watches every clock edge and independently checks the DUT
# against a Python model of the counter — a scoreboard in miniature.
# ---------------------------------------------------------------------

async def count_monitor(dut, errors):
    """Shadow the counter in Python and flag any mismatch."""
    model = 0
    while True:
        await RisingEdge(dut.clk)
        # values *before* this edge decide the next state
        if dut.reset.value:
            model = 0
        elif dut.en.value:
            model = (model + 1) % (MAX + 1)
        await FallingEdge(dut.clk)   # now compare the new state
        if int(dut.Count.value) != model:
            errors.append(f"t={cocotb.utils.get_sim_time('ns')}ns: "
                          f"DUT={int(dut.Count.value)} model={model}")


@cocotb.test()
async def test_against_monitor(dut):
    """Random enable pattern, checked by a background monitor."""
    import random
    random.seed(2)

    errors = []
    await start(dut)
    cocotb.start_soon(count_monitor(dut, errors))

    for _ in range(100):
        dut.en.value = random.randint(0, 1)
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)

    assert not errors, "monitor mismatches:\n" + "\n".join(errors)


# ---------------------------------------------------------------------
# 6. Bonus: how NOT to write a check.
#
# Reading an output immediately after a rising edge, without waiting,
# can return the value from before the edge. Always separate driving
# and sampling with a trigger — that is what Timer/FallingEdge are for.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_sampling_convention(dut):
    """Show why sampling needs a settling delay after the edge."""
    await start(dut)
    dut.en.value = 1
    await RisingEdge(dut.clk)
    # A tiny Timer is enough to let the flip-flop output settle.
    await Timer(1, unit="ns")
    assert dut.Count.value == 1, \
        "read too early — no time advanced after the edge"
