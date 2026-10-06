/*
 * hw1_check — self-checking test of the homework 1 instructions.
 *
 * Every instruction runs on all operand pairs from vec[] and is
 * compared with a reference written in plain RV32I C, so the reference
 * does not depend on the hardware under test. One line per instruction:
 *
 *   andn    OK
 *   min     FAIL 23/144  a=80000000 b=00000001 hw=00000001 ref=80000000
 *
 * The FAIL line shows the number of wrong results and the first one.
 *
 *   make run            required instructions, compared with expected.txt
 *   make run BONUS=1    also the bonus instructions (expected_bonus.txt,
 *                       see docs/LectureNotes/HW1_bonus.md)
 *   make run REF=1      reference against itself: checks this program
 *                       and the flow on a core without the extensions
 */

#include "bsp.h"
#include "hw1_insn.h"

/* zero, all ones, sign boundaries, single bits at the 16-bit and byte seams */
static const uint32_t vec[] = {
    0x00000000u, 0x00000001u, 0xFFFFFFFFu, 0x80000000u,
    0x7FFFFFFFu, 0x0000FFFFu, 0x00010000u, 0xFFFF0000u,
    0x00008000u, 0x8000FFFFu, 0x12345678u, 0xDEADBEEFu,
};
#define NVEC (sizeof vec / sizeof vec[0])

/* ---- references, plain RV32I C ------------------------------------- */

static inline uint32_t ref_sh1add(uint32_t a, uint32_t b) { return (a << 1) + b; }
static inline uint32_t ref_sh2add(uint32_t a, uint32_t b) { return (a << 2) + b; }
static inline uint32_t ref_sh3add(uint32_t a, uint32_t b) { return (a << 3) + b; }
static inline uint32_t ref_andn(uint32_t a, uint32_t b)   { return a & ~b; }
static inline uint32_t ref_orn(uint32_t a, uint32_t b)    { return a | ~b; }
static inline uint32_t ref_xnor(uint32_t a, uint32_t b)   { return ~(a ^ b); }
static inline uint32_t ref_min(uint32_t a, uint32_t b)    { return (int32_t)a < (int32_t)b ? a : b; }
static inline uint32_t ref_minu(uint32_t a, uint32_t b)   { return a < b ? a : b; }
static inline uint32_t ref_max(uint32_t a, uint32_t b)    { return (int32_t)a < (int32_t)b ? b : a; }
static inline uint32_t ref_maxu(uint32_t a, uint32_t b)   { return a < b ? b : a; }

static inline uint32_t ref_clz(uint32_t a)
{
    uint32_t n = 0;
    for (uint32_t m = 0x80000000u; m && !(a & m); m >>= 1)
        n++;
    return n;
}

static inline uint32_t ref_cpop(uint32_t a)
{
    uint32_t n = 0;
    for (; a; a >>= 1)
        n += a & 1u;
    return n;
}

static inline uint32_t ref_ctz(uint32_t a)
{
    uint32_t n = 0;
    for (uint32_t m = 1u; m && !(a & m); m <<= 1)
        n++;
    return n;
}

static inline uint32_t ref_sext_b(uint32_t a) { return (uint32_t)(int32_t)(int8_t)a; }
static inline uint32_t ref_sext_h(uint32_t a) { return (uint32_t)(int32_t)(int16_t)a; }
static inline uint32_t ref_zext_h(uint32_t a) { return a & 0xFFFFu; }

static inline uint32_t ref_orc_b(uint32_t a)
{
    uint32_t r = 0;
    for (int i = 0; i < 32; i += 8)
        if ((a >> i) & 0xFFu)
            r |= 0xFFu << i;
    return r;
}

static inline uint32_t ref_rev8(uint32_t a)
{
    return (a << 24) | ((a << 8) & 0x00FF0000u) | ((a >> 8) & 0x0000FF00u) | (a >> 24);
}

static inline uint32_t ref_rol(uint32_t a, uint32_t b)
{
    b &= 31u;
    return b ? (a << b) | (a >> (32u - b)) : a;
}

static inline uint32_t ref_ror(uint32_t a, uint32_t b)  { return ref_rol(a, 32u - (b & 31u)); }
static inline uint32_t ref_rori7(uint32_t a)            { return ref_ror(a, 7u); }

static inline uint32_t ref_mul(uint32_t a, uint32_t b)  { return a * b; }

static inline uint32_t ref_mulh(uint32_t a, uint32_t b)
{
    return (uint32_t)((uint64_t)((int64_t)(int32_t)a * (int64_t)(int32_t)b) >> 32);
}

