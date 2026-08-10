# cocotb testbench for the idu module (Decode stage).
#
# The testbench plays the Fetch stage (ValidF/InstrF/PCF/PCPlus4F),
# the Execute stage (ReadyE, PCSrcE) and the Writeback stage
# (RegWriteW/RdW/ResultW around the register file write port).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

# --- control encodings, mirror config/hipv_pkg.sv ---------------------

ALU = {"ADD": 0, "SUB": 1, "SLL": 2, "SLT": 3, "SLTU": 4,
       "XOR": 5, "SRL": 6, "SRA": 7, "OR": 8, "AND": 9}
RESULT_ALU, RESULT_MEM, RESULT_PC4 = 0, 1, 2
SRCA_RF, SRCA_PC, SRCA_ZERO = 0, 1, 2

# --- RV32I instruction encoders ---------------------------------------


def r_type(f7, rs2, rs1, f3, rd):
    return f7 << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | rd << 7 | 0b0110011


def i_type(imm, rs1, f3, rd, op=0b0010011):
    return (imm & 0xFFF) << 20 | rs1 << 15 | f3 << 12 | rd << 7 | op


def s_type(imm, rs2, rs1, f3):
    imm &= 0xFFF
    return (imm >> 5) << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | \
        (imm & 0x1F) << 7 | 0b0100011


def b_type(imm, rs2, rs1, f3):
    imm &= 0x1FFF
    return (imm >> 12) << 31 | ((imm >> 5) & 0x3F) << 25 | rs2 << 20 | \
        rs1 << 15 | f3 << 12 | ((imm >> 1) & 0xF) << 8 | \
        ((imm >> 11) & 1) << 7 | 0b1100011


def u_type(imm20, rd, op=0b0110111):
    return (imm20 & 0xFFFFF) << 12 | rd << 7 | op


def j_type(imm, rd):
    imm &= 0x1FFFFF
    return (imm >> 20) << 31 | ((imm >> 1) & 0x3FF) << 21 | \
        ((imm >> 11) & 1) << 20 | ((imm >> 12) & 0xFF) << 12 | \
        rd << 7 | 0b1101111


def sext32(v):
    return v & 0xFFFFFFFF

# --- helpers ----------------------------------------------------------


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for sig in (dut.ValidF, dut.InstrF, dut.PCF, dut.PCPlus4F, dut.PCSrcE,
                dut.RegWriteW, dut.RdW, dut.ResultW):
        sig.value = 0
    dut.ReadyE.value = 1
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def push_instr(dut, instr, pc=0):
    """Present an instruction on the F inputs and wait until accepted."""
    dut.ValidF.value = 1
    dut.InstrF.value = instr
    dut.PCF.value = pc
    dut.PCPlus4F.value = (pc + 4) & 0xFFFFFFFF
    for _ in range(20):
        await FallingEdge(dut.clk)
        if dut.ReadyD.value:
            await RisingEdge(dut.clk)
            dut.ValidF.value = 0
            await FallingEdge(dut.clk)
            return
    raise AssertionError("timeout waiting for ReadyD")


async def rf_write(dut, rd, value):
    """One-cycle register file write through the W-stage port."""
    dut.RegWriteW.value = 1
    dut.RdW.value = rd
    dut.ResultW.value = value
    await RisingEdge(dut.clk)
    dut.RegWriteW.value = 0
    await FallingEdge(dut.clk)

# --- tests ------------------------------------------------------------


@cocotb.test()
async def test_handshake_and_fields(dut):
    """addi x5, x3, -7: fields, controls and immediate."""
    await start(dut)
    assert dut.ValidD.value == 0, "ValidD high after reset"
    await push_instr(dut, i_type(-7, 3, 0b000, 5), pc=0x40)
    assert dut.ValidD.value == 1
    assert dut.Rs1D.value == 3 and dut.RdD.value == 5
    assert dut.Funct3D.value == 0
    assert int(dut.ImmExtD.value) == sext32(-7)
    assert dut.RegWriteD.value == 1 and dut.MemWriteD.value == 0
    assert dut.ALUSrcBD.value == 1 and int(dut.ALUSrcAD.value) == SRCA_RF
    assert int(dut.ALUControlD.value) == ALU["ADD"]
    assert int(dut.PCD.value) == 0x40 and int(dut.PCPlus4D.value) == 0x44


@cocotb.test()
async def test_rtype_decode(dut):
    """All R-type ALU operations map to the right ALUControlD."""
    await start(dut)
    cases = [(0x00, 0b000, "ADD"), (0x20, 0b000, "SUB"),
             (0x00, 0b001, "SLL"), (0x00, 0b010, "SLT"),
             (0x00, 0b011, "SLTU"), (0x00, 0b100, "XOR"),
             (0x00, 0b101, "SRL"), (0x20, 0b101, "SRA"),
             (0x00, 0b110, "OR"), (0x00, 0b111, "AND")]
    for f7, f3, name in cases:
        await push_instr(dut, r_type(f7, 2, 1, f3, 3))
        assert int(dut.ALUControlD.value) == ALU[name], f"{name} wrong"
        assert dut.ALUSrcBD.value == 0 and dut.RegWriteD.value == 1


@cocotb.test()
async def test_itype_shifts(dut):
    """slli/srli/srai use funct7 bit 5 like R-type shifts."""
    await start(dut)
    for f7, f3, name in [(0x00, 0b001, "SLL"), (0x00, 0b101, "SRL"),
                         (0x20, 0b101, "SRA")]:
        instr = i_type((f7 << 5) | 4, 1, f3, 2)  # shamt = 4
        await push_instr(dut, instr)
        assert int(dut.ALUControlD.value) == ALU[name], f"{name} wrong"
        assert dut.ALUSrcBD.value == 1


