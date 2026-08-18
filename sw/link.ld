/*
 * link.ld — HIPV SoC linker script.
 *
 * The SoC has ONE physical RAM behind two crossbar windows that alias
 * each other (docs/MEMORY.md):
 *
 *   code window  IMEM  0x00000000   served by RAM port A
 *   data window  DMEM  0x10000000   served by RAM port B
 *
 * Both windows must therefore address DISJOINT offsets, or data would
 * overwrite code. The split is:
 *
 *   offset 0             .. TEXT_SIZE   code + rodata   (via IMEM)
 *   offset TEXT_SIZE     .. RAM_SIZE    data + bss + stack (via DMEM)
 *
 * Data is linked to run at DMEM_BASE + TEXT_SIZE but is *loaded* at
 * offset TEXT_SIZE of the flat image — the same physical words. That is
 * why crt0 has no .data copy loop: LMA and VMA are the same memory seen
 * through two windows.
 *
 * Fetching through IMEM and loading/storing through DMEM also keeps the
 * two RAM ports busy independently, which is the point of the dual-port
 * memory.
 *
 * Sizes match the default SoC configuration (RAM_ADDR_WIDTH = 14, so
 * 64 KiB). Override with --defsym if the SoC is built with a different
 * RAM size.
 */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    /* code window, physical offsets 0x0000 .. 0x3FFF */
    IMEM  (rx) : ORIGIN = 0x00000000, LENGTH = 16K

    /*
     * Load addresses for .data. These are code-window addresses for the
     * SAME physical offsets the data window runs at (0x4000 ..), so the
     * image places initialised data exactly where the DMEM window will
     * read it. This is what removes the startup copy — the load and run
     * addresses differ only by which window names them.
     */
    DLOAD (r)  : ORIGIN = 0x00004000, LENGTH = 48K

    /* data window, physical offsets 0x4000 .. 0xFFFF */
    DMEM  (rw) : ORIGIN = 0x10004000, LENGTH = 48K
}

SECTIONS
{
    .text : ALIGN(4)
    {
        KEEP(*(.text.init))          /* _start must come first */
        *(.text .text.*)
        *(.rodata .rodata.*)
        *(.srodata .srodata.*)
        . = ALIGN(4);
        __text_end = .;
    } > IMEM

    /*
     * .data runs in the DMEM window but is loaded at its IMEM-window
     * address. Those are the same physical words, so no startup copy is
     * needed — the image simply contains the initialised values at that
     * offset.
     */
    .data : ALIGN(4)
    {
        __data_start = .;
        *(.data .data.*)
        *(.sdata .sdata.*)
        . = ALIGN(4);
        __data_end = .;
    } > DMEM AT > DLOAD

    /* gp addresses the small-data area with signed 12-bit offsets */
    __global_pointer$ = __data_start + 0x800;

    .bss (NOLOAD) : ALIGN(4)
    {
        __bss_start = .;
        *(.sbss .sbss.*)
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > DMEM

    /* stack grows down from the top of the data window */
    __stack_top = ORIGIN(DMEM) + LENGTH(DMEM);
    __heap_start = __bss_end;

    /DISCARD/ : { *(.comment) *(.note.*) *(.eh_frame) }
}

/*
 * Fail the link rather than silently overflowing into the data area:
 * because the windows alias, code running past the IMEM region would
 * occupy the same physical words as .data.
 */
ASSERT(__text_end <= ORIGIN(IMEM) + LENGTH(IMEM),
       "code overflows the IMEM window and would collide with data")

/*
 * The load address of .data must name the same physical word as its run
 * address, or the missing startup copy would leave data uninitialised.
 * A code-window address is its own physical offset; a data-window
 * address is its offset above 0x10000000.
 */
ASSERT(LOADADDR(.data) == ADDR(.data) - 0x10000000,
       ".data load and run addresses do not alias — check the DLOAD/DMEM origins")