static inline uint32_t ref_mulhsu(uint32_t a, uint32_t b)
{
    return (uint32_t)((uint64_t)((int64_t)(int32_t)a * (int64_t)b) >> 32);
}

static inline uint32_t ref_mulhu(uint32_t a, uint32_t b)
{
    return (uint32_t)(((uint64_t)a * b) >> 32);
}

/* REF=1 runs the references against themselves (checks the program) */
#ifdef HW1_REF
#define HW(name) ref_##name
#else
#define HW(name) hw_##name
#endif

/* ---- test driver --------------------------------------------------- */

typedef uint32_t (*binop_t)(uint32_t, uint32_t);
typedef uint32_t (*unop_t)(uint32_t);

static void report(const char *name, uint32_t bad, uint32_t total,
                   uint32_t a, uint32_t b, uint32_t hw, uint32_t ref)
{
    uart_puts(name);
    uint32_t len = 0;
    while (name[len])
        len++;
    for (; len < 8; len++)
        uart_putc(' ');
    if (!bad) {
        uart_puts("OK\n");
        return;
    }
    uart_puts("FAIL ");
    print_udec(bad);
    uart_putc('/');
    print_udec(total);
    uart_puts("  a=");   print_hex(a);
    uart_puts(" b=");    print_hex(b);
    uart_puts(" hw=");   print_hex(hw);
    uart_puts(" ref=");  print_hex(ref);
    uart_putc('\n');
}

static void check_binary(const char *name, binop_t hw, binop_t ref)
{
    uint32_t bad = 0, fa = 0, fb = 0, fh = 0, fr = 0;
    for (uint32_t i = 0; i < NVEC; i++) {
        for (uint32_t j = 0; j < NVEC; j++) {
            uint32_t h = hw(vec[i], vec[j]);
            uint32_t r = ref(vec[i], vec[j]);
            if (h != r && bad++ == 0) {
                fa = vec[i]; fb = vec[j]; fh = h; fr = r;
            }
        }
    }
    report(name, bad, NVEC * NVEC, fa, fb, fh, fr);
}

static void check_unary(const char *name, unop_t hw, unop_t ref)
{
    uint32_t bad = 0, fa = 0, fh = 0, fr = 0;
    for (uint32_t i = 0; i < NVEC; i++) {
        uint32_t h = hw(vec[i]);
        uint32_t r = ref(vec[i]);
        if (h != r && bad++ == 0) {
            fa = vec[i]; fh = h; fr = r;
        }
    }
    report(name, bad, NVEC, fa, 0, fh, fr);
}

int main(void)
{
    uart_init(BAUD);
    uart_puts("HW1 check\n");

    uart_puts("Task 1: Zba/Zbb\n");
    check_binary("sh1add", HW(sh1add), ref_sh1add);
    check_binary("sh2add", HW(sh2add), ref_sh2add);
    check_binary("sh3add", HW(sh3add), ref_sh3add);
    check_binary("andn",   HW(andn),   ref_andn);
    check_binary("orn",    HW(orn),    ref_orn);
    check_binary("xnor",   HW(xnor),   ref_xnor);
    check_binary("min",    HW(min),    ref_min);
    check_binary("minu",   HW(minu),   ref_minu);
    check_binary("max",    HW(max),    ref_max);
    check_binary("maxu",   HW(maxu),   ref_maxu);
    check_unary("clz",     HW(clz),    ref_clz);
    check_unary("cpop",    HW(cpop),   ref_cpop);
#ifdef HW1_BONUS
    uart_puts("Task 1: bonus\n");
    check_unary("ctz",     HW(ctz),    ref_ctz);
    check_unary("sext.b",  HW(sext_b), ref_sext_b);
    check_unary("sext.h",  HW(sext_h), ref_sext_h);
    check_unary("zext.h",  HW(zext_h), ref_zext_h);
    check_unary("orc.b",   HW(orc_b),  ref_orc_b);
    check_unary("rev8",    HW(rev8),   ref_rev8);
    check_binary("rol",    HW(rol),    ref_rol);
    check_binary("ror",    HW(ror),    ref_ror);
    check_unary("rori 7",  HW(rori7),  ref_rori7);
#endif

    uart_puts("Task 2: Zmmul\n");
    check_binary("mul",    HW(mul),    ref_mul);
    check_binary("mulh",   HW(mulh),   ref_mulh);
    check_binary("mulhsu", HW(mulhsu), ref_mulhsu);
    check_binary("mulhu",  HW(mulhu),  ref_mulhu);

    uart_puts("done\n");
    return 0;
}
