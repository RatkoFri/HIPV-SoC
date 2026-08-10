# RV32I instruction encoders for HIPV testbenches.

NOP = 0x00000013  # addi x0, x0, 0


def m32(v):
    return v & 0xFFFFFFFF


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


# convenience mnemonics ------------------------------------------------

def addi(rd, rs1, imm):
    return i_type(imm, rs1, 0b000, rd)


def add(rd, rs1, rs2):
    return r_type(0x00, rs2, rs1, 0b000, rd)


def sub(rd, rs1, rs2):
    return r_type(0x20, rs2, rs1, 0b000, rd)


def lw(rd, imm, rs1):
    return i_type(imm, rs1, 0b010, rd, op=0b0000011)


def lh(rd, imm, rs1):
    return i_type(imm, rs1, 0b001, rd, op=0b0000011)


def lhu(rd, imm, rs1):
    return i_type(imm, rs1, 0b101, rd, op=0b0000011)


def lb(rd, imm, rs1):
    return i_type(imm, rs1, 0b000, rd, op=0b0000011)


def lbu(rd, imm, rs1):
    return i_type(imm, rs1, 0b100, rd, op=0b0000011)


def sw(rs2, imm, rs1):
    return s_type(imm, rs2, rs1, 0b010)


def sh(rs2, imm, rs1):
    return s_type(imm, rs2, rs1, 0b001)


def sb(rs2, imm, rs1):
    return s_type(imm, rs2, rs1, 0b000)


def beq(rs1, rs2, imm):
    return b_type(imm, rs2, rs1, 0b000)


def bne(rs1, rs2, imm):
    return b_type(imm, rs2, rs1, 0b001)


def blt(rs1, rs2, imm):
    return b_type(imm, rs2, rs1, 0b100)


def jal(rd, imm):
    return j_type(imm, rd)


def jalr(rd, rs1, imm):
    return i_type(imm, rs1, 0b000, rd, op=0b1100111)


def lui(rd, imm20):
    return u_type(imm20, rd, op=0b0110111)


def auipc(rd, imm20):
    return u_type(imm20, rd, op=0b0010111)


def program(instrs, base=0):
    """Turn a list of instruction words into an imem dict."""
    return {base + 4 * i: w for i, w in enumerate(instrs)}
