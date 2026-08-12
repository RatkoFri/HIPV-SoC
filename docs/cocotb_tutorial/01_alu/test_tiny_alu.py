# Example 1: testing a combinational circuit with cocotb.
#
# Read this file top to bottom together with docs/CocotbTutorial.md.
# Run it with:  make        (add WAVES=1 for a dump.vcd)

import random

import cocotb
from cocotb.triggers import Timer

ADD, SUB, AND, OR = 0, 1, 2, 3
MASK = 0xFF  # the DUT is 8 bits wide


# ---------------------------------------------------------------------
# 1. The simplest possible test: drive inputs, wait, check the output.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_single_add(dut):
    """3 + 4 = 7."""
    dut.A.value = 3
    dut.B.value = 4
    dut.Op.value = ADD

    # Assignments are scheduled, not applied instantly. Without waiting,
    # dut.Y still holds the previous value. Timer(1, unit="ns") lets
    # simulation time advance so the combinational logic settles.
    await Timer(1, unit="ns")

    assert dut.Y.value == 7, f"expected 7, got {dut.Y.value}"


# ---------------------------------------------------------------------
# 2. A helper keeps the tests short and readable.
# ---------------------------------------------------------------------

async def do_op(dut, a, b, op):
    """Apply one operation and return (Y, Zero) as Python ints."""
    dut.A.value = a
    dut.B.value = b
    dut.Op.value = op
    await Timer(1, unit="ns")
    return int(dut.Y.value), int(dut.Zero.value)


@cocotb.test()
async def test_all_operations(dut):
    """One directed case per opcode."""
    a, b = 0b1100, 0b1010

    y, _ = await do_op(dut, a, b, ADD)
    assert y == (a + b) & MASK

    y, _ = await do_op(dut, a, b, SUB)
    assert y == (a - b) & MASK

    y, _ = await do_op(dut, a, b, AND)
    assert y == a & b

    y, _ = await do_op(dut, a, b, OR)
    assert y == a | b


# ---------------------------------------------------------------------
# 3. Checking a flag, and the wraparound behaviour of fixed-width math.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_zero_flag(dut):
    """Zero is high exactly when the result is zero."""
    _, zero = await do_op(dut, 5, 5, SUB)      # 5 - 5 = 0
    assert zero == 1, "Zero should be set"

    _, zero = await do_op(dut, 5, 4, SUB)      # 5 - 4 = 1
    assert zero == 0, "Zero should be clear"

    # 8-bit wraparound: 200 + 56 = 256 -> 0, so Zero is set again.
    y, zero = await do_op(dut, 200, 56, ADD)
    assert y == 0 and zero == 1, f"Y={y} Zero={zero}"


# ---------------------------------------------------------------------
# 4. Randomised testing against a Python reference model.
#
# The model describes *what* the circuit should compute; the RTL
# describes *how*. Comparing them over many random inputs finds cases
# a human would not think to write down.
# ---------------------------------------------------------------------

def alu_model(a, b, op):
    """Golden reference for tiny_alu."""
    if op == ADD:
        return (a + b) & MASK
    if op == SUB:
        return (a - b) & MASK
    if op == AND:
        return a & b
    return a | b


@cocotb.test()
async def test_random(dut):
    """200 random stimuli compared against the reference model."""
    random.seed(1)  # fixed seed: a failure is reproducible
    for _ in range(200):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)
        op = random.randint(0, 3)

        y, zero = await do_op(dut, a, b, op)
        expected = alu_model(a, b, op)

        assert y == expected, \
            f"op={op} a={a} b={b}: got {y}, expected {expected}"
        assert zero == (expected == 0), f"Zero wrong for {a},{b},op={op}"


# ---------------------------------------------------------------------
# 5. Exhaustive testing: for small circuits, just try everything.
#
# 4 opcodes x 256 x 256 inputs is 262144 cases and still runs in
# seconds. If you can be exhaustive, be exhaustive.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_exhaustive_low_nibble(dut):
    """All input combinations with A, B in 0..15, for every opcode."""
    for op in (ADD, SUB, AND, OR):
        for a in range(16):
            for b in range(16):
                y, _ = await do_op(dut, a, b, op)
                assert y == alu_model(a, b, op), \
                    f"op={op} a={a} b={b}: got {y}"


# ---------------------------------------------------------------------
# 6. Logging: cocotb gives every DUT a logger. Useful while debugging;
# keep it out of the inner loop of long tests.
# ---------------------------------------------------------------------

@cocotb.test()
async def test_with_logging(dut):
    """Same as test_all_operations, but prints what it does."""
    for op, name in ((ADD, "add"), (SUB, "sub"), (AND, "and"), (OR, "or")):
        y, zero = await do_op(dut, 0x0F, 0x33, op)
        dut._log.info("%s(0x0F, 0x33) = 0x%02X (Zero=%d)", name, y, zero)
