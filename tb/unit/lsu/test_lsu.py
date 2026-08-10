# cocotb testbench for the lsu module (Memory stage).
#
# The testbench plays the Execute stage (ValidE + payload), the
# Writeback stage (ReadyW) and the OBI data-memory slave (obi.py).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

from obi import obi_slave

RESULT_ALU, RESULT_MEM, RESULT_PC4 = 0, 1, 2

E_INPUTS = ("ALUResultE", "WriteDataE", "PCPlus4E", "RdE", "Funct3E",
            "RegWriteE", "MemWriteE", "ResultSrcE")


def m32(v):
    return v & 0xFFFFFFFF


async def start(dut, mem, gnt_delay=0, rvalid_delay=1):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(obi_slave(
        dut.clk, mem, dut.ObiReqM, dut.ObiGntM, dut.ObiAddrM,
        dut.ObiRvalidM, dut.ObiRdataM, we=dut.ObiWeM, be=dut.ObiBeM,
        wdata=dut.ObiWdataM, gnt_delay=gnt_delay, rvalid_delay=rvalid_delay))
    for name in E_INPUTS:
        getattr(dut, name).value = 0
    dut.ValidE.value = 0
    dut.ReadyW.value = 1
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def push_op(dut, **sig):
    """Present one operation on the E inputs and wait until accepted."""
    for name in E_INPUTS:
        getattr(dut, name).value = m32(sig.get(name, 0))
    dut.ValidE.value = 1
    await Timer(1, unit="ns")          # settle combinational ReadyM
    for _ in range(30):
        if dut.ReadyM.value:           # sampled before the loading edge
            await RisingEdge(dut.clk)
            dut.ValidE.value = 0
            await FallingEdge(dut.clk)
            return
        await FallingEdge(dut.clk)
    raise AssertionError("timeout waiting for ReadyM")


async def wait_valid(dut, max_cycles=30):
    for _ in range(max_cycles):
        if dut.ValidM.value:
            return
        await FallingEdge(dut.clk)
    raise AssertionError("timeout waiting for ValidM")


@cocotb.test()
async def test_passthrough(dut):
    """A non-memory instruction passes through in one cycle."""
    await start(dut, {})
    await push_op(dut, ALUResultE=0x1234, RdE=7, RegWriteE=1,
                  ResultSrcE=RESULT_ALU)
    assert dut.ValidM.value == 1, "no single-cycle pass-through"
    assert int(dut.ALUResultM.value) == 0x1234
    assert dut.RdM.value == 7 and dut.RegWriteM.value == 1
    assert int(dut.ForwardDataM.value) == 0x1234
    await FallingEdge(dut.clk)
    assert dut.ValidM.value == 0, "stage did not drain"


@cocotb.test()
async def test_store_word(dut):
    """sw writes the full word through the OBI port."""
    mem = {}
    await start(dut, mem)
    await push_op(dut, ALUResultE=0x100, WriteDataE=0xCAFEBABE,
                  Funct3E=0b010, MemWriteE=1)
    await wait_valid(dut)
    assert mem.get(0x100) == 0xCAFEBABE, f"mem: {mem}"


@cocotb.test()
async def test_store_byte_half(dut):
    """sb/sh write only the addressed bytes."""
    mem = {0x40: 0x11223344}
    await start(dut, mem)
    await push_op(dut, ALUResultE=0x42, WriteDataE=0xAB,
                  Funct3E=0b000, MemWriteE=1)          # sb at offset 2
    await wait_valid(dut)
    assert mem[0x40] == 0x11AB3344, f"sb: {hex(mem[0x40])}"
    await push_op(dut, ALUResultE=0x42, WriteDataE=0xBEEF,
                  Funct3E=0b001, MemWriteE=1)          # sh at offset 2
    await wait_valid(dut)
    assert mem[0x40] == 0xBEEF3344, f"sh: {hex(mem[0x40])}"


@cocotb.test()
async def test_loads(dut):
    """lw/lh/lhu/lb/lbu with alignment and sign extension."""
    mem = {0x80: 0x8091A2B3}
    await start(dut, mem)
    cases = [  # funct3, byte offset, expected
        (0b010, 0, 0x8091A2B3),              # lw
        (0b000, 3, m32(-0x80)),              # lb  byte 3 = 0x80, signed
        (0b100, 3, 0x80),                    # lbu
        (0b000, 0, m32(-0x4D)),              # lb  byte 0 = 0xB3, signed
        (0b001, 2, m32(-0x7F6F)),            # lh  upper half 0x8091, signed
        (0b101, 2, 0x8091),                  # lhu
        (0b001, 0, m32(-0x5D4D)),            # lh  lower half 0xA2B3, signed
    ]
    for f3, off, expected in cases:
        await push_op(dut, ALUResultE=0x80 + off, Funct3E=f3, RegWriteE=1,
                      ResultSrcE=RESULT_MEM, RdE=5)
        await wait_valid(dut)
        got = int(dut.ReadDataM.value)
        assert got == expected, f"f3={f3:03b} off={off}: {hex(got)}"
        assert int(dut.ForwardDataM.value) == expected, "ForwardDataM wrong"
        await FallingEdge(dut.clk)


@cocotb.test()
async def test_memory_stall(dut):
    """ReadyM stays low while the OBI transaction is in flight."""
    mem = {0x10: 0x55}
    await start(dut, mem, gnt_delay=2, rvalid_delay=3)
    await push_op(dut, ALUResultE=0x10, Funct3E=0b010, RegWriteE=1,
                  ResultSrcE=RESULT_MEM, RdE=1)
    stalled = 0
    for _ in range(30):
        if dut.ValidM.value:
            break
        assert dut.ReadyM.value == 0, "ReadyM high during transaction"
        stalled += 1
        await FallingEdge(dut.clk)
    assert stalled >= 5, f"expected a long stall, got {stalled} cycles"
    assert int(dut.ReadDataM.value) == 0x55


@cocotb.test()
async def test_backpressure(dut):
    """With ReadyW low the stage holds its completed result."""
    await start(dut, {})
    dut.ReadyW.value = 0
    await push_op(dut, ALUResultE=0x77, RdE=2, RegWriteE=1,
                  ResultSrcE=RESULT_ALU)
    for _ in range(3):
        assert dut.ValidM.value == 1 and int(dut.ALUResultM.value) == 0x77
        assert dut.ReadyM.value == 0, "ReadyM high while full and stalled"
        await FallingEdge(dut.clk)
    dut.ReadyW.value = 1
    await FallingEdge(dut.clk)
    assert dut.ValidM.value == 0, "stage did not drain after ReadyW"
