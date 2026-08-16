TOPLEVEL_DIR := $(abspath ../../..)

# ARB_POLICY: 0 = fixed priority, 1 = round robin. The testbench reads
# it from the environment to know which behaviour to expect.
ARB_POLICY ?= 0
export ARB_POLICY

TOPLEVEL = obi_arbiter
MODULE   = test_obi_arbiter
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/hipv_soc_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_arbiter.sv

COMPILE_ARGS += -GNUM_MASTERS=4 -GARB_POLICY=$(ARB_POLICY)

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
