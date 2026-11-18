# cocotb testbench for the ieu module (Execute stage).
#
# The testbench plays the Decode stage (ValidD + operands/controls),
# the Memory stage (ReadyM) and the hazard unit / later stages
# (ForwardAE/ForwardBE, ALUResultM, ResultW).

import os
import random
import re
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge

from hw1_model import BINARY, UNARY, EDGE

# --- control encodings, mirror config/hipv_pkg.sv ---------------------

ALU = {"ADD": 0, "SUB": 1, "SLL": 2, "SLT": 3, "SLTU": 4,
       "XOR": 5, "SRL": 6, "SRA": 7, "OR": 8, "AND": 9}
RESULT_ALU, RESULT_MEM, RESULT_PC4 = 0, 1, 2
SRCA_RF, SRCA_PC, SRCA_ZERO = 0, 1, 2
FWD_RF, FWD_WB, FWD_MEM = 0, 1, 2

D_INPUTS = ("RD1D", "RD2D", "ImmExtD", "PCD", "PCPlus4D", "Rs1D", "Rs2D",
            "RdD", "Funct3D", "RegWriteD", "MemWriteD", "BranchD", "JumpD",
            "JalrD", "ResultSrcD", "ALUSrcAD", "ALUSrcBD", "ALUControlD")


def m32(v):
    return v & 0xFFFFFFFF

# --- helpers ----------------------------------------------------------


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    for name in D_INPUTS:
        getattr(dut, name).value = 0
    dut.ValidD.value = 0
    dut.ReadyM.value = 1
    dut.ForwardAE.value = FWD_RF
    dut.ForwardBE.value = FWD_RF
    dut.ForwardDataM.value = 0
    dut.ResultW.value = 0
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await FallingEdge(dut.clk)


async def push_op(dut, **sig):
    """Present one operation on the D inputs and wait until accepted."""
    for name in D_INPUTS:
        getattr(dut, name).value = m32(sig.get(name, 0))
    dut.ValidD.value = 1
    for _ in range(20):
        await FallingEdge(dut.clk)
        if dut.ReadyE.value:
            await RisingEdge(dut.clk)
            dut.ValidD.value = 0
            await FallingEdge(dut.clk)
            return
    raise AssertionError("timeout waiting for ReadyE")

# --- tests ------------------------------------------------------------


@cocotb.test()
async def test_alu_ops(dut):
    """All ten ALU operations produce correct results."""
    await start(dut)
    a, b = 0xF0F0A5A5, 0x00000013  # b also acts as shamt 19 & 0x1F
    cases = [
        ("ADD", m32(a + b)), ("SUB", m32(a - b)),
        ("AND", a & b), ("OR", a | b), ("XOR", a ^ b),
        ("SLL", m32(a << (b & 0x1F))), ("SRL", a >> (b & 0x1F)),
        ("SRA", m32((a - (1 << 32)) >> (b & 0x1F))),  # a is negative
        ("SLT", 1), ("SLTU", 0),                      # signed a < b, unsigned not
    ]
    for name, expected in cases:
        await push_op(dut, RD1D=a, RD2D=b, ALUControlD=ALU[name], RegWriteD=1)
        assert dut.ValidE.value == 1
        got = int(dut.ALUResultE.value)
        assert got == expected, f"{name}: {hex(got)} != {hex(expected)}"


@cocotb.test()
async def test_branches(dut):
    """All six branch conditions, taken and not taken, and the target."""
    await start(dut)
    neg5, pos3 = m32(-5), 3
    cases = [  # funct3, A, B, taken
        (0b000, 7, 7, 1), (0b000, 7, 8, 0),          # beq
        (0b001, 7, 8, 1), (0b001, 7, 7, 0),          # bne
        (0b100, neg5, pos3, 1), (0b100, pos3, neg5, 0),  # blt (signed)
        (0b101, pos3, neg5, 1), (0b101, neg5, pos3, 0),  # bge (signed)
        (0b110, pos3, neg5, 1), (0b110, neg5, pos3, 0),  # bltu (unsigned)
        (0b111, neg5, pos3, 1), (0b111, pos3, neg5, 0),  # bgeu (unsigned)
    ]
    for f3, a, b, taken in cases:
        await push_op(dut, BranchD=1, Funct3D=f3, RD1D=a, RD2D=b,
                      PCD=0x1000, ImmExtD=0x40)
        assert dut.PCSrcE.value == taken, f"funct3={f3:03b} A={hex(a)} B={hex(b)}"
        if taken:
            assert int(dut.PCTargetE.value) == 0x1040
    # pipeline drained: stale branch controls must not fire again
    await FallingEdge(dut.clk)
    assert dut.PCSrcE.value == 0, "PCSrcE asserted without a valid instruction"


