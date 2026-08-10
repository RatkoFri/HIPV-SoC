# cocotb testbench for the regfile module.
import cocotb
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_regfile_reset(dut):
    """Placeholder: verify regfile resets cleanly."""
    pass
