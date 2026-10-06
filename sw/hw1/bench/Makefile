# hw1_bench: cycle counts of the new instructions against their
# software (libgcc / plain C) equivalents, for the homework report.
#
#   make run            print the table (no expected output: the numbers
#                       depend on your implementation)
#   make run REF=1      software versions in both columns (baseline core)

PROG = hw1_bench
SRCS = main.c

# each variant gets its own build directory, so switching never reuses
# objects compiled with other flags
BUILD       ?= build$(if $(filter 1,$(REF)),-ref)
RUN_CYCLES  ?= 3000000
BAUD         = 1000000

include ../../rules.mk

CFLAGS += -I$(SW_DIR)/hw1
ifeq ($(REF),1)
CFLAGS += -DHW1_REF
endif

# BUG-UART (KnownBugs.md): the BSP programs CPU_HZ / (BAUD / 2) clock
# cycles per bit, not the CPU_HZ / BAUD that rules.mk assumes, so tell
# the testbench the divider the program really uses.
UART_DIV := $(shell echo $$(( $(CPU_HZ) / ($(BAUD) / 2) )))
