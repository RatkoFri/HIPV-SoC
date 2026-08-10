# cocotb testbench for the wbu module.
import cocotb
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_wbu_reset(dut):
    """Placeholder: verify wbu resets cleanly."""
    pass
