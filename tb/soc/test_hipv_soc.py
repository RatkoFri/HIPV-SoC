# SoC-level cocotb testbench: the whole hipv_soc running a real program.
#
# The program in gen_prog.py is loaded at elaboration through INIT_FILE
# (synthesis-time initialization, the same path the FPGA flow uses) and
# exercises every slave. It reports results by transmitting bytes over
# the UART, so everything is checked at the SoC pins.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer

from gen_prog import (BAUD_LIMIT, EXPECTED_UART, GPIO_VALUE, TIMER_COMPARE)

CLK_NS = 10


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.Rx.value = 1              # UART line idles high
    dut.GpioIn.value = 0
    dut.reset.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.reset.value = 0


async def uart_rx(dut, out, count):
    """Decode 8N1 frames off the Tx pin by mid-bit sampling."""
    for _ in range(count):
        while dut.Tx.value == 1:
            await RisingEdge(dut.clk)
        await ClockCycles(dut.clk, BAUD_LIMIT // 2)   # middle of start bit
        byte = 0
        for i in range(8):
            await ClockCycles(dut.clk, BAUD_LIMIT)
            byte |= int(dut.Tx.value) << i
        await ClockCycles(dut.clk, BAUD_LIMIT)        # stop bit
        out.append(byte)


@cocotb.test()
async def test_program_reports_over_uart(dut):
    """The program runs end to end and reports the expected bytes.

    Each byte proves a different path:
      42   store to RAM through the DMEM window, then load back
      0xA5 GPIO register read back over the bus
      55   a branch loop (sum 1..10) with forwarding
      0xB7 low byte of instruction word 0, read through the DMEM window
           — the unified-memory aliasing
    """
    await start(dut)
    got = []
    rx = cocotb.start_soon(uart_rx(dut, got, len(EXPECTED_UART)))
    await ClockCycles(dut.clk, 20000)
    rx.cancel()
    assert got == EXPECTED_UART, \
        f"UART reported {[hex(b) for b in got]}, expected " \
        f"{[hex(b) for b in EXPECTED_UART]}"


@cocotb.test()
async def test_gpio_pins(dut):
    """The program drives the GPIO output pins."""
    await start(dut)
    for _ in range(2000):
        await RisingEdge(dut.clk)
        if int(dut.GpioOut.value) == GPIO_VALUE:
            return
    raise AssertionError(
        f"GpioOut is {int(dut.GpioOut.value):#04x}, expected {GPIO_VALUE:#04x}")


@cocotb.test()
async def test_timer_runs(dut):
    """The program starts the timer and its compare match fires."""
    await start(dut)
    await Timer(1, unit="ns")
    # compare registers reset to 0, so the level compare is true at first
    assert dut.TimerOverflow.value == 1, "expected the reset-value compare"

    # once the program writes a non-zero compare it must drop ...
    for _ in range(3000):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        if dut.TimerOverflow.value == 0:
            break
    else:
        raise AssertionError("TimerOverflow never cleared after programming")

    # ... and rise again when the counter reaches the compare value
    for _ in range(TIMER_COMPARE * 4):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        if dut.TimerOverflow.value == 1:
            return
    raise AssertionError("TimerOverflow never fired at the compare value")


@cocotb.test()
async def test_memory_contents(dut):
    """Results the program stored are present in the RAM array."""
    await start(dut)
    await ClockCycles(dut.clk, 20000)
    ram = dut.mem.ram.mem
    word = 0x200 // 4
    assert int(ram[word].value) == 42, \
        f"mem[{word}] = {int(ram[word].value)}, expected 42"
    assert int(ram[word + 1].value) == 55, \
        f"mem[{word + 1}] = {int(ram[word + 1].value)}, expected 55"


@cocotb.test()
async def test_reset_is_synchronous(dut):
    """Reset with the clock running restarts the program from address 0."""
    await start(dut)
    await ClockCycles(dut.clk, 3000)
    assert int(dut.GpioOut.value) == GPIO_VALUE, "program did not run"

    dut.reset.value = 1
    await ClockCycles(dut.clk, 4)
    dut.reset.value = 0
    await Timer(1, unit="ns")
    assert int(dut.GpioOut.value) == 0, "GPIO not cleared by reset"

    # and the program runs again from the start
    for _ in range(3000):
        await RisingEdge(dut.clk)
        if int(dut.GpioOut.value) == GPIO_VALUE:
            return
    raise AssertionError("the SoC did not restart after reset")
