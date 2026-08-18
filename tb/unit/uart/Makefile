TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = uart
MODULE   = test_uart
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/periph.vlt \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/uart_system.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_uart.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/uart.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
