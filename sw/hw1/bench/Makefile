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
RUN_CYCLES  ?= 18000000
BAUD         = 19200

include ../../rules.mk

CFLAGS += -I$(SW_DIR)/hw1
ifeq ($(REF),1)
CFLAGS += -DHW1_REF
endif
