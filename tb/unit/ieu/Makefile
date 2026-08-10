TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = ieu
MODULE   = test_ieu
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/hipv_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux2.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux3.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/adder.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/alu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/branchcmp.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/ieu.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
