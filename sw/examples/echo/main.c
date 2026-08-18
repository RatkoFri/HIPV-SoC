/*
 * echo — read characters from the UART and echo them back, mirroring
 * the low bits onto the GPIO pins.
 *
 * Polling only: there are no interrupts in this SoC iteration, so the
 * loop spins on the receive-available status bit.
 *
 * In simulation, drive the Rx pin from the testbench. On hardware,
 * connect a serial terminal.
 */

#include "bsp.h"

int main(void)
{
    uart_init(BAUD);

    uart_puts("echo\n");

    for (;;) {
        char c = uart_getc();       /* blocks on UART_STATUS_RX_AVAIL */

        gpio_write((uint32_t)(uint8_t)c);

        if (c == '\r')              /* terminals send CR, echo a newline */
            uart_putc('\n');
        uart_putc(c);

        if (c == 'q') {             /* quit so a simulation can finish */
            uart_puts("\nbye\n");
            return 0;
        }
    }
}
