# cocotb testbench for hipv_core: runs RV32I programs from a Python
# OBI instruction memory and checks results in the OBI data memory.
#
# Programs are built with the encoders in tb/common/rv32i.py and end
# in a spin loop (jal x0, 0); each test runs a fixed cycle budget and
# then checks the data-memory contents.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from obi import obi_slave
from rv32i import (NOP, m32, program, addi, add, sub, lw, lh, lhu, lb, lbu,
                   sw, sh, sb, beq, bne, blt, jal, jalr, lui, auipc)

SPIN = jal(0, 0)  # jump-to-self


async def run_program(dut, imem, dmem, cycles, gnt_delay=0, rvalid_delay=1):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(obi_slave(
        dut.clk, imem, dut.ObiIReq, dut.ObiIGnt, dut.ObiIAddr,
        dut.ObiIRvalid, dut.ObiIRdata, default=NOP,
        gnt_delay=gnt_delay, rvalid_delay=rvalid_delay))
    cocotb.start_soon(obi_slave(
        dut.clk, dmem, dut.ObiDReq, dut.ObiDGnt, dut.ObiDAddr,
        dut.ObiDRvalid, dut.ObiDRdata, we=dut.ObiDWe, be=dut.ObiDBe,
        wdata=dut.ObiDWdata, gnt_delay=gnt_delay, rvalid_delay=rvalid_delay))
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_arith_forwarding(dut):
    """Back-to-back dependent arithmetic exercises the forwarding paths."""
    dmem = {}
    imem = program([
        addi(1, 0, 5),      # x1 = 5
        addi(2, 0, 7),      # x2 = 7
        add(3, 1, 2),       # x3 = 12   (E->E distance 2, W fwd)
        sub(4, 3, 1),       # x4 = 7    (immediate dependence)
        add(5, 4, 4),       # x5 = 14
        sw(3, 0, 0),        # mem[0] = 12
        sw(4, 4, 0),        # mem[4] = 7
        sw(5, 8, 0),        # mem[8] = 14
        SPIN,
    ])
    await run_program(dut, imem, dmem, 200)
    assert dmem.get(0) == 12, f"mem[0]={dmem.get(0)}"
    assert dmem.get(4) == 7, f"mem[4]={dmem.get(4)}"
    assert dmem.get(8) == 14, f"mem[8]={dmem.get(8)}"


@cocotb.test()
async def test_load_use(dut):
    """A load immediately followed by a use of the loaded value."""
    dmem = {0x40: 100}
    imem = program([
        addi(1, 0, 0x40),   # x1 = 0x40
        lw(2, 0, 1),        # x2 = mem[0x40] = 100
        addi(3, 2, 1),      # x3 = 101   (load-use dependence)
        sw(3, 4, 1),        # mem[0x44] = 101
        SPIN,
    ])
    await run_program(dut, imem, dmem, 200)
    assert dmem.get(0x44) == 101, f"mem[0x44]={dmem.get(0x44)}"


@cocotb.test()
async def test_branch_loop(dut):
    """Sum 1..5 with a bne loop: mem[0] = 15."""
    dmem = {}
    imem = program([
        addi(1, 0, 0),      # x1 = sum
        addi(2, 0, 1),      # x2 = i
        addi(3, 0, 6),      # x3 = limit
        add(1, 1, 2),       # loop: sum += i
        addi(2, 2, 1),      # i++
        bne(2, 3, -8),      # while i != 6
        sw(1, 0, 0),        # mem[0] = 15
        SPIN,
    ])
    await run_program(dut, imem, dmem, 400)
    assert dmem.get(0) == 15, f"mem[0]={dmem.get(0)}"


@cocotb.test()
async def test_branch_not_taken(dut):
    """A not-taken branch must not disturb the instruction stream."""
    dmem = {}
    imem = program([
        addi(1, 0, 1),      # x1 = 1
        addi(2, 0, 2),      # x2 = 2
        beq(1, 2, 12),      # not taken
        blt(2, 1, 12),      # not taken
        sw(2, 0, 0),        # mem[0] = 2
        SPIN,
    ])
    await run_program(dut, imem, dmem, 200)
    assert dmem.get(0) == 2, f"mem[0]={dmem.get(0)}"


