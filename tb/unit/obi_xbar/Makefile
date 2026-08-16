TOPLEVEL_DIR := $(abspath ../../..)

# ARB_POLICY: 0 = fixed priority (data over fetch), 1 = round robin.
ARB_POLICY ?= 0
export ARB_POLICY

TOPLEVEL = obi_xbar
MODULE   = test_obi_xbar
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/hipv_soc_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_decoder.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_arbiter.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_xbar.sv

COMPILE_ARGS += -GARB_POLICY=$(ARB_POLICY)

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
