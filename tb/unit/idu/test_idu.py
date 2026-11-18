# cocotb testbench for the idu module (Decode stage).
#
# The testbench plays the Fetch stage (ValidF/InstrF/PCF/PCPlus4F),
# the Execute stage (ReadyE, PCSrcE) and the Writeback stage
# (RegWriteW/RdW/ResultW around the register file write port).

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

import rv32i as rv  # shared encoders, tb/common/rv32i.py

BONUS = os.environ.get("HW1_BONUS", "0") == "1"

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


# --- HW1: Zba/Zbb and Zmmul decode -------------------------------------
#
# These tests do not depend on how ALUControlD is encoded or on what the
# multiply control signal is called: they compare *every* control output
# of the stage between a new instruction and a plain RV32I instruction
# that has the same funct3 and the same registers. If the decoder ignores
# the extra funct7/rs2 bits, the two snapshots are identical and the test
# fails.

_INPUTS = {"clk", "reset", "ValidF", "InstrF", "PCF", "PCPlus4F", "PCSrcE",
           "ReadyE", "RegWriteW", "RdW", "ResultW"}
_DATA = {"RD1D", "RD2D", "ImmExtD", "PCD", "PCPlus4D"}
# internal state that merely echoes the instruction word / handshake
_INTERNAL = {"InstrD", "ValidDReg", "EnFD", "ImmSrcD"}


def ctrl_snapshot(dut):
    """Value of every control output of the stage, keyed by name."""
    return {h._name: int(h.value) for h in dut
            if h._name not in _INPUTS | _DATA | _INTERNAL
            and hasattr(h, "value")}


async def decode(dut, instr):
    await push_instr(dut, instr)
    return ctrl_snapshot(dut)


def check_alu_op(snap, rd, rs1, rs2=None):
    """Common to every new register-writing ALU/multiply instruction."""
    assert snap["ValidD"] == 1
    assert snap["RegWriteD"] == 1, "result must be written back"
    assert snap["MemWriteD"] == 0 and snap["BranchD"] == 0
    assert snap["JumpD"] == 0 and snap["JalrD"] == 0
    assert snap["ResultSrcD"] == RESULT_ALU
    assert snap["ALUSrcAD"] == SRCA_RF
    assert snap["RdD"] == rd and snap["Rs1D"] == rs1
    if rs2 is not None:
        assert snap["Rs2D"] == rs2 and snap["ALUSrcBD"] == 0


@cocotb.test()
async def test_zba_zbb_decode(dut):
    """Zba/Zbb are decoded, and differ from the RV32I op with the same funct3."""
    await start(dut)
    # (name, new instruction, plain RV32I instruction with same funct3/regs)
    rtype = [
        ("sh1add", rv.sh1add(3, 1, 2), r_type(0x00, 2, 1, 0b010, 3)),
        ("sh2add", rv.sh2add(3, 1, 2), r_type(0x00, 2, 1, 0b100, 3)),
        ("sh3add", rv.sh3add(3, 1, 2), r_type(0x00, 2, 1, 0b110, 3)),
        ("andn", rv.andn(3, 1, 2), r_type(0x00, 2, 1, 0b111, 3)),
        ("orn", rv.orn(3, 1, 2), r_type(0x00, 2, 1, 0b110, 3)),
        ("xnor", rv.xnor(3, 1, 2), r_type(0x00, 2, 1, 0b100, 3)),
        ("min", rv.min_(3, 1, 2), r_type(0x00, 2, 1, 0b100, 3)),
        ("minu", rv.minu(3, 1, 2), r_type(0x00, 2, 1, 0b101, 3)),
        ("max", rv.max_(3, 1, 2), r_type(0x00, 2, 1, 0b110, 3)),
        ("maxu", rv.maxu(3, 1, 2), r_type(0x00, 2, 1, 0b111, 3)),
    ]
    itype = [  # one-operand: I-type encoding, rs2 field is part of the opcode
        ("clz", rv.clz(3, 1), i_type(0, 1, 0b001, 3)),
        ("cpop", rv.cpop(3, 1), i_type(0, 1, 0b001, 3)),
    ]
    if BONUS:
        rtype += [
            ("rol", rv.rol(3, 1, 2), r_type(0x00, 2, 1, 0b001, 3)),
            ("ror", rv.ror(3, 1, 2), r_type(0x00, 2, 1, 0b101, 3)),
            ("zext.h", rv.zext_h(3, 1), r_type(0x00, 0, 1, 0b100, 3)),
        ]
        itype += [
            ("ctz", rv.ctz(3, 1), i_type(0, 1, 0b001, 3)),
            ("sext.b", rv.sext_b(3, 1), i_type(0, 1, 0b001, 3)),
            ("sext.h", rv.sext_h(3, 1), i_type(0, 1, 0b001, 3)),
            ("rori", rv.rori(3, 1, 5), i_type(5, 1, 0b101, 3)),
            ("orc.b", rv.orc_b(3, 1), i_type(0, 1, 0b101, 3)),
            ("rev8", rv.rev8(3, 1), i_type(0, 1, 0b101, 3)),
        ]

    seen = {}
    for name, new, base in rtype + itype:
        base_snap = await decode(dut, base)
        snap = await decode(dut, new)
        is_r = (new & 0x7F) == 0b0110011
        check_alu_op(snap, 3, 1, 2 if is_r and name != "zext.h" else None)
        assert snap["Funct3D"] == (new >> 12) & 7
        assert snap != base_snap, f"{name} decodes like a plain RV32I op"
        seen[name] = snap
    # different operations must not collapse onto one control word
    names = list(seen)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert seen[a] != seen[b], f"{a} and {b} share one control word"


