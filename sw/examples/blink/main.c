/*
 * blink — walk a bit across the GPIO outputs, using the timer for the
 * delay. On the FPGA this is an LED chaser; in simulation the pattern
 * is visible on GpioOut (and echoed over the UART so it is checkable).
 */

#include "bsp.h"

#define STEPS 8

/* Short delay so the simulation finishes quickly. Scale up for hardware:
 * DELAY_CYCLES = CPU_HZ / 4 gives a quarter-second step. */
#ifndef DELAY_CYCLES
#define DELAY_CYCLES 200u
#endif

int main(void)
{
    uart_init(BAUD);
    timer_start();

    uart_puts("blink\n");

    for (int step = 0; step < STEPS; step++) {
        uint32_t pattern = 1u << step;
        gpio_write(pattern);

        /* report the pattern so the run is verifiable in simulation */
        print_hex8((uint8_t)pattern);
        uart_putc('\n');

        delay_cycles(DELAY_CYCLES);
    }

    gpio_write(0);
    uart_puts("done\n");
    return 0;
}
