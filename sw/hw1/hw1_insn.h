/*
 * hw1_insn.h — inline-assembly wrappers for the homework 1 instructions.
 *
 * The programs are compiled with -march=rv32i, so the compiler never
 * emits a Zba/Zbb/Zmmul instruction on its own: the only new
 * instructions in the binary are the ones written here. Check with
 * `make dump`. `.option arch, +ext` enables an extension for the
 * assembler inside one asm block only.
 *
 * `volatile` keeps the compiler from merging or hoisting the asm, so
 * every call in a benchmark loop really executes the instruction.
 */

#ifndef HW1_INSN_H
#define HW1_INSN_H

#include <stdint.h>

/* rd = insn(rs1, rs2) */
#define HW1_RR(fn, insn, ext)                                           \
    static inline uint32_t fn(uint32_t a, uint32_t b)                   \
    {                                                                   \
        uint32_t r;                                                     \
        __asm__ volatile (".option push\n.option arch, +" ext "\n"      \
                          insn " %0, %1, %2\n.option pop"               \
                          : "=r"(r) : "r"(a), "r"(b));                  \
        return r;                                                       \
    }

/* rd = insn(rs1) */
#define HW1_R(fn, insn, ext)                                            \
    static inline uint32_t fn(uint32_t a)                               \
    {                                                                   \
        uint32_t r;                                                     \
        __asm__ volatile (".option push\n.option arch, +" ext "\n"      \
                          insn " %0, %1\n.option pop"                   \
                          : "=r"(r) : "r"(a));                          \
        return r;                                                       \
    }

/* rd = insn(rs1, imm), the immediate is a compile-time constant */
#define HW1_RI(fn, insn, ext, imm)                                      \
    static inline uint32_t fn(uint32_t a)                               \
    {                                                                   \
        uint32_t r;                                                     \
        __asm__ volatile (".option push\n.option arch, +" ext "\n"      \
                          insn " %0, %1, " #imm "\n.option pop"         \
                          : "=r"(r) : "r"(a));                          \
        return r;                                                       \
    }

/* Task 1, required: Zba */
HW1_RR(hw_sh1add, "sh1add", "zba")
HW1_RR(hw_sh2add, "sh2add", "zba")
HW1_RR(hw_sh3add, "sh3add", "zba")

/* Task 1, required: Zbb */
HW1_RR(hw_andn, "andn", "zbb")
HW1_RR(hw_orn,  "orn",  "zbb")
HW1_RR(hw_xnor, "xnor", "zbb")
HW1_RR(hw_min,  "min",  "zbb")
HW1_RR(hw_minu, "minu", "zbb")
HW1_RR(hw_max,  "max",  "zbb")
HW1_RR(hw_maxu, "maxu", "zbb")
HW1_R(hw_clz,   "clz",  "zbb")
HW1_R(hw_cpop,  "cpop", "zbb")

/* Task 1, bonus: Zbb */
HW1_R(hw_ctz,    "ctz",    "zbb")
HW1_R(hw_sext_b, "sext.b", "zbb")
HW1_R(hw_sext_h, "sext.h", "zbb")
HW1_R(hw_zext_h, "zext.h", "zbb")
HW1_R(hw_orc_b,  "orc.b",  "zbb")
HW1_R(hw_rev8,   "rev8",   "zbb")
HW1_RR(hw_rol,   "rol",    "zbb")
HW1_RR(hw_ror,   "ror",    "zbb")
HW1_RI(hw_rori7, "rori",   "zbb", 7)

/* Task 2: Zmmul */
HW1_RR(hw_mul,    "mul",    "zmmul")
HW1_RR(hw_mulh,   "mulh",   "zmmul")
HW1_RR(hw_mulhsu, "mulhsu", "zmmul")
HW1_RR(hw_mulhu,  "mulhu",  "zmmul")

#endif /* HW1_INSN_H */
