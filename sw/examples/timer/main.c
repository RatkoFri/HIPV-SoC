/*
 * timer — measure elapsed cycles and show that the 64-bit counter
 * advances monotonically.
 *
 * Note the peripheral's overflow output is a level compare, not an
 * interrupt: this SoC iteration has no traps, so software polls.
 */

#include "bsp.h"

static uint32_t busy_work(uint32_t n)
{
    uint32_t acc = 0;
    for (uint32_t i = 0; i < n; i++)
        acc += i;
    return acc;
}

int main(void)
{
    uart_init(BAUD);
    timer_start();

    uart_puts("timer\n");

    uint64_t t0 = timer_get();
    uint32_t result = busy_work(50);
    uint64_t t1 = timer_get();

    uart_puts("work=");
    print_udec(result);                 /* 1225 */
    uart_putc('\n');

    uart_puts("elapsed>0:");
    print_udec(t1 > t0 ? 1u : 0u);      /* 1 */
    uart_putc('\n');

    /* the counter keeps running while we print */
    uint64_t t2 = timer_get();
    uart_puts("monotonic:");
    print_udec(t2 >= t1 ? 1u : 0u);     /* 1 */
    uart_putc('\n');

    /* stop it and confirm it holds */
    timer_stop();
    uint64_t s0 = timer_get();
    busy_work(20);
    uint64_t s1 = timer_get();
    uart_puts("stopped:");
    print_udec(s0 == s1 ? 1u : 0u);     /* 1 */
    uart_putc('\n');

    return 0;
}
