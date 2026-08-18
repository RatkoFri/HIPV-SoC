/*
 * crt0.S — HIPV startup code.
 *
 * Runs from the reset vector at address 0. There are no traps or
 * interrupts in this iteration of the SoC, so there is no trap vector
 * and no mtvec setup.
 *
 * Note what is NOT here: a .data copy loop. The IMEM and DMEM windows
 * alias the same physical RAM, so the load address of .data (in the
 * code window) and its virtual address (in the data window) are the
 * same memory. The linker script arranges that; see sw/link.ld.
 * Only .bss needs clearing.
 */

    .section .text.init, "ax"
    .global _start
    .type _start, @function

_start:
    /* No interrupts to disable, no mtvec to program. */

    /* set up the stack and global pointer */
    .option push
    .option norelax
    la      gp, __global_pointer$
    .option pop
    la      sp, __stack_top

    /* zero .bss */
    la      t0, __bss_start
    la      t1, __bss_end
1:  bgeu    t0, t1, 2f
    sw      zero, 0(t0)
    addi    t0, t0, 4
    j       1b
2:

    /* argc = 0, argv = NULL */
    li      a0, 0
    li      a1, 0
    call    main

    /* main returned: park in a spin loop with the return code in a0 */
    .global _exit
_exit:
3:  j       3b

    .size _start, . - _start
