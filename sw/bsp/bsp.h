/*
 * bsp.h — small board-support layer for the HIPV SoC.
 *
 * Blocking, polling drivers only: this iteration of the SoC has no
 * traps or interrupts.
 */

#ifndef BSP_H
#define BSP_H

#include <stdint.h>
#include "hipv.h"

/* Clock frequency assumed when converting baud rates, in Hz.
 * Override at build time with -DCPU_HZ=... */
#ifndef CPU_HZ
#define CPU_HZ 50000000u
#endif

/* ---- UART -------------------------------------------------------- */
void uart_init(uint32_t baud);
void uart_putc(char c);
void uart_puts(const char *s);      /* no newline translation */
int  uart_rx_ready(void);
char uart_getc(void);               /* blocking */

/* ---- formatted output (tiny, no libc) ---------------------------- */
void print_dec(int32_t v);
void print_udec(uint32_t v);
void print_hex(uint32_t v);         /* 8 digits, no 0x prefix */
void print_hex8(uint8_t v);

/* ---- GPIO -------------------------------------------------------- */
static inline void gpio_write(uint32_t value) { GPIO_OUT = value; }
static inline uint32_t gpio_read_out(void)    { return GPIO_OUT; }
static inline uint32_t gpio_read_in(void)     { return GPIO_IN; }

/* ---- timer ------------------------------------------------------- */
void     timer_start(void);                  /* clear, then run freely */
void     timer_stop(void);
uint64_t timer_get(void);                    /* 64-bit, tear-free read */
void     timer_set_compare(uint64_t value);
void     delay_cycles(uint32_t cycles);      /* busy wait on the timer */

#endif /* BSP_H */
