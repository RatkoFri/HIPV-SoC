TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = mul
MODULE   = test_mul
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/hipv_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux2.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux3.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/adder.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/mulctrl.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/mul.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
