TOPLEVEL_DIR := $(abspath ../../..)

TOPLEVEL = gpio
MODULE   = test_gpio
VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/periph.vlt \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_gpio.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/gpio.sv

include $(TOPLEVEL_DIR)/tb/common/Makefile.include