@cocotb.test()
async def test_call_return(dut):
    """jal/jalr call and return: mem[0] = 42."""
    dmem = {}
    imem = program([
        jal(1, 0x10),       # 0x00: call func at 0x10
        sw(9, 0, 0),        # 0x04: after return: mem[0] = x9
        SPIN,               # 0x08:
        NOP,                # 0x0c:
        addi(9, 0, 42),     # 0x10: func: x9 = 42
        jalr(0, 1, 0),      # 0x14: return to x1 (= 0x04)
    ])
    await run_program(dut, imem, dmem, 300)
    assert dmem.get(0) == 42, f"mem[0]={dmem.get(0)}"


@cocotb.test()
async def test_lui_auipc(dut):
    """lui/auipc build addresses and constants."""
    dmem = {}
    imem = program([
        lui(1, 0x12345),    # x1 = 0x12345000
        addi(1, 1, 0x678),  # x1 = 0x12345678
        auipc(2, 0),        # x2 = PC of this instruction (0x8)
        sw(1, 0, 0),        # mem[0] = 0x12345678
        sw(2, 4, 0),        # mem[4] = 0x8
        SPIN,
    ])
    await run_program(dut, imem, dmem, 200)
    assert dmem.get(0) == 0x12345678, f"mem[0]={hex(dmem.get(0, 0))}"
    assert dmem.get(4) == 0x8, f"mem[4]={hex(dmem.get(4, 0))}"


@cocotb.test()
async def test_byte_half_access(dut):
    """sb/sh/lb/lbu/lh/lhu with sign extension through memory."""
    dmem = {0x20: 0x00000000}
    imem = program([
        addi(1, 0, 0x20),   # base
        addi(2, 0, -1),     # x2 = 0xFFFFFFFF
        sb(2, 1, 1),        # mem byte at 0x21 = 0xFF
        sh(2, 4, 1),        # mem half at 0x24 = 0xFFFF
        lb(3, 1, 1),        # x3 = sign-extended 0xFF = -1
        lbu(4, 1, 1),       # x4 = 0xFF
        lh(5, 4, 1),        # x5 = -1
        lhu(6, 4, 1),       # x6 = 0xFFFF
        sw(3, 8, 1),        # mem[0x28] = 0xFFFFFFFF
        sw(4, 12, 1),       # mem[0x2c] = 0xFF
        sw(5, 16, 1),       # mem[0x30] = 0xFFFFFFFF
        sw(6, 20, 1),       # mem[0x34] = 0xFFFF
        SPIN,
    ])
    await run_program(dut, imem, dmem, 500)
    assert dmem.get(0x20) == 0x0000FF00, f"sb: {hex(dmem.get(0x20, 0))}"
    assert dmem.get(0x24) == 0x0000FFFF, f"sh: {hex(dmem.get(0x24, 0))}"
    assert dmem.get(0x28) == m32(-1), "lb sign extension"
    assert dmem.get(0x2C) == 0xFF, "lbu zero extension"
    assert dmem.get(0x30) == m32(-1), "lh sign extension"
    assert dmem.get(0x34) == 0xFFFF, "lhu zero extension"


@cocotb.test()
async def test_slow_memories(dut):
    """The same branch loop with slow instruction and data memories."""
    dmem = {}
    imem = program([
        addi(1, 0, 0),
        addi(2, 0, 1),
        addi(3, 0, 4),
        add(1, 1, 2),       # loop: sum += i
        addi(2, 2, 1),
        bne(2, 3, -8),      # sum 1..3 = 6
        sw(1, 0, 0),
        SPIN,
    ])
    await run_program(dut, imem, dmem, 900, gnt_delay=1, rvalid_delay=2)
    assert dmem.get(0) == 6, f"mem[0]={dmem.get(0)}"
