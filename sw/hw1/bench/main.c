/*
 * hw1_bench — what do the new instructions buy?
 *
 * Each row times a loop of N operations twice: once with the new
 * instruction (inline assembly) and once with the code an RV32I
 * compiler produces without it (a libgcc call or a few base
 * instructions). The numbers are timer ticks (core clock cycles) per
 * operation and include the same loop overhead in both columns; the
 * "loop only" row shows that overhead.
 *
 * The output depends on your implementation, so there is no
 * expected.txt: copy the table into your report.
 */

#include "bsp.h"
#include "hw1_insn.h"

#define N 64u

static uint32_t in_a[N], in_b[N];
static volatile uint32_t sink;      /* keeps the results alive */

#ifdef HW1_REF
#define HW(expr_hw, expr_sw) (expr_sw)
#else
#define HW(expr_hw, expr_sw) (expr_hw)
#endif

/* time one loop body over the input arrays, return ticks per operation */
#define TIME(expr)                                                      \
    ({                                                                  \
        uint32_t acc = 0;                                               \
        uint64_t t0 = timer_get();                                      \
        for (uint32_t i = 0; i < N; i++) {                              \
            uint32_t a = in_a[i], b = in_b[i];                          \
            (void)a; (void)b;                                           \
            acc ^= (expr);                                              \
        }                                                               \
        uint64_t t1 = timer_get();                                      \
        sink = acc;                                                     \
        (uint32_t)((t1 - t0) / N);                                      \
    })

static void row(const char *name, uint32_t hw, uint32_t sw)
{
    uint32_t len = 0;
    uart_puts(name);
    while (name[len])
        len++;
    for (; len < 10; len++)
        uart_putc(' ');
    print_udec(hw);
    uart_puts("\t");
    print_udec(sw);
    uart_putc('\n');
}

static inline uint32_t sw_mulh(uint32_t a, uint32_t b)
{
    return (uint32_t)((uint64_t)((int64_t)(int32_t)a * (int64_t)(int32_t)b) >> 32);
}

int main(void)
{
    uart_init(BAUD);

    /* pseudo-random operands; clz input is forced non-zero below */
    uint32_t x = 0x2545F491u;
    for (uint32_t i = 0; i < N; i++) {
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        in_a[i] = x;
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        in_b[i] = x;
    }
    timer_start();

    uart_puts("HW1 bench: ticks per operation\n");
    uart_puts("op        new\tRV32I\n");
    row("loop only", TIME(a ^ b), TIME(a ^ b));
    row("sh2add", TIME(HW(hw_sh2add(a, b), (a << 2) + b)), TIME((a << 2) + b));
    row("andn",   TIME(HW(hw_andn(a, b), a & ~b)),         TIME(a & ~b));
    row("minu",   TIME(HW(hw_minu(a, b), a < b ? a : b)),  TIME(a < b ? a : b));
    row("clz",    TIME(HW(hw_clz(a | 1u), (uint32_t)__builtin_clz(a | 1u))),
                  TIME((uint32_t)__builtin_clz(a | 1u)));
    row("cpop",   TIME(HW(hw_cpop(a), (uint32_t)__builtin_popcount(a))),
                  TIME((uint32_t)__builtin_popcount(a)));
    row("mul",    TIME(HW(hw_mul(a, b), a * b)),           TIME(a * b));
    row("mulh",   TIME(HW(hw_mulh(a, b), sw_mulh(a, b))),  TIME(sw_mulh(a, b)));

    uart_puts("done\n");
    return 0;
}
