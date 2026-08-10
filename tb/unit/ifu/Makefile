TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = ifu
MODULE   = test_ifu
VERILOG_SOURCES = $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux2.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/adder.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ifu/ifuctrl.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ifu/ifu.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
