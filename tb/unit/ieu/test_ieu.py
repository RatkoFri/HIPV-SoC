# cocotb testbench for the ieu module (Execute stage).
#
# The testbench plays the Decode stage (ValidD + operands/controls),
# the Memory stage (ReadyM) and the hazard unit / later stages
# (ForwardAE/ForwardBE, ALUResultM, ResultW).

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge

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
