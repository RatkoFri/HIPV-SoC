TOPLEVEL_DIR := $(abspath ../..)

TOPLEVEL = hipv_core
MODULE   = test_hipv_core
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/hipv_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux2.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux3.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/adder.sv \
                  $(TOPLEVEL_DIR)/rtl/core/regfile/regfile.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ifu/ifuctrl.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ifu/ifu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/extend.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/idudec.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/idu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/alu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/branchcmp.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/ieu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/lsu/lsu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/wbu/wbu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/hazard/hazard.sv \
                  $(TOPLEVEL_DIR)/rtl/core/hipv_core.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
