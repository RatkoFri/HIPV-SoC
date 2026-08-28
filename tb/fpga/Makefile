TOPLEVEL_DIR := $(abspath ../..)

# Same program image the FPGA build bakes in.
INIT_FILE ?= $(PWD)/firmware.hex
RAM_WORDS ?= 1024

TOPLEVEL = top
MODULE   = test_fpga_top

VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/periph.vlt \
                  $(TOPLEVEL_DIR)/config/hipv_pkg.sv \
                  $(TOPLEVEL_DIR)/config/hipv_soc_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux2.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux3.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/adder.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register_wclear.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/cntr.sv \
                  $(TOPLEVEL_DIR)/rtl/mem/sync_dual_port_RAM.sv \
                  $(TOPLEVEL_DIR)/rtl/mem/obi_ram_port.sv \
                  $(TOPLEVEL_DIR)/rtl/mem/obi_ram.sv \
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
                  $(TOPLEVEL_DIR)/rtl/core/hipv_core.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_decoder.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_arbiter.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_xbar.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_uart.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/uart_system.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/uart.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_timer.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/timer.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_gpio.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/gpio.sv \
                  $(TOPLEVEL_DIR)/rtl/top/hipv_soc.sv \
                  $(TOPLEVEL_DIR)/fpga/anvil/top.sv

# Small RAM keeps elaboration fast; the FPGA build uses the full 64 KiB.
COMPILE_ARGS += -GRAM_ADDR_WIDTH=10 -GINIT_FILE=\"$(INIT_FILE)\"

include $(TOPLEVEL_DIR)/tb/common/Makefile.include

$(INIT_FILE): gen_fw.py
	python3 gen_fw.py $@ $(RAM_WORDS)

$(SIM_BUILD)/Vtop.mk: $(INIT_FILE)

clean::
	@rm -f $(INIT_FILE)
