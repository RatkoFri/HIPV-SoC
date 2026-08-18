TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = timer
MODULE   = test_timer
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/periph.vlt \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register_wclear.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/cntr.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_timer.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/timer.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