@cocotb.test()
async def test_load_store(dut):
    """lw x1, 8(x2) and sw x1, -4(x2)."""
    await start(dut)
    await push_instr(dut, i_type(8, 2, 0b010, 1, op=0b0000011))
    assert dut.RegWriteD.value == 1 and dut.MemWriteD.value == 0
    assert int(dut.ResultSrcD.value) == RESULT_MEM
    assert dut.ALUSrcBD.value == 1 and int(dut.ImmExtD.value) == 8
    await push_instr(dut, s_type(-4, 1, 2, 0b010))
    assert dut.RegWriteD.value == 0 and dut.MemWriteD.value == 1
    assert int(dut.ImmExtD.value) == sext32(-4)
    assert dut.Rs2D.value == 1 and dut.Rs1D.value == 2


@cocotb.test()
async def test_branch_jump_upper(dut):
    """beq, jal, jalr, lui, auipc controls and immediates."""
    await start(dut)
    await push_instr(dut, b_type(-16, 2, 1, 0b000))  # beq x1, x2, -16
    assert dut.BranchD.value == 1 and dut.RegWriteD.value == 0
    assert int(dut.ImmExtD.value) == sext32(-16)
    await push_instr(dut, j_type(0x800, 1))          # jal x1, +0x800
    assert dut.JumpD.value == 1 and dut.RegWriteD.value == 1
    assert int(dut.ResultSrcD.value) == RESULT_PC4
    assert int(dut.ImmExtD.value) == 0x800
    await push_instr(dut, i_type(0x20, 3, 0b000, 1, op=0b1100111))  # jalr
    assert dut.JalrD.value == 1 and int(dut.ResultSrcD.value) == RESULT_PC4
    assert int(dut.ALUControlD.value) == ALU["ADD"] and dut.ALUSrcBD.value == 1
    await push_instr(dut, u_type(0xABCDE, 1, op=0b0110111))  # lui
    assert int(dut.ALUSrcAD.value) == SRCA_ZERO
    assert int(dut.ImmExtD.value) == 0xABCDE000
    await push_instr(dut, u_type(0x12345, 1, op=0b0010111))  # auipc
    assert int(dut.ALUSrcAD.value) == SRCA_PC
    assert int(dut.ImmExtD.value) == 0x12345000


@cocotb.test()
async def test_regfile_read_write(dut):
    """Values written from W are read by a following instruction; x0 is 0."""
    await start(dut)
    await rf_write(dut, 7, 0xDEADBEEF)
    await rf_write(dut, 9, 0x123)
    await push_instr(dut, r_type(0, 9, 7, 0b000, 1))  # add x1, x7, x9
    assert int(dut.RD1D.value) == 0xDEADBEEF
    assert int(dut.RD2D.value) == 0x123
    await rf_write(dut, 0, 0x5555)                    # write to x0 ignored
    await push_instr(dut, r_type(0, 0, 0, 0b000, 1))  # add x1, x0, x0
    assert int(dut.RD1D.value) == 0 and int(dut.RD2D.value) == 0


@cocotb.test()
async def test_regfile_bypass(dut):
    """A same-cycle W write is visible on the read ports (write-first)."""
    await start(dut)
    await push_instr(dut, r_type(0, 5, 5, 0b000, 1))  # add x1, x5, x5 in D
    dut.RegWriteW.value = 1
    dut.RdW.value = 5
    dut.ResultW.value = 0xCAFE0001
    await Timer(1, unit="ns")
    assert int(dut.RD1D.value) == 0xCAFE0001, "bypass on RD1 failed"
    assert int(dut.RD2D.value) == 0xCAFE0001, "bypass on RD2 failed"
    await RisingEdge(dut.clk)                          # value stored
    dut.RegWriteW.value = 0
    await FallingEdge(dut.clk)
    assert int(dut.RD1D.value) == 0xCAFE0001, "stored value wrong"


@cocotb.test()
async def test_flush(dut):
    """PCSrcE kills the instruction held in Decode."""
    await start(dut)
    await push_instr(dut, i_type(1, 1, 0b000, 1))
    assert dut.ValidD.value == 1
    dut.PCSrcE.value = 1
    await Timer(1, unit="ns")
    assert dut.ValidD.value == 0, "ValidD not gated during flush"
    await RisingEdge(dut.clk)
    dut.PCSrcE.value = 0
    await FallingEdge(dut.clk)
    assert dut.ValidD.value == 0, "ValidD not cleared after flush"


@cocotb.test()
async def test_backpressure(dut):
    """With ReadyE low the stage holds its instruction and stalls Fetch."""
    await start(dut)
    instr_a = i_type(3, 1, 0b000, 1)   # addi x1, x1, 3
    instr_b = r_type(0, 2, 2, 0b111, 4)  # and x4, x2, x2
    await push_instr(dut, instr_a)
    dut.ReadyE.value = 0
    await FallingEdge(dut.clk)
    assert dut.ReadyD.value == 0, "ReadyD high while full and stalled"
    # offer instruction B; it must not displace A
    dut.ValidF.value = 1
    dut.InstrF.value = instr_b
    for _ in range(3):
        await FallingEdge(dut.clk)
        assert dut.ValidD.value == 1
        assert dut.RdD.value == 1, "instruction A displaced during stall"
    dut.ReadyE.value = 1
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.ValidF.value = 0
    await FallingEdge(dut.clk)
    assert dut.RdD.value == 4, "instruction B not loaded after stall"
