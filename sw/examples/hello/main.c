/*
 * hello — smallest useful HIPV program: print over the UART.
 *
 * Also exercises initialised data and .bss, so it proves the linker
 * script's aliased load/run addresses work without a startup copy.
 */

#include "bsp.h"

/*
 * volatile so the optimiser cannot fold these into immediates: they must
 * really occupy .data and .bss for this program to test those paths.
 */
static const char message[] = "HIPV\n";      /* .rodata, in the code window */
volatile uint32_t counter = 7;               /* .data, loaded from the image */
volatile uint32_t zeroed;                    /* .bss, cleared by crt0 */

int main(void)
{
    uart_init(BAUD);

    uart_puts(message);

    uart_puts("counter=");
    print_udec(counter);        /* 7, from .data */
    uart_putc('\n');

    uart_puts("bss=");
    print_udec(zeroed);         /* 0, cleared by crt0 */
    uart_putc('\n');

    uart_puts("sum=");
    uint32_t sum = 0;
    for (uint32_t i = 1; i <= 10; i++)
        sum += i;
    print_udec(sum);            /* 55 */
    uart_putc('\n');

    uart_puts("hex=");
    print_hex(0xDEADBEEFu);
    uart_putc('\n');

    return 0;
}
