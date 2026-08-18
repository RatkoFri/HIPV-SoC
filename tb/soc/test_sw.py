# Run an arbitrary program image on the SoC and capture its UART output.
#
# Used by `make run` in sw/: the image comes from INIT_FILE, so this
# testbench does not care what the program does — it boots the SoC,
# decodes whatever the program prints, and logs it.
#
# Environment:
#   UART_DIV    clock cycles per bit (must match what the program sets)
#   RUN_CYCLES  how long to run
#   EXPECT_FILE golden file; the captured text must match it exactly
#   EXPECT      same, as a literal string (single line; a golden file
#               avoids quoting trouble with newlines)
# With neither set the test only reports the output and checks that the
# program printed something.

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

UART_DIV = int(os.environ.get("UART_DIV", "48"))
RUN_CYCLES = int(os.environ.get("RUN_CYCLES", "200000"))

# unset or empty means "just report what the program printed"
EXPECT_FILE = os.environ.get("EXPECT_FILE") or None
EXPECT = os.environ.get("EXPECT") or None
if EXPECT_FILE:
    with open(EXPECT_FILE) as f:
        EXPECT = f.read()


async def uart_monitor(dut, out):
    """Decode 8N1 frames off Tx forever, appending bytes to `out`."""
    while True:
        while dut.Tx.value == 1:
            await RisingEdge(dut.clk)
        await ClockCycles(dut.clk, UART_DIV // 2)      # middle of start bit
        byte = 0
        for i in range(8):
            await ClockCycles(dut.clk, UART_DIV)
            byte |= int(dut.Tx.value) << i
        await ClockCycles(dut.clk, UART_DIV)           # stop bit
        out.append(byte)


@cocotb.test()
async def run_program(dut):
    """Boot the image in INIT_FILE and report what it prints."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.Rx.value = 1
    dut.GpioIn.value = 0
    dut.reset.value = 1
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.reset.value = 0

    out = []
    mon = cocotb.start_soon(uart_monitor(dut, out))
    await ClockCycles(dut.clk, RUN_CYCLES)
    mon.cancel()

    text = "".join(chr(b) for b in out)
    dut._log.info("UART output (%d bytes):\n%s", len(out), text)

    if EXPECT is not None:
        expected = EXPECT.replace("\\n", "\n")
        assert text == expected, \
            f"UART output {text!r} does not match expected {expected!r}"
    else:
        assert out, "the program produced no UART output"


# keep the module importable without a DUT for quick checks
if __name__ == "__main__":
    print(f"UART_DIV={UART_DIV} RUN_CYCLES={RUN_CYCLES} EXPECT={EXPECT!r}")
