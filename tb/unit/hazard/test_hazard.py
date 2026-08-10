# cocotb testbench for the hazard module (combinational forwarding).

import cocotb
from cocotb.triggers import Timer

FWD_RF, FWD_WB, FWD_MEM = 0, 1, 2


async def check(dut, rs1e, rs2e, rdm, rdw, wm, ww, exp_a, exp_b, msg):
    dut.Rs1E.value = rs1e
    dut.Rs2E.value = rs2e
    dut.RdM.value = rdm
    dut.RdW.value = rdw
    dut.RegWriteM.value = wm
    dut.RegWriteW.value = ww
    await Timer(1, unit="ns")
    assert int(dut.ForwardAE.value) == exp_a, f"{msg}: ForwardAE"
    assert int(dut.ForwardBE.value) == exp_b, f"{msg}: ForwardBE"


@cocotb.test()
async def test_forwarding_priority(dut):
    """M beats W, W beats none, x0 never forwards."""
    # no dependency
    await check(dut, 1, 2, 3, 4, 1, 1, FWD_RF, FWD_RF, "no match")
    # match in M only
    await check(dut, 3, 2, 3, 4, 1, 1, FWD_MEM, FWD_RF, "A from M")
    await check(dut, 1, 3, 3, 4, 1, 1, FWD_RF, FWD_MEM, "B from M")
    # match in W only
    await check(dut, 4, 2, 3, 4, 1, 1, FWD_WB, FWD_RF, "A from W")
    # match in both: M (newer) wins
    await check(dut, 5, 5, 5, 5, 1, 1, FWD_MEM, FWD_MEM, "M priority")
    # matches ignored when RegWrite is low
    await check(dut, 3, 3, 3, 3, 0, 0, FWD_RF, FWD_RF, "no write")
    await check(dut, 5, 5, 5, 5, 0, 1, FWD_WB, FWD_WB, "only W writes")
    # x0 is never forwarded
    await check(dut, 0, 0, 0, 0, 1, 1, FWD_RF, FWD_RF, "x0")
