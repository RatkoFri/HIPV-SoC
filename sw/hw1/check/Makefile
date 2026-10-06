# hw1_check: self-checking test of the homework 1 instructions.
#
#   make run            required instructions, compared with expected.txt
#   make run BONUS=1    also the bonus instructions (expected_bonus.txt)
#   make run REF=1      reference against itself (checks the program and
#                       the flow on a core without the extensions)

PROG = hw1_check
SRCS = main.c

# each variant gets its own build directory, so switching never reuses
# objects compiled with other flags
BUILD       ?= build$(if $(filter 1,$(BONUS)),-bonus)$(if $(filter 1,$(REF)),-ref)
EXPECT_FILE ?= $(if $(filter 1,$(BONUS)),expected_bonus.txt,expected.txt)
RUN_CYCLES  ?= 4000000
BAUD         = 1000000

include ../../rules.mk

CFLAGS += -I$(SW_DIR)/hw1
ifeq ($(BONUS),1)
CFLAGS += -DHW1_BONUS
endif
ifeq ($(REF),1)
CFLAGS += -DHW1_REF
endif

# BUG-UART (KnownBugs.md): the BSP programs CPU_HZ / (BAUD / 2) clock
# cycles per bit, not the CPU_HZ / BAUD that rules.mk assumes, so tell
# the testbench the divider the program really uses.
UART_DIV := $(shell echo $$(( $(CPU_HZ) / ($(BAUD) / 2) )))
