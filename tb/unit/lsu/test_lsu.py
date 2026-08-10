# cocotb testbench for the lsu module.
import cocotb
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_lsu_reset(dut):
    """Placeholder: verify lsu resets cleanly."""
    pass
