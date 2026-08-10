# cocotb testbench for the ifu module.
import cocotb
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_ifu_reset(dut):
    """Placeholder: verify ifu resets cleanly."""
    pass