@cocotb.test()
async def test_zba_zbb_same_funct3_distinct(dut):
    """Instructions that differ only in funct7 / rs2 get different controls."""
    await start(dut)
    groups = {
        "xor/xnor/min": [r_type(0x00, 2, 1, 0b100, 3), rv.xnor(3, 1, 2),
                         rv.min_(3, 1, 2), rv.sh2add(3, 1, 2)],
        "or/orn/max/sh3add": [r_type(0x00, 2, 1, 0b110, 3), rv.orn(3, 1, 2),
                              rv.max_(3, 1, 2), rv.sh3add(3, 1, 2)],
        "and/andn/maxu": [r_type(0x00, 2, 1, 0b111, 3), rv.andn(3, 1, 2),
                          rv.maxu(3, 1, 2)],
        "slt/sh1add": [r_type(0x00, 2, 1, 0b010, 3), rv.sh1add(3, 1, 2)],
        "srl/sra/minu": [r_type(0x00, 2, 1, 0b101, 3),
                         r_type(0x20, 2, 1, 0b101, 3), rv.minu(3, 1, 2)],
        "slli/clz/cpop": [i_type(0, 1, 0b001, 3), rv.clz(3, 1),
                          rv.cpop(3, 1)],
    }
    for label, instrs in groups.items():
        snaps = [await decode(dut, i) for i in instrs]
        for i in range(len(snaps)):
            for j in range(i + 1, len(snaps)):
                assert snaps[i] != snaps[j], \
                    f"{label}: instructions {i} and {j} decode identically"


@cocotb.test()
async def test_zmmul_decode(dut):
    """mul/mulh/mulhsu/mulhu reach the multiplier; div/rem write nothing."""
    await start(dut)
    plain = {0b000: r_type(0x00, 2, 1, 0b000, 3),   # add
             0b001: r_type(0x00, 2, 1, 0b001, 3),   # sll
             0b010: r_type(0x00, 2, 1, 0b010, 3),   # slt
             0b011: r_type(0x00, 2, 1, 0b011, 3)}   # sltu
    muls = [rv.mul(3, 1, 2), rv.mulh(3, 1, 2), rv.mulhsu(3, 1, 2),
            rv.mulhu(3, 1, 2)]
    snaps = []
    for f3, instr in enumerate(muls):
        base_snap = await decode(dut, plain[f3])
        snap = await decode(dut, instr)
        check_alu_op(snap, 3, 1, 2)
        assert snap["Funct3D"] == f3, "multiplier selects the variant by funct3"
        assert snap != base_snap, \
            f"{['mul', 'mulh', 'mulhsu', 'mulhu'][f3]} decodes like its RV32I twin"
        snaps.append(snap)
    # the multiply must be flagged the same way for all four variants:
    # everything except Funct3D (and the ALU code, which is a don't-care
    # for a multiply) is shared
    for s in snaps[1:]:
        shared = [k for k in s if k not in ("Funct3D", "ALUControlD")
                  and s[k] != snaps[0][k]]
        assert not shared, f"mul variants disagree on {shared}"

    # M-extension divides are not implemented: they must be inert
    for name, instr in [("div", rv.div(3, 1, 2)), ("divu", rv.divu(3, 1, 2)),
                        ("rem", rv.rem(3, 1, 2)), ("remu", rv.remu(3, 1, 2))]:
        snap = await decode(dut, instr)
        assert snap["RegWriteD"] == 0, f"{name} must not write a register"
        assert snap["MemWriteD"] == 0 and snap["BranchD"] == 0
        assert snap["JumpD"] == 0 and snap["JalrD"] == 0
