# cocotb testbench for the wbu module (Writeback stage).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge

RESULT_ALU, RESULT_MEM, RESULT_PC4 = 0, 1, 2


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for name in ("ValidM", "ALUResultM", "ReadDataM", "PCPlus4M", "RdM",
                 "RegWriteM", "ResultSrcM"):
        getattr(dut, name).value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def push(dut, **sig):
    for name, val in sig.items():
        getattr(dut, name).value = val
    dut.ValidM.value = 1
    await RisingEdge(dut.clk)
    dut.ValidM.value = 0
    await FallingEdge(dut.clk)


@cocotb.test()
async def test_result_mux(dut):
    """ResultW selects ALU result, load data or PC+4."""
    await start(dut)
    assert dut.ReadyW.value == 1, "writeback must never stall"
    await push(dut, ALUResultM=0x111, ReadDataM=0x222, PCPlus4M=0x333,
               RdM=1, RegWriteM=1, ResultSrcM=RESULT_ALU)
    assert dut.ValidW.value == 1 and dut.RegWriteW.value == 1
    assert int(dut.ResultW.value) == 0x111 and dut.RdW.value == 1
    await push(dut, ALUResultM=0x111, ReadDataM=0x222, PCPlus4M=0x333,
               RdM=2, RegWriteM=1, ResultSrcM=RESULT_MEM)
    assert int(dut.ResultW.value) == 0x222 and dut.RdW.value == 2
    await push(dut, ALUResultM=0x111, ReadDataM=0x222, PCPlus4M=0x333,
               RdM=3, RegWriteM=1, ResultSrcM=RESULT_PC4)
    assert int(dut.ResultW.value) == 0x333 and dut.RdW.value == 3


@cocotb.test()
async def test_regwrite_qualification(dut):
    """RegWriteW is low for bubbles and non-writing instructions."""
    await start(dut)
    await push(dut, ALUResultM=0x5, RdM=4, RegWriteM=0, ResultSrcM=RESULT_ALU)
    assert dut.ValidW.value == 1 and dut.RegWriteW.value == 0
    await FallingEdge(dut.clk)                 # bubble follows
    assert dut.ValidW.value == 0 and dut.RegWriteW.value == 0, \
        "RegWriteW asserted for a bubble"
