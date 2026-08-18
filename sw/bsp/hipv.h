/*
 * hipv.h — HIPV SoC memory map and register definitions.
 *
 * Mirrors config/hipv_soc_pkg.sv and the peripheral register maps in
 * rtl/periph/README.md. Keep the two in step.
 */

#ifndef HIPV_H
#define HIPV_H

#include <stdint.h>

#define REG32(addr) (*(volatile uint32_t *)(addr))

/* ------------------------------------------------------------------ */
/* address map                                                        */
/* ------------------------------------------------------------------ */
#define IMEM_BASE   0x00000000u   /* code window  */
#define DMEM_BASE   0x10000000u   /* data window  */
#define UART_BASE   0x20000000u
#define TIMER_BASE  0x20001000u
#define GPIO_BASE   0x20002000u

/*
 * The two memory windows alias one physical RAM (docs/MEMORY.md), so an
 * address in DMEM_BASE and the same offset in IMEM_BASE are the same
 * word. The linker script keeps code and data in disjoint offsets.
 */

/* ------------------------------------------------------------------ */
/* UART                                                               */
/* ------------------------------------------------------------------ */
#define UART_CONF    REG32(UART_BASE + 0x00)
#define UART_SPEED   REG32(UART_BASE + 0x04)  /* clk cycles per bit */
#define UART_TX      REG32(UART_BASE + 0x08)  /* write starts a frame */
#define UART_RX      REG32(UART_BASE + 0x0C)
#define UART_STATUS  REG32(UART_BASE + 0x10)

#define UART_STATUS_TX_EMPTY  (1u << 0)
#define UART_STATUS_RX_AVAIL  (1u << 1)

/* ------------------------------------------------------------------ */
/* timer (64-bit up counter with a 64-bit compare)                     */
/* ------------------------------------------------------------------ */
#define TIMER_CONF     REG32(TIMER_BASE + 0x00)
#define TIMER_COUNT_LO REG32(TIMER_BASE + 0x04)  /* read-only */
#define TIMER_COUNT_HI REG32(TIMER_BASE + 0x08)  /* read-only */
#define TIMER_CMP_LO   REG32(TIMER_BASE + 0x0C)
#define TIMER_CMP_HI   REG32(TIMER_BASE + 0x10)

#define TIMER_CONF_ENABLE  (1u << 0)
#define TIMER_CONF_CLEAR   (1u << 1)

/*
 * Overflow is a level (count >= compare), not a sticky flag, and both
 * compare registers reset to 0 — so it is asserted out of reset.
 * Always program the compare before enabling the counter.
 */

/* ------------------------------------------------------------------ */
/* GPIO                                                               */
/* ------------------------------------------------------------------ */
#define GPIO_OUT  REG32(GPIO_BASE + 0x00)  /* drives the pins, reads back */
#define GPIO_IN   REG32(GPIO_BASE + 0x04)  /* registered input pins */

/*
 * The GPIO output register masks with the byte enables rather than
 * merging, so always write it a full word at a time.
 */

#endif /* HIPV_H */
