# HIPV software

Bare-metal C for the HIPV SoC. No operating system, no C library, and — in this
iteration of the SoC — **no traps or interrupts**: every driver polls.

```
sw/
├── bsp/          startup and drivers
│   ├── crt0.S    reset entry: gp/sp, zero .bss, call main
│   ├── hipv.h    memory map and peripheral registers
│   ├── bsp.h/.c  UART, timer, GPIO drivers and tiny print helpers
├── link.ld       linker script (see "Memory layout" below)
├── rules.mk      shared build rules
└── examples/
    ├── hello/    UART output, .data and .bss
    ├── blink/    GPIO walking bit with timer delays
    ├── timer/    reading the 64-bit counter
    └── echo/     UART receive (interactive)
```

## Toolchain

Any RV32I bare-metal GCC. On Debian/Ubuntu:

```sh
sudo apt install gcc-riscv64-unknown-elf
```

The default prefix is `riscv64-unknown-elf-` (it builds RV32I via multilib). Override
with `CROSS=`, and use `TOOLFLAGS=-B/path/to/bin/` if the toolchain lives outside its
configured prefix.

## Building and running

```sh
cd sw/examples/hello
make                 # -> build/hello.{elf,bin,hex,lst,map}
make run             # run it on the SoC testbench, print the UART output
make size dump clean
```

`make` in `sw/` builds every example; `make run` runs them all.

`build/<prog>.hex` is the `$readmemh` image for the SoC's `INIT_FILE` parameter —
synthesis-time initialization, the same file the FPGA flow puts in the bitstream
(`docs/MEMORY.md`).

If an example has an `expected.txt`, `make run` compares the captured UART output
against it, so running an example is a regression test. Without one it just prints what
the program produced.

Useful variables: `CPU_HZ` (default 50 MHz, used for baud maths), `BAUD` (1 Mbaud),
`OPT` (`-Os`), `RAM_ADDR_WIDTH` (14 → 64 KiB, must match the SoC), `RUN_CYCLES`.

## Memory layout

The SoC has **one** physical RAM behind two aliasing windows (`docs/MEMORY.md`):

| Window | Address | Physical offsets | Used for |
|--------|---------|------------------|----------|
| IMEM (code) | `0x0000_0000` | `0x0000`–`0x3FFF` | `.text`, `.rodata` |
| DMEM (data) | `0x1000_0000` | `0x4000`–`0xFFFF` | `.data`, `.bss`, stack |

Two consequences that shape `link.ld`:

1. **The windows must not overlap in physical offsets.** Code is capped at 16 KiB and
   data starts at physical `0x4000`. The link fails with a clear message if `.text`
   grows past that, rather than silently corrupting data.

2. **`.data` needs no startup copy.** Its load address (`0x0000_4000`, in the code
   window) and its run address (`0x1000_4000`, in the data window) are *the same
   physical words* — the image already places initialised data where the program will
   read it. `crt0.S` therefore only zeroes `.bss`. A linker assertion checks the two
   addresses really do alias.

Fetching through IMEM and loading/storing through DMEM also keeps the two RAM ports
independent, which is why memory accesses do not stall instruction fetch.

Adjust the sizes in `link.ld` if you build the SoC with a different `RAM_ADDR_WIDTH`.

## Notes on the C environment

- **RV32I has no multiply or divide.** GCC emits calls to libgcc helpers
  (`__mulsi3`, `__udivsi3`, ...), so `libgcc` is linked even though libc is not. Prefer
  shifts over `/` and `%` in hot code.
- **No libc**: no `printf`, `malloc`, or string functions. `bsp.h` provides
  `uart_puts`, `print_dec`, `print_udec`, `print_hex`.
- **`volatile` matters.** Peripheral registers are `volatile` in `hipv.h`; a variable
  the optimiser can fold away will not appear in `.data`/`.bss` at all.
- **`main` returning** parks in a spin loop in `crt0.S`.

## Peripheral notes worth knowing

- **Timer overflow is a level**, not a sticky flag, and both compare registers reset to
  0 — so it is asserted out of reset. `timer_start()` programs the compare first for
  that reason.
- **GPIO output masks with byte enables** instead of merging, so always write it a full
  word at a time (`gpio_write`).
- **UART divider** is clock cycles per bit; the receiver oversamples ×16, so
  `uart_init` rounds down to a multiple of 16.

## Next iteration

Traps and interrupts are deliberately out of scope here. When they arrive: `crt0.S`
gains an `mtvec` setup and a trap vector, the timer's `Overflow` becomes an interrupt
source, and `echo` can move from polling to interrupt-driven receive.