@cocotb.test()
async def test_jal_jalr(dut):
    """jal target is PC+imm; jalr target is (rs1+imm) with bit 0 cleared."""
    await start(dut)
    await push_op(dut, JumpD=1, PCD=0x200, PCPlus4D=0x204, ImmExtD=0x100,
                  RegWriteD=1, ResultSrcD=RESULT_PC4)
    assert dut.PCSrcE.value == 1
    assert int(dut.PCTargetE.value) == 0x300
    assert int(dut.PCPlus4E.value) == 0x204
    assert int(dut.ResultSrcE.value) == RESULT_PC4
    await push_op(dut, JalrD=1, RD1D=0x1000, ImmExtD=0xF, ALUSrcBD=1,
                  ALUControlD=ALU["ADD"], RegWriteD=1, ResultSrcD=RESULT_PC4)
    assert dut.PCSrcE.value == 1
    assert int(dut.PCTargetE.value) == 0x100E, "jalr LSB not cleared"


@cocotb.test()
async def test_lui_auipc(dut):
    """lui adds zero + imm, auipc adds PC + imm."""
    await start(dut)
    await push_op(dut, ALUSrcAD=SRCA_ZERO, ALUSrcBD=1, ImmExtD=0xABCDE000,
                  RegWriteD=1)
    assert int(dut.ALUResultE.value) == 0xABCDE000
    await push_op(dut, ALUSrcAD=SRCA_PC, ALUSrcBD=1, PCD=0x400,
                  ImmExtD=0x1000, RegWriteD=1)
    assert int(dut.ALUResultE.value) == 0x1400


@cocotb.test()
async def test_forwarding(dut):
    """ForwardAE/ForwardBE select ResultW and ALUResultM operands."""
    await start(dut)
    dut.ForwardDataM.value = 0xAAAA0000
    dut.ResultW.value = 0x0000BBBB
    # operand A from Writeback
    dut.ForwardAE.value = FWD_WB
    await push_op(dut, RD1D=1, RD2D=2, ALUControlD=ALU["ADD"], RegWriteD=1)
    assert int(dut.ALUResultE.value) == 0x0000BBBB + 2
    # operand A from Memory
    dut.ForwardAE.value = FWD_MEM
    await push_op(dut, RD1D=1, RD2D=2, ALUControlD=ALU["ADD"], RegWriteD=1)
    assert int(dut.ALUResultE.value) == 0xAAAA0000 + 2
    # operand B (store data path) from Memory
    dut.ForwardAE.value = FWD_RF
    dut.ForwardBE.value = FWD_MEM
    await push_op(dut, RD1D=5, RD2D=2, MemWriteD=1, ALUSrcBD=1, ImmExtD=8,
                  ALUControlD=ALU["ADD"])
    assert int(dut.WriteDataE.value) == 0xAAAA0000, "store data not forwarded"
    assert int(dut.ALUResultE.value) == 5 + 8, "address must use rs1 + imm"
    dut.ForwardBE.value = FWD_RF


@cocotb.test()
async def test_backpressure(dut):
    """With ReadyM low the stage holds its result and stalls Decode."""
    await start(dut)
    await push_op(dut, RD1D=10, RD2D=20, ALUControlD=ALU["ADD"], RegWriteD=1,
                  RdD=3)
    dut.ReadyM.value = 0
    await FallingEdge(dut.clk)
    assert dut.ReadyE.value == 0, "ReadyE high while full and stalled"
    # offer a second operation; it must not displace the first
    for name, val in [("RD1D", 1), ("RD2D", 2), ("RdD", 4)]:
        getattr(dut, name).value = val
    dut.ValidD.value = 1
    for _ in range(3):
        await FallingEdge(dut.clk)
        assert dut.ValidE.value == 1
        assert int(dut.ALUResultE.value) == 30 and dut.RdE.value == 3, \
            "operation displaced during stall"
    dut.ReadyM.value = 1
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.ValidD.value = 0
    await FallingEdge(dut.clk)
    assert int(dut.ALUResultE.value) == 3 and dut.RdE.value == 4, \
        "second operation not loaded after stall"


@cocotb.test()
async def test_bubble(dut):
    """Without a valid input the stage drains to a bubble."""
    await start(dut)
    await push_op(dut, RD1D=1, RD2D=1, ALUControlD=ALU["ADD"], RegWriteD=1)
    assert dut.ValidE.value == 1
    await FallingEdge(dut.clk)
    assert dut.ValidE.value == 0, "stage did not drain to a bubble"


