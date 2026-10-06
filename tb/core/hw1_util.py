# Program builders shared by test_zbb.py and test_zmmul.py (homework 1).
#
# A vector program loads each operand pair into x1/x2, runs every
# instruction under test on them, and stores each result through a
# base pointer in x10. The builder returns the program together with the
# expected data-memory contents, computed by tb/common/hw1_model.py.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from obi import obi_slave
from rv32i import NOP, li, addi, sw, jal
from hw1_model import BINARY, UNARY

SPIN = jal(0, 0)       # jump-to-self, ends every program
RESULT_BASE = 0x1000   # data-memory address of the first result


async def run(dut, imem, dmem, cycles, imem_delay=(0, 1), dmem_delay=(0, 1)):
    """Run a program on hipv_core.

    Unlike run_program in test_hipv_core.py, the two memories get their
    own (gnt_delay, rvalid_delay). A fast instruction memory with a slow
    data memory is what puts a dependent instruction into Execute while
    its load is still waiting in Memory.
    """
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    cocotb.start_soon(obi_slave(
        dut.clk, imem, dut.ObiIReq, dut.ObiIGnt, dut.ObiIAddr,
        dut.ObiIRvalid, dut.ObiIRdata, default=NOP,
        gnt_delay=imem_delay[0], rvalid_delay=imem_delay[1]))
    cocotb.start_soon(obi_slave(
        dut.clk, dmem, dut.ObiDReq, dut.ObiDGnt, dut.ObiDAddr,
        dut.ObiDRvalid, dut.ObiDRdata, we=dut.ObiDWe, be=dut.ObiDBe,
        wdata=dut.ObiDWdata,
        gnt_delay=dmem_delay[0], rvalid_delay=dmem_delay[1]))
    dut.reset.value = 1
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    for _ in range(cycles):
        await RisingEdge(dut.clk)


def vector_program(ops, operands):
    """ops: list of (name, encoder); operands: list of (a, b) pairs.

    Unary instructions (clz, cpop, ...) use only a. Returns
    (instrs, expected) where expected maps address -> (value, label).
    """
    instrs = li(10, RESULT_BASE)
    expected = {}
    addr = RESULT_BASE
    for a, b in operands:
        instrs += li(1, a) + li(2, b)
        for slot, (name, enc) in enumerate(ops):
            if name in UNARY:
                instrs.append(enc(3, 1))
                value, label = UNARY[name](a), f"{name}({a:#010x})"
            else:
                instrs.append(enc(3, 1, 2))
                value = BINARY[name](a, b)
                label = f"{name}({a:#010x}, {b:#010x})"
            instrs.append(sw(3, 4 * slot, 10))
            expected[addr + 4 * slot] = (value, label)
        instrs.append(addi(10, 10, 4 * len(ops)))
        addr += 4 * len(ops)
    instrs.append(SPIN)
    return instrs, expected


def budget(instrs, per_instr=24):
    """Generous cycle budget: fetch is ~3 cycles/instr, mul adds more."""
    return per_instr * len(instrs) + 200


def check(dmem, expected, limit=10):
    """Assert every expected word; report up to `limit` mismatches."""
    bad = []
    for addr, (value, label) in sorted(expected.items()):
        got = dmem.get(addr)
        if got != value:
            shown = "never written" if got is None else f"{got:#010x}"
            bad.append(f"{label} = {shown}, expected {value:#010x}")
    assert not bad, f"{len(bad)} wrong result(s):\n  " + "\n  ".join(bad[:limit])
