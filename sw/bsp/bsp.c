/*
 * bsp.c — HIPV SoC drivers. Polling only: no traps or interrupts yet.
 */

#include "bsp.h"

/* ------------------------------------------------------------------ */
/* UART                                                               */
/* ------------------------------------------------------------------ */

void uart_init(uint32_t baud)
{
    /* SPEED is the number of core clocks per bit. The receiver
     * oversamples by 16, so keep the divider a multiple of 16. */
    uint32_t div = CPU_HZ / (baud >> 1);
    UART_SPEED = div;
    UART_CONF = 0;
}

void uart_putc(char c)
{
    while (!(UART_STATUS & UART_STATUS_TX_EMPTY))
        ;                       /* wait for the transmit buffer */
    UART_TX = (uint8_t)c;
}

void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

int uart_rx_ready(void)
{
    return (UART_STATUS & UART_STATUS_RX_AVAIL) != 0;
}

char uart_getc(void)
{
    while (!uart_rx_ready())
        ;
    return (char)(UART_RX & 0xFFu);
}

/* ------------------------------------------------------------------ */
/* formatted output                                                    */
/* ------------------------------------------------------------------ */

void print_udec(uint32_t v)
{
    char buf[10];
    int n = 0;

    if (v == 0) {
        uart_putc('0');
        return;
    }
    while (v > 0 && n < 10) {
        buf[n++] = (char)('0' + (v % 10u));
        v /= 10u;
    }
    while (n > 0)
        uart_putc(buf[--n]);
}

void print_dec(int32_t v)
{
    if (v < 0) {
        uart_putc('-');
        /* negate as unsigned so INT32_MIN survives */
        print_udec((uint32_t)0 - (uint32_t)v);
    } else {
        print_udec((uint32_t)v);
    }
}

static char hex_digit(uint32_t nibble)
{
    return (char)(nibble < 10u ? '0' + nibble : 'a' + nibble - 10u);
}

void print_hex(uint32_t v)
{
    for (int i = 28; i >= 0; i -= 4)
        uart_putc(hex_digit((v >> i) & 0xFu));
}

void print_hex8(uint8_t v)
{
    uart_putc(hex_digit((uint32_t)(v >> 4) & 0xFu));
    uart_putc(hex_digit((uint32_t)v & 0xFu));
}

/* ------------------------------------------------------------------ */
/* timer                                                               */
/* ------------------------------------------------------------------ */

void timer_start(void)
{
    /* compare first: the overflow output is a level and both compare
     * registers reset to 0, so enabling first would assert it at once */
    TIMER_CMP_LO = 0xFFFFFFFFu;
    TIMER_CMP_HI = 0xFFFFFFFFu;
    TIMER_CONF = TIMER_CONF_CLEAR;      /* clear the counter */
    TIMER_CONF = TIMER_CONF_ENABLE;     /* and run */
}

void timer_stop(void)
{
    TIMER_CONF = 0;
}

uint64_t timer_get(void)
{
    /* Re-read the high word to detect a carry between the two reads. */
    uint32_t hi = TIMER_COUNT_HI;
    uint32_t lo = TIMER_COUNT_LO;
    uint32_t hi2 = TIMER_COUNT_HI;

    if (hi != hi2) {
        lo = TIMER_COUNT_LO;            /* low word wrapped, re-read it */
        hi = hi2;
    }
    return ((uint64_t)hi << 32) | lo;
}

void timer_set_compare(uint64_t value)
{
    TIMER_CMP_LO = (uint32_t)value;
    TIMER_CMP_HI = (uint32_t)(value >> 32);
}

void delay_cycles(uint32_t cycles)
{
    uint64_t target = timer_get() + cycles;
    while (timer_get() < target)
        ;
}
