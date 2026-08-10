TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = idu
MODULE   = test_idu
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/hipv_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/core/regfile/regfile.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/extend.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/idudec.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/idu.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
