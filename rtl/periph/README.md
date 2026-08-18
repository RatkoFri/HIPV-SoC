# Peripherals

OBI slaves for the HIPV SoC.

| File | Role |
|------|------|
| `obi_uart.sv`, `uart_system.sv` | UART core, from https://github.com/RatkoFri/obi_uart |
| `obi_gpio.sv` | GPIO core, from https://github.com/RatkoFri/obi_gpio |
| `obi_timer.sv` | 64-bit timer core, from https://github.com/RatkoFri/obi_timer |
| `uart.sv`, `gpio.sv`, `timer.sv` | SoC adapters: project naming, active-high reset, `rready` tied high, `rerr` unrouted. Interface only, cores instantiated as-is |

The `register` / `cntr` primitives these cores depend on come from the std-lib
dependency declared in their `Bender.yml`, imported into `rtl/stdlib/` and converted
to **synchronous reset** to match the project standard (see `rtl/stdlib/README.md`).
All peripheral state therefore resets synchronously.

Lint: the imported cores are waived in `config/periph.vlt` (their style predates the
project standard); the adapters compile clean under `-Wall`.

## Fixes applied to the cores (worth pushing to the repos)

### obi_timer: unconnected `clear` pin

The std-lib `cntr` has a `clear` input that the `cntr` instantiation left unconnected,
so it floated (Verilator reports `PINMISSING`). The counter is cleared through `rstn`
(`rstn_i & ~timer_conf[1]`), so `clear` is tied to 0. Marked `HIPV FIX` in
`obi_timer.sv`.

### obi_uart: tx_start timing

`tx_start` is registered one cycle after the TX write (marked `HIPV FIX` in
`obi_uart.sv`). Original code drives the transmitter FSM's `tx_start` combinationally
from the write enable, so the FSM latches the TX buffer's *pre-write* value on the same
edge the buffer updates — every byte transmits one write late and the first frame is
0x00. Verified in `tb/unit/uart`: `frames = ['0x0', '0xa3']` before, `['0xa3', '0x5c']`
after.

## Register maps

UART (`0x2000_0000`): 0x00 CONF, 0x04 SPEED (baud limit in clk cycles/bit), 0x08 TX
(write starts transmission), 0x0C RX, 0x10 STATUS {bit1: rx available, bit0: tx empty}.

TIMER (`0x2000_1000`): 0x00 CONF {bit1: reset counter, bit0: enable}, 0x04 COUNT_LO
(ro), 0x08 COUNT_HI (ro), 0x0C CMP_LO, 0x10 CMP_HI. `Overflow` is a *level*
(`count >= {CMP_HI, CMP_LO}`), not a sticky flag, and both compare registers reset to
0 — so it is asserted out of reset. Software must program the compare before enabling
the counter. It is the future machine-timer interrupt source.

GPIO (`0x2000_2000`): 0x00 GPO (write drives pins; note byte-enable masks to zero,
always write with be=0xF), 0x04 GPI (registered input pins).