# --- HW1 Task 1: Zba/Zbb in the ALU ------------------------------------
#
# The ALU codes for the new operations are yours to choose, so the tests
# read them from config/hipv_pkg.sv. Define one localparam per operation
# with exactly these names (the width is up to you):
#
#   Zba:        ALU_SH1ADD ALU_SH2ADD ALU_SH3ADD
#   Zbb:        ALU_ANDN ALU_ORN ALU_XNOR ALU_MIN ALU_MINU ALU_MAX ALU_MAXU
#               ALU_CLZ ALU_CPOP
#   bonus:      ALU_CTZ ALU_SEXTB ALU_SEXTH ALU_ZEXTH ALU_ROL ALU_ROR
#               ALU_ORCB ALU_REV8      (only with HW1_BONUS=1)
#
# One-operand instructions (clz, cpop, ...) read operand A only; the tests
# drive random garbage on B to check that it is ignored.

BONUS = os.environ.get("HW1_BONUS", "0") == "1"
PKG = Path(__file__).resolve().parents[3] / "config" / "hipv_pkg.sv"

# instruction name (hw1_model) -> hipv_pkg constant
ZBA = {"sh1add": "ALU_SH1ADD", "sh2add": "ALU_SH2ADD", "sh3add": "ALU_SH3ADD"}
ZBB_LOGIC = {"andn": "ALU_ANDN", "orn": "ALU_ORN", "xnor": "ALU_XNOR"}
ZBB_MINMAX = {"min": "ALU_MIN", "minu": "ALU_MINU",
              "max": "ALU_MAX", "maxu": "ALU_MAXU"}
ZBB_COUNT = {"clz": "ALU_CLZ", "cpop": "ALU_CPOP"}
BONUS_BINARY = {"rol": "ALU_ROL", "ror": "ALU_ROR"}
BONUS_UNARY = {"ctz": "ALU_CTZ", "sext.b": "ALU_SEXTB", "sext.h": "ALU_SEXTH",
               "zext.h": "ALU_ZEXTH", "orc.b": "ALU_ORCB", "rev8": "ALU_REV8"}

# Required encoding of the ALU codes (5 bits wide). The ALU, the decoder
# and the testbenches all rely on these values, so hipv_pkg.sv must use
# exactly this table: the existing ten codes keep their values (zero-
# extended), the new operations follow in this order.
REF_CODES = {
    "ALU_ADD": 0b00000, "ALU_SUB": 0b00001, "ALU_SLL": 0b00010,
    "ALU_SLT": 0b00011, "ALU_SLTU": 0b00100, "ALU_XOR": 0b00101,
    "ALU_SRL": 0b00110, "ALU_SRA": 0b00111, "ALU_OR": 0b01000,
    "ALU_AND": 0b01001,
    "ALU_SH1ADD": 0b01010, "ALU_SH2ADD": 0b01011, "ALU_SH3ADD": 0b01100,
    "ALU_ANDN": 0b01101, "ALU_ORN": 0b01110, "ALU_XNOR": 0b01111,
    "ALU_MIN": 0b10000, "ALU_MINU": 0b10001, "ALU_MAX": 0b10010,
    "ALU_MAXU": 0b10011, "ALU_CLZ": 0b10100, "ALU_CPOP": 0b10101,
}
REF_CODES_BONUS = {
    "ALU_CTZ": 0b10110, "ALU_SEXTB": 0b10111, "ALU_SEXTH": 0b11000,
    "ALU_ZEXTH": 0b11001, "ALU_ROL": 0b11010, "ALU_ROR": 0b11011,
    "ALU_ORCB": 0b11100, "ALU_REV8": 0b11101,
}

RNG = random.Random(33)
PAIRS = [(a, b) for a in EDGE for b in EDGE[::3]] + \
        [(RNG.getrandbits(32), RNG.getrandbits(32)) for _ in range(16)]
# rotate amounts: 0, 31, and values above 31 (only [4:0] counts)
SHIFT_PAIRS = [(a, b) for a in EDGE[:6]
               for b in (0, 1, 15, 16, 31, 32, 63, 0xFFFFFFE1)]


def pkg_codes():
    """All ALU_* localparams of hipv_pkg.sv as {name: int}."""
    codes = {}
    pat = re.compile(r"localparam\s+logic\s*(?:\[[^\]]*\])?\s*(ALU_\w+)\s*="
                     r"\s*\d*'([bBdDhH])([0-9a-fA-F_]+)")
    base = {"b": 2, "d": 10, "h": 16}
    for m in pat.finditer(PKG.read_text()):
        codes[m.group(1)] = int(m.group(3).replace("_", ""),
                                base[m.group(2).lower()])
    return codes


def code_of(name):
    codes = pkg_codes()
    assert name in codes, f"{name} is not defined in config/hipv_pkg.sv"
    return codes[name]


def pkg_width(name):
    """Declared bit width of an ALU_* localparam (None if not found)."""
    m = re.search(r"localparam\s+logic\s*\[\s*(\d+)\s*:\s*0\s*\]\s*"
                  + name + r"\b", PKG.read_text())
    return int(m.group(1)) + 1 if m else None


