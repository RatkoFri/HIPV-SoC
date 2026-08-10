# cocotb testbench for the hazard module.
import cocotb
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_hazard_reset(dut):
    """Placeholder: verify hazard resets cleanly."""
    pass
