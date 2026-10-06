# Reference models for the homework 1 instructions (Zba/Zbb subset and
# Zmmul), straight from the RISC-V unprivileged specification. Operands
# and results are unsigned 32-bit Python ints.

M32 = 0xFFFFFFFF


def s32(v):
    """Interpret a 32-bit pattern as a signed integer."""
    v &= M32
    return v - (1 << 32) if v >> 31 else v


def _clz(a):
    return 32 - (a & M32).bit_length()


def _ctz(a):
    a &= M32
    return 32 if a == 0 else (a & -a).bit_length() - 1


def _rol(a, n):
    n &= 31
    return ((a << n) | (a >> (32 - n))) & M32


def _orc_b(a):
    return sum(0xFF << (8 * i) for i in range(4) if (a >> (8 * i)) & 0xFF)


def _rev8(a):
    return int.from_bytes((a & M32).to_bytes(4, "little"), "big")


# two-operand instructions: name -> f(rs1, rs2)
BINARY = {
    # Zba
    "sh1add": lambda a, b: ((a << 1) + b) & M32,
    "sh2add": lambda a, b: ((a << 2) + b) & M32,
    "sh3add": lambda a, b: ((a << 3) + b) & M32,
    # Zbb, required
    "andn":   lambda a, b: a & ~b & M32,
    "orn":    lambda a, b: (a | ~b) & M32,
    "xnor":   lambda a, b: ~(a ^ b) & M32,
    "min":    lambda a, b: a if s32(a) < s32(b) else b,
    "minu":   lambda a, b: a if a < b else b,
    "max":    lambda a, b: a if s32(a) > s32(b) else b,
    "maxu":   lambda a, b: a if a > b else b,
    # Zbb, bonus
    "rol":    lambda a, b: _rol(a, b),
    "ror":    lambda a, b: _rol(a, 32 - (b & 31)),
    # Zmmul
    "mul":    lambda a, b: (a * b) & M32,
    "mulh":   lambda a, b: ((s32(a) * s32(b)) >> 32) & M32,
    "mulhsu": lambda a, b: ((s32(a) * b) >> 32) & M32,
    "mulhu":  lambda a, b: ((a * b) >> 32) & M32,
}

# one-operand instructions: name -> f(rs1)
UNARY = {
    # Zbb, required
    "clz":    _clz,
    "cpop":   lambda a: bin(a & M32).count("1"),
    # Zbb, bonus
    "ctz":    _ctz,
    "sext.b": lambda a: (((a & 0xFF) ^ 0x80) - 0x80) & M32,
    "sext.h": lambda a: (((a & 0xFFFF) ^ 0x8000) - 0x8000) & M32,
    "zext.h": lambda a: a & 0xFFFF,
    "orc.b":  _orc_b,
    "rev8":   _rev8,
}

# Zmmul funct3 -> instruction name (the unit test of mul.sv uses this)
MUL_FUNCT3 = {0b000: "mul", 0b001: "mulh", 0b010: "mulhsu", 0b011: "mulhu"}

# operands that break naive implementations: zero, all ones, sign
# boundaries, single bits at the 16-bit and byte seams
EDGE = [0x00000000, 0x00000001, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF,
        0x0000FFFF, 0x00010000, 0xFFFF0000, 0x00008000, 0x8000FFFF,
        0x00000080, 0x12345678]
