# cocotb testbench for the Nexys A7 FPGA wrapper (fpga/anvil/top.sv).
#
# The SoC itself is verified in tb/soc; this checks only the board
# plumbing, which is exactly where bring-up bugs hide:
#   - the active-low CPU_RESETN button becomes an active-high SoC reset
#   - the power-on reset releases on its own
#   - GPIO reaches the LEDs, the switches reach GPIO in
#   - the UART reaches the right pin
#
# `clk` drives the SoC directly (no divider), so a UART bit lasts
# BAUD_LIMIT clk cycles. The testbench clocks it at 20 ns = 50 MHz, the
# frequency the XDC constrains.

import os
import sys

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "soc"))
from gen_prog import EXPECTED_UART, GPIO_VALUE, BAUD_LIMIT  # noqa: E402

BIT_CYCLES = BAUD_LIMIT         # clk cycles per UART bit
                                # (the SoC is clocked directly by clk)


# cocotb runs every test in one simulation, and cancels the coroutines a
# test started when that test ends — so every test must start its own
# clock. What does *not* restart by itself is the SoC: the program runs
# once at boot, so a test that wants to watch it from the beginning has
# to press the reset button first.


async def start(dut, hold_reset=True, restart=True):
    """Clock running; optionally restart the SoC via the reset button.

    hold_reset: leave the button pressed on return.
    restart:    pulse the button first, so the program runs again from
                the beginning (needed by any test that observes boot).
    """
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())   # 50 MHz

    dut.uart_rx.value = 1
    dut.sw.value = 0

    if restart:
        dut.cpu_resetn.value = 0            # press reset
        await ClockCycles(dut.clk, 8)

    dut.cpu_resetn.value = 0 if hold_reset else 1
    await ClockCycles(dut.clk, 4)


@cocotb.test()
async def test_power_on_reset(dut):
    """With the button never pressed, the POR still resets the SoC.

    This test must run FIRST: cocotb runs every test in one simulation,
    and power-on state exists only once — by the second test the POR
    counter has long since saturated. Keep it at the top of the file.
    """
    await start(dut, hold_reset=False, restart=False)   # pristine power-up
    await Timer(1, unit="ns")
    assert int(dut.SocReset.value) == 1, "no power-on reset asserted"
    await ClockCycles(dut.clk, 80)
    assert int(dut.SocReset.value) == 0, "power-on reset never released"


@cocotb.test()
async def test_reset_polarity(dut):
    """Holding the button (low) asserts the SoC's active-high reset."""
    await start(dut, hold_reset=True, restart=False)
    await ClockCycles(dut.clk, 20)
    assert int(dut.SocReset.value) == 1, \
        "cpu_resetn low must produce SoC reset high"

    dut.cpu_resetn.value = 1                 # release the button
    await ClockCycles(dut.clk, 60)
    assert int(dut.SocReset.value) == 0, \
        "releasing the button must deassert the SoC reset"


@cocotb.test()
async def test_gpio_to_leds(dut):
    """The program's GPIO writes appear on the LED pins."""
    await start(dut, hold_reset=False)
    for _ in range(4000):
        await RisingEdge(dut.clk)
        if int(dut.led.value) == GPIO_VALUE:
            return
    raise AssertionError(
        f"led is {int(dut.led.value):#04x}, expected {GPIO_VALUE:#04x}")


@cocotb.test()
async def test_switches_to_gpio(dut):
    """The switch pins reach the GPIO peripheral's input register."""
    await start(dut, hold_reset=False)
    dut.sw.value = 0x5A
    await ClockCycles(dut.clk, 20)
    assert int(dut.soc.gpio.GpioIn.value) == 0x5A, \
        "switch pins are not wired to the GPIO input"


@cocotb.test()
async def test_uart_pin(dut):
    """The program's UART output comes out on the uart_tx pin."""
    await start(dut, hold_reset=False)

    got = []

    async def sample():
        """Read Tx just after a clock edge, once it has settled."""
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        return int(dut.uart_tx.value)

    async def monitor():
        # Resynchronise on every frame: wait for the line to be idle,
        # then for a start bit. Out of reset Tx is still low, and the
        # last data bit of a frame can also be low, so hunting for a
        # start bit without first seeing idle latches a false one.
        while True:
            while await sample() != 1:       # idle
                pass
            while await sample() != 0:       # start bit
                pass
            await ClockCycles(dut.clk, BIT_CYCLES // 2)   # mid start bit
            byte = 0
            for i in range(8):
                await ClockCycles(dut.clk, BIT_CYCLES)
                await Timer(1, unit="ns")
                byte |= int(dut.uart_tx.value) << i
            got.append(byte)

    mon = cocotb.start_soon(monitor())
    await ClockCycles(dut.clk, 40000)
    mon.cancel()

    assert got == EXPECTED_UART, \
        f"uart_tx sent {[hex(b) for b in got]}, expected " \
        f"{[hex(b) for b in EXPECTED_UART]}"


@cocotb.test()
async def test_timer_led(dut):
    """led_timer follows the SoC's timer compare match."""
    await start(dut, hold_reset=False)
    await ClockCycles(dut.clk, 20)
    for _ in range(6000):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        assert int(dut.led_timer.value) == int(dut.soc.TimerOverflow.value), \
            "led_timer does not track TimerOverflow"