async def check_binary(dut, ops, pairs):
    for insn, const in ops.items():
        code = code_of(const)
        for a, b in pairs:
            await push_op(dut, RD1D=a, RD2D=b, ALUControlD=code, RegWriteD=1)
            got, exp = int(dut.ALUResultE.value), BINARY[insn](a, b)
            assert got == exp, \
                f"{insn}({a:#010x}, {b:#010x}) = {got:#010x}, expected {exp:#010x}"


async def check_unary(dut, ops, values):
    for insn, const in ops.items():
        code = code_of(const)
        for a in values:
            junk = RNG.getrandbits(32)
            await push_op(dut, RD1D=a, RD2D=junk, ALUControlD=code, RegWriteD=1)
            got, exp = int(dut.ALUResultE.value), UNARY[insn](a)
            assert got == exp, \
                f"{insn}({a:#010x}) = {got:#010x}, expected {exp:#010x}"


@cocotb.test()
async def test_alu_encoding(dut):
    """hipv_pkg.sv defines every ALU_* code with the required value, 5 bits."""
    await start(dut)
    ref = {**REF_CODES, **(REF_CODES_BONUS if BONUS else {})}
    codes = pkg_codes()
    errors = []
    for name, want in ref.items():
        if name not in codes:
            errors.append(f"{name} missing (expected {want:05b})")
        elif codes[name] != want:
            errors.append(f"{name} = {codes[name]:05b}, expected {want:05b}")
        elif pkg_width(name) != 5:
            errors.append(f"{name} is {pkg_width(name)} bits wide, expected 5")
    values = {}
    for name, v in codes.items():
        if v in values and name in ref and values[v] in ref:
            errors.append(f"{name} and {values[v]} share the code {v:05b}")
        values.setdefault(v, name)
    assert not errors, "ALU encoding in config/hipv_pkg.sv:\n  " + \
        "\n  ".join(errors)


@cocotb.test()
async def test_zba(dut):
    """sh1add, sh2add, sh3add: (rs1 << n) + rs2."""
    await start(dut)
    await check_binary(dut, ZBA, PAIRS)


@cocotb.test()
async def test_zbb_logic_with_negate(dut):
    """andn, orn, xnor."""
    await start(dut)
    await check_binary(dut, ZBB_LOGIC, PAIRS)


@cocotb.test()
async def test_zbb_min_max(dut):
    """min, minu, max, maxu: signed and unsigned compares."""
    await start(dut)
    await check_binary(dut, ZBB_MINMAX, PAIRS)


@cocotb.test()
async def test_zbb_count(dut):
    """clz, cpop: operand B is ignored."""
    await start(dut)
    singles = [1 << i for i in range(32)]
    await check_unary(dut, ZBB_COUNT, EDGE + singles + [0xFFFFFFFE, 0x00FF00FF])


@cocotb.test()
async def test_zbb_immediate_operand(dut):
    """New ops take operand B from the immediate when ALUSrcB is set."""
    await start(dut)
    for insn, const in {**ZBA, "andn": "ALU_ANDN", "max": "ALU_MAX"}.items():
        for a, imm in [(0x12345678, 0x7FF), (0xFFFFFFFF, 0xFFFFF800)]:
            await push_op(dut, RD1D=a, RD2D=0xDEADBEEF, ImmExtD=imm,
                          ALUSrcBD=1, ALUControlD=code_of(const), RegWriteD=1)
            exp = BINARY[insn](a, imm)
            assert int(dut.ALUResultE.value) == exp, f"{insn} with immediate"


@cocotb.test()
async def test_rv32i_unchanged(dut):
    """The original ALU operations still work with the wider control code."""
    await start(dut)
    a, b = 0xF0F0A5A5, 0x00000013
    for name, expected in [("ADD", (a + b) & 0xFFFFFFFF), ("AND", a & b),
                           ("OR", a | b), ("XOR", a ^ b),
                           ("SUB", (a - b) & 0xFFFFFFFF)]:
        code = code_of("ALU_" + name)
        assert code == ALU[name], f"ALU_{name} must keep its original code"
        await push_op(dut, RD1D=a, RD2D=b, ALUControlD=code, RegWriteD=1)
        assert int(dut.ALUResultE.value) == expected, name


@cocotb.test(skip=not BONUS)
async def test_zbb_bonus(dut):
    """rol, ror, ctz, sext.b, sext.h, zext.h, orc.b, rev8 (HW1_BONUS=1)."""
    await start(dut)
    await check_binary(dut, BONUS_BINARY, SHIFT_PAIRS)
    await check_unary(dut, BONUS_UNARY, EDGE + [RNG.getrandbits(32)
                                                 for _ in range(16)])
